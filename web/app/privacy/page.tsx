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
          
          <div className="card" style={{ margin: 0, display: "flex", flexDirection: "column" }}>
            <div style={{ fontWeight: 700, fontSize: "14px", color: "var(--fg)", marginBottom: "6px" }}>
              One buyer is protected across all queries, not per transaction.
            </div>
            <h3 style={{ margin: "0 0 6px", fontSize: "13px", color: "var(--accent)" }}>1. Single privacy unit</h3>
            <p className="muted small" style={{ margin: "0 0 10px", lineHeight: 1.5, flex: 1 }}>
              The mathematical privacy unit binds to a single buyer across all of a brand&apos;s lifetime questions, preventing reconstruction from multiple purchases.
            </p>
            <div style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)", borderTop: "1px dashed var(--line)", paddingTop: "6px" }}>
              unit: u_buyer (lifetime across brand)
            </div>
          </div>

          <div className="card" style={{ margin: 0, display: "flex", flexDirection: "column" }}>
            <div style={{ fontWeight: 700, fontSize: "14px", color: "var(--fg)", marginBottom: "6px" }}>
              Limits how much any single customer can influence an answer.
            </div>
            <h3 style={{ margin: "0 0 6px", fontSize: "13px", color: "var(--accent)" }}>2. Cell &amp; spend clamping</h3>
            <p className="muted small" style={{ margin: "0 0 10px", lineHeight: 1.5, flex: 1 }}>
              Each buyer contributes to at most 4 cells per query, and individual spend is strictly capped at 1,000 to bound sensitivity.
            </p>
            <div style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)", borderTop: "1px dashed var(--line)", paddingTop: "6px" }}>
              k ≤ 4 cells · spend clamped at 1,000/cell
            </div>
          </div>

          <div className="card" style={{ margin: 0, display: "flex", flexDirection: "column" }}>
            <div style={{ fontWeight: 700, fontSize: "14px", color: "var(--fg)", marginBottom: "6px" }}>
              Random variation is added so individual buyers cannot be picked out.
            </div>
            <h3 style={{ margin: "0 0 6px", fontSize: "13px", color: "var(--accent)" }}>3. Calibrated Gaussian noise</h3>
            <p className="muted small" style={{ margin: "0 0 10px", lineHeight: 1.5, flex: 1 }}>
              Noise is generated via <strong>OpenDP</strong> under Zero-Concentrated Differential Privacy (zCDP). Every released metric carries transparent <strong>±95% confidence intervals</strong>.
            </p>
            <div style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)", borderTop: "1px dashed var(--line)", paddingTop: "6px" }}>
              OpenDP Gaussian mechanism · zCDP · ±1.96σ
            </div>
          </div>

          <div className="card" style={{ margin: 0, display: "flex", flexDirection: "column" }}>
            <div style={{ fontWeight: 700, fontSize: "14px", color: "var(--fg)", marginBottom: "6px" }}>
              A fixed privacy limit: asking more questions can&apos;t reveal more about anyone.
            </div>
            <h3 style={{ margin: "0 0 6px", fontSize: "13px", color: "var(--accent)" }}>4. Private release (budget spent once)</h3>
            <p className="muted small" style={{ margin: "0 0 10px", lineHeight: 1.5, flex: 1 }}>
              Buyer answers come from a one-time private release; answering questions from it spends no further privacy budget (post-processing).
            </p>
            <div style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)", borderTop: "1px dashed var(--line)", paddingTop: "6px" }}>
              ρ = 0.20 (≈ ε 3.69 at δ = 10⁻⁸) · Post-processing immunity
            </div>
          </div>

          <div className="card" style={{ margin: 0, display: "flex", flexDirection: "column" }}>
            <div style={{ fontWeight: 700, fontSize: "14px", color: "var(--fg)", marginBottom: "6px" }}>
              Repeating the exact question returns the same answer without averaging.
            </div>
            <h3 style={{ margin: "0 0 6px", fontSize: "13px", color: "var(--accent)" }}>5. Deterministic query cache</h3>
            <p className="muted small" style={{ margin: "0 0 10px", lineHeight: 1.5, flex: 1 }}>
              Repeating a query returns the cached answer with identical noise, preventing attackers from repeatedly sampling noise to average it out.
            </p>
            <div style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)", borderTop: "1px dashed var(--line)", paddingTop: "6px" }}>
              repeat questions return the stored answer (same noise) · _cache_key (paypal_node/main.py:83)
            </div>
          </div>

          <div className="card" style={{ margin: 0, display: "flex", flexDirection: "column" }}>
            <div style={{ fontWeight: 700, fontSize: "14px", color: "var(--fg)", marginBottom: "6px" }}>
              Tiny groups of customers are hidden so nobody stands out in a crowd.
            </div>
            <h3 style={{ margin: "0 0 6px", fontSize: "13px", color: "var(--accent)" }}>6. Small groups hidden</h3>
            <p className="muted small" style={{ margin: "0 0 10px", lineHeight: 1.5, flex: 1 }}>
              Display floor enforcement: cells below a safe threshold are automatically hidden after noise to reduce small-cohort re-identification.
            </p>
            <div style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)", borderTop: "1px dashed var(--line)", paddingTop: "6px" }}>
              display floor = max(10, 2σ)
            </div>
          </div>

          <div className="card" style={{ margin: 0, display: "flex", flexDirection: "column" }}>
            <div style={{ fontWeight: 700, fontSize: "14px", color: "var(--fg)", marginBottom: "6px" }}>
              Queries can only ask about broad categories, never personal details.
            </div>
            <h3 style={{ margin: "0 0 6px", fontSize: "13px", color: "var(--accent)" }}>7. Allowlisted dimensions only</h3>
            <p className="muted small" style={{ margin: "0 0 10px", lineHeight: 1.5, flex: 1 }}>
              Strict schema constraints: queries are limited to allowable aggregate dimensions. Payer IDs, precise timestamps, and individual payment amounts are completely disallowed.
            </p>
            <div style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)", borderTop: "1px dashed var(--line)", paddingTop: "6px" }}>
              dimensions ≤ 2 · cells ≤ 300 · no raw IDs
            </div>
          </div>

          <div className="card" style={{ margin: 0, display: "flex", flexDirection: "column" }}>
            <div style={{ fontWeight: 700, fontSize: "14px", color: "var(--fg)", marginBottom: "6px" }}>
              Customer identities are scrambled with a secret key before entering.
            </div>
            <h3 style={{ margin: "0 0 6px", fontSize: "13px", color: "var(--accent)" }}>8. Hashed payer IDs on arrival</h3>
            <p className="muted small" style={{ margin: "0 0 10px", lineHeight: 1.5, flex: 1 }}>
              Buyer IDs are replaced by a keyed hash on arrival; the secret key never leaves the PayPal-side node. Payer IDs are never stored raw (paypal_node/main.py:424).
            </p>
            <div style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)", borderTop: "1px dashed var(--line)", paddingTop: "6px" }}>
              HMAC-SHA256(payer_hash_key, payer_ref)
            </div>
          </div>

        </div>

        {/* Evidence & Verification Footnote */}
        <div className="card elevated" style={{ background: "var(--chip)", padding: "18px 22px", border: "1px solid var(--line)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 700, fontSize: "14px", marginBottom: "4px" }}>
            <span>Evidence &amp; red-team validation</span>
          </div>
          <p style={{ margin: 0, fontSize: "13.5px", lineHeight: 1.5, color: "var(--fg)" }}>
            Internal red-team: 11 attack types, none extracted a confident individual-level fact (<code>evals/results/redteam_repeated.md</code>).
          </p>
          <details style={{ marginTop: "12px", fontSize: "12px", color: "var(--muted)", borderTop: "1px dashed var(--line)", paddingTop: "10px", cursor: "pointer" }}>
            <summary style={{ fontWeight: 650, color: "var(--fg)" }}>Note on scope &amp; credentials</summary>
            <p style={{ margin: "8px 0 0", lineHeight: 1.5 }}>
              Brand entity counts are exact because they describe businesses, not people. The hackathon demo operates with a shared node token; a production deployment would issue per-brand credentials so <code>brand_id</code> cannot be chosen by the caller.
            </p>
          </details>
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
