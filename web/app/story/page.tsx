"use client";

import { Suspense, useEffect, useState } from "react";
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
  { id: "problem", title: "USD 467 billion in counterfeit goods", desc: "Up to 2.3% of world trade · Hazardous fakes rising" },
  { id: "phones", title: "12.9% smartphone sales lost", desc: "≈ EUR 45.3 billion lost to counterfeits" },
  { id: "gap", title: "Verification exists. Nobody uses it.", desc: "Optional · Separate from paying · Different for every brand" },
  { id: "idea", title: "Make authenticity a condition of payment.", desc: "Scan → Brand verifies → PayPal payment created" },
  { id: "s1", title: "Scenario 1: Genuine phone at authorized store", desc: "The brand verifies it, then PayPal creates the payment." },
  { id: "s2", title: "Scenario 2: Serial outside supply chain", desc: "No verification, no payment." },
  { id: "s3", title: "Scenario 3: The brand investigates", desc: "An AI agent works only from privacy-protected aggregates." },
  { id: "s4", title: "Scenario 4: Privacy by design", desc: "Analysts get answers, never individual buyers." },
  { id: "redteam", title: "11 of 11 attacks blocked", desc: "No attack extracted a confident individual-level fact" },
  { id: "onboard", title: "One API. Every checkout.", desc: "OpenAPI → APIMatic (SDKs, portal, MCP) → Commerce ecosystem" },
  { id: "close", title: "TrustLedger pitch close", desc: "Trust for buyers · Intelligence for brands · Trusted network for PayPal" },
];

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
  const problemVal = useCountUp(467, 0, 1200);
  const phonesVal = useCountUp(12.9, 1, 1200);
  const redteamVal = useCountUp(11, 0, 1200);

  useEffect(() => {
    // Notify demo recorder after animations complete
    const timer = setTimeout(() => {
      document.body.dataset.ready = "1";
    }, 1250);

    return () => {
      clearTimeout(timer);
      delete document.body.dataset.ready;
    };
  }, [cardId]);

  return (
    <div className={s.storyContainer}>
      <div className={`${s.safeArea} ${s.fadeIn}`} key={cardId}>
        {cardId === "hook" && (
          <>
            <h1 className={s.titleHero}>One phone. One serial number. Two stores.</h1>
            <p className={s.subHero}>Only one of them is selling the real thing.</p>
          </>
        )}

        {cardId === "problem" && (
          <>
            <div className={s.statHuge}>USD {problemVal} billion</div>
            <div className={s.statLabel}>in counterfeit goods traded in a year</div>
            <div className={s.statGrid}>
              <div className={s.statPill}>up to 2.3% of world trade</div>
              <div className={s.statPill}>up to 4.7% of EU imports</div>
            </div>
            <p className={s.calloutText}>
              Hazardous fakes are rising: car parts, medicines, cosmetics, toys.
            </p>
            <div className={s.sourceFooter}>
              OECD / EUIPO, Mapping Global Trade in Fakes 2025 (2021 data)
            </div>
          </>
        )}

        {cardId === "phones" && (
          <>
            <div className={s.statHuge}>{phonesVal}%</div>
            <div className={s.statLabel}>of legitimate smartphone sales lost to counterfeits</div>
            <div className={s.statGrid}>
              <div className={`${s.statPill} ${s.statGreen}`}>≈ EUR 45.3 billion</div>
            </div>
            <div className={s.sourceFooter}>
              EUIPO / ITU, smartphone sector study (2015 data)
            </div>
          </>
        )}

        {cardId === "gap" && (
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

        {cardId === "idea" && (
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

        {cardId === "s1" && (
          <>
            <div className={`${s.badge} ${s.badgeBlue}`}>Scenario 1</div>
            <h1 className={s.titleHero}>A genuine phone at an authorized store</h1>
            <p className={s.subHero}>The brand verifies it, then PayPal creates the payment.</p>
          </>
        )}

        {cardId === "s2" && (
          <>
            <div className={`${s.badge} ${s.badgeRed}`}>Scenario 2</div>
            <h1 className={s.titleHero}>The same serial at a store outside the supply chain</h1>
            <p className={`${s.subHero} ${s.subRed}`}>No verification, no payment.</p>
          </>
        )}

        {cardId === "s3" && (
          <>
            <div className={`${s.badge} ${s.badgePurple}`}>Scenario 3</div>
            <h1 className={s.titleHero}>The brand investigates</h1>
            <p className={s.subHero}>An AI agent works only from privacy-protected aggregates.</p>
          </>
        )}

        {cardId === "s4" && (
          <>
            <div className={`${s.badge} ${s.badgeTeal}`}>Scenario 4</div>
            <h1 className={s.titleHero}>Privacy by design</h1>
            <p className={s.subHero}>Analysts get answers, never individual buyers.</p>
          </>
        )}

        {cardId === "redteam" && (
          <>
            <div className={`${s.badge} ${s.badgeTeal}`}>Privacy Layer</div>
            <div className={s.statHuge}>{redteamVal} of 11</div>
            <div className={s.statLabel}>re-identification attacks blocked</div>
            <p className={s.calloutText}>
              No attack extracted a confident individual-level fact
            </p>
            <div className={s.sourceFooter}>
              Scripted battery: small cells, differencing, membership, cross-node linkage, averaging, budget probing · evals/redteam.py
            </div>
          </>
        )}

        {cardId === "onboard" && (
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

        {cardId === "close" && (
          <div className={s.closeWrap}>
            <div className={`${s.closeLine} ${s.line1}`}>Trust at checkout for buyers.</div>
            <div className={`${s.closeLine} ${s.line2}`}>Intelligence for brands.</div>
            <div className={`${s.closeLine} ${s.line3}`}>A more trusted network for PayPal.</div>
            <div className={s.brandFooter}>
              <div className={s.brandWordmark}>
                <span className={s.brandDiamond} aria-hidden>◆</span>
                TrustLedger
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
