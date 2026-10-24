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
            <h3 style={{ margin: "0 0 6px", fontSize: "15px", color: "var(--fg)", fontWeight: 700 }}>
              1. One buyer protected across all purchases
            </h3>
            <p className="muted small" style={{ margin: "0 0 10px", lineHeight: 1.5, flex: 1 }}>
              The mathematical privacy unit binds to a single buyer across all of a brand&apos;s lifetime questions, preventing reconstruction of activity from multiple transactions.
            </p>
            <div style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)", borderTop: "1px dashed var(--line)", paddingTop: "6px" }}>
              Lifetime privacy unit per buyer across brand
            </div>
          </div>

          <div className="card" style={{ margin: 0, display: "flex", flexDirection: "column" }}>
            <h3 style={{ margin: "0 0 6px", fontSize: "15px", color: "var(--fg)", fontWeight: 700 }}>
              2. Bounded customer influence
            </h3>
            <p className="muted small" style={{ margin: "0 0 10px", lineHeight: 1.5, flex: 1 }}>
              Limits how much any single customer can affect an answer: each buyer contributes to at most 4 cells per query, and individual spend is strictly capped to bound sensitivity.
            </p>
            <div style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)", borderTop: "1px dashed var(--line)", paddingTop: "6px" }}>
              k ≤ 4 cells · spend clamped at 1,000/cell
            </div>
          </div>

          <div className="card" style={{ margin: 0, display: "flex", flexDirection: "column" }}>
            <h3 style={{ margin: "0 0 6px", fontSize: "15px", color: "var(--fg)", fontWeight: 700 }}>
              3. Calibrated differential privacy
            </h3>
            <p className="muted small" style={{ margin: "0 0 10px", lineHeight: 1.5, flex: 1 }}>
              Random mathematical variation is added so individual buyers cannot be singled out. Every released metric carries transparent confidence intervals.
            </p>
            <div style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)", borderTop: "1px dashed var(--line)", paddingTop: "6px" }}>
              OpenDP Gaussian mechanism · zCDP · ±1.96σ confidence
            </div>
          </div>

          <div className="card" style={{ margin: 0, display: "flex", flexDirection: "column" }}>
            <h3 style={{ margin: "0 0 6px", fontSize: "15px", color: "var(--fg)", fontWeight: 700 }}>
              4. Single-spend private release
            </h3>
            <p className="muted small" style={{ margin: "0 0 10px", lineHeight: 1.5, flex: 1 }}>
              Customer answers come from a one-time private release; answering and exploring questions from it spends no further privacy budget (post-processing immunity).
            </p>
            <div style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)", borderTop: "1px dashed var(--line)", paddingTop: "6px" }}>
              ρ = 0.20 (≈ ε 3.69 at δ = 10⁻⁸) · Post-processing immunity
            </div>
          </div>

          <div className="card" style={{ margin: 0, display: "flex", flexDirection: "column" }}>
            <h3 style={{ margin: "0 0 6px", fontSize: "15px", color: "var(--fg)", fontWeight: 700 }}>
              5. Deterministic query cache
            </h3>
            <p className="muted small" style={{ margin: "0 0 10px", lineHeight: 1.5, flex: 1 }}>
              Repeating the exact query returns the stored answer with identical noise, preventing attackers from repeatedly sampling noise to average it out.
            </p>
            <div style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)", borderTop: "1px dashed var(--line)", paddingTop: "6px" }}>
              Deterministic cache · Repeat questions return identical noise
            </div>
          </div>

          <div className="card" style={{ margin: 0, display: "flex", flexDirection: "column" }}>
            <h3 style={{ margin: "0 0 6px", fontSize: "15px", color: "var(--fg)", fontWeight: 700 }}>
              6. Small-group suppression
            </h3>
            <p className="muted small" style={{ margin: "0 0 10px", lineHeight: 1.5, flex: 1 }}>
              Tiny groups of customers are hidden so nobody stands out in a crowd. Result cells below a safe threshold are automatically suppressed.
            </p>
            <div style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)", borderTop: "1px dashed var(--line)", paddingTop: "6px" }}>
              Display floor: count &lt; max(10, 2σ) suppressed
            </div>
          </div>

          <div className="card" style={{ margin: 0, display: "flex", flexDirection: "column" }}>
            <h3 style={{ margin: "0 0 6px", fontSize: "15px", color: "var(--fg)", fontWeight: 700 }}>
              7. High-level categories only
            </h3>
            <p className="muted small" style={{ margin: "0 0 10px", lineHeight: 1.5, flex: 1 }}>
              Queries can only ask about broad aggregate categories (like distributor, store, and week). Personal account IDs, precise timestamps, and individual payment amounts are strictly prohibited.
            </p>
            <div style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)", borderTop: "1px dashed var(--line)", paddingTop: "6px" }}>
              Allowlisted schema: dimensions ≤ 2 · cells ≤ 300 · zero personal IDs
            </div>
          </div>

          <div className="card" style={{ margin: 0, display: "flex", flexDirection: "column" }}>
            <h3 style={{ margin: "0 0 6px", fontSize: "15px", color: "var(--fg)", fontWeight: 700 }}>
              8. Keyed identifier hashing on arrival
            </h3>
            <p className="muted small" style={{ margin: "0 0 10px", lineHeight: 1.5, flex: 1 }}>
              Buyer identities are irreversibly scrambled with a secret key upon arrival. The secret key never leaves the PayPal boundary, and account IDs are never stored raw.
            </p>
            <div style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)", borderTop: "1px dashed var(--line)", paddingTop: "6px" }}>
              HMAC-SHA256 keyed tokenization at PayPal boundary
            </div>
          </div>

        </div>

        {/* Evidence & Verification Footnote */}
        <div className="card elevated" style={{ background: "var(--chip)", padding: "18px 22px", border: "1px solid var(--line)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 700, fontSize: "14px", marginBottom: "4px" }}>
            <span>Evidence &amp; red-team validation</span>
          </div>
          <p style={{ margin: 0, fontSize: "13.5px", lineHeight: 1.5, color: "var(--fg)" }}>
            Internal red-team: 11 attack types tested against private releases, none extracted an individual-level fact.
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
