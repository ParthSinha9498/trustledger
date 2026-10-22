"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import s from "./story.module.css";

interface CardMeta {
  id: string;
  title: string;
  desc: string;
}

const CARDS: CardMeta[] = [
  { id: "hook", title: "One phone. One serial number. Two stores.", desc: "Only one of them is selling the real thing." },
  { id: "problem", title: "USD 467 billion in counterfeit goods", desc: "Up to 2.3% of world trade · Smartphones 12.9% lost (EUR 45.3B)" },
  { id: "gap", title: "Verification exists. Nobody uses it.", desc: "Optional · Separate from paying · Different for every brand" },
  { id: "idea", title: "Make authenticity a condition of payment.", desc: "Scan → Brand verifies → PayPal payment created" },
  { id: "how", title: "How it works: Data never moves", desc: "Two locked nodes · Questions in · Private aggregates out" },
  { id: "s1", title: "Scenario 1: Genuine phone at authorized store", desc: "The brand verifies it, then PayPal creates the payment." },
  { id: "s2", title: "Scenario 2: Serial outside supply chain", desc: "No verification, no payment." },
  { id: "s3", title: "Scenario 3: The brand investigates", desc: "An AI agent works only from privacy-protected aggregates." },
  { id: "business", title: "How does this pay for itself?", desc: "USD 150B+ a year on market insights · TrustLedger answers from verified purchases" },
  { id: "s4", title: "Scenario 4: Brand insights", desc: "Verified transaction insights with formal differential privacy." },
  { id: "guarantee", title: "Formal privacy guarantee", desc: "Every buyer protected across all of a brand's questions: zCDP ρ 0.25 ≈ ε 4.2" },
  { id: "levels", title: "One standard. Three integrations.", desc: "Brand API · PayPal checkout gate · Seller POS SDK via APIMatic" },
  { id: "close", title: "TrustLedger pitch close", desc: "Brands pay for insights; the checkout check is free for shoppers." },
  { id: "terminal", title: "AI Shopping Agent Terminal", desc: "Live MCP client verifyProduct execution and brand verdict" },
  { id: "code", title: "Checkout Integration Code", desc: "One call to verifyProduct before PayPal payment creation" },
  { id: "onboard", title: "One API. Every checkout.", desc: "OpenAPI → APIMatic (SDKs, portal, MCP) → Commerce ecosystem" },
  { id: "redteam", title: "220 of 220 attempts blocked", desc: "Best guesses were right 23% of the time, no better than chance" },
];

const DEFAULT_TERMINAL_LINES = [
  "────────────────────────────────────────────────────────────",
  "TrustLedger · AI agent → brand verification over MCP",
  "────────────────────────────────────────────────────────────",
  "",
  "[1] Connecting to MCP server http://localhost:3333/mcp",
  "    connected to trustledger-brand-verification v1.0.0",
  "",
  "[2] Discovering tools",
  "    • verifyProduct  Brand verification of a physical product at checkout…",
  "    • confirmSale    Mark a verified serial number as sold…",
  "",
  "[3] Calling verifyProduct",
  "    serial        X123",
  "    sku           NMB-P8-128",
  "    store_id      store_b",
  "    requested_at  2026-10-21T14:30:00.000Z",
  "",
  "[4] Brand verdict",
  "    result           ✘ NOT_VERIFIED",
  "    reason_code      NOT_IN_CHANNEL",
  "    verification_id  ver_mcp_09a1f48c",
  "",
  "    → Do not take payment: no PayPal order is created.",
];

