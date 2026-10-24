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
  { id: "gap", title: "Verification exists. Most buyers skip it.", desc: "Optional · Separate from paying · Different for every brand" },
  { id: "idea", title: "Make authenticity a condition of payment.", desc: "Scan → Brand verifies → PayPal payment created" },
  { id: "how", title: "How it works: Data never moves", desc: "Two locked nodes · Questions in · Private aggregates out" },
  { id: "s1", title: "Scenario 1: Genuine phone at authorized store", desc: "The brand verifies it, then PayPal creates the payment." },
  { id: "s2", title: "Scenario 2: Serial outside supply chain", desc: "No verification, no payment." },
  { id: "s3", title: "Scenario 3: The brand investigates", desc: "An AI agent works only from privacy-protected aggregates." },
  { id: "business", title: "How does this pay for itself?", desc: "USD 150B+ a year on market insights · TrustLedger answers from verified purchases" },
  { id: "s4", title: "Scenario 4: Brand insights", desc: "Answers from verified purchases in seconds, buyers stay anonymous." },
  { id: "guarantee", title: "Formal privacy guarantee", desc: "Buyers stay anonymous: one fixed privacy limit per brand, for life" },
  { id: "levels", title: "One standard. Three integrations.", desc: "Brand API · PayPal checkout gate · Store POS API" },
  { id: "close", title: "TrustLedger pitch close", desc: "Brands pay for insights; the checkout check is free for shoppers." },
  { id: "code", title: "Checkout Integration Code", desc: "One POST to /checkout/scan before PayPal payment creation" },
];


interface ShowCodePayload {
  title?: string;
  language?: string;
  code: string;
  highlight?: number[];
}

