import Link from "next/link";

export const metadata = {
  title: "Privacy Architecture | TrustLedger",
  description: "How TrustLedger protects people: Data never moves and no person is identifiable.",
};

export default function PrivacyPage() {
  return (
    <main className="wide">
      {/* Header */}
      <div style={{ marginBottom: "32px" }}>
        <div className="crumbs">
          <Link href="/">TrustLedger</Link> <span>/</span> <span>Privacy</span>
        </div>
        <div style={{ display: "inline-flex", alignItems: "center", gap: "8px", padding: "4px 12px", borderRadius: "999px", background: "var(--ok-bg)", color: "var(--ok)", fontSize: "13px", fontWeight: 650, marginBottom: "14px", border: "1px solid var(--ok-border)" }}>
          <span aria-hidden>🔒</span> Formal guarantees (OpenDP · zCDP)
        </div>
        <h1 style={{ fontSize: "32px", letterSpacing: "-0.03em", margin: "0 0 10px" }}>
          How TrustLedger protects people
        </h1>
        <p className="muted" style={{ fontSize: "16px", maxWidth: "840px", lineHeight: 1.5, margin: 0 }}>
          TrustLedger is built from the ground up on two architectural moats:
          <strong> data never moves</strong>, and <strong>no person is identifiable</strong>.
        </p>
      </div>

      {/* Part 1: Data Never Moves */}
      <section style={{ marginBottom: "48px" }}>
        <h2 style={{ fontSize: "22px", margin: "0 0 8px" }}>Data never moves</h2>
        <p className="muted" style={{ maxWidth: "800px", margin: "0 0 20px" }}>
          Neither customer nor brand records ever leave their local boundary. Questions travel to the data as structured query specifications; only verified verdicts or noisy aggregates travel out.
        </p>

        {/* Visual Node Diagram with AI Box */}
        <div className="card elevated" style={{ padding: "28px", marginBottom: "20px" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "20px", alignItems: "stretch" }}>
            
            {/* Brand Node */}
            <div style={{ border: "1px solid var(--line)", borderRadius: "12px", padding: "20px", background: "var(--bg)", display: "grid", gap: "12px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontWeight: 700, fontSize: "15px" }}>Brand node</span>
                <span className="badge badge-exact">Private DB</span>
              </div>
              <p className="muted small" style={{ margin: 0 }}>
                Holds serial numbers, manufacturing batches, distributor shipments, and checkout verification logs.
              </p>
              <div style={{ padding: "10px", borderRadius: "8px", background: "var(--card)", border: "1px solid var(--line)", fontSize: "12.5px" }}>
                <strong>Allowed out:</strong> <code>VERIFIED</code> or <code>NOT_VERIFIED</code> with a reason code, plus business-level entity counts. Zero consumer identity.
              </div>
            </div>

            {/* Questions Flow Centre with AI Box */}
            <div style={{ border: "1.5px dashed var(--accent)", borderRadius: "12px", padding: "20px", background: "var(--accent-bg)", display: "grid", placeContent: "center", textAlign: "center", gap: "12px" }}>
              <div style={{ display: "flex", justifyContent: "center", gap: "16px", fontSize: "13px", fontWeight: 700, color: "var(--accent)" }}>
                <span>Structured questions in →</span>
                <span>← Aggregates out</span>
              </div>
              <p className="muted small" style={{ margin: 0, lineHeight: 1.45 }}>
                Questions are strict JSON specs—never arbitrary SQL. The platform API and AI agent have <strong>zero database credentials</strong> to either node.
              </p>
              <div style={{ display: "inline-block", fontSize: "12px", fontWeight: 650, background: "var(--card)", padding: "6px 12px", borderRadius: "8px", color: "var(--fg)", border: "1px solid var(--line)", boxShadow: "var(--shadow-sm)" }}>
                Autonomous AI investigation: <strong>The AI never sees a record</strong>
              </div>
            </div>

            {/* PayPal Node */}
            <div style={{ border: "1px solid var(--line)", borderRadius: "12px", padding: "20px", background: "var(--bg)", display: "grid", gap: "12px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontWeight: 700, fontSize: "15px" }}>PayPal-side node</span>
                <span className="badge badge-dp">DP Boundary</span>
              </div>
              <p className="muted small" style={{ margin: 0 }}>
                Holds transactions, store payments, hashed buyer IDs, and demographics (demographics exist only on the PayPal side).
              </p>
              <div style={{ padding: "10px", borderRadius: "8px", background: "var(--card)", border: "1px solid var(--line)", fontSize: "12.5px" }}>
                <strong>Allowed out:</strong> Calibrated differential privacy aggregates with ±95% confidence intervals.
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* Part 2: No Person Identifiable */}
      <section style={{ marginBottom: "40px" }}>
        <h2 style={{ fontSize: "22px", margin: "0 0 8px" }}>No person is identifiable</h2>
        <p className="muted" style={{ maxWidth: "800px", margin: "0 0 24px" }}>
          Eight protections bound the privacy risk of every query released by the system.
        </p>

        {/* 8 Protection Cards Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px", marginBottom: "32px" }}>
          
          <div className="card" style={{ margin: 0 }}>
            <h3 style={{ margin: "0 0 6px", fontSize: "15px" }}>1. Single privacy unit</h3>
            <p className="muted small" style={{ margin: 0, lineHeight: 1.5 }}>
              The mathematical privacy unit is <strong>one buyer across all of a brand&apos;s questions</strong>, rather than isolated per-transaction events. All lifetime queries bind to the same unit.
            </p>
          </div>

          <div className="card" style={{ margin: 0 }}>
            <h3 style={{ margin: "0 0 6px", fontSize: "15px" }}>2. Cell & spend clamping</h3>
            <p className="muted small" style={{ margin: 0, lineHeight: 1.5 }}>
              Each buyer counts in at most <strong>4 cells per question</strong> (k=1 for demographic-only grouping), and individual spend is strictly clamped at 1,000 per cell to bound sensitivity.
            </p>
          </div>

          <div className="card" style={{ margin: 0 }}>
            <h3 style={{ margin: "0 0 6px", fontSize: "15px" }}>3. Calibrated Gaussian noise</h3>
            <p className="muted small" style={{ margin: 0, lineHeight: 1.5 }}>
              Noise is generated via <strong>OpenDP</strong> under Zero-Concentrated Differential Privacy (zCDP). Every released metric carries transparent <strong>±95% confidence intervals</strong>.
            </p>
          </div>

          <div className="card" style={{ margin: 0 }}>
            <h3 style={{ margin: "0 0 6px", fontSize: "15px" }}>4. Private release (budget spent once)</h3>
            <p className="muted small" style={{ margin: 0, lineHeight: 1.5 }}>
              Each brand operates under a private release measured once under zCDP with <strong>ρ = 0.20 (≈ ε 3.69 at δ = 10⁻⁸)</strong>. Under post-processing immunity (Dwork &amp; Roth 2014), queries are answered from the private release: no further budget spent.
            </p>
          </div>

          <div className="card" style={{ margin: 0 }}>
            <h3 style={{ margin: "0 0 6px", fontSize: "15px" }}>5. Deterministic query cache</h3>
            <p className="muted small" style={{ margin: 0, lineHeight: 1.5 }}>
              Repeating a question returns the same answer at no cost, and every new question spends budget. Attackers cannot repeatedly sample noise to average out the variance.
            </p>
          </div>

          <div className="card" style={{ margin: 0 }}>
            <h3 style={{ margin: "0 0 6px", fontSize: "15px" }}>6. Small groups hidden</h3>
            <p className="muted small" style={{ margin: 0, lineHeight: 1.5 }}>
              Display floor enforcement: cells below <code>max(10, 2σ)</code> are automatically hidden after noise to reduce small-cohort re-identification, while empty groups are listed to preserve shape.
            </p>
          </div>

          <div className="card" style={{ margin: 0 }}>
            <h3 style={{ margin: "0 0 6px", fontSize: "15px" }}>7. Allowlisted dimensions only</h3>
            <p className="muted small" style={{ margin: 0, lineHeight: 1.5 }}>
              Strict schema constraints: queries are limited to ≤ 2 dimensions and ≤ 300 cells. Payer IDs, precise timestamps, and per-buyer payment amounts are completely disallowed.
            </p>
          </div>

          <div className="card" style={{ margin: 0 }}>
            <h3 style={{ margin: "0 0 6px", fontSize: "15px" }}>8. Hashed payer IDs on arrival</h3>
            <p className="muted small" style={{ margin: 0, lineHeight: 1.5 }}>
              Buyer IDs are replaced by a keyed hash on arrival; the key never leaves the PayPal-side node. Raw buyer names, account numbers, and payment details never enter the query database.
            </p>
          </div>

        </div>

        {/* Evidence & Verification Footnote */}
        <div className="card elevated" style={{ background: "var(--chip)", padding: "18px 22px", border: "1px solid var(--line)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 700, fontSize: "14px", marginBottom: "4px" }}>
            <span>Evidence & red-team validation</span>
          </div>
          <p style={{ margin: 0, fontSize: "13.5px", lineHeight: 1.5, color: "var(--fg)" }}>
            Internal red-team: 11 attack types, none extracted a confident individual-level fact (<code>evals/results/redteam_repeated.md</code>).
          </p>
          <div style={{ marginTop: "10px", fontSize: "12px", color: "var(--muted)", borderTop: "1px dashed var(--line)", paddingTop: "8px" }}>
            <strong>Note on scope & credentials:</strong> Brand entity counts are exact because they describe businesses, not people. The hackathon demo operates with a shared node token; a production deployment would issue per-brand credentials so <code>brand_id</code> cannot be chosen by the caller.
          </div>
        </div>

      </section>

      {/* Navigation Footer */}
      <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", borderTop: "1px solid var(--line)", paddingTop: "20px" }}>
        <Link className="button" href="/cockpit/console">Try Brand Insights</Link>
        <Link className="button secondary" href="/cockpit">View investigations</Link>
        <Link className="button secondary" href="/">Back to home</Link>
      </div>
    </main>
  );
}
