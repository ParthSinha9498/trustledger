"use client";

import { useEffect, useState } from "react";
import { API } from "@/lib/api";

export default function ColdStartNotice() {
  const [waking, setWaking] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    let cancelled = false;

    const checkHealth = async () => {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 2000);
        const res = await fetch(`${API}/health`, { signal: controller.signal, cache: "no-store" });
        clearTimeout(timeoutId);
        if (res.ok) {
          if (waking) {
            setReady(true);
            setTimeout(() => {
              if (!cancelled) {
                setWaking(false);
                setReady(false);
              }
            }, 2000);
          }
          return;
        }
      } catch {
        // Backend is sleeping / cold start in progress
      }

      if (!cancelled) {
        setWaking(true);
        timer = setTimeout(checkHealth, 3000);
      }
    };

    const initTimer = setTimeout(checkHealth, 300);

    return () => {
      cancelled = true;
      clearTimeout(timer);
      clearTimeout(initTimer);
    };
  }, [waking]);

  if (!waking && !ready) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 9999,
        pointerEvents: "none",
        background: ready
          ? "rgba(16, 185, 129, 0.95)"
          : "rgba(15, 23, 42, 0.92)",
        backdropFilter: "blur(8px)",
        borderBottom: `1px solid ${ready ? "#059669" : "rgba(255, 255, 255, 0.15)"}`,
        color: "#ffffff",
        padding: "8px 16px",
        fontSize: "13px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "10px",
        boxShadow: "0 4px 12px rgba(0, 0, 0, 0.3)",
        transition: "all 0.3s ease",
      }}
    >
      {ready ? (
        <>
          <span style={{ fontSize: "15px" }}>✓</span>
          <span>Demo backend is awake and ready.</span>
        </>
      ) : (
        <>
          <span
            style={{
              display: "inline-block",
              width: "12px",
              height: "12px",
              borderRadius: "50%",
              border: "2px solid rgba(255, 255, 255, 0.3)",
              borderTopColor: "#38bdf8",
              animation: "spin 1s linear infinite",
            }}
          />
          <style>{`@keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
          <span>
            <strong>Waking the demo (~1 min)</strong> — backend container is spinning up on Render free tier.
          </span>
        </>
      )}
    </div>
  );
}