const DEFAULT_CODE_PAYLOAD: ShowCodePayload = {
  title: "src/checkout.ts",
  language: "TypeScript",
  code: `// 1. Any checkout: scan serial with TrustLedger before payment
const res = await fetch("https://api.trustledger.io/checkout/scan", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    serial: item.serial,
    sku: item.sku,
    amount: item.amount,
    store_id: checkout.storeId,
  }),
});
const verdict = await res.json();

// 2. Only genuine goods create a PayPal payment order
if (verdict.status === "VERIFIED") {
  return verdict.paypal_order_id;
}

// 3. Failed items never create an order; investigation opens automatically
throw new Error(\`Authenticity check failed: \${verdict.reason_code}\`);`,
  highlight: [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15, 16],
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
  const actualCardId = cardId;
  const problemVal = useCountUp(467, 0, 1200);

  useEffect(() => {
    const timer = setTimeout(() => {
      document.body.dataset.ready = "1";
    }, 1250);

    return () => {
      clearTimeout(timer);
      delete document.body.dataset.ready;
    };
  }, [actualCardId]);

  return (
    <div className={`${s.storyContainer} storyCardRoot`}>
      <Link href="/story" style={{ position: "fixed", top: "20px", left: "24px", color: "#94a3b8", textDecoration: "none", fontSize: "14px", fontWeight: 600, display: "inline-flex", alignItems: "center", gap: "6px", zIndex: 100, background: "rgba(15, 23, 42, 0.6)", padding: "6px 12px", borderRadius: "8px", border: "1px solid rgba(51, 65, 85, 0.5)", backdropFilter: "blur(6px)" }}>
        ← All cards
      </Link>
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
            <div className={s.statLabel}>in counterfeit goods traded in a year (2021 data)</div>
            <div className={s.statGrid}>
              <div className={s.statPill}>up to 2.3% of world trade</div>
              <div className={s.statPill}>up to 4.7% of EU imports</div>
            </div>
            <p className={s.calloutText} style={{ marginBottom: 12 }}>
              Smartphones alone: 12.9% of sales lost, ≈ EUR 45.3 billion (2015 data)
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
            <h1 className={s.titleLarge}>Verification exists. Most buyers skip it.</h1>
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
            <h1 className={s.titleLarge} style={{ marginBottom: 12 }}>How it works: Data never moves</h1>
            <div className={s.nodeCardGrid}>
              {/* Brand Node (Left) */}
              <div className={s.nodeCard}>
                <div className={s.nodeCardHeader}>
                  <div className={s.lockIconWrap}>
                    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#38bdf8" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                  </div>
                  <div className={s.nodeCardTitle}>Brand Node</div>
                  <span className={s.statPill} style={{ fontSize: 15, padding: "4px 10px" }}>Private DB</span>
                </div>
                <p style={{ margin: "4px 0", fontSize: 20, color: "#cbd5e1", lineHeight: 1.4 }}>
                  Serials, batches, shipments, and checkout logs remain locked inside.
                </p>
                <div style={{ marginTop: "auto", fontSize: 20, color: "#38bdf8", fontWeight: 700 }}>
                  Answers with business-level counts only
                </div>
              </div>

              {/* Center Asker */}
              <div className={`${s.nodeCard} ${s.nodeCardCenter}`}>
                <div style={{ fontSize: 20, color: "#93c5fd", fontWeight: 800, letterSpacing: "0.03em" }}>
                  Brand Analyst / AI Agent
                </div>
                <div className={s.centerExchange}>
                  <div className={s.exchangeSide} style={{ textAlign: "left" }}>
                    <div style={{ color: "#38bdf8" }}>← Question</div>
                    <div style={{ color: "#93c5fd" }}>Aggregate →</div>
                  </div>
                  <div className={s.exchangeDivider} />
                  <div className={s.exchangeSide} style={{ textAlign: "right" }}>
                    <div style={{ color: "#34d399" }}>Question →</div>
                    <div style={{ color: "#a7f3d0" }}>← Aggregate</div>
                  </div>
                </div>
                <p style={{ margin: 0, fontSize: 20, color: "var(--fg)", fontWeight: 600, lineHeight: 1.4 }}>
                  JSON query specs only (no SQL).<br />
                  <span style={{ color: "#38bdf8" }}>The AI agent never sees a raw record.</span>
                </p>
              </div>

              {/* PayPal Node (Right) */}
              <div className={s.nodeCard}>
                <div className={s.nodeCardHeader}>
                  <div className={s.lockIconWrap}>
                    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#34d399" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                  </div>
                  <div className={s.nodeCardTitle}>PayPal Node</div>
                  <span className={s.statPill} style={{ fontSize: 15, padding: "4px 10px" }}>DP Boundary</span>
                </div>
                <p style={{ margin: "4px 0", fontSize: 20, color: "#cbd5e1", lineHeight: 1.4 }}>
                  Transactions, keyed hashed buyer IDs, and demographics remain locked inside.
                </p>
                <div style={{ marginTop: "auto", fontSize: 20, color: "#34d399", fontWeight: 700 }}>
                  Answers with noisy aggregates (±95% CI)
                </div>
              </div>
            </div>
            <div className={s.sourceFooter} style={{ marginTop: 22, fontSize: 20, fontWeight: 600, color: "var(--fg)" }}>
              0 records leave a node · No person is identifiable
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
              TrustLedger answers from verified purchases in seconds, and no buyer is ever exposed.
            </p>
          </>
        )}

        {actualCardId === "s4" && (
          <>
            <div className={`${s.badge} ${s.badgeTeal}`}>Scenario 4</div>
            <h1 className={s.titleHero}>Brand insights in seconds</h1>
            <p className={s.subHero}>Answers from real purchases in seconds, not surveys in weeks. Buyers stay anonymous.</p>
          </>
        )}

        {actualCardId === "guarantee" && (
          <>
            <div className={`${s.badge} ${s.badgeTeal}`}>Privacy Guarantee</div>
            <h1 className={s.titleLarge} style={{ marginBottom: 12 }}>Buyers stay anonymous. Provably.</h1>
            <p className={s.subHero} style={{ fontSize: 24, marginBottom: 20 }}>The AI never sees a customer record, only group answers with noise added</p>
            <div className={s.guaranteeBox}>
              <div className={s.formulaHighlight}>Differential privacy, built on OpenDP</div>
              <div style={{ display: "flex", gap: 20, flexWrap: "wrap", justifyContent: "center", fontSize: 20, fontWeight: 600, color: "#e2e8f0" }}>
                <span>✓ Each buyer’s influence is capped</span>
                <span>✓ Every answer shows its margin of error</span>
                <span>✓ A fixed privacy limit per brand</span>
                <span>✓ Tiny groups hidden</span>
              </div>
            </div>
            <div className={s.sourceFooter} style={{ marginTop: 20 }}>
              Our internal red-team tried 11 attack types; none pinned down a single buyer
            </div>
          </>
        )}

        {actualCardId === "levels" && (
          <>
            <div className={`${s.badge} ${s.badgeBlue}`}>Ecosystem</div>
            <h1 className={s.titleLarge} style={{ marginBottom: 12 }}>One standard. Three simple integrations.</h1>
            <div className={s.levelsRow}>
              <div className={s.levelBox}>
                <div style={{ fontSize: 15, color: "#60a5fa", fontWeight: 700, letterSpacing: "0.05em" }}>1. FOR BRANDS</div>
                <div style={{ fontSize: 24, fontWeight: 750, color: "#ffffff" }}>Verification API</div>
                <p style={{ margin: 0, fontSize: 20, color: "#cbd5e1", lineHeight: 1.45 }}>
                  Brand verification endpoint + local brand node holding serial inventory.
                </p>
              </div>

              <div className={s.levelBox}>
                <div style={{ fontSize: 15, color: "#34d399", fontWeight: 700, letterSpacing: "0.05em" }}>2. FOR PAYPAL</div>
                <div style={{ fontSize: 24, fontWeight: 750, color: "#ffffff" }}>Checkout Gate</div>
                <p style={{ margin: 0, fontSize: 20, color: "#cbd5e1", lineHeight: 1.45 }}>
                  Creates payment only on brand verification. Stores the verification ID in the PayPal order&apos;s custom_id.
                </p>
              </div>

              <div className={`${s.levelBox} ${s.levelBoxHighlight}`}>
                <div style={{ fontSize: 15, color: "#38bdf8", fontWeight: 700, letterSpacing: "0.05em" }}>3. FOR SELLERS / POS</div>
                <div style={{ fontSize: 24, fontWeight: 750, color: "#ffffff" }}>One API Call</div>
                <p style={{ margin: 0, fontSize: 20, color: "#cbd5e1", lineHeight: 1.45 }}>
                  In production, the store&apos;s POS sends the scanned serial through the TrustLedger API.
                </p>
              </div>
            </div>
          </>
        )}

        {actualCardId === "code" && (
          <CodeCard />
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
                Built with PayPal Server SDK (APIMatic) · AG Grid · Bryntum · OpenDP
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
        <div style={{ marginBottom: "16px" }}>
          <Link href="/" style={{ display: "inline-flex", alignItems: "center", gap: "6px", color: "var(--accent, #60a5fa)", textDecoration: "none", fontSize: "14px", fontWeight: 600 }}>
            ← Back to Home
          </Link>
        </div>
        <h1 className={s.indexTitle}>TrustLedger in 3 minutes</h1>
        <p className={s.indexSubtitle}>
          Interactive walkthrough covering checkout authenticity verification, differential privacy, and brand insights.
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

  if (card && CARDS.some((c) => c.id === card)) {

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
