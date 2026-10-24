import Link from "next/link";

export default function Home() {
  return (
    <main>
      {/* Hero Section */}
      <div className="card hero" style={{ padding: "36px 32px", marginBottom: "28px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "28px", alignItems: "center" }}>
          <div>
            <div style={{ display: "inline-flex", alignItems: "center", gap: "8px", padding: "4px 12px", borderRadius: "999px", background: "var(--accent-bg)", color: "var(--accent)", fontSize: "13px", fontWeight: 650, marginBottom: "16px", border: "1px solid var(--accent-border)" }}>
              <span aria-hidden>◆</span> Authenticity as a Condition of Payment
            </div>
            <h1 style={{ fontSize: "32px", lineHeight: 1.2, margin: "0 0 14px", letterSpacing: "-0.03em" }}>
              Product authenticity is no longer a post-sale dispute.<br />
              It&apos;s the gate before payment.
            </h1>
            <p className="muted" style={{ fontSize: "16px", maxWidth: "600px", lineHeight: 1.5, margin: "0 0 24px" }}>
              TrustLedger connects brand serial intelligence directly to the point of sale before any PayPal payment is created.
              If verified, the buyer pays seamlessly. If unverified, the payment order is <strong>never created</strong>, so nothing can be paid, and an investigation opens.
            </p>
            <div className="row" style={{ gap: "12px", marginBottom: "18px", flexWrap: "wrap" }}>
              <Link className="button" href="/pos">Open the store checkout</Link>
              <Link className="button secondary" href="/cockpit">Open the brand cockpit</Link>
              <Link className="button secondary" href="/story">Walkthrough story mode</Link>
            </div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", flexWrap: "wrap", fontSize: "13.5px", color: "var(--muted)", background: "var(--chip)", padding: "10px 14px", borderRadius: "8px", border: "1px solid var(--line)" }}>
              <span><strong>Demo walk:</strong> Fill an unsold unit at Store A, then try it at Store B (or use <code>X123 (fresh seed)</code>).</span>
              <Link className="button secondary" href="/pos" style={{ padding: "4px 12px", fontSize: "12.5px" }}>Demo walk →</Link>
            </div>
          </div>

          {/* Hero Visual Mock: Small static mock of the verdict card (green verified, red blocked) */}
          <div style={{ display: "flex", flexDirection: "column", gap: "12px", maxWidth: "340px", justifySelf: "center", width: "100%" }}>
            {/* Mini Verified Verdict Mock */}
            <div style={{ background: "var(--card)", border: "1.5px solid var(--ok)", borderRadius: "10px", padding: "14px 16px", boxShadow: "0 4px 16px rgba(0,0,0,0.06)" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", fontWeight: 700, fontSize: "14px", color: "var(--ok)" }}>
                  <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: "18px", height: "18px", borderRadius: "50%", background: "var(--ok-bg)", border: "1px solid var(--ok-border)", fontSize: "11px" }}>✓</span>
                  VERIFIED
                </div>
                <span style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)" }}>serial: SN-8802</span>
              </div>
              <div style={{ fontSize: "12.5px", color: "var(--fg)", marginBottom: "4px" }}>Authenticity confirmed with brand</div>
              <div style={{ fontSize: "11.5px", color: "var(--muted)" }}>PayPal payment order authorized</div>
            </div>

            {/* Mini Blocked Verdict Mock */}
            <div style={{ background: "var(--card)", border: "1.5px solid var(--bad)", borderRadius: "10px", padding: "14px 16px", boxShadow: "0 4px 16px rgba(0,0,0,0.06)" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", fontWeight: 700, fontSize: "14px", color: "var(--bad)" }}>
                  <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: "18px", height: "18px", borderRadius: "50%", background: "var(--bad-bg)", border: "1px solid var(--bad-border)", fontSize: "11px" }}>✕</span>
                  BLOCKED
                </div>
                <span style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)" }}>serial: X123</span>
              </div>
              <div style={{ fontSize: "12.5px", color: "var(--fg)", marginBottom: "4px" }}>Serial not assigned to this store</div>
              <div style={{ fontSize: "11.5px", color: "var(--bad)", fontWeight: 600 }}>Order never created · Investigation opened</div>
            </div>
          </div>
        </div>
      </div>

      {/* 3 Core Value Props - Single row of 3 tiles */}
      <h2 style={{ fontSize: "19px", marginBottom: "14px" }}>Three Principles of TrustLedger</h2>
      <div className="tiles" style={{ marginBottom: "32px" }}>
        <div className="tile card" style={{ padding: "20px", display: "flex", flexDirection: "column" }}>
          <b>Payment Gate, Not Paper Warranties</b>
          <span className="muted" style={{ fontSize: "13.5px", lineHeight: 1.45, marginTop: "6px" }}>
            Authenticity is verified at the POS scanner before the PayPal order is created. Failed units never create an order, so nothing can be paid.
          </span>
        </div>
        <div className="tile card" style={{ padding: "20px", display: "flex", flexDirection: "column" }}>
          <b>Autonomous AI Investigation</b>
          <span className="muted" style={{ fontSize: "13.5px", lineHeight: 1.45, marginTop: "6px" }}>
            When a checkout diverges from the authorized channel, an AI agent investigates supply chain batches and generates cited evidence steps in the brand cockpit.
          </span>
        </div>
        <div className="tile card" style={{ padding: "20px", display: "flex", flexDirection: "column" }}>
          <div style={{ fontSize: "28px", fontWeight: 800, color: "var(--accent)", lineHeight: 1.1, marginBottom: "4px" }}>
            $150B+ a year
          </div>
          <b style={{ fontSize: "14px" }}>Spent on market insights</b>
          <span className="muted" style={{ fontSize: "13px", lineHeight: 1.45, marginTop: "6px", flex: 1 }}>
            While surveys take weeks, and in a 2024 Pew survey 18% of responses were flagged as bogus, TrustLedger answers from verified purchases in seconds without exposing buyers.
          </span>
          <span className="muted" style={{ fontSize: "11px", marginTop: "10px" }}>(ESOMAR, 2024 data)</span>
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
            <h3 style={{ margin: 0, fontSize: "16px", color: "var(--accent)" }}>Moat 2: Buyers Stay Anonymous</h3>
            <span className="badge badge-dp">Differential privacy · OpenDP</span>
          </div>
          <p className="muted" style={{ fontSize: "13.5px", margin: "0 0 12px", lineHeight: 1.5 }}>
            The AI only gets answers about groups, with a little noise added, so no one&apos;s purchase can be picked out.
            Each brand has a fixed privacy limit: asking the same thing again and again can&apos;t reveal anyone. Our internal red-team tried 11 attack types; none pinned down a single buyer.
          </p>
          <div style={{ fontSize: "12.5px", color: "var(--muted)" }}>
            ✓ Every answer shows its margin of error · ✓ Tiny groups hidden · ✓ Questions stop when the limit is reached
          </div>
        </div>
      </div>

      {/* Quick Links Footer Grid */}
      <h2 style={{ fontSize: "19px", marginBottom: "14px" }}>Explore TrustLedger</h2>
      <div className="tiles">
        <Link href="/cockpit" className="tile card">
          <b>Brand Cockpit & Investigations</b>
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
          <b>Privacy & Protections</b>
          <span className="muted">Interactive architecture explainer: how the two nodes protect brand and customer privacy.</span>
        </Link>
      </div>
    </main>
  );
}
