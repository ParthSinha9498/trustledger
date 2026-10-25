"use client";
import { useState } from "react";
import Link from "next/link";

export default function Home() {
  const [moatStep, setMoatStep] = useState<0 | 1>(0);

  return (
    <main>
      {/* Hero Section */}
      <div className="card hero" style={{ padding: "36px 32px", marginBottom: "28px" }}>
        <div className="hero-grid">
          <div>
            <div style={{ display: "inline-flex", alignItems: "center", gap: "8px", padding: "4px 12px", borderRadius: "999px", background: "var(--accent-bg)", color: "var(--accent)", fontSize: "13px", fontWeight: 650, marginBottom: "16px", border: "1px solid var(--accent-border)" }}>
              <span aria-hidden>◆</span> Authenticity as a Condition of Payment
            </div>
            <h1 style={{ fontSize: "32px", lineHeight: 1.2, margin: "0 0 14px", letterSpacing: "-0.03em" }}>
              Product authenticity is no longer a post-sale dispute.<br />
              It&apos;s the gate before payment.
            </h1>
            <p className="muted" style={{ fontSize: "16px", maxWidth: "600px", lineHeight: 1.5, margin: "0 0 20px" }}>
              TrustLedger makes authenticity a condition of payment. If the brand can&apos;t verify the product, no PayPal order is ever created.
              Questions travel to the data, and only private aggregates come back.
            </p>

            {/* 3-Step Flow Summary */}
            <div className="hero-steps" style={{ display: "flex", gap: "10px", flexWrap: "wrap", margin: "0 0 22px" }}>
              <div className="hero-step-chip" style={{ display: "inline-flex", alignItems: "center", gap: "6px", padding: "6px 12px", borderRadius: "var(--radius-pill)", background: "var(--card-hover)", border: "1px solid var(--line)", fontSize: "13px", fontWeight: 600 }}>
                <span style={{ color: "var(--accent)" }}>1. Scan</span> At store POS
              </div>
              <span style={{ alignSelf: "center", color: "var(--muted)", fontSize: "12px" }}>→</span>
              <div className="hero-step-chip" style={{ display: "inline-flex", alignItems: "center", gap: "6px", padding: "6px 12px", borderRadius: "var(--radius-pill)", background: "var(--card-hover)", border: "1px solid var(--line)", fontSize: "13px", fontWeight: 600 }}>
                <span style={{ color: "var(--accent)" }}>2. Brand verifies</span> Authorized channel
              </div>
              <span style={{ alignSelf: "center", color: "var(--muted)", fontSize: "12px" }}>→</span>
              <div className="hero-step-chip" style={{ display: "inline-flex", alignItems: "center", gap: "6px", padding: "6px 12px", borderRadius: "var(--radius-pill)", background: "var(--card-hover)", border: "1px solid var(--line)", fontSize: "13px", fontWeight: 600 }}>
                <span style={{ color: "var(--accent)" }}>3. Pay or investigate</span> PayPal gated
              </div>
            </div>

            <div className="hero-ctas">
              <Link className="button" href="/story">
                Interactive walkthrough &amp; demo →
              </Link>
              <Link className="button secondary" href="/pos">
                Store checkout
              </Link>
              <Link className="button secondary" href="/cockpit">
                Brand cockpit
              </Link>
            </div>
            <p className="muted small" style={{ margin: 0 }}>
              Live demo: Scan <code>X123</code> (fresh seed) at Store A (verified) and Store C (blocked). Once sold, click &ldquo;Fill an unsold unit&rdquo; at the checkout to test newly stocked inventory.
            </p>
          </div>

          {/* Hero Visual Mock: Small static mock of the verdict card (green verified, red blocked) */}
          <div style={{ display: "flex", flexDirection: "column", gap: "12px", maxWidth: "340px", justifySelf: "center", width: "100%" }}>
            {/* Mini Verified Verdict Mock */}
            <div style={{ background: "var(--card)", border: "1.5px solid var(--ok)", borderRadius: "10px", padding: "14px 16px", boxShadow: "0 4px 16px rgba(0,0,0,0.06)" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", fontWeight: 700, fontSize: "14px", color: "var(--ok)" }}>
                  <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: "18px", height: "18px", borderRadius: "50%", background: "var(--ok-bg)", border: "1px solid var(--ok-border)", fontSize: "11px" }}>✓</span>
                  VERIFIED · Store A
                </div>
                <span style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)" }}>serial: X123</span>
              </div>
              <div style={{ fontSize: "12.5px", color: "var(--fg)", marginBottom: "4px" }}>Authenticity confirmed at Store A</div>
              <div style={{ fontSize: "11.5px", color: "var(--muted)" }}>PayPal payment order created</div>
            </div>

            {/* Mini Blocked Verdict Mock */}
            <div style={{ background: "var(--card)", border: "1.5px solid var(--bad)", borderRadius: "10px", padding: "14px 16px", boxShadow: "0 4px 16px rgba(0,0,0,0.06)" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", fontWeight: 700, fontSize: "14px", color: "var(--bad)" }}>
                  <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: "18px", height: "18px", borderRadius: "50%", background: "var(--bad-bg)", border: "1px solid var(--bad-border)", fontSize: "11px" }}>✕</span>
                  BLOCKED · Store C
                </div>
                <span style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)" }}>serial: X123</span>
              </div>
              <div style={{ fontSize: "12.5px", color: "var(--fg)", marginBottom: "4px" }}>Serial not assigned to Store C</div>
              <div style={{ fontSize: "11.5px", color: "var(--bad)", fontWeight: 600 }}>Order never created · Investigation opened</div>
            </div>
          </div>
        </div>
      </div>

      {/* The Two Architectural Moats as a Stepper / Slider */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px", flexWrap: "wrap", gap: "10px" }}>
        <h2 style={{ fontSize: "20px", margin: 0 }}>The Two Architectural Moats</h2>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <button
            type="button"
            className="chip"
            style={{ fontWeight: moatStep === 0 ? 700 : 500, borderColor: moatStep === 0 ? "var(--ok)" : "var(--line)", color: moatStep === 0 ? "var(--ok)" : "var(--muted)" }}
            onClick={() => setMoatStep(0)}
          >
            Moat 1: Data never moves
          </button>
          <button
            type="button"
            className="chip"
            style={{ fontWeight: moatStep === 1 ? 700 : 500, borderColor: moatStep === 1 ? "var(--accent)" : "var(--line)", color: moatStep === 1 ? "var(--accent)" : "var(--muted)" }}
            onClick={() => setMoatStep(1)}
          >
            Moat 2: No buyer is identifiable
          </button>
        </div>
      </div>

      <div style={{ marginBottom: "32px" }}>
        {moatStep === 0 ? (
          <div className="card elevated" style={{ borderLeft: "4px solid var(--ok)", padding: "24px", transition: "all 0.2s ease" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px", flexWrap: "wrap", gap: "8px" }}>
              <div>
                <span style={{ fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--ok)", fontWeight: 700 }}>
                  Moat 1 of 2
                </span>
                <h3 style={{ margin: "4px 0 0", fontSize: "18px", color: "var(--fg)" }}>
                  Data Never Moves
                </h3>
              </div>
              <span className="badge badge-exact">Zero raw records shared</span>
            </div>
            <p className="muted" style={{ fontSize: "14.5px", margin: "0 0 16px", lineHeight: 1.55 }}>
              Brand serials, shipments, and logs stay in the brand node. Transactions and hashed buyer IDs stay in the PayPal node.
              Questions travel as structured specs to the data—the AI never sees a raw record.
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px", marginBottom: "18px", fontSize: "13.5px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--fg)" }}>
                <span style={{ color: "var(--ok)", fontWeight: "bold" }}>✓</span> Nodes return only group aggregates
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--fg)" }}>
                <span style={{ color: "var(--ok)", fontWeight: "bold" }}>✓</span> No direct SQL access between nodes
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--fg)" }}>
                <span style={{ color: "var(--ok)", fontWeight: "bold" }}>✓</span> Isolated database credentials
              </div>
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button type="button" className="button secondary" onClick={() => setMoatStep(1)} style={{ fontSize: "13px", padding: "6px 14px" }}>
                Next: Moat 2 (No buyer is identifiable) →
              </button>
            </div>
          </div>
        ) : (
          <div className="card elevated" style={{ borderLeft: "4px solid var(--accent)", padding: "24px", transition: "all 0.2s ease" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px", flexWrap: "wrap", gap: "8px" }}>
              <div>
                <span style={{ fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--accent)", fontWeight: 700 }}>
                  Moat 2 of 2
                </span>
                <h3 style={{ margin: "4px 0 0", fontSize: "18px", color: "var(--fg)" }}>
                  No Buyer is Identifiable
                </h3>
              </div>
              <span className="badge badge-dp">Differential privacy · OpenDP</span>
            </div>
            <p className="muted" style={{ fontSize: "14.5px", margin: "0 0 16px", lineHeight: 1.55 }}>
              The AI only gets answers about groups, with mathematically calibrated noise added via differential privacy, so no buyer&apos;s purchase can be singled out.
              Each brand has a fixed privacy allowance: repeated queries cannot reveal individual customers.
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px", marginBottom: "18px", fontSize: "13.5px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--fg)" }}>
                <span style={{ color: "var(--accent)", fontWeight: "bold" }}>✓</span> Every answer shows 95% margin of error (±)
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--fg)" }}>
                <span style={{ color: "var(--accent)", fontWeight: "bold" }}>✓</span> Tiny cells suppressed below safety floor
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--fg)" }}>
                <span style={{ color: "var(--accent)", fontWeight: "bold" }}>✓</span> Questions stop when privacy allowance is exhausted
              </div>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <button type="button" className="button secondary" onClick={() => setMoatStep(0)} style={{ fontSize: "13px", padding: "6px 14px" }}>
                ← Back to Moat 1
              </button>
              <Link href="/privacy" className="button secondary" style={{ fontSize: "13px", padding: "6px 14px" }}>
                Deep-dive into Privacy &amp; Protections →
              </Link>
            </div>
          </div>
        )}
      </div>

      {/* Quick Links Footer Grid (4 Key Cards) */}
      <h2 style={{ fontSize: "20px", marginBottom: "14px" }}>Explore TrustLedger</h2>
      <div className="tiles">
        <Link href="/cockpit" className="tile card">
          <b>Brand Cockpit &amp; Investigations</b>
          <span className="muted">Agent steps, data boundary flow, cited findings, and see what the agent saw.</span>
        </Link>
        <Link href="/cockpit/console" className="tile card">
          <b>Brand Insights</b>
          <span className="muted">Ask questions in plain English, inspect query specs, and get verified purchase insights.</span>
        </Link>
        <Link href="/cockpit/supply-chain" className="tile card">
          <b>Supply Chain Timeline</b>
          <span className="muted">Serial batches mapped by week with off-channel divergences highlighted in red.</span>
        </Link>
        <Link href="/privacy" className="tile card">
          <b>Privacy &amp; Protections</b>
          <span className="muted">Interactive architecture explainer: how the two nodes protect brand and customer privacy.</span>
        </Link>
      </div>
    </main>
  );
}
