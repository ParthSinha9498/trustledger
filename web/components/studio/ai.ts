// The Studio agents. Primary: our own "Insights analyst" (Studio's loop, our adapter, our tools). It
// answers from the private release and hands widget building to Studio's built-in page and widget
// agents through delegate_to. Every model call goes through POST /ai/turn on our API (the server picks
// the model, holds the key and refuses buyer-level fields).
//
// What can reach the model: the questions, tool schemas, Studio's schema/page/widget views, and the
// results of query_release / privacy_budget. Studio's data sources hold only release cells (noisy,
// small groups hidden) and exact brand counts, so no buyer row exists anywhere it could read.
// No agent here has execute_query (the built-in data agent is left out, and the tool is filtered).

import {
  createAiHarness,
  directLlmRunner,
  type AgAiHarnessSetup,
  type AgAiParamsBuilder,
  type AgAiToolContext,
  type AgAiPromptStarter,
  type AgAiTool,
  type AgAnyAiAgentDefinition,
} from 'ag-studio';
import { createChatCompletionsAdapter } from './chatCompletionsAdapter';
import { queryRelease, tableCatalogue, type Names, type QueryRow, type ReleaseCells } from './data';

export const PROMPT_STARTERS: AgAiPromptStarter[] = [
  {
    label: 'Who buys the P8 128GB?',
    prompt: 'Which age bands buy the Nimbus P8 128GB the most? Give the estimates with their 95% intervals.',
  },
  {
    label: 'Spend by store',
    prompt: 'Which store has the highest total spend, and is the difference to the next store bigger than the uncertainty?',
  },
  {
    label: 'Chart buyers by week',
    prompt: 'Add an Estimate widget to this page showing weekly buyers of the Nimbus P8 128GB across all stores.',
  },
];

const NO_DATA_QUERY = new Set(['execute_query']);
const withoutDataQuery = (tools: AgAiTool[]) => tools.filter((t) => !NO_DATA_QUERY.has(t.name));

function table(rows: QueryRow[], limit = 50): string {
  if (!rows.length) return '(no rows)';
  const cols = Object.keys(rows[0]);
  const cell = (v: unknown) => (v == null ? 'hidden' : String(v));
  const head = `| ${cols.join(' | ')} |\n|${cols.map(() => '---').join('|')}|`;
  const body = rows.slice(0, limit).map((r) => `| ${cols.map((c) => cell(r[c])).join(' | ')} |`).join('\n');
  return `${head}\n${body}${rows.length > limit ? `\n(${rows.length - limit} more rows not shown; filter or group more coarsely)` : ''}`;
}

export interface AnalystDeps {
  cells: ReleaseCells;
  names: Names;
  apiBase: string;
  /** fetch used for /ai/turn (wrapped by the page to detect mock answers). */
  fetch?: typeof fetch;
}

function analystInstructions(cells: ReleaseCells): string {
  return `You are the TrustLedger Insights analyst for the brand Nimbus. You answer business questions about buyers
WITHOUT ever seeing a buyer: you only have a one-time differentially private release (tables M1-M6: noisy
estimates, small groups hidden) and exact brand counts about stores and products (tables B1-B5).

Tables:
${tableCatalogue(cells)}

How to answer:
1. Call query_release with ONE table, the dimensions to group by and optional filters. Pick the table whose
   dimensions match the question exactly (e.g. age band by product -> M2; spend -> M4 or M6; weekly -> M1 or M5).
2. Report every noisy number with its 95% interval written as "95% interval (±) N". Say when an interval is wide
   compared with a difference, and say when a total leaves out hidden small groups.
3. Never claim anything about an individual person; never invent numbers; never combine tables.
4. If asked to show or chart something, delegate to the page agent to add an "estimate" widget, then to the
   widget agent to configure it (value = sum(<table>.value), interval = <table>_interval, hidden = sum(<table>.hiddenGroups)).
5. Keep answers short and plain. Call privacy_budget only when asked about privacy budget or cost.
This release spent rho ${cells.rho_spent} once (about epsilon ${cells.epsilon} at delta ${cells.delta ?? '1e-8'}); answering from it spends nothing more.`;
}

