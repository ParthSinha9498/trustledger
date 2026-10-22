import Link from "next/link";

export default function Home() {
  return (
    <main>
      {/* Hero Section */}
      <div className="card hero" style={{ padding: "36px 32px", marginBottom: "28px" }}>
        <div style={{ display: "inline-flex", alignItems: "center", gap: "8px", padding: "4px 12px", borderRadius: "999px", background: "var(--accent-bg)", color: "var(--accent)", fontSize: "13px", fontWeight: 650, marginBottom: "16px", border: "1px solid var(--accent-border)" }}>
          <span aria-hidden>◆</span> Authenticity as a Condition of Payment
        </div>
        <h1 style={{ fontSize: "32px", lineHeight: 1.2, margin: "0 0 14px", letterSpacing: "-0.03em" }}>
          Product authenticity is no longer a post-sale dispute.<br />
          It&apos;s the gate before payment.
        </h1>
        <p className="muted" style={{ fontSize: "16px", maxWidth: "800px", lineHeight: 1.5, margin: "0 0 24px" }}>
          TrustLedger connects brand serial intelligence directly to the point of sale before any PayPal payment is created.
          If verified, the buyer pays seamlessly. If unverified, the payment order is <strong>never created</strong>, money never moves, and an investigation opens.
        </p>
        <div className="row" style={{ gap: "12px", marginBottom: "18px" }}>
          <Link className="button" href="/pos">Open the store checkout</Link>
          <Link className="button secondary" href="/cockpit">Open the brand cockpit</Link>
          <Link className="button secondary" href="/story">Walkthrough story mode</Link>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13.5px", color: "var(--muted)", background: "var(--chip)", padding: "10px 14px", borderRadius: "8px", border: "1px solid var(--line)" }}>
          <span aria-hidden>💡</span>
          <span><strong>Demo walk:</strong> Serial <code>X123</code> belongs to Store A&apos;s supply chain. Scan at Store A (Verified & Paid), then at Store B (Blocked & Investigated).</span>
        </div>
      </div>

      {/* 3 Core Value Props */}
      <h2 style={{ fontSize: "19px", marginBottom: "14px" }}>Three Principles of TrustLedger</h2>
      <div className="tiles" style={{ marginBottom: "32px" }}>
        <div className="tile card" style={{ padding: "20px" }}>
          <b>Payment Gate, Not Paper Warranties</b>
          <span className="muted" style={{ fontSize: "13.5px", lineHeight: 1.45 }}>
            Authenticity is verified at the POS scanner before the PayPal order is created. Failed units never create an order, stopped before any money moves.
          </span>
        </div>
        <div className="tile card" style={{ padding: "20px" }}>
          <b>Autonomous AI Investigation</b>
          <span className="muted" style={{ fontSize: "13.5px", lineHeight: 1.45 }}>
            When a checkout diverges from the authorized channel, an AI agent investigates supply chain batches and generates cited evidence steps in the brand cockpit.
          </span>
        </div>
        <div className="tile card" style={{ padding: "20px" }}>
          <b>Brand Intelligence as a Product</b>
          <span className="muted" style={{ fontSize: "13.5px", lineHeight: 1.45 }}>
            USD 150B+ is spent a year on market insights (ESOMAR, 2024 data). While survey results take weeks, and in a 2024 Pew survey 18% of responses were flagged as bogus, TrustLedger delivers verified purchase insights with mathematical differential privacy.
          </span>
        </div>
      </div>

      {/* The Two Architectural Moats */}
      <h2 style={{ fontSize: "19px", marginBottom: "14px" }}>The Two Moats</h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px", marginBottom: "32px" }}>
        <div className="card elevated" style={{ borderLeft: "4px solid var(--ok)", padding: "22px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "8px" }}>
            <h3 style={{ margin: 0, fontSize: "16px", color: "var(--ok)" }}>Moat 1: Data Never Moves</h3>
            <span className="badge badge-exact">Zero raw records shared</span>
          </div>
          <p className="muted" style={{ fontSize: "13.5px", margin: "0 0 12px", lineHeight: 1.5 }}>
            Brand serials, shipments, and logs stay in the brand node. Transactions and hashed buyer IDs stay in the PayPal node.
            Questions travel as structured specs to the data—the AI never sees a raw record.
          </p>
          <div style={{ fontSize: "12.5px", color: "var(--muted)" }}>
            ✓ Nodes return only group aggregates · ✓ No direct SQL access · ✓ Isolated database credentials
          </div>
        </div>

        <div className="card elevated" style={{ borderLeft: "4px solid var(--accent)", padding: "22px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "8px" }}>
            <h3 style={{ margin: 0, fontSize: "16px", color: "var(--accent)" }}>Moat 2: No Person Identifiable</h3>
            <span className="badge badge-dp">OpenDP · zCDP</span>
          </div>
          <p className="muted" style={{ fontSize: "13.5px", margin: "0 0 12px", lineHeight: 1.5 }}>
            Calibrated Gaussian differential privacy noise with ±95% intervals. Lifetime budget ρ 0.25; each release spends ρ 0.20 (ε ≈ 3.69),
            small groups hidden, and deterministic query caching. Internal red-team: 11 attack types, none extracted a confident individual-level fact.
          </p>
          <div style={{ fontSize: "12.5px", color: "var(--muted)" }}>
            ✓ One buyer unit bound · ✓ Spend clamped to 1,000 · ✓ Refused when budget spent
          </div>
        </div>
      </div>

      {/* Quick Links Footer Grid */}
      <h2 style={{ fontSize: "19px", marginBottom: "14px" }}>Explore TrustLedger</h2>
      <div className="tiles">
        <Link href="/cockpit" className="tile card">
          <b>Brand Cockpit & Investigations</b>
          <span className="muted">Agent steps, data boundary flow, cited findings, and privacy budget meters.</span>
        </Link>
        <Link href="/cockpit/console" className="tile card">
          <b>Brand Insights</b>
          <span className="muted">Ask natural language business questions, inspect query specs, and run DP queries.</span>
        </Link>
        <Link href="/cockpit/supply-chain" className="tile card">
          <b>Supply Chain Timeline</b>
          <span className="muted">Serial batches mapped by week with off-channel divergences highlighted in red.</span>
        </Link>
        <Link href="/privacy" className="tile card">
          <b>Privacy & Protections</b>
          <span className="muted">Interactive architecture explainer: how the two nodes protect brand and customer privacy.</span>
        </Link>
      </div>
    </main>
  );
}
