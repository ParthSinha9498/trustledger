import Link from "next/link";
import { LANDING_COPY } from "@/components/home/copy";
import HeroCheckoutPreview from "@/components/home/HeroCheckoutPreview";
import WhyBrandsPay from "@/components/cockpit/WhyBrandsPay";

export default function Home() {
  const { hero, how, features, business, privacy, closing } = LANDING_COPY;

  return (
    <main style={{ maxWidth: "1080px", margin: "0 auto", padding: "32px 20px 80px" }}>
      {/* 1. Hero: Split layout with interactive checkout gate */}
      <section style={{ marginBottom: "72px" }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
            gap: "48px",
            alignItems: "center",
          }}
        >
          {/* Left Column: Headlines & Actions */}
          <div>
            <div
              style={{
                display: "inline-block",
                padding: "4px 12px",
                borderRadius: "var(--radius-pill)",
                background: "var(--accent-bg)",
                border: "1px solid var(--accent-border)",
                color: "var(--accent)",
                fontSize: "12px",
                fontWeight: 650,
                letterSpacing: "0.03em",
                marginBottom: "16px",
              }}
            >
              {hero.eyebrow}
            </div>
            <h1
              style={{
                fontSize: "clamp(34px, 5vw, 48px)",
                fontWeight: 800,
                lineHeight: 1.15,
                margin: "0 0 16px",
                letterSpacing: "-0.03em",
                color: "var(--fg)",
              }}
            >
              {hero.headline}
            </h1>
            <p
              className="muted"
              style={{
                fontSize: "17px",
                lineHeight: 1.55,
                margin: "0 0 24px",
                maxWidth: "490px",
              }}
            >
              {hero.subhead}
            </p>

            {/* Scope badge */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "12.5px",
                color: "var(--muted)",
                marginBottom: "28px",
              }}
            >
              <span style={{ color: "var(--ok)", fontSize: "14px" }}>✓</span>
              <span>{hero.scopeBadge}</span>
            </div>

            {/* CTAs */}
            <div className="hero-ctas" style={{ display: "flex", gap: "14px", flexWrap: "wrap", alignItems: "center" }}>
              <Link className="button" href="/pos" style={{ padding: "10px 22px", fontSize: "15px" }}>
                {hero.primaryCta}
              </Link>
              <Link className="button secondary" href="/cockpit" style={{ padding: "10px 20px", fontSize: "15px" }}>
                {hero.secondaryCta}
              </Link>
            </div>
          </div>

          {/* Right Column: Visual Centerpiece (Interactive Checkout Gate Preview) */}
          <div style={{ display: "flex", justifyContent: "center", width: "100%" }}>
            <HeroCheckoutPreview />
          </div>
        </div>
      </section>

      {/* 2. How it works: 3 steps horizontally with branching */}
      <section style={{ marginBottom: "72px" }}>
        <div style={{ marginBottom: "28px" }}>
          <h2 style={{ fontSize: "26px", fontWeight: 700, margin: "0 0 8px", letterSpacing: "-0.02em" }}>
            {how.title}
          </h2>
          <p className="muted" style={{ fontSize: "15px", margin: 0 }}>
            {how.subtitle}
          </p>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: "20px",
            position: "relative",
          }}
        >
          {/* Step 1 */}
          <div
            className="card"
            style={{
              padding: "24px",
              borderRadius: "var(--radius-lg)",
              border: "1px solid var(--line)",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
            }}
          >
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "50%",
                background: "var(--accent-bg)",
                color: "var(--accent)",
                border: "1px solid var(--accent-border)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "14px",
                fontWeight: 750,
              }}
            >
              1
            </div>
            <h3 style={{ fontSize: "17px", fontWeight: 700, margin: 0, color: "var(--fg)" }}>
              {how.steps[0].title}
            </h3>
            <p className="muted" style={{ fontSize: "14px", lineHeight: 1.55, margin: 0 }}>
              {how.steps[0].body}
            </p>
          </div>

          {/* Step 2 */}
          <div
            className="card"
            style={{
              padding: "24px",
              borderRadius: "var(--radius-lg)",
              border: "1px solid var(--line)",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
            }}
          >
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "50%",
                background: "var(--chip)",
                color: "var(--fg)",
                border: "1px solid var(--line)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "14px",
                fontWeight: 750,
              }}
            >
              2
            </div>
            <h3 style={{ fontSize: "17px", fontWeight: 700, margin: 0, color: "var(--fg)" }}>
              {how.steps[1].title}
            </h3>
            <p className="muted" style={{ fontSize: "14px", lineHeight: 1.55, margin: 0 }}>
              {how.steps[1].body}
            </p>
          </div>

          {/* Step 3 (Branching Outcomes) */}
          <div
            className="card elevated"
            style={{
              padding: "20px",
              borderRadius: "var(--radius-lg)",
              border: "1px solid var(--line)",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <div
                style={{
                  width: "32px",
                  height: "32px",
                  borderRadius: "50%",
                  background: "var(--chip)",
                  color: "var(--fg)",
                  border: "1px solid var(--line)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "14px",
                  fontWeight: 750,
                }}
              >
                3
              </div>
              <h3 style={{ fontSize: "17px", fontWeight: 700, margin: 0, color: "var(--fg)" }}>
                {how.steps[2].title}
              </h3>
            </div>

            {/* Branch A: Verified */}
            <div
              style={{
                padding: "10px 12px",
                borderRadius: "var(--radius-sm)",
                background: "var(--ok-bg)",
                border: "1px solid var(--ok-border)",
                fontSize: "12.5px",
                display: "flex",
                flexDirection: "column",
                gap: "2px",
              }}
            >
              <div style={{ fontWeight: 700, color: "var(--ok)" }}>✓ Verified: Order Created</div>
              <div style={{ color: "var(--ok-hover)", fontSize: "12px" }}>
                PayPal generates payment order with verification ID attached.
              </div>
            </div>

            {/* Branch B: Blocked */}
            <div
              style={{
                padding: "10px 12px",
                borderRadius: "var(--radius-sm)",
                background: "var(--bad-bg)",
                border: "1px solid var(--bad-border)",
                fontSize: "12.5px",
                display: "flex",
                flexDirection: "column",
                gap: "2px",
              }}
            >
              <div style={{ fontWeight: 700, color: "var(--bad)" }}>✕ Blocked: Investigation Opened</div>
              <div style={{ color: "var(--bad-hover)", fontSize: "12px" }}>
                No payment created. Autonomous agent traces supply chain discrepancy.
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Features: 5 cards with concrete product previews */}
      <section style={{ marginBottom: "72px" }}>
        <div style={{ marginBottom: "28px" }}>
          <h2 style={{ fontSize: "26px", fontWeight: 700, margin: "0 0 8px", letterSpacing: "-0.02em" }}>
            {features.title}
          </h2>
          <p className="muted" style={{ fontSize: "15px", margin: 0 }}>
            {features.subtitle}
          </p>
        </div>

        {/* Top row: 2 Prominent cards (Checkout Gate & AI Investigations) */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
            gap: "24px",
            marginBottom: "24px",
          }}
        >
          {/* Feature 1: Checkout Gate */}
          <Link
            href="/pos"
            className="card elevated"
            style={{
              display: "flex",
              flexDirection: "column",
              padding: "24px",
              borderRadius: "var(--radius-lg)",
              textDecoration: "none",
              color: "inherit",
              border: "1px solid var(--line)",
              transition: "transform 0.15s ease, box-shadow 0.15s ease",
            }}
          >
            {/* Embedded Mini UI Preview */}
            <div
              style={{
                padding: "16px",
                borderRadius: "var(--radius-md)",
                background: "var(--bg)",
                border: "1px solid var(--line)",
                marginBottom: "20px",
                display: "flex",
                flexDirection: "column",
                gap: "10px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--muted)" }}>STORE POS GATEWAY</span>
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 700,
                    padding: "2px 8px",
                    borderRadius: "4px",
                    background: "var(--ok-bg)",
                    color: "var(--ok)",
                    border: "1px solid var(--ok-border)",
                  }}
                >
                  STATUS: VERIFIED
                </span>
              </div>
              <div style={{ fontSize: "13px", fontWeight: 650, color: "var(--fg)" }}>
                Lumina P8 Pro · Serial: <code>SN-P8-88319</code>
              </div>
              <div
                style={{
                  fontSize: "12px",
                  color: "var(--accent)",
                  background: "var(--card)",
                  padding: "8px 10px",
                  borderRadius: "6px",
                  border: "1px solid var(--line)",
                  display: "flex",
                  justifyContent: "space-between",
                }}
              >
                <span>PayPal Order Attached</span>
                <span style={{ fontWeight: 600 }}>#8JP97654EE</span>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: 700,
                  color: "var(--accent)",
                  background: "var(--accent-bg)",
                  padding: "2px 8px",
                  borderRadius: "4px",
                  border: "1px solid var(--accent-border)",
                }}
              >
                Checkout Gate
              </span>
            </div>
            <h3 style={{ fontSize: "19px", fontWeight: 700, margin: "0 0 8px", color: "var(--fg)" }}>
              {features.cards[0].title}
            </h3>
            <p className="muted" style={{ fontSize: "14px", lineHeight: 1.55, margin: 0, flex: 1 }}>
              {features.cards[0].body}
            </p>
            <div style={{ marginTop: "18px", fontSize: "13.5px", fontWeight: 650, color: "var(--accent)" }}>
              Try the store checkout demo →
            </div>
          </Link>

          {/* Feature 2: AI Investigations */}
          <Link
            href="/cockpit"
            className="card elevated"
            style={{
              display: "flex",
              flexDirection: "column",
              padding: "24px",
              borderRadius: "var(--radius-lg)",
              textDecoration: "none",
              color: "inherit",
              border: "1px solid var(--line)",
              transition: "transform 0.15s ease, box-shadow 0.15s ease",
            }}
          >
            {/* Embedded Mini UI Preview */}
            <div
              style={{
                padding: "16px",
                borderRadius: "var(--radius-md)",
                background: "var(--bg)",
                border: "1px solid var(--line)",
                marginBottom: "20px",
                display: "flex",
                flexDirection: "column",
                gap: "8px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--muted)" }}>CASE #INV-2026-042</span>
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 700,
                    padding: "2px 8px",
                    borderRadius: "4px",
                    background: "var(--warn-bg)",
                    color: "var(--warn)",
                    border: "1px solid var(--warn-border)",
                  }}
                >
                  AUTONOMOUS TRACE
                </span>
              </div>
              <div style={{ fontSize: "12px", color: "var(--fg)", lineHeight: 1.4 }}>
                <strong>Step 1:</strong> Query Brand Depot log → <code>London Central (Dispatched)</code>
              </div>
              <div style={{ fontSize: "12px", color: "var(--fg)", lineHeight: 1.4 }}>
                <strong>Step 2:</strong> Scan location mismatch → <code>Attempted Berlin Store #14</code>
              </div>
              <div style={{ fontSize: "11.5px", color: "var(--bad)", fontWeight: 650 }}>
                Discrepancy cited: Off-route diversion flagged without customer identity disclosure
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: 700,
                  color: "var(--accent)",
                  background: "var(--accent-bg)",
                  padding: "2px 8px",
                  borderRadius: "4px",
                  border: "1px solid var(--accent-border)",
                }}
              >
                AI Investigations
              </span>
            </div>
            <h3 style={{ fontSize: "19px", fontWeight: 700, margin: "0 0 8px", color: "var(--fg)" }}>
              {features.cards[1].title}
            </h3>
            <p className="muted" style={{ fontSize: "14px", lineHeight: 1.55, margin: 0, flex: 1 }}>
              {features.cards[1].body}
            </p>
            <div style={{ marginTop: "18px", fontSize: "13.5px", fontWeight: 650, color: "var(--accent)" }}>
              Inspect live brand investigations →
            </div>
          </Link>
        </div>

        {/* Bottom row: 3 Cards (Insights, Supply Chain, Privacy) */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: "20px",
          }}
        >
          {/* Feature 3: Brand Insights */}
          <Link
            href="/cockpit/console"
            className="card"
            style={{
              padding: "22px",
              borderRadius: "var(--radius-lg)",
              textDecoration: "none",
              color: "inherit",
              border: "1px solid var(--line)",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            <div>
              {/* Mini Preview */}
              <div
                style={{
                  padding: "12px",
                  borderRadius: "var(--radius-sm)",
                  background: "var(--bg)",
                  border: "1px solid var(--line)",
                  marginBottom: "14px",
                }}
              >
                <div style={{ fontSize: "11.5px", color: "var(--muted)", marginBottom: "6px" }}>
                  Query: <em>&ldquo;What age group buys P8 in Riverton?&rdquo;</em>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px" }}>
                    <span>25–34</span>
                    <span style={{ fontWeight: 650 }}>48% (±3.2%)</span>
                  </div>
                  <div style={{ width: "100%", height: "5px", background: "var(--chip)", borderRadius: "2px", overflow: "hidden" }}>
                    <div style={{ width: "48%", height: "100%", background: "var(--accent)" }} />
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", marginTop: "2px" }}>
                    <span>35–44</span>
                    <span style={{ fontWeight: 650 }}>31% (±2.8%)</span>
                  </div>
                  <div style={{ width: "100%", height: "5px", background: "var(--chip)", borderRadius: "2px", overflow: "hidden" }}>
                    <div style={{ width: "31%", height: "100%", background: "var(--accent)" }} />
                  </div>
                </div>
              </div>

              <h3 style={{ fontSize: "17px", fontWeight: 700, margin: "0 0 6px", color: "var(--fg)" }}>
                {features.cards[2].title}
              </h3>
              <p className="muted" style={{ fontSize: "13.5px", lineHeight: 1.5, margin: 0 }}>
                {features.cards[2].body}
              </p>
            </div>
            <div style={{ marginTop: "16px", fontSize: "13px", fontWeight: 650, color: "var(--accent)" }}>
              Explore query console →
            </div>
          </Link>

          {/* Feature 4: Supply-chain Timeline */}
          <Link
            href="/cockpit/supply-chain"
            className="card"
            style={{
              padding: "22px",
              borderRadius: "var(--radius-lg)",
              textDecoration: "none",
              color: "inherit",
              border: "1px solid var(--line)",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            <div>
              {/* Mini Preview */}
              <div
                style={{
                  padding: "12px",
                  borderRadius: "var(--radius-sm)",
                  background: "var(--bg)",
                  border: "1px solid var(--line)",
                  marginBottom: "14px",
                }}
              >
                <div style={{ fontSize: "11.5px", color: "var(--muted)", marginBottom: "6px" }}>
                  Batch #BT-40291 Logistics Flow
                </div>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "11px" }}>
                  <span style={{ padding: "2px 6px", background: "var(--chip)", borderRadius: "4px" }}>Factory</span>
                  <span>→</span>
                  <span style={{ padding: "2px 6px", background: "var(--chip)", borderRadius: "4px" }}>EU Hub</span>
                  <span>→</span>
                  <span style={{ padding: "2px 6px", background: "var(--ok-bg)", color: "var(--ok)", borderRadius: "4px", fontWeight: 650 }}>Store POS</span>
                </div>
              </div>

              <h3 style={{ fontSize: "17px", fontWeight: 700, margin: "0 0 6px", color: "var(--fg)" }}>
                {features.cards[3].title}
              </h3>
              <p className="muted" style={{ fontSize: "13.5px", lineHeight: 1.5, margin: 0 }}>
                {features.cards[3].body}
              </p>
            </div>
            <div style={{ marginTop: "16px", fontSize: "13px", fontWeight: 650, color: "var(--accent)" }}>
              View supply chain timeline →
            </div>
          </Link>

          {/* Feature 5: Privacy */}
          <Link
            href="/privacy"
            className="card"
            style={{
              padding: "22px",
              borderRadius: "var(--radius-lg)",
              textDecoration: "none",
              color: "inherit",
              border: "1px solid var(--line)",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            <div>
              {/* Mini Preview */}
              <div
                style={{
                  padding: "12px",
                  borderRadius: "var(--radius-sm)",
                  background: "var(--bg)",
                  border: "1px solid var(--line)",
                  marginBottom: "14px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-around",
                  fontSize: "11px",
                }}
              >
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontWeight: 700 }}>Brand DB</div>
                  <div style={{ color: "var(--muted)", fontSize: "10px" }}>Private node</div>
                </div>
                <div style={{ color: "var(--accent)", fontWeight: 700, fontSize: "12px" }}>
                  ↔ OpenDP ↔
                </div>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontWeight: 700 }}>PayPal DB</div>
                  <div style={{ color: "var(--muted)", fontSize: "10px" }}>Private node</div>
                </div>
              </div>

              <h3 style={{ fontSize: "17px", fontWeight: 700, margin: "0 0 6px", color: "var(--fg)" }}>
                {features.cards[4].title}
              </h3>
              <p className="muted" style={{ fontSize: "13.5px", lineHeight: 1.5, margin: 0 }}>
                {features.cards[4].body}
              </p>
            </div>
            <div style={{ marginTop: "16px", fontSize: "13px", fontWeight: 650, color: "var(--accent)" }}>
              Read privacy architecture →
            </div>
          </Link>
        </div>
      </section>

      {/* 4. Business model: Consolidated section */}
      <section
        className="card elevated"
        style={{
          padding: "36px 32px",
          borderRadius: "var(--radius-lg)",
          marginBottom: "72px",
          borderLeft: "4px solid var(--accent)",
        }}
      >
        <div style={{ marginBottom: "28px" }}>
          <h2 style={{ fontSize: "26px", fontWeight: 700, margin: "0 0 10px", letterSpacing: "-0.02em" }}>
            {business.title}
          </h2>
          <p style={{ fontSize: "16px", color: "var(--muted)", margin: 0, lineHeight: 1.55 }}>
            {business.subhead}
          </p>
        </div>

        {/* Lead with sample Brand Insights question & result */}
        <div
          style={{
            padding: "20px 24px",
            background: "var(--bg)",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--line)",
            marginBottom: "28px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px", flexWrap: "wrap", gap: "8px" }}>
            <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--accent)", letterSpacing: "0.03em" }}>
              SAMPLE BRAND INSIGHTS QUERY
            </span>
            <span style={{ fontSize: "12px", color: "var(--muted)", fontWeight: 600 }}>
              {business.sampleQuery.timing}
            </span>
          </div>
          <div style={{ fontSize: "16px", fontWeight: 700, color: "var(--fg)", marginBottom: "6px" }}>
            &ldquo;{business.sampleQuery.question}&rdquo;
          </div>
          <div style={{ fontSize: "15px", color: "var(--ok)", fontWeight: 650, marginBottom: "8px" }}>
            {business.sampleQuery.result}
          </div>
          <div style={{ fontSize: "12px", color: "var(--muted)" }}>
            {business.sampleQuery.note}
          </div>
        </div>

        {/* Core Formula */}
        <div
          style={{
            padding: "14px 18px",
            background: "var(--accent-bg)",
            border: "1px solid var(--accent-border)",
            borderRadius: "var(--radius-md)",
            fontSize: "15px",
            fontWeight: 700,
            color: "var(--accent)",
            marginBottom: "28px",
            textAlign: "center",
          }}
        >
          {business.formula}
        </div>

        {/* 3 reasons brands pay */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "16px",
            marginBottom: "28px",
          }}
        >
          {business.reasons.map((r) => (
            <div
              key={r.title}
              style={{
                padding: "18px",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--line)",
                background: "var(--card)",
              }}
            >
              <h3 style={{ fontSize: "15.5px", fontWeight: 700, margin: "0 0 6px" }}>{r.title}</h3>
              <p style={{ fontSize: "14px", color: "var(--muted)", margin: 0, lineHeight: 1.55 }}>{r.body}</p>
            </div>
          ))}
        </div>

        {/* Survey vs TrustLedger Comparison Panel */}
        <div style={{ marginBottom: "28px" }}>
          <WhyBrandsPay title="A traditional survey vs TrustLedger verified insights" />
        </div>

        {/* 4-step arrow chain */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "10px",
            marginBottom: "20px",
            padding: "16px",
            background: "var(--bg)",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--line)",
          }}
        >
          {business.chain.map((item, idx) => (
            <div key={idx} style={{ display: "inline-flex", alignItems: "center", gap: "10px" }}>
              <span
                style={{
                  padding: "6px 14px",
                  borderRadius: "6px",
                  background: idx === business.chain.length - 1 ? "var(--ok-bg)" : "var(--card)",
                  color: idx === business.chain.length - 1 ? "var(--ok)" : "var(--fg)",
                  border: `1px solid ${idx === business.chain.length - 1 ? "var(--ok-border)" : "var(--line)"}`,
                  fontSize: "13.5px",
                  fontWeight: 650,
                  whiteSpace: "nowrap",
                }}
              >
                {item}
              </span>
              {idx < business.chain.length - 1 && (
                <span style={{ color: "var(--muted)", fontWeight: 700, fontSize: "14px" }}>→</span>
              )}
            </div>
          ))}
        </div>

        {/* Compact supporting facts (ESOMAR + Pew) */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <p className="muted" style={{ fontSize: "13px", margin: 0 }}>
            • {business.marketStat}
          </p>
          <p className="muted" style={{ fontSize: "13px", margin: 0 }}>
            • {business.pewEvidence}
          </p>
        </div>
      </section>

      {/* 5. Private by design: 2 balanced columns + architecture diagram */}
      <section style={{ marginBottom: "72px" }}>
        <div style={{ marginBottom: "28px" }}>
          <h2 style={{ fontSize: "26px", fontWeight: 700, margin: "0 0 8px", letterSpacing: "-0.02em" }}>
            {privacy.title}
          </h2>
          <p className="muted" style={{ fontSize: "15px", margin: 0 }}>
            {privacy.subtitle}
          </p>
        </div>

        {/* Privacy Architecture Diagram */}
        <div
          className="card elevated"
          style={{
            padding: "24px",
            borderRadius: "var(--radius-lg)",
            border: "1px solid var(--line)",
            marginBottom: "24px",
            background: "var(--bg)",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
              gap: "20px",
              alignItems: "center",
            }}
          >
            {/* Brand Boundary */}
            <div
              style={{
                background: "var(--card)",
                padding: "18px",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--line)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <span style={{ fontWeight: 700, fontSize: "14px" }}>Brand Private Node</span>
                <span style={{ fontSize: "11px", fontWeight: 700, padding: "2px 6px", background: "var(--ok-bg)", color: "var(--ok)", borderRadius: "4px" }}>
                  Private DB
                </span>
              </div>
              <p className="muted" style={{ fontSize: "12.5px", margin: 0, lineHeight: 1.5 }}>
                Houses product serials, production batch logs, and authorized retailer lists. Only deterministic verification verdicts and entity counts exit.
              </p>
            </div>

            {/* Structured Exchange Barrier */}
            <div
              style={{
                border: "1.5px dashed var(--accent)",
                borderRadius: "var(--radius-md)",
                padding: "16px",
                background: "var(--accent-bg)",
                textAlign: "center",
              }}
            >
              <div style={{ fontSize: "13px", fontWeight: 750, color: "var(--accent)", marginBottom: "4px" }}>
                Query Spec Engine
              </div>
              <p className="muted" style={{ fontSize: "12px", margin: 0, lineHeight: 1.45 }}>
                Questions enter as strict JSON specs. Zero raw SQL. Zero direct cross-database credentials.
              </p>
            </div>

            {/* PayPal Boundary */}
            <div
              style={{
                background: "var(--card)",
                padding: "18px",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--line)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <span style={{ fontWeight: 700, fontSize: "14px" }}>PayPal Private Node</span>
                <span style={{ fontSize: "11px", fontWeight: 700, padding: "2px 6px", background: "var(--accent-bg)", color: "var(--accent)", borderRadius: "4px" }}>
                  OpenDP Engine
                </span>
              </div>
              <p className="muted" style={{ fontSize: "12.5px", margin: 0, lineHeight: 1.5 }}>
                Houses customer profiles and transaction records. Only differentially private, group-level estimates with calibrated noise leave this node.
              </p>
            </div>
          </div>
        </div>

        {/* 2 Balanced Columns */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
            gap: "20px",
            marginBottom: "16px",
          }}
        >
          {privacy.columns.map((col, i) => (
            <div
              key={i}
              className="card"
              style={{
                padding: "24px",
                borderRadius: "var(--radius-lg)",
                borderTop: `3px solid ${i === 0 ? "var(--ok)" : "var(--accent)"}`,
              }}
            >
              <h3 style={{ fontSize: "18px", fontWeight: 700, margin: "0 0 16px", color: "var(--fg)" }}>
                {col.title}
              </h3>
              <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "14px", lineHeight: 1.7, color: "var(--fg)" }}>
                {col.bullets.map((bullet, j) => (
                  <li key={j} style={{ marginBottom: "6px" }}>
                    {bullet}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <p className="muted" style={{ fontSize: "13px", margin: 0 }}>
          {privacy.footnote}
        </p>
      </section>

      {/* 6. Closing CTA: Return to the proof */}
      <section
        className="card hero"
        style={{
          padding: "48px 28px",
          textAlign: "center",
          borderRadius: "var(--radius-lg)",
          background: "linear-gradient(180deg, var(--card) 0%, var(--bg) 100%)",
          border: "1px solid var(--line)",
        }}
      >
        <h2 style={{ fontSize: "28px", fontWeight: 800, margin: "0 0 10px", letterSpacing: "-0.02em" }}>
          {closing.headline}
        </h2>
        <p
          className="muted"
          style={{
            fontSize: "16px",
            maxWidth: "560px",
            margin: "0 auto 24px",
            lineHeight: 1.55,
          }}
        >
          {closing.body}
        </p>
        <div style={{ display: "inline-flex", justifyContent: "center" }}>
          <Link className="button" href="/story" style={{ padding: "12px 28px", fontSize: "15px" }}>
            {closing.cta}
          </Link>
        </div>
      </section>
    </main>
  );
}
