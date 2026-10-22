import Link from "next/link";

export const metadata = {
  title: "Privacy Architecture | TrustLedger",
  description: "How TrustLedger protects people: Data never moves and No person is identifiable.",
};

export default function PrivacyPage() {
  return (
    <main className="wide">
      {/* Header */}
      <div style={{ marginBottom: "32px" }}>
        <div className="crumbs">
          <Link href="/">TrustLedger</Link> <span>/</span> <span>Privacy & Protections</span>
        </div>
        <div style={{ display: "inline-flex", alignItems: "center", gap: "8px", padding: "4px 12px", borderRadius: "999px", background: "var(--ok-bg)", color: "var(--ok)", fontSize: "13px", fontWeight: 650, marginBottom: "14px", border: "1px solid var(--ok-border)" }}>
          <span aria-hidden>🔒</span> Formal Mathematical Guarantees (OpenDP · zCDP)
        </div>
        <h1 style={{ fontSize: "32px", letterSpacing: "-0.03em", margin: "0 0 10px" }}>
          How TrustLedger Protects People
        </h1>
        <p className="muted" style={{ fontSize: "16px", maxWidth: "840px", lineHeight: 1.5, margin: 0 }}>
          TrustLedger is built from the ground up on two non-negotiable architectural moats:
          <strong> data never moves</strong>, and <strong>no individual person is identifiable</strong>.
        </p>
      </div>

      {/* Section 1: Data Never Moves */}
      <section style={{ marginBottom: "48px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
          <span style={{ fontSize: "22px" }} aria-hidden>🏛️</span>
          <h2 style={{ fontSize: "22px", margin: 0 }}>Section 1: Data Never Moves</h2>
        </div>
        <p className="muted" style={{ maxWidth: "800px", margin: "0 0 20px" }}>
          Neither customer nor brand records ever leave their local boundary. Questions travel to the data as structured query specifications; only verified verdicts or noisy aggregates travel out.
        </p>

        {/* Visual Node Diagram */}
        <div className="card elevated" style={{ padding: "28px", marginBottom: "20px" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "20px", alignItems: "stretch" }}>
            
            {/* Brand Node */}
            <div style={{ border: "1px solid var(--line)", borderRadius: "12px", padding: "20px", background: "var(--bg)", display: "grid", gap: "12px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontWeight: 700, fontSize: "15px" }}>Brand Node</span>
                <span className="badge badge-exact">Private DB</span>
              </div>
              <p className="muted small" style={{ margin: 0 }}>
                Holds serial numbers, manufacturing batches, authorized distributor shipments, and verification event logs.
              </p>
              <div style={{ padding: "10px", borderRadius: "8px", background: "var(--card)", border: "1px solid var(--line)", fontSize: "12.5px" }}>
                <strong>Allowed Out:</strong> Binary <code>VERIFIED / NOT_VERIFIED</code> and business-level entity counts. Zero consumer identity.
              </div>
            </div>

            {/* Questions Flow Centre */}
            <div style={{ border: "1.5px dashed var(--accent)", borderRadius: "12px", padding: "20px", background: "var(--accent-bg)", display: "grid", placeContent: "center", textAlign: "center", gap: "10px" }}>
              <div style={{ fontSize: "24px" }} aria-hidden>↔</div>
              <strong style={{ color: "var(--accent)", fontSize: "15px" }}>Structured Questions in, Aggregates out</strong>
              <p className="muted small" style={{ margin: 0, lineHeight: 1.45 }}>
                Questions are strict JSON specs—never SQL. The platform API and AI agent have <strong>zero database credentials</strong> to either node.
              </p>
              <div style={{ display: "inline-block", fontSize: "11.5px", fontWeight: 700, background: "var(--card)", padding: "4px 10px", borderRadius: "999px", color: "var(--accent)", border: "1px solid var(--accent-border)" }}>
                The AI never sees a record
              </div>
            </div>

            {/* PayPal Node */}
            <div style={{ border: "1px solid var(--line)", borderRadius: "12px", padding: "20px", background: "var(--bg)", display: "grid", gap: "12px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontWeight: 700, fontSize: "15px" }}>PayPal Node</span>
                <span className="badge badge-dp">DP Boundary</span>
              </div>
              <p className="muted small" style={{ margin: 0 }}>
                Holds transactions, store payments, irreversible hashed buyer IDs, and simulated buyer demographics.
              </p>
              <div style={{ padding: "10px", borderRadius: "8px", background: "var(--card)", border: "1px solid var(--line)", fontSize: "12.5px" }}>
                <strong>Allowed Out:</strong> Calibrated differential privacy aggregates with ±95% confidence intervals.
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* Section 2: No Person Identifiable */}
      <section style={{ marginBottom: "40px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
          <span style={{ fontSize: "22px" }} aria-hidden>🛡️</span>
          <h2 style={{ fontSize: "22px", margin: 0 }}>Section 2: No Person Is Identifiable</h2>
        </div>
        <p className="muted" style={{ maxWidth: "800px", margin: "0 0 24px" }}>
          Eight layered cryptographic and differential privacy mechanisms protect consumer anonymity. Even with unlimited arbitrary queries, an individual&apos;s purchase cannot be isolated.
        </p>

        {/* 8 Protection Cards Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px", marginBottom: "32px" }}>
          
          <div className="card" style={{ margin: 0 }}>
            <div style={{ fontSize: "20px", marginBottom: "6px" }} aria-hidden>👤</div>
            <h3 style={{ margin: "0 0 6px", fontSize: "15px" }}>1. Single Privacy Unit</h3>
            <p className="muted small" style={{ margin: 0, lineHeight: 1.5 }}>
              The mathematical privacy unit is <strong>one buyer across all of a brand&apos;s questions</strong>, rather than isolated per-transaction events. All lifetime queries bind to the same unit.
            </p>
          </div>

          <div className="card" style={{ margin: 0 }}>
            <div style={{ fontSize: "20px", marginBottom: "6px" }} aria-hidden>📏</div>
            <h3 style={{ margin: "0 0 6px", fontSize: "15px" }}>2. Cell & Spend Clamping</h3>
            <p className="muted small" style={{ margin: 0, lineHeight: 1.5 }}>
              Each buyer counts in at most <strong>≤ 4 cells per question</strong> (k=1 for demographic-only grouping), and individual spend is strictly clamped at 1,000 per cell to bound outlier sensitivity.
            </p>
          </div>

          <div className="card" style={{ margin: 0 }}>
            <div style={{ fontSize: "20px", marginBottom: "6px" }} aria-hidden>📈</div>
            <h3 style={{ margin: "0 0 6px", fontSize: "15px" }}>3. Calibrated Gaussian Noise</h3>
            <p className="muted small" style={{ margin: 0, lineHeight: 1.5 }}>
              Noise is generated via <strong>OpenDP</strong> under Zero-Concentrated Differential Privacy (zCDP). Every released metric is published with transparent <strong>±95% confidence intervals</strong>.
            </p>
          </div>

          <div className="card" style={{ margin: 0 }}>
            <div style={{ fontSize: "20px", marginBottom: "6px" }} aria-hidden>⏱️</div>
            <h3 style={{ margin: "0 0 6px", fontSize: "15px" }}>4. Lifetime Privacy Budget</h3>
            <p className="muted small" style={{ margin: 0, lineHeight: 1.5 }}>
              Each brand operates under a fixed lifetime budget of <strong>ρ = 0.25 (≈ ε 4.16 at δ = 10⁻⁸)</strong>. When the budget is depleted, the node issues a hard refusal to prevent reconstruction attacks.
            </p>
          </div>

          <div className="card" style={{ margin: 0 }}>
            <div style={{ fontSize: "20px", marginBottom: "6px" }} aria-hidden>🔁</div>
            <h3 style={{ margin: "0 0 6px", fontSize: "15px" }}>5. Deterministic Query Cache</h3>
            <p className="muted small" style={{ margin: 0, lineHeight: 1.5 }}>
              Repeated or permuted queries return the exact same cached answer with zero additional privacy cost. Attackers cannot repeatedly sample noise to average out the variance.
            </p>
          </div>

          <div className="card" style={{ margin: 0 }}>
            <div style={{ fontSize: "20px", marginBottom: "6px" }} aria-hidden>👁️‍🗨️</div>
            <h3 style={{ margin: "0 0 6px", fontSize: "15px" }}>6. Small Groups Hidden</h3>
            <p className="muted small" style={{ margin: 0, lineHeight: 1.5 }}>
              Display floor enforcement: cells below <code>max(10, 2σ)</code> are automatically suppressed after noise to eliminate small-cohort re-identification, while empty groups are listed to preserve shape.
            </p>
          </div>

          <div className="card" style={{ margin: 0 }}>
            <div style={{ fontSize: "20px", marginBottom: "6px" }} aria-hidden>📑</div>
            <h3 style={{ margin: "0 0 6px", fontSize: "15px" }}>7. Allowlisted Dimensions Only</h3>
            <p className="muted small" style={{ margin: 0, lineHeight: 1.5 }}>
              Strict schema constraints: queries are limited to ≤ 2 dimensions and ≤ 300 cells. Payer IDs, precise timestamps, and per-buyer payment amounts are completely disallowed.
            </p>
          </div>

          <div className="card" style={{ margin: 0 }}>
            <div style={{ fontSize: "20px", marginBottom: "6px" }} aria-hidden>🔑</div>
            <h3 style={{ margin: "0 0 6px", fontSize: "15px" }}>8. Hashed Payer IDs on Ingestion</h3>
            <p className="muted small" style={{ margin: 0, lineHeight: 1.5 }}>
              Raw buyer identifiers are irreversibly hashed upon ingestion into the PayPal node. Cleartext buyer names, account numbers, and credit card credentials never enter the query database.
            </p>
          </div>

        </div>

        {/* Evidence & Verification Footnote */}
        <div className="card elevated" style={{ background: "var(--chip)", padding: "18px 22px", border: "1px solid var(--line)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 700, fontSize: "14px", marginBottom: "4px" }}>
            <span aria-hidden>🧪</span> Evidence & Red-Team Validation
          </div>
          <p style={{ margin: 0, fontSize: "13.5px", lineHeight: 1.5, color: "var(--fg)" }}>
            <strong>Internal red-team:</strong> Across 11 attack types (membership inference, differencing, reconstruction, and noisy averaging), none extracted an individual&apos;s data (verified in <code>evals/redteam.py</code>).
          </p>
          <div style={{ marginTop: "10px", fontSize: "12px", color: "var(--muted)", borderTop: "1px dashed var(--line)", paddingTop: "8px" }}>
            <strong>Note on scope & credentials:</strong> Brand entity counts are exact because they describe business inventories, not people. The hackathon demo operates with a shared node token; production deployment binds per-brand credentials so <code>brand_id</code> cannot be specified by the caller.
          </div>
        </div>

      </section>

      {/* Navigation Footer */}
      <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", borderTop: "1px solid var(--line)", paddingTop: "20px" }}>
        <Link className="button" href="/cockpit/console">Try the Brand Insights Console</Link>
        <Link className="button secondary" href="/cockpit">View Live Investigations</Link>
        <Link className="button secondary" href="/">Back to Home</Link>
      </div>
    </main>
  );
}
