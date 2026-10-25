import Link from "next/link";

export default function Home() {
  return (
    <main>
      {/* 1. Hero Section (Clean above-the-fold) */}
      <section className="card hero" style={{ padding: "40px 36px", marginBottom: "36px" }}>
        <div className="hero-grid">
          <div>
            <div style={{ display: "inline-flex", alignItems: "center", gap: "8px", padding: "4px 12px", borderRadius: "999px", background: "var(--accent-bg)", color: "var(--accent)", fontSize: "13px", fontWeight: 650, marginBottom: "16px", border: "1px solid var(--accent-border)" }}>
              <span aria-hidden>◆</span> Authenticity as a Condition of Payment
            </div>
            <h1 style={{ fontSize: "36px", lineHeight: 1.18, margin: "0 0 16px", letterSpacing: "-0.03em" }}>
              Authenticity, checked before payment.
            </h1>
            <p className="muted" style={{ fontSize: "16.5px", maxWidth: "620px", lineHeight: 1.55, margin: "0 0 24px" }}>
              Before PayPal creates an order, the brand confirms the product is genuine. If it isn&apos;t, there is no order, and an AI agent investigates where it came from.
            </p>
            <div className="hero-ctas">
              <Link className="button" href="/pos">
                Try the checkout →
              </Link>
              <Link className="button secondary" href="/cockpit">
                Explore the brand cockpit
              </Link>
            </div>
          </div>

          {/* Mini Verified / Blocked Pair Visual */}
          <div style={{ display: "flex", flexDirection: "column", gap: "12px", maxWidth: "340px", justifySelf: "center", width: "100%" }}>
            {/* Mini Verified Mock */}
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

            {/* Mini Blocked Mock */}
            <div style={{ background: "var(--card)", border: "1.5px solid var(--bad)", borderRadius: "10px", padding: "14px 16px", boxShadow: "0 4px 16px rgba(0,0,0,0.06)" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", fontWeight: 700, fontSize: "14px", color: "var(--bad)" }}>
                  <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: "18px", height: "18px", borderRadius: "50%", background: "var(--bad-bg)", border: "1px solid var(--bad-border)", fontSize: "11px" }}>✕</span>
                  BLOCKED · Store C
                </div>
                <span style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)" }}>serial: X123</span>
              </div>
              <div style={{ fontSize: "12.5px", color: "var(--fg)", marginBottom: "4px" }}>Serial not assigned to Store C</div>
              <div style={{ fontSize: "11.5px", color: "var(--bad)", fontWeight: 600 }}>No order created · Investigation opened</div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. How It Works (3 Steps) */}
      <section style={{ marginBottom: "40px" }}>
        <h2 style={{ fontSize: "22px", marginBottom: "18px", letterSpacing: "-0.02em" }}>How It Works</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "16px" }}>
          <div className="card" style={{ padding: "22px" }}>
            <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--accent)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>
              Step 1
            </div>
            <h3 style={{ fontSize: "17px", margin: "0 0 8px" }}>Scan at checkout</h3>
            <p className="muted" style={{ fontSize: "14px", margin: 0, lineHeight: 1.5 }}>
              The store&apos;s barcode scanner sends the serial number through the TrustLedger API before payment begins.
            </p>
          </div>
          <div className="card" style={{ padding: "22px" }}>
            <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--accent)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>
              Step 2
            </div>
            <h3 style={{ fontSize: "17px", margin: "0 0 8px" }}>Brand verifies</h3>
            <p className="muted" style={{ fontSize: "14px", margin: 0, lineHeight: 1.5 }}>
              The brand confirms the unit is genuine and in its authorized channel before any payment transaction exists.
            </p>
          </div>
          <div className="card" style={{ padding: "22px" }}>
            <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--accent)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>
              Step 3
            </div>
            <h3 style={{ fontSize: "17px", margin: "0 0 8px" }}>PayPal pays or AI investigates</h3>
            <p className="muted" style={{ fontSize: "14px", margin: 0, lineHeight: 1.5 }}>
              If verified, PayPal creates the payment order. If unverified, no order is created and an autonomous agent investigates the divergence.
            </p>
          </div>
        </div>
      </section>

      {/* 3. Product Features (5 Cards Grid) */}
      <section style={{ marginBottom: "40px" }}>
        <h2 style={{ fontSize: "22px", marginBottom: "18px", letterSpacing: "-0.02em" }}>Product Features</h2>
        <div className="tiles">
          <Link href="/pos" className="tile card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <b>Point-of-Sale Gate</b>
              <span className="badge badge-exact">Checkout</span>
            </div>
            <span className="muted">Verify before paying. Unverified items never create an order, preventing unverified sales before money moves.</span>
          </Link>
          <Link href="/cockpit" className="tile card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <b>Autonomous AI Investigations</b>
              <span className="badge badge-exact">Cockpit</span>
            </div>
            <span className="muted">When a scan fails, an AI agent investigates supply chain batches and cites every step of its evidence.</span>
          </Link>
          <Link href="/cockpit/console" className="tile card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <b>Brand Insights</b>
              <span className="badge badge-dp">Console</span>
            </div>
            <span className="muted">Ask business questions in plain English and receive answers from verified purchases in seconds with privacy protection.</span>
          </Link>
          <Link href="/cockpit/supply-chain" className="tile card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <b>Supply Chain Timeline</b>
              <span className="badge badge-exact">Schedule</span>
            </div>
            <span className="muted">Track shipments and identify unauthorized stock diversions across distributor channels on an interactive timeline.</span>
          </Link>
          <Link href="/privacy" className="tile card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <b>Privacy Protections</b>
              <span className="badge badge-dp">Architecture</span>
            </div>
            <span className="muted">Two separate data nodes answer questions with privacy protection; raw records never move.</span>
          </Link>
        </div>
      </section>

      {/* 4. Self-Sustaining Business Model Section */}
      <section className="card elevated" style={{ padding: "30px 32px", marginBottom: "40px", borderLeft: "4px solid var(--accent)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px", marginBottom: "14px" }}>
          <div>
            <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--accent)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "4px" }}>
              Business Model
            </div>
            <h2 style={{ fontSize: "22px", margin: 0, letterSpacing: "-0.02em" }}>Self-sustaining: Intelligence pays for the protection.</h2>
          </div>
          <div style={{ fontSize: "26px", fontWeight: 800, color: "var(--accent)", lineHeight: 1 }}>
            $150B+ <span style={{ fontSize: "14px", fontWeight: 500, color: "var(--muted)" }}>market</span>
          </div>
        </div>
        <p style={{ fontSize: "15px", lineHeight: 1.6, margin: "0 0 16px", color: "var(--fg)" }}>
          Brands pay for privacy-safe insights from verified purchases; the authenticity check is free for shoppers.
          Brands spend over USD 150B a year on market insights (ESOMAR, 2024 data). Traditional surveys take weeks, and in a Pew survey (Nov 2024, 11,114 US adults), 18% of cases were flagged as bogus. TrustLedger delivers answers from verified purchases in seconds, and that revenue pays for the free check.
        </p>
        <div style={{ fontSize: "13px", color: "var(--muted)" }}>
          Data sources: ESOMAR Insights Industry report · Pew Research Center
        </div>
      </section>

      {/* 5. Private by Design Section */}
      <section style={{ marginBottom: "40px" }}>
        <h2 style={{ fontSize: "22px", marginBottom: "18px", letterSpacing: "-0.02em" }}>Private by Design</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "18px" }}>
          <div className="card" style={{ padding: "24px", borderTop: "3px solid var(--ok)" }}>
            <h3 style={{ fontSize: "18px", margin: "0 0 12px" }}>Data never leaves its owner</h3>
            <p className="muted" style={{ fontSize: "14px", lineHeight: 1.55, margin: "0 0 16px" }}>
              Brand serials and supply logs stay in the brand node. Transactions and buyer accounts stay in the PayPal node.
            </p>
            <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "13.5px", lineHeight: 1.7, color: "var(--fg)" }}>
              <li>Brand serials and shipment logs stay with the brand.</li>
              <li>Transactions and buyer accounts stay with PayPal.</li>
              <li>Questions travel to the data as structured query specs; raw records never move.</li>
            </ul>
          </div>

          <div className="card" style={{ padding: "24px", borderTop: "3px solid var(--accent)" }}>
            <h3 style={{ fontSize: "18px", margin: "0 0 12px" }}>No buyer is identifiable</h3>
            <p className="muted" style={{ fontSize: "14px", lineHeight: 1.55, margin: "0 0 16px" }}>
              The AI analyst only answers about groups with mathematically guaranteed privacy protections.
            </p>
            <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "13.5px", lineHeight: 1.7, color: "var(--fg)" }}>
              <li>Answers about buyers carry calibrated noise (differential privacy, OpenDP).</li>
              <li>Every buyer answer shows a 95% interval (±); brand counts are exact.</li>
              <li>Small groups are hidden.</li>
            </ul>
          </div>
        </div>
      </section>

      {/* 6. Closing CTA Banner */}
      <section className="card hero" style={{ padding: "36px 32px", textAlign: "center", marginBottom: "20px" }}>
        <h2 style={{ fontSize: "24px", margin: "0 0 10px", letterSpacing: "-0.02em" }}>
          Experience authenticity gating in action
        </h2>
        <p className="muted" style={{ fontSize: "15px", maxWidth: "540px", margin: "0 auto 22px", lineHeight: 1.5 }}>
          Follow the step-by-step interactive walkthrough or test a live transaction at the store checkout.
        </p>
        <div style={{ display: "inline-flex", gap: "12px", justifyContent: "center", flexWrap: "wrap" }}>
          <Link className="button" href="/story">
            Interactive walkthrough →
          </Link>
          <Link className="button secondary" href="/pos">
            Store checkout
          </Link>
        </div>
      </section>
    </main>
  );
}
