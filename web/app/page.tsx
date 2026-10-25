import Link from "next/link";
import { LANDING_COPY } from "@/components/home/copy";
import WhyBrandsPay from "@/components/cockpit/WhyBrandsPay";

export default function Home() {
  const { hero, heroFlow, how, features, business, privacy, closing } = LANDING_COPY;

  return (
    <main style={{ maxWidth: "1080px", margin: "0 auto", padding: "32px 20px 80px" }}>
      {/* 1. Hero: Lead with the transaction gate */}
      <section style={{ marginBottom: "64px" }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
            gap: "40px",
            alignItems: "center",
          }}
        >
          {/* Left Column: Headlines & Actions */}
          <div>
            <div
              style={{
                display: "inline-block",
                padding: "4px 10px",
                borderRadius: "9999px",
                background: "var(--accent-bg)",
                border: "1px solid var(--accent-border)",
                color: "var(--accent)",
                fontSize: "12px",
                fontWeight: 600,
                letterSpacing: "0.03em",
                marginBottom: "14px",
              }}
            >
              {hero.eyebrow}
            </div>
            <h1
              style={{
                fontSize: "clamp(32px, 5vw, 44px)",
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
                margin: "0 0 28px",
                maxWidth: "480px",
              }}
            >
              {hero.subhead}
            </p>
            <div className="hero-ctas" style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center" }}>
              <Link className="button" href="/pos">
                {hero.primaryCta}
              </Link>
              <Link className="button secondary" href="/cockpit">
                {hero.secondaryCta}
              </Link>
            </div>
          </div>

          {/* Right Column: Visual Centerpiece (3-Stage Flow Card + Quiet Blocked State) */}
          <div style={{ display: "flex", flexDirection: "column", gap: "14px", width: "100%", maxWidth: "420px", justifySelf: "center" }}>
            {/* 3-Stage Verified Flow */}
            <div
              className="card elevated"
              style={{
                padding: "20px",
                border: "1px solid var(--line)",
                borderRadius: "var(--radius-lg)",
                boxShadow: "var(--shadow-md)",
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {heroFlow.steps.map((st, i) => (
                  <div key={i} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                    <div style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
                      <span
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          justifyContent: "center",
                          padding: "2px 8px",
                          borderRadius: "6px",
                          fontSize: "11px",
                          fontWeight: 700,
                          background: i === 1 ? "var(--ok-bg)" : i === 2 ? "var(--accent-bg)" : "var(--chip)",
                          color: i === 1 ? "var(--ok)" : i === 2 ? "var(--accent)" : "var(--muted)",
                          border: `1px solid ${i === 1 ? "var(--ok-border)" : i === 2 ? "var(--accent-border)" : "var(--line)"}`,
                          marginTop: "2px",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {st.badge}
                      </span>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 600, fontSize: "14px", color: "var(--fg)" }}>{st.title}</div>
                        <div style={{ fontSize: "12.5px", color: "var(--muted)", marginTop: "2px" }}>{st.body}</div>
                      </div>
                    </div>
                    {i < heroFlow.steps.length - 1 && (
                      <div
                        style={{
                          marginLeft: "24px",
                          height: "12px",
                          borderLeft: "2px dashed var(--line)",
                        }}
                      />
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Quiet Blocked State */}
            <div
              className="card"
              style={{
                padding: "14px 18px",
                background: "var(--bad-bg)",
                border: "1px solid var(--bad-border)",
                borderRadius: "var(--radius-md)",
                display: "flex",
                alignItems: "flex-start",
                gap: "12px",
              }}
            >
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: "2px 8px",
                  borderRadius: "6px",
                  fontSize: "11px",
                  fontWeight: 700,
                  background: "var(--bad)",
                  color: "#ffffff",
                  marginTop: "2px",
                }}
              >
                {heroFlow.blocked.badge}
              </span>
              <div>
                <div style={{ fontWeight: 600, fontSize: "13.5px", color: "var(--bad)" }}>
                  {heroFlow.blocked.title}
                </div>
                <div style={{ fontSize: "12px", color: "var(--bad-hover)", marginTop: "2px" }}>
                  {heroFlow.blocked.body}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. How it works: 3 connected steps */}
      <section style={{ marginBottom: "64px" }}>
        <h2 style={{ fontSize: "24px", fontWeight: 700, marginBottom: "24px", letterSpacing: "-0.02em" }}>
          {how.title}
        </h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: "20px",
          }}
        >
          {how.steps.map((st, i) => (
            <div
              key={i}
              className="card"
              style={{
                padding: "24px",
                borderRadius: "var(--radius-lg)",
                position: "relative",
              }}
            >
              <div
                style={{
                  width: "28px",
                  height: "28px",
                  borderRadius: "50%",
                  background: "var(--accent-bg)",
                  color: "var(--accent)",
                  border: "1px solid var(--accent-border)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "13px",
                  fontWeight: 700,
                  marginBottom: "14px",
                }}
              >
                {i + 1}
              </div>
              <h3 style={{ fontSize: "17px", fontWeight: 600, margin: "0 0 8px", color: "var(--fg)" }}>
                {st.title}
              </h3>
              <p className="muted" style={{ fontSize: "14px", lineHeight: 1.55, margin: 0 }}>
                {st.body}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* 3. Features: 5 cards (2 large with screenshots, 3 small) */}
      <section style={{ marginBottom: "64px" }}>
        <h2 style={{ fontSize: "24px", fontWeight: 700, marginBottom: "24px", letterSpacing: "-0.02em" }}>
          {features.title}
        </h2>

        {/* Top row: 2 Large cards with screenshots */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
            gap: "20px",
            marginBottom: "20px",
          }}
        >
          {features.cards
            .filter((c) => c.size === "large")
            .map((c, i) => (
              <Link
                key={i}
                href={c.href}
                className="card elevated"
                style={{
                  display: "flex",
                  flexDirection: "column",
                  padding: "20px",
                  borderRadius: "var(--radius-lg)",
                  textDecoration: "none",
                  color: "inherit",
                  transition: "transform 0.15s ease, box-shadow 0.15s ease",
                  overflow: "hidden",
                }}
              >
                {c.image && (
                  <div
                    style={{
                      width: "100%",
                      borderRadius: "var(--radius-md)",
                      overflow: "hidden",
                      border: "1px solid var(--line)",
                      marginBottom: "16px",
                      background: "var(--bg)",
                    }}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={c.image}
                      alt={c.title}
                      style={{
                        width: "100%",
                        height: "auto",
                        display: "block",
                        objectFit: "cover",
                      }}
                    />
                  </div>
                )}
                <h3 style={{ fontSize: "18px", fontWeight: 700, margin: "0 0 8px", color: "var(--fg)" }}>
                  {c.title}
                </h3>
                <p className="muted" style={{ fontSize: "14px", lineHeight: 1.5, margin: 0, flex: 1 }}>
                  {c.body}
                </p>
              </Link>
            ))}
        </div>

        {/* Bottom row: 3 Small cards */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: "16px",
          }}
        >
          {features.cards
            .filter((c) => c.size !== "large")
            .map((c, i) => (
              <Link
                key={i}
                href={c.href}
                className="card"
                style={{
                  padding: "20px",
                  borderRadius: "var(--radius-md)",
                  textDecoration: "none",
                  color: "inherit",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                }}
              >
                <div>
                  <h3 style={{ fontSize: "16px", fontWeight: 600, margin: "0 0 8px", color: "var(--fg)" }}>
                    {c.title}
                  </h3>
                  <p className="muted" style={{ fontSize: "13.5px", lineHeight: 1.5, margin: 0 }}>
                    {c.body}
                  </p>
                </div>
                <div style={{ marginTop: "14px", fontSize: "13px", fontWeight: 600, color: "var(--accent)" }}>
                  Learn more →
                </div>
              </Link>
            ))}
        </div>
      </section>

      {/* 4. Business model: 4-step arrow chain + 3 explanatory lines */}
      <section
        className="card elevated"
        style={{
          padding: "32px",
          borderRadius: "var(--radius-lg)",
          marginBottom: "64px",
          borderLeft: "4px solid var(--accent)",
        }}
      >
        <h2 style={{ fontSize: "24px", fontWeight: 700, margin: "0 0 24px", letterSpacing: "-0.02em" }}>
          {business.title}
        </h2>
        <p style={{ fontSize: "15px", color: "var(--muted)", margin: "-12px 0 24px", lineHeight: 1.6 }}>{business.subhead}</p>

        {/* 3 reasons brands pay */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px", marginBottom: "24px" }}>
          {business.reasons.map((r) => (
            <div key={r.title} style={{ padding: "16px", borderRadius: "var(--radius-md)", border: "1px solid var(--line)", background: "var(--card)" }}>
              <h3 style={{ fontSize: "15.5px", fontWeight: 700, margin: "0 0 6px" }}>{r.title}</h3>
              <p style={{ fontSize: "14px", color: "var(--muted)", margin: 0, lineHeight: 1.55 }}>{r.body}</p>
            </div>
          ))}
        </div>

        {/* Survey vs TrustLedger (same panel as Insights; cites ESOMAR + Pew) */}
        <div style={{ marginBottom: "24px" }}>
          <WhyBrandsPay title="A survey vs TrustLedger" />
        </div>

        {/* 4-step arrow chain */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "10px",
            marginBottom: "24px",
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
                  fontWeight: 600,
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

        {/* 3 explanatory lines */}
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {business.lines.map((line, idx) => (
            <p
              key={idx}
              style={{
                fontSize: "14.5px",
                lineHeight: 1.6,
                margin: 0,
                color: idx === business.lines.length - 1 ? "var(--fg)" : "var(--muted)",
                fontWeight: idx === business.lines.length - 1 ? 600 : 400,
              }}
            >
              {line}
            </p>
          ))}
        </div>
      </section>

      {/* 5. Private by design: 2 balanced columns + footnote */}
      <section style={{ marginBottom: "64px" }}>
        <h2 style={{ fontSize: "24px", fontWeight: 700, marginBottom: "24px", letterSpacing: "-0.02em" }}>
          {privacy.title}
        </h2>
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
              <h3 style={{ fontSize: "18px", fontWeight: 600, margin: "0 0 16px", color: "var(--fg)" }}>
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
          padding: "44px 28px",
          textAlign: "center",
          borderRadius: "var(--radius-lg)",
          background: "linear-gradient(180deg, var(--card) 0%, var(--bg) 100%)",
        }}
      >
        <h2 style={{ fontSize: "26px", fontWeight: 800, margin: "0 0 10px", letterSpacing: "-0.02em" }}>
          {closing.headline}
        </h2>
        <p
          className="muted"
          style={{
            fontSize: "15px",
            maxWidth: "540px",
            margin: "0 auto 24px",
            lineHeight: 1.55,
          }}
        >
          {closing.body}
        </p>
        <div style={{ display: "inline-flex", justifyContent: "center" }}>
          <Link className="button" href="/story" style={{ padding: "10px 24px", fontSize: "15px" }}>
            {closing.cta}
          </Link>
        </div>
      </section>
    </main>
  );
}
