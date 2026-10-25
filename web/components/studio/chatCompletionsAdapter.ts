/**
 * AG Studio LLM adapter for OpenAI-compatible **Chat Completions** endpoints.
 *
 * Studio's reference adapter speaks the OpenAI Responses API, which our providers (Groq, Gemini's
 * OpenAI-compatible endpoint) don't reliably support. This one maps an AgLlmRequest to a Chat Completions
 * body and the streamed `chat.completion.chunk`s back to Studio events.
 *
 * It posts to OUR backend (`POST /ai/turn`), never to a provider: the server picks the model from its own
 * allowlist, injects the key, caps tokens and refuses requests that name buyer-level fields. So no key or
 * model lives here; `request.model` is ignored on purpose.
 */
import type {
    AgAiConversationItem,
    AgAiEvent,
    AgAiOutputItem,
    AgAiToolSchema,
    AgAiUsage,
    AgLlmAdapter,
    AgLlmExecuteTurnOptions,
    AgLlmRequest,
    AgLlmResponse,
    AgLlmResponseHandler,
} from 'ag-studio';

export interface ChatCompletionsAdapterOptions {
    /** Full URL of the turn endpoint, e.g. `${NEXT_PUBLIC_API_URL}/ai/turn`. */
    endpoint: string;
    /** Extra request headers (no secrets: this runs in the browser). */
    headers?: Record<string, string>;
    /** For tests. Defaults to the global fetch. */
    fetch?: typeof fetch;
}

type Json = Record<string, unknown>;

/** Error thrown for a failed turn. `code` is the server's code (e.g. `waiting_capacity`, `BUYER_FIELDS`). */
export class ChatTurnError extends Error {
    constructor(
        message: string,
        readonly code: string,
        readonly status?: number,
        readonly retryAfter?: number
    ) {
        super(message);
        this.name = 'ChatTurnError';
    }
}

// =============================================================================
// JSON Schema clean-up (Shape emits 2020-12; OpenAI-compatible providers accept a subset)
// =============================================================================

function isObj(v: unknown): v is Json {
    return typeof v === 'object' && v !== null && !Array.isArray(v);
}

/** Shape's "undefined" sentinel inside anyOf: `{ not: {} }`. */
function isUndefinedSentinel(s: unknown): boolean {
    return isObj(s) && Object.keys(s).length === 1 && isObj(s.not) && Object.keys(s.not).length === 0;
}

