"use client";

// Shown only when the API answers 401 judge_key_required. Submitting stores the password
// (lib/judgeKey.ts) and the failed request is retried once by lib/api.ts judgedFetch.

import { useEffect, useId, useRef, useState } from "react";
import { onJudgeKeyRequest } from "@/lib/judgeKey";

export default function JudgeKeyGate() {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");
  const resolver = useRef<((key: string | null) => void) | null>(null);
  const uid = useId();
  const titleId = `${uid}-title`;
  const inputId = `${uid}-input`;

  useEffect(
    () =>
      onJudgeKeyRequest((resolve) => {
        resolver.current = resolve;
        setValue("");
        setOpen(true);
      }),
    [],
  );

  if (!open) return null;

  function close(key: string | null) {
    setOpen(false);
    const done = resolver.current;
    resolver.current = null;
    done?.(key);
  }

  return (
    <div className="judge-gate-backdrop">
      <form
        className="judge-gate"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onKeyDown={(e) => {
          if (e.key === "Escape") close(null);
        }}
        onSubmit={(e) => {
          e.preventDefault();
          const key = value.trim();
          if (key) close(key);
        }}
      >
        <h2 id={titleId}>Judge password</h2>
        <p className="muted small">This TrustLedger API is locked for judging. Enter the judge password to continue.</p>
        <label htmlFor={inputId}>Judge password</label>
        <input
          id={inputId}
          type="password"
          autoComplete="off"
          autoFocus
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
        <div className="judge-gate-actions">
          <button type="button" className="secondary" onClick={() => close(null)}>
            Cancel
          </button>
          <button type="submit" disabled={!value.trim()}>
            Continue
          </button>
        </div>
      </form>
    </div>
  );
}
