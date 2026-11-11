// Judge password: stored once in this browser (localStorage, best effort) and sent as X-Judge-Key.
// Storage can be unavailable (private windows, blocked site data), so every access is guarded.

export const JUDGE_KEY_NAME = "tl_judge_key";

export function getJudgeKey(): string | null {
  try {
    return window.localStorage.getItem(JUDGE_KEY_NAME);
  } catch {
    return null;
  }
}

export function setJudgeKey(key: string | null): void {
  try {
    if (key) window.localStorage.setItem(JUDGE_KEY_NAME, key);
    else window.localStorage.removeItem(JUDGE_KEY_NAME);
  } catch {
    /* storage unavailable: the key is only kept for this retry */
  }
}

// The gate component registers itself; requests share one open prompt.
type Handler = (resolve: (key: string | null) => void) => void;
let handler: Handler | null = null;
let inflight: Promise<string | null> | null = null;

export function onJudgeKeyRequest(fn: Handler): () => void {
  handler = fn;
  return () => {
    if (handler === fn) handler = null;
  };
}

/** Asks the user for the judge password. Resolves null when cancelled or no prompt is mounted. */
export function requestJudgeKey(): Promise<string | null> {
  if (inflight) return inflight;
  if (!handler) return Promise.resolve(null);
  inflight = new Promise<string | null>((resolve) => {
    handler?.((key) => {
      inflight = null;
      resolve(key);
    });
  });
  return inflight;
}