/** Inline local `$ref`s (depth-capped for recursive defs), drop sentinels/meta keys, `const` -> `enum`. */
export function cleanSchema(schema: unknown, defs: Json = {}, depth = 0): unknown {
    if (Array.isArray(schema)) return schema.map((s) => cleanSchema(s, defs, depth));
    if (!isObj(schema)) return schema;
    const localDefs = isObj(schema.$defs) ? { ...defs, ...schema.$defs } : defs;
    if (typeof schema.$ref === 'string') {
        const name = schema.$ref.replace(/^#\/\$defs\//, '');
        const target = localDefs[name];
        const { $ref: _ref, ...siblings } = schema;
        if (!isObj(target) || depth > 6) return { type: 'object', ...cleanSiblings(siblings) };
        return cleanSchema({ ...target, ...siblings }, localDefs, depth + 1);
    }
    const out: Json = {};
    for (const [k, v] of Object.entries(schema)) {
        if (k === '$defs' || k === '$schema' || k === '$id') continue;
        if (k === 'const') {
            out.enum = [v];
            continue;
        }
        if (k === 'anyOf' && Array.isArray(v)) {
            const kept = v.filter((b) => !isUndefinedSentinel(b)).map((b) => cleanSchema(b, localDefs, depth));
            if (kept.length === 1 && isObj(kept[0])) Object.assign(out, kept[0]);
            else if (kept.length) out.anyOf = kept;
            continue;
        }
        out[k] = k === 'properties' && isObj(v)
            ? Object.fromEntries(Object.entries(v).map(([p, s]) => [p, cleanSchema(s, localDefs, depth)]))
            : cleanSchema(v, localDefs, depth);
    }
    return out;
}

function cleanSiblings(s: Json): Json {
    const { description } = s;
    return typeof description === 'string' ? { description } : {};
}

// =============================================================================
// Encoding: AgLlmRequest -> Chat Completions body
// =============================================================================

type ChatMessage = Json & { role: string };

function textOf(parts: { type: string; text?: string; refusal?: string }[]): string {
    return parts.map((p) => (p.type === 'text' ? p.text ?? '' : p.type === 'refusal' ? p.refusal ?? '' : '')).join('');
}

export function encodeMessages(input: AgAiConversationItem[], instructions?: string): ChatMessage[] {
    const msgs: ChatMessage[] = [];
    if (instructions) msgs.push({ role: 'system', content: instructions });
    for (const item of input) {
        if (item.type === 'message' && item.kind === 'input') {
            const hasImage = item.content.some((c) => c.type === 'image' && c.imageUrl);
            const content = hasImage
                ? item.content.flatMap((c): Json[] =>
                      c.type === 'text'
                          ? [{ type: 'text', text: c.text }]
                          : c.type === 'image' && c.imageUrl
                            ? [{ type: 'image_url', image_url: { url: c.imageUrl, detail: c.detail } }]
                            : []
                  )
                : item.content.map((c) => (c.type === 'text' ? c.text : '')).join('');
            msgs.push({ role: item.role, content });
        } else if (item.type === 'message' && item.kind === 'output') {
            msgs.push({ role: 'assistant', content: textOf(item.content) });
        } else if (item.type === 'function_call') {
            const call = {
                id: item.callId,
                type: 'function',
                function: { name: item.name, arguments: item.arguments || '{}' },
            };
            const last = msgs[msgs.length - 1];
            // Parallel calls (and text said before them) belong to one assistant message.
            if (last?.role === 'assistant') {
                last.tool_calls = [...((last.tool_calls as unknown[]) ?? []), call];
            } else {
                msgs.push({ role: 'assistant', content: null, tool_calls: [call] });
            }
        } else if (item.type === 'function_call_output') {
            msgs.push({ role: 'tool', tool_call_id: item.callId, content: item.output });
        }
        // Reasoning items are not sent back: Chat Completions has no input form for them.
    }
    return msgs;
}

export function encodeRequest(request: AgLlmRequest): Json {
    const tools = (request.tools ?? [])
        .filter((t: AgAiToolSchema) => t.kind !== 'provided')
        .map((t: AgAiToolSchema) => ({
            type: 'function',
            function: { name: t.name, description: t.description, parameters: cleanSchema(t.parameters) },
        }));
    const body: Json = { messages: encodeMessages(request.input, request.instructions), stream: true };
    if (tools.length) {
        body.tools = tools;
        const tc = request.toolChoice;
        if (tc) body.tool_choice = typeof tc === 'string' ? tc : { type: 'function', function: { name: tc.name } };
    }
    const rf = request.responseFormat;
    if (rf?.type === 'json') {
        body.response_format = {
            type: 'json_schema',
            json_schema: { name: rf.name, description: rf.description, schema: cleanSchema(rf.schema), strict: false },
        };
    }
    return body;
}

// =============================================================================
// Decoding: chat.completion.chunk stream -> Studio events + final response
// =============================================================================

let seq = 0;
const newId = (p: string) => `${p}_${Date.now().toString(36)}${(seq++).toString(36)}`;

interface OpenCall {
    id: string;
    name: string;
    args: string;
    started: boolean;
}

/** Stateful translator: feed it each parsed chunk, then `finish()` once the stream ends. */
export class ChunkTranslator {
    private textId?: string;
    private text = '';
    private reasoningId?: string;
    private reasoningOpen = false;
    private reasoning = '';
    private calls = new Map<number, OpenCall>();
    private finishReason?: string;
    private usage?: AgAiUsage;
    private model?: string;
    private responseId?: string;
    private sawAny = false;
    private textClosed = false;
    error?: ChatTurnError;

    push(chunk: Json): AgAiEvent[] {
        const ev: AgAiEvent[] = [];
        if (isObj(chunk.error)) {
            const e = chunk.error;
            this.error ??= new ChatTurnError(String(e.message ?? 'provider error'), String(e.code ?? 'api_error'));
            return ev;
        }
        this.sawAny = true;
        if (typeof chunk.id === 'string') this.responseId ??= chunk.id;
        if (typeof chunk.model === 'string') this.model ??= chunk.model;
        if (isObj(chunk.usage)) {
            const u = chunk.usage;
            const details = isObj(u.prompt_tokens_details) ? u.prompt_tokens_details : {};
            this.usage = {
                inputTokens: Number(u.prompt_tokens ?? 0),
                outputTokens: Number(u.completion_tokens ?? 0),
                totalTokens: u.total_tokens == null ? undefined : Number(u.total_tokens),
                cachedInputTokens: details.cached_tokens == null ? undefined : Number(details.cached_tokens),
            };
        }
        const choices = Array.isArray(chunk.choices) ? (chunk.choices as Json[]) : [];
        const choice = choices.find((c) => (c.index ?? 0) === 0) ?? choices[0];
        if (!choice) return ev;
        const delta = isObj(choice.delta) ? choice.delta : {};

        const reasoning = delta.reasoning_content ?? delta.reasoning;
        if (typeof reasoning === 'string' && reasoning) {
            if (!this.reasoningOpen) {
                this.reasoningId = newId('rs');
                this.reasoningOpen = true;
                ev.push({ type: 'REASONING_MESSAGE_START', messageId: this.reasoningId, role: 'reasoning' });
            }
            this.reasoning += reasoning;
            ev.push({ type: 'REASONING_MESSAGE_CONTENT', messageId: this.reasoningId!, delta: reasoning });
        }

        if (typeof delta.content === 'string' && delta.content && !this.textClosed) {
            ev.push(...this.closeReasoning());
            if (!this.textId) {
                this.textId = newId('msg');
                ev.push({ type: 'TEXT_MESSAGE_START', messageId: this.textId, role: 'assistant' });
            }
            this.text += delta.content;
            ev.push({ type: 'TEXT_MESSAGE_CONTENT', messageId: this.textId, delta: delta.content });
        }

        if (Array.isArray(delta.tool_calls)) {
            ev.push(...this.closeReasoning(), ...this.closeText());
            (delta.tool_calls as Json[]).forEach((tc, pos) => {
                const index = typeof tc.index === 'number' ? tc.index : pos;
                const fn = isObj(tc.function) ? tc.function : {};
                let call = this.calls.get(index);
                if (!call) {
                    call = { id: typeof tc.id === 'string' && tc.id ? tc.id : newId('call'), name: '', args: '', started: false };
                    this.calls.set(index, call);
                }
                if (typeof fn.name === 'string' && fn.name) call.name += call.started ? '' : fn.name;
                if (!call.started && call.name) {
                    call.started = true;
                    ev.push({ type: 'TOOL_CALL_START', toolCallId: call.id, toolCallName: call.name });
                    if (call.args) ev.push({ type: 'TOOL_CALL_ARGS', toolCallId: call.id, delta: call.args });
                }
                const args = typeof fn.arguments === 'string' ? fn.arguments : isObj(fn.arguments) ? JSON.stringify(fn.arguments) : '';
                if (args) {
                    call.args += args;
                    if (call.started) ev.push({ type: 'TOOL_CALL_ARGS', toolCallId: call.id, delta: args });
                }
            });
        }

        if (typeof choice.finish_reason === 'string') this.finishReason = choice.finish_reason;
        return ev;
    }

    private closeText(): AgAiEvent[] {
        if (!this.textId || this.textClosed) return [];
        this.textClosed = true;
        return [{ type: 'TEXT_MESSAGE_END', messageId: this.textId }];
    }

    private closeReasoning(): AgAiEvent[] {
        if (!this.reasoningOpen) return [];
        this.reasoningOpen = false;
        return [{ type: 'REASONING_MESSAGE_END', messageId: this.reasoningId! }];
    }

    /** Close open items. Returns the closing events and the final response (or sets `error`). */
    finish(): { events: AgAiEvent[]; response?: AgLlmResponse } {
        const events = [...this.closeReasoning(), ...this.closeText()];
        for (const call of this.calls.values()) {
            if (call.started) events.push({ type: 'TOOL_CALL_END', toolCallId: call.id });
        }
        if (this.error) return { events };
        if (!this.sawAny) {
            this.error = new ChatTurnError('The model stream ended without any output.', 'empty_stream');
            return { events };
        }
        if (this.finishReason === 'length' || this.finishReason === 'content_filter') {
            const reason = this.finishReason === 'length' ? 'max_output_tokens' : 'content_filter';
            this.error = new ChatTurnError(`The model stopped early (${reason}).`, reason);
            return { events };
        }
        const output: AgAiOutputItem[] = [];
        if (this.reasoning) {
            output.push({
                id: this.reasoningId ?? newId('rs'),
                kind: 'output',
                type: 'reasoning',
                summary: [],
                content: [{ type: 'text', text: this.reasoning }],
            });
        }
        if (this.text) {
            output.push({
                id: this.textId!,
                kind: 'output',
                type: 'message',
                role: 'assistant',
                status: 'completed',
                content: [{ type: 'text', text: this.text, annotations: [] }],
            });
        }
        for (const call of this.calls.values()) {
            output.push({
                id: call.id,
                kind: 'output',
                type: 'function_call',
                callId: call.id,
                name: call.name,
                arguments: call.args || '{}',
                status: 'completed',
            });
        }
        return {
            events,
            response: {
                id: this.responseId ?? newId('resp'),
                createdAt: Date.now(),
                output,
                status: 'completed',
                usage: this.usage,
                model: this.model,
            },
        };
    }
}

/** Split an SSE byte stream into `data:` payloads (handles frames split across reads). */
export async function* sseData(body: ReadableStream<Uint8Array>): AsyncGenerator<string> {
    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    try {
        while (true) {
            const { done, value } = await reader.read();
            buffer += done ? decoder.decode() : decoder.decode(value, { stream: true });
            const frames = buffer.split(/\r?\n\r?\n/);
            buffer = done ? '' : frames.pop() ?? '';
            for (const frame of frames) {
                const data = frame
                    .split(/\r?\n/)
                    .filter((l) => l.startsWith('data:'))
                    .map((l) => l.slice(5).replace(/^ /, ''))
                    .join('\n');
                if (data) yield data;
            }
            if (done) return;
        }
    } finally {
        reader.releaseLock();
    }
}

async function errorFrom(res: Response): Promise<ChatTurnError> {
    const raw = await res.text().catch(() => '');
    let body: Json = {};
    try {
        body = JSON.parse(raw);
    } catch {
        /* not JSON */
    }
    // FastAPI errors: {detail: str | {refused, detail}}; provider/our proxy errors: {error: {code, message}}.
    const err = isObj(body.error) ? body.error : isObj(body.detail) ? body.detail : {};
    const code = String(err.code ?? err.refused ?? `http_${res.status}`);
    const message = String(err.message ?? err.detail ?? (typeof body.detail === 'string' ? body.detail : raw) ?? res.statusText);
    const retry = Number(err.retry_after ?? res.headers.get('Retry-After') ?? NaN);
    return new ChatTurnError(message || `HTTP ${res.status}`, code, res.status, Number.isFinite(retry) ? retry : undefined);
}

// =============================================================================
// Adapter
// =============================================================================

function runTurn(opts: ChatCompletionsAdapterOptions, request: AgLlmRequest, options?: AgLlmExecuteTurnOptions): AgLlmResponseHandler {
    const doFetch = opts.fetch ?? fetch;
    const translator = new ChunkTranslator();
    let resolveComplete!: (r: AgLlmResponse) => void;
    let rejectComplete!: (e: Error) => void;
    const complete = new Promise<AgLlmResponse>((res, rej) => {
        resolveComplete = res;
        rejectComplete = rej;
    });
    // Mark observed: a consumer that abandons the stream may never await `complete`.
    void complete.catch(() => {});

    async function* events(): AsyncGenerator<AgAiEvent> {
        let failure: Error | undefined;
        let response: AgLlmResponse | undefined;
        try {
            const res = await doFetch(opts.endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream', ...opts.headers },
                body: JSON.stringify(encodeRequest(request)),
                signal: options?.signal,
            });
            if (!res.ok || !res.body) throw await errorFrom(res);
            for await (const data of sseData(res.body)) {
                if (data === '[DONE]') break;
                let chunk: Json;
                try {
                    chunk = JSON.parse(data);
                } catch {
                    continue; // keep-alives and comments
                }
                yield* translator.push(chunk);
                if (translator.error) break;
            }
            const done = translator.finish();
            yield* done.events;
            failure = translator.error;
            response = done.response;
        } catch (e) {
            failure = e instanceof Error ? e : new Error(String(e));
        }
        if (failure) rejectComplete(failure);
        else resolveComplete(response!);
    }

    const it = events();
    return { stream: { [Symbol.asyncIterator]: () => it }, complete };
}

export function createChatCompletionsAdapter(opts: ChatCompletionsAdapterOptions): AgLlmAdapter {
    return { executeTurn: (request, options) => runTurn(opts, request, options) };
}