function formatTerminalLine(line: string) {
  if (line.startsWith("───")) return <span className={s.termDim}>{line}</span>;
  if (/^\[\d\]/.test(line)) {
    const parts = line.match(/^(\[\d\])(.*)$/);
    return (
      <>
        <span className={s.termCyan}>{parts?.[1]}</span>
        <span style={{ fontWeight: 600 }}>{parts?.[2]}</span>
      </>
    );
  }
  if (line.includes("✘ NOT_VERIFIED")) {
    const [left] = line.split("✘ NOT_VERIFIED");
    return (
      <>
        <span>{left}</span>
        <span className={s.termRed}>✘ NOT_VERIFIED</span>
      </>
    );
  }
  if (line.includes("✔ VERIFIED")) {
    const [left] = line.split("✔ VERIFIED");
    return (
      <>
        <span>{left}</span>
        <span className={s.termGreen}>✔ VERIFIED</span>
      </>
    );
  }
  if (line.includes("→ Do not take payment")) {
    return <span className={s.termRed}>{line}</span>;
  }
  if (line.includes("→ Safe to create")) {
    return <span className={s.termGreen}>{line}</span>;
  }
  if (line.startsWith("    • ")) {
    return (
      <>
        <span className={s.termCyan}>    • </span>
        <span>{line.slice(6)}</span>
      </>
    );
  }
  return <span>{line}</span>;
}

function TerminalCard() {
  const [lines, setLines] = useState<string[]>([
    "# [Sample output of mcp/demo_agent_call.mjs]",
    "# Run 'node mcp/demo_agent_call.mjs' to stream live MCP verification.",
    "",
    ...DEFAULT_TERMINAL_LINES,
  ]);
  const streamIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    let active = true;

    // Direct-load readiness: show static sample block, mark ready after mount
    const readyTimer = setTimeout(() => {
      if (active && !(window as unknown as { __typedByRecorder?: boolean }).__typedByRecorder) {
        document.body.dataset.ready = "1";
      }
    }, 100);

    // Expose window.typeLines for the Playwright demo recorder
    (window as unknown as { typeLines?: (l: string[]) => void }).typeLines = (newLines: string[]) => {
      if (!active) return;
      (window as unknown as { __typedByRecorder?: boolean }).__typedByRecorder = true;
      clearTimeout(readyTimer);
      if (streamIntervalRef.current) {
        clearInterval(streamIntervalRef.current);
        streamIntervalRef.current = null;
      }
      delete document.body.dataset.ready;
      setLines([]);

      let i = 0;
      streamIntervalRef.current = setInterval(() => {
        if (!active) {
          if (streamIntervalRef.current) clearInterval(streamIntervalRef.current);
          return;
        }
        if (i < newLines.length) {
          setLines(newLines.slice(0, i + 1));
          i++;
        } else {
          if (streamIntervalRef.current) clearInterval(streamIntervalRef.current);
          streamIntervalRef.current = null;
          document.body.dataset.ready = "1";
        }
      }, 50);
    };

    return () => {
      active = false;
      clearTimeout(readyTimer);
      if (streamIntervalRef.current) {
        clearInterval(streamIntervalRef.current);
        streamIntervalRef.current = null;
      }
      delete (window as unknown as { typeLines?: unknown }).typeLines;
      delete (window as unknown as { __typedByRecorder?: unknown }).__typedByRecorder;
      delete document.body.dataset.ready;
    };
  }, []);

  return (
    <div className={s.terminalWindow}>
      <div className={s.terminalHeader}>
        <div className={s.terminalDots}>
          <span className={`${s.terminalDot} ${s.dotRed}`} />
          <span className={`${s.terminalDot} ${s.dotYellow}`} />
          <span className={`${s.terminalDot} ${s.dotGreen}`} />
        </div>
        <div className={s.terminalTitle}>AI shopping agent · MCP client</div>
        <div className={s.terminalRight} />
      </div>
      <div className={s.terminalBody}>
        {lines.map((l, idx) => (
          <div key={idx} className={s.terminalLine}>
            {formatTerminalLine(l)}
          </div>
        ))}
      </div>
    </div>
  );
}

interface ShowCodePayload {
  title?: string;
  language?: string;
  code: string;
  highlight?: number[];
}

const DEFAULT_CODE_PAYLOAD: ShowCodePayload = {
  title: "src/checkout.ts",
  language: "TypeScript",
  code: `import { verifyProduct } from "@trustledger/sdk";

// 1. Any checkout: verify serial with brand before payment
const verdict = await verifyProduct({
  serialNumber: item.serial,
  sku: item.sku,
  storeId: checkout.storeId,
});

// 2. Only genuine goods reach PayPal payment creation
if (verdict.status === "VERIFIED") {
  return await paypal.createOrder({
    ...orderData,
    custom_id: verdict.id,
  });
}

throw new Error(\`Authenticity check failed: \${verdict.reason}\`);`,
  highlight: [4, 5, 6, 7, 8, 11, 12, 13, 14],
};