export function buildAi(deps: AnalystDeps): AgAiHarnessSetup {
  const adapter = createChatCompletionsAdapter({ endpoint: `${deps.apiBase}/ai/turn`, fetch: deps.fetch });
  const tableIds = [...deps.cells.marginals, ...deps.cells.brand_counts].map((t) => t.id);

  return ({ api }) => {
    const queryTool = api.defineAiTool({
      name: 'query_release',
      description:
        'Read the private release (M1-M6, noisy, with 95% intervals) or an exact brand count table (B1-B5): ' +
        'group one table by some of its dimensions with optional equality filters. Spends no privacy budget.',
      params: (s: AgAiParamsBuilder) =>
        s.object({
          table: s.enum(tableIds, { description: 'One table id.' }),
          group_by: s.array(s.string(), { description: 'Dimension field ids of that table, e.g. ["ageBand"]. Empty for one total.' }),
          filters: s
            .record(s.string(), s.string(), { description: 'Equality filters on dimensions, by display value, e.g. {"product": "Nimbus P8 128GB"}.' })
            .optional(),
        }),
      execute: (args: { table: string; group_by: string[]; filters?: Record<string, string> }, ctx: AgAiToolContext) => {
        const res = queryRelease(deps.cells, deps.names, args.table, args.group_by ?? [], args.filters ?? {});
        if ('error' in res) return ctx.error(res.error);
        const note =
          res.kind === 'estimate'
            ? 'Noisy estimates. buyers_interval_95 is the 95% interval (±) of each total; "hidden" = every cell in that group was a hidden small group; hidden_small_groups counts cells left out of a total.'
            : 'Exact counts from the brand (stores and products, not people).';
        return ctx.success(`${res.table}: ${note}\n\n${table(res.rows)}`);
      },
    } as never);

    const budgetTool = api.defineAiTool({
      name: 'privacy_budget',
      description: "The brand's privacy budget (zCDP rho): total, spent by the one-time release, remaining.",
      params: (s: AgAiParamsBuilder) => s.object({}),
      execute: async (_args: unknown, ctx: AgAiToolContext) => {
        try {
          const r = await fetch(`${deps.apiBase}/console/budget`, { signal: ctx.signal });
          if (!r.ok) return ctx.error(`budget unavailable (HTTP ${r.status})`);
          const b = (await r.json()) as Record<string, unknown>;
          return ctx.success(
            `rho total ${b.total}, spent ${b.spent} (the one-time release used ${b.release_rho}), remaining ${b.remaining}; ` +
              `about epsilon ${b.eps_equivalent_total} in total at delta 1e-8. ${b.guarantee ?? ''}`,
          );
        } catch (e) {
          return ctx.error(`budget unavailable: ${e instanceof Error ? e.message : String(e)}`);
        }
      },
    } as never);

    return createAiHarness(api, ({ builtIn, tools: harnessTools }) => {
      const insights = directLlmRunner({
        id: 'insights',
        name: 'Insights analyst',
        description: 'Answers questions about buyers from the private release, and asks the page and widget agents to build widgets.',
        instructions: () => analystInstructions(deps.cells),
        tools: ({ studio }) => [queryTool, budgetTool, studio.viewSchema(), studio.viewPage(), harnessTools.delegateTo(['page', 'widget'])],
        maxTurns: 6,
        adapter,
      });
      // Studio's own agents, unchanged except: no execute_query (defensive; neither has it today), fewer rounds.
      const delegate = (def: AgAnyAiAgentDefinition, maxTurns: number) =>
        directLlmRunner({
          ...def,
          tools: (ctx, params) => withoutDataQuery(def.tools?.(ctx, params) ?? []),
          maxTurns,
          adapter,
        });
      return {
        agents: [insights, delegate(builtIn.page, 6), delegate(builtIn.widget, 6)],
        primary: 'insights',
        promptStarters: PROMPT_STARTERS,
      };
    });
  };
}