function formatCodeLine(line: string) {
  if (line.trim().startsWith("//")) {
    return <span className={s.synComment}>{line}</span>;
  }
  let codePart = line;
  let commentPart = "";
  const commentIdx = line.indexOf("//");
  if (commentIdx !== -1) {
    codePart = line.slice(0, commentIdx);
    commentPart = line.slice(commentIdx);
  }

  const tokens = codePart.split(/(\b(?:import|from|const|let|var|await|async|function|return|if|else|throw|new)\b|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`|\b(?:VERIFIED|NOT_VERIFIED)\b|\b\d+\b)/g);

  return (
    <>
      {tokens.map((token, idx) => {
        if (!token) return null;
        if (/^(import|from|const|let|var|await|async|function|return|if|else|throw|new)$/.test(token)) {
          return <span key={idx} className={s.synKeyword}>{token}</span>;
        }
        if (/^(".*"|'.*'|`.*`)$/.test(token)) {
          return <span key={idx} className={s.synString}>{token}</span>;
        }
        if (/^(VERIFIED|NOT_VERIFIED)$/.test(token)) {
          return <span key={idx} className={s.synConst}>{token}</span>;
        }
        if (/^\d+$/.test(token)) {
          return <span key={idx} className={s.synNum}>{token}</span>;
        }
        return <span key={idx}>{token}</span>;
      })}
      {commentPart && <span className={s.synComment}>{commentPart}</span>}
    </>
  );
}

function CodeCard() {
  const [title, setTitle] = useState(DEFAULT_CODE_PAYLOAD.title || "src/checkout.ts");
  const [language, setLanguage] = useState(DEFAULT_CODE_PAYLOAD.language || "TypeScript");
  const [codeLines, setCodeLines] = useState<string[]>(DEFAULT_CODE_PAYLOAD.code.split("\n"));
  const [highlight, setHighlight] = useState<number[]>(DEFAULT_CODE_PAYLOAD.highlight || []);
  const streamIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    let active = true;

    // Direct-load readiness: mark ready after initial render
    const readyTimer = setTimeout(() => {
      if (active && !(window as unknown as { __codeTypedByRecorder?: boolean }).__codeTypedByRecorder) {
        document.body.dataset.ready = "1";
      }
    }, 100);

    // Expose window.showCode for demo recorder
    (window as unknown as { showCode?: (p: ShowCodePayload) => void }).showCode = (payload: ShowCodePayload) => {
      if (!active) return;
      (window as unknown as { __codeTypedByRecorder?: boolean }).__codeTypedByRecorder = true;
      clearTimeout(readyTimer);
      if (streamIntervalRef.current) {
        clearInterval(streamIntervalRef.current);
        streamIntervalRef.current = null;
      }
      delete document.body.dataset.ready;

      if (payload.title) setTitle(payload.title);
      if (payload.language) setLanguage(payload.language);
      setHighlight(payload.highlight || []);

      const allLines = payload.code.split("\n");
      setCodeLines([]);
      let i = 0;
      streamIntervalRef.current = setInterval(() => {
        if (!active) {
          if (streamIntervalRef.current) clearInterval(streamIntervalRef.current);
          return;
        }
        if (i < allLines.length) {
          setCodeLines(allLines.slice(0, i + 1));
          i++;
        } else {
          if (streamIntervalRef.current) clearInterval(streamIntervalRef.current);
          streamIntervalRef.current = null;
          document.body.dataset.ready = "1";
        }
      }, 45);
    };

    return () => {
      active = false;
      clearTimeout(readyTimer);
      if (streamIntervalRef.current) {
        clearInterval(streamIntervalRef.current);
        streamIntervalRef.current = null;
      }
      delete (window as unknown as { showCode?: unknown }).showCode;
      delete (window as unknown as { __codeTypedByRecorder?: unknown }).__codeTypedByRecorder;
      delete document.body.dataset.ready;
    };
  }, []);

  return (
    <div className={s.codeWindow}>
      <div className={s.codeHeader}>
        <div className={s.terminalDots}>
          <span className={`${s.terminalDot} ${s.dotRed}`} />
          <span className={`${s.terminalDot} ${s.dotYellow}`} />
          <span className={`${s.terminalDot} ${s.dotGreen}`} />
        </div>
        <div className={s.codeTab}>
          <span>📄</span>
          <span>{title}</span>
        </div>
        <div className={s.codeLangBadge}>{language}</div>
      </div>
      <div className={s.codeBody}>
        {codeLines.map((line, idx) => {
          const lineNum = idx + 1;
          const isHighlighted = highlight.includes(lineNum);
          return (
            <div
              key={idx}
              className={`${s.codeLine} ${isHighlighted ? s.codeLineHighlighted : ""}`}
            >
              <div className={s.codeGutter}>{lineNum}</div>
              <div className={s.codeText}>{formatCodeLine(line)}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function useCountUp(target: number, decimals: number = 0, duration: number = 1200) {
  const [val, setVal] = useState<number>(0);

  useEffect(() => {
    let start: number | null = null;
    let frame: number;

    const step = (now: number) => {
      if (!start) start = now;
      const progress = Math.min((now - start) / duration, 1);
      // ease-out cubic
      const ease = 1 - Math.pow(1 - progress, 3);
      setVal(ease * target);

      if (progress < 1) {
        frame = requestAnimationFrame(step);
      } else {
        setVal(target);
      }
    };

    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [target, duration]);

  return val.toFixed(decimals);
}

function CardView({ cardId }: { cardId: string }) {
  const actualCardId = cardId === "phones" ? "problem" : cardId;
  const problemVal = useCountUp(467, 0, 1200);
  const redteamVal = useCountUp(220, 0, 1200);

  useEffect(() => {
    if (actualCardId === "terminal") return;
    const timer = setTimeout(() => {
      document.body.dataset.ready = "1";
    }, 1250);

    return () => {
      clearTimeout(timer);
      delete document.body.dataset.ready;
    };
  }, [actualCardId]);

  return (
    <div className={s.storyContainer}>
      <div className={`${s.safeArea} ${s.fadeIn}`} key={actualCardId}>
        {actualCardId === "hook" && (
          <>
            <h1 className={s.titleHero}>One phone. One serial number. Two stores.</h1>
            <p className={s.subHero}>Only one of them is selling the real thing.</p>
          </>
        )}

        {actualCardId === "problem" && (
          <>
            <div className={s.statHuge}>USD {problemVal} billion</div>
            <div className={s.statLabel}>in counterfeit goods traded in a year</div>
            <div className={s.statGrid}>
              <div className={s.statPill}>up to 2.3% of world trade</div>
              <div className={s.statPill}>up to 4.7% of EU imports</div>
            </div>
            <p className={s.calloutText} style={{ marginBottom: 12 }}>
              Smartphones alone: 12.9% of sales lost, ≈ EUR 45.3 billion
            </p>
            <p className={s.calloutSub}>
              Hazardous fakes are rising: car parts, medicines, cosmetics, toys.
            </p>
            <div className={s.sourceFooter}>
              OECD / EUIPO (2025) · EUIPO / ITU smartphone sector study
            </div>
          </>
        )}

        {actualCardId === "gap" && (
          <>
            <h1 className={s.titleLarge}>Verification exists. Nobody uses it.</h1>
            <div className={s.gapCols}>
              <div className={s.gapCard}>
                <div className={s.gapIcon}>👁️</div>
                <div className={s.gapCardTitle}>Optional</div>
                <p className={s.gapCardDesc}>buyers must know it exists</p>
              </div>
              <div className={s.gapCard}>
                <div className={s.gapIcon}>⚡</div>
                <div className={s.gapCardTitle}>Separate from paying</div>
                <p className={s.gapCardDesc}>a lookup you do before, or never</p>
              </div>
              <div className={s.gapCard}>
                <div className={s.gapIcon}>🧩</div>
                <div className={s.gapCardTitle}>Different for every brand</div>
                <p className={s.gapCardDesc}>one app or website each</p>
              </div>
            </div>
          </>
        )}

        {actualCardId === "idea" && (
          <>
            <h1 className={s.titleLarge}>Make authenticity a condition of payment.</h1>
            <div className={s.diagramWrap}>
              <div className={s.diagramRow}>
                <div className={s.diagramNode}>Scan</div>
                <div className={s.diagramArrow}>→</div>
                <div className={s.diagramNode}>Brand verifies</div>
                <div className={s.diagramArrow}>→</div>
                <div className={`${s.diagramNode} ${s.nodeSuccess}`}>✓ PayPal payment created</div>
              </div>
              <div className={s.diagramRow}>
                <div className={`${s.diagramNode} ${s.nodeFail}`}>✕ Not verified</div>
                <div className={s.diagramArrow}>→</div>
                <div className={`${s.diagramNode} ${s.nodeFail}`}>No payment exists</div>
              </div>
            </div>
          </>
        )}

        {actualCardId === "how" && (
          <>
            <div className={`${s.badge} ${s.badgeBlue}`}>Architecture</div>
            <h1 className={s.titleLarge}>How it works: Data never moves</h1>
            <div className={s.nodeCardGrid}>
              <div className={s.nodeCard}>
                <div className={s.nodeCardHeader}>
                  <div className={s.nodeCardTitle}>Brand Node</div>
                  <span className={s.statPill} style={{ fontSize: 11 }}>Private DB</span>
                </div>
                <p className={s.calloutSub} style={{ margin: 0, textAlign: "left" }}>
                  Serials, batches, shipments, and checkout logs remain locked inside.
                </p>
                <div style={{ marginTop: "auto", fontSize: 13, color: "#38bdf8", fontWeight: 600 }}>
                  Answers: VERIFIED / NOT_VERIFIED
                </div>
              </div>

              <div className={`${s.nodeCard} ${s.nodeCardCenter}`}>
                <div style={{ fontSize: 24, color: "#38bdf8", fontWeight: 700 }}>
                  Questions in →<br />← Aggregates out
                </div>
                <p style={{ margin: "10px 0 0", fontSize: 13, color: "#94a3b8", lineHeight: 1.4 }}>
                  JSON query specs only (no SQL).<br />
                  <strong style={{ color: "#ffffff" }}>The AI agent never sees a raw record.</strong>
                </p>
              </div>

              <div className={s.nodeCard}>
                <div className={s.nodeCardHeader}>
                  <div className={s.nodeCardTitle}>PayPal Node</div>
                  <span className={s.statPill} style={{ fontSize: 11 }}>DP Boundary</span>
                </div>
                <p className={s.calloutSub} style={{ margin: 0, textAlign: "left" }}>
                  Transactions, keyed hashed buyer IDs, and demographics remain locked inside.
                </p>
                <div style={{ marginTop: "auto", fontSize: 13, color: "#34d399", fontWeight: 600 }}>
                  Answers: Noisy aggregates with ±95% CI
                </div>
              </div>
            </div>
            <div className={s.sourceFooter} style={{ marginTop: 24 }}>
              Zero raw buyer records leave a node · No person is identifiable
            </div>
          </>
        )}

        {actualCardId === "s1" && (
          <>
            <div className={`${s.badge} ${s.badgeBlue}`}>Scenario 1</div>
            <h1 className={s.titleHero}>A genuine phone at an authorized store</h1>
            <p className={s.subHero}>The brand verifies it, then PayPal creates the payment.</p>
          </>
        )}

        {actualCardId === "s2" && (
          <>
            <div className={`${s.badge} ${s.badgeRed}`}>Scenario 2</div>
            <h1 className={s.titleHero}>The same serial at a store outside the supply chain</h1>
            <p className={`${s.subHero} ${s.subRed}`}>No verification, no payment.</p>
          </>
        )}

        {actualCardId === "s3" && (
          <>
            <div className={`${s.badge} ${s.badgePurple}`}>Scenario 3</div>
            <h1 className={s.titleHero}>The brand investigates</h1>
            <p className={s.subHero}>An AI agent works only from privacy-protected aggregates.</p>
          </>
        )}

        {actualCardId === "business" && (
          <>
            <div className={`${s.badge} ${s.badgeTeal}`}>Business Model</div>
            <h1 className={s.titleHero}>How does this pay for itself?</h1>
            <div className={s.statHuge}>USD 150B+</div>
            <div className={s.statLabel}>a year spent on market insights (ESOMAR, 2024 data)</div>
            <p className={s.calloutText} style={{ marginTop: 18, marginBottom: 8 }}>
              Survey results take weeks, and in a 2024 Pew survey 18% of responses were flagged as bogus.
            </p>
            <p className={s.calloutSub} style={{ color: "#38bdf8", fontSize: 20, fontWeight: 700 }}>
              TrustLedger answers from verified purchases with mathematical differential privacy.
            </p>
          </>
        )}

        {actualCardId === "s4" && (
          <>
            <div className={`${s.badge} ${s.badgeTeal}`}>Scenario 4</div>
            <h1 className={s.titleHero}>Brand insights in seconds</h1>
            <p className={s.subHero}>Verified transaction analytics with formal differential privacy instead of waiting weeks.</p>
          </>
        )}

        {actualCardId === "guarantee" && (
          <>
            <div className={`${s.badge} ${s.badgeTeal}`}>Privacy Guarantee</div>
            <h1 className={s.titleLarge} style={{ marginBottom: 12 }}>Formal mathematical guarantee</h1>
            <p className={s.subHero} style={{ fontSize: 24, marginBottom: 20 }}>Every buyer protected across all of a brand&apos;s questions</p>
            <div className={s.guaranteeBox}>
              <div className={s.formulaHighlight}>zCDP ρ = 0.25 ≈ ε 4.2 (δ = 10⁻⁸)</div>
              <div style={{ display: "flex", gap: 16, flexWrap: "wrap", justifyContent: "center", fontSize: 15, color: "#cbd5e1" }}>
                <span>✓ Single privacy unit</span>
                <span>✓ OpenDP Gaussian noise (±95% CI)</span>
                <span>✓ Lifetime budget meter</span>
                <span>✓ Small groups hidden</span>
              </div>
            </div>
            <div className={s.sourceFooter} style={{ marginTop: 20 }}>
              Internal red-team: 11 attack types, none extracted a confident individual-level fact (evals/results/redteam_repeated.md)
            </div>
          </>
        )}

        {actualCardId === "levels" && (
          <>
            <div className={`${s.badge} ${s.badgeBlue}`}>Ecosystem</div>
            <h1 className={s.titleLarge}>One standard. Three simple integrations.</h1>
            <div className={s.levelsRow}>
              <div className={s.levelBox}>
                <div style={{ fontSize: 13, color: "#60a5fa", fontWeight: 700 }}>1. FOR BRANDS</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: "#ffffff" }}>Verification API</div>
                <p style={{ margin: 0, fontSize: 14, color: "#94a3b8", lineHeight: 1.45 }}>
                  Brand verification endpoint + local brand node holding serial inventory.
                </p>
              </div>

              <div className={s.levelBox}>
                <div style={{ fontSize: 13, color: "#34d399", fontWeight: 700 }}>2. FOR PAYPAL</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: "#ffffff" }}>Checkout Gate</div>
                <p style={{ margin: 0, fontSize: 14, color: "#94a3b8", lineHeight: 1.45 }}>
                  Creates payment only on brand verification. Binds verification ID in custom_id.
                </p>
              </div>

              <div className={`${s.levelBox} ${s.levelBoxHighlight}`}>
                <div style={{ fontSize: 13, color: "#38bdf8", fontWeight: 700 }}>3. FOR SELLERS / POS</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: "#ffffff" }}>One SDK Call</div>
                <p style={{ margin: 0, fontSize: 14, color: "#94a3b8", lineHeight: 1.45 }}>
                  Single verifyProduct call at scan. SDK generated from OpenAPI spec by APIMatic.
                </p>
              </div>
            </div>
            <div className={s.sourceFooter} style={{ marginTop: 24 }}>
              Self-sustaining model: brands pay for insights, checkout verification is free for shoppers
            </div>
          </>
        )}

        {actualCardId === "redteam" && (
          <>
            <div className={`${s.badge} ${s.badgeTeal}`}>Privacy Layer</div>
            <div className={s.statHuge}>{redteamVal} of 220</div>
            <div className={s.statLabel}>re-identification attempts blocked</div>
            <p className={s.calloutText}>
              Best guesses were right 23% of the time, no better than chance
            </p>
            <div className={s.sourceFooter}>
              20 runs × 11 scripted attacks: small cells, differencing, membership, cross-node linkage, averaging, budget probing · evals/redteam.py --repeat 20
            </div>
          </>
        )}

        {actualCardId === "s5" && (
          <>
            <div className={`${s.badge} ${s.badgeBlue}`}>Scenario 5</div>
            <h1 className={s.titleHero}>An AI shopping agent checks before it pays</h1>
            <p className={s.subHero}>Brand verification over MCP: the same check, for agents</p>
          </>
        )}

        {actualCardId === "terminal" && (
          <TerminalCard />
        )}

        {actualCardId === "code" && (
          <CodeCard />
        )}

        {actualCardId === "onboard" && (
          <>
            <h1 className={s.titleLarge}>One API. Every checkout.</h1>
            <div className={s.pipelineWrap}>
              <div className={s.pipelineStage}>
                <div className={s.stageTitle}>Brand Verification API</div>
                <div className={s.stageSub}>OpenAPI 3.1 Specification</div>
              </div>
              <div className={s.diagramArrow}>→</div>
              <div className={`${s.pipelineStage} ${s.stageHighlight}`}>
                <div className={s.stageTitle}>APIMatic</div>
                <div className={s.stageSub}>SDKs · Docs Portal · MCP Server</div>
                <div className={s.stageSubContext}>PayPal Server SDK via Context Plugin</div>
              </div>
              <div className={s.diagramArrow}>→</div>
              <div className={s.pipelineStage}>
                <div className={s.stageTitle}>Commerce Ecosystem</div>
                <div className={s.stageSub}>POS · E-commerce · AI shopping agents</div>
              </div>
            </div>
            <div className={s.sourceFooter}>
              MCP server via APIMatic&apos;s MCP generator (alpha)
            </div>
          </>
        )}

        {actualCardId === "close" && (
          <div className={s.closeWrap}>
            <div className={`${s.closeLine} ${s.line1}`}>Brands pay for insights; the checkout check is free for shoppers.</div>
            <div className={`${s.closeLine} ${s.line2}`}>Trust for buyers · Intelligence for brands.</div>
            <div className={`${s.closeLine} ${s.line3}`}>A more trusted network for PayPal.</div>
            <div className={s.brandFooter}>
              <div className={s.brandWordmark}>
                <span className={s.brandDiamond} aria-hidden>◆</span>
                TrustLedger
              </div>
              <div className={s.techStrip}>
                Built with PayPal Server SDK (APIMatic) · AG Grid · Bryntum · OpenDP · Render
              </div>
              <div className={s.repoLink}>github.com/ParthSinha9498/trustledger</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StoryIndex() {
  return (
    <div className={s.indexContainer}>
      <div className={s.indexHeader}>
        <h1 className={s.indexTitle}>TrustLedger Pitch Storyboard</h1>
        <p className={s.indexSubtitle}>
          Full-screen presentation cards designed for the video demo and judges review (1280×720)
        </p>
      </div>

      <div className={s.indexGrid}>
        {CARDS.map((c, i) => (
          <Link key={c.id} href={`/story?card=${c.id}`} className={s.indexCard}>
            <div className={s.indexCardTop}>
              <div className={s.indexCardId}>Card {i + 1} · {c.id}</div>
              <div className={s.indexCardTitle}>{c.title}</div>
            </div>
            <p className={s.indexCardDesc}>{c.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}

function StoryContent() {
  const searchParams = useSearchParams();
  const card = searchParams.get("card");

  if (card && (CARDS.some((c) => c.id === card) || card === "phones")) {
    return <CardView cardId={card} />;
  }

  return <StoryIndex />;
}

export default function StoryPage() {
  return (
    <Suspense fallback={<div className={s.storyContainer}><div className={s.safeArea}><p>Loading story card…</p></div></div>}>
      <StoryContent />
    </Suspense>
  );
}
