import Link from "next/link";
import { LANDING_COPY } from "@/components/home/copy";

export default function Home() {
  const { hero, howItWorks, features, businessModel, privacy, closing } = LANDING_COPY;

  return (
    <main>
      {/* 1. Hero Section */}
      <section className="card hero" style={{ padding: "40px 36px", marginBottom: "36px" }}>
        <div className="hero-grid">
          <div>
            <div style={{ display: "inline-flex", alignItems: "center", gap: "8px", padding: "4px 12px", borderRadius: "999px", background: "var(--accent-bg)", color: "var(--accent)", fontSize: "13px", fontWeight: 650, marginBottom: "16px", border: "1px solid var(--accent-border)" }}>
              <span aria-hidden>◆</span> {hero.badge}
            </div>
            <h1 style={{ fontSize: "36px", lineHeight: 1.18, margin: "0 0 16px", letterSpacing: "-0.03em" }}>
              {hero.headline}
            </h1>
            <p className="muted" style={{ fontSize: "16.5px", maxWidth: "620px", lineHeight: 1.55, margin: "0 0 24px" }}>
              {hero.explanation}
            </p>
            <div className="hero-ctas">
              <Link className="button" href={hero.primaryCta.href}>
                {hero.primaryCta.text}
              </Link>
              <Link className="button secondary" href={hero.secondaryCta.href}>
                {hero.secondaryCta.text}
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
                  {hero.verdictVerified.tag}
                </div>
                <span style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)" }}>{hero.verdictVerified.serial}</span>
              </div>
              <div style={{ fontSize: "12.5px", color: "var(--fg)", marginBottom: "4px" }}>{hero.verdictVerified.title}</div>
              <div style={{ fontSize: "11.5px", color: "var(--muted)" }}>{hero.verdictVerified.subtitle}</div>
            </div>

            {/* Mini Blocked Mock */}
            <div style={{ background: "var(--card)", border: "1.5px solid var(--bad)", borderRadius: "10px", padding: "14px 16px", boxShadow: "0 4px 16px rgba(0,0,0,0.06)" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", fontWeight: 700, fontSize: "14px", color: "var(--bad)" }}>
                  <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: "18px", height: "18px", borderRadius: "50%", background: "var(--bad-bg)", border: "1px solid var(--bad-border)", fontSize: "11px" }}>✕</span>
                  {hero.verdictBlocked.tag}
                </div>
                <span style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)" }}>{hero.verdictBlocked.serial}</span>
              </div>
              <div style={{ fontSize: "12.5px", color: "var(--fg)", marginBottom: "4px" }}>{hero.verdictBlocked.title}</div>
              <div style={{ fontSize: "11.5px", color: "var(--bad)", fontWeight: 600 }}>{hero.verdictBlocked.subtitle}</div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. How It Works (3 Steps) */}
      <section style={{ marginBottom: "40px" }}>
        <h2 style={{ fontSize: "22px", marginBottom: "18px", letterSpacing: "-0.02em" }}>{howItWorks.title}</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "16px" }}>
          {howItWorks.steps.map((st, i) => (
            <div key={i} className="card" style={{ padding: "22px" }}>
              <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--accent)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>
                {st.step}
              </div>
              <h3 style={{ fontSize: "17px", margin: "0 0 8px" }}>{st.title}</h3>
              <p className="muted" style={{ fontSize: "14px", margin: 0, lineHeight: 1.5 }}>
                {st.description}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* 3. Product Features (5 Cards Grid) */}
      <section style={{ marginBottom: "40px" }}>
        <h2 style={{ fontSize: "22px", marginBottom: "18px", letterSpacing: "-0.02em" }}>{features.title}</h2>
        <div className="tiles">
          {features.cards.map((fc, i) => (
            <Link key={i} href={fc.href} className="tile card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                <b>{fc.title}</b>
                <span className={`badge ${fc.badge === "Architecture" || fc.badge === "Console" ? "badge-dp" : "badge-exact"}`}>{fc.badge}</span>
              </div>
              <span className="muted">{fc.description}</span>
            </Link>
          ))}
        </div>
      </section>

      {/* 4. Self-Sustaining Business Model Section */}
      <section className="card elevated" style={{ padding: "30px 32px", marginBottom: "40px", borderLeft: "4px solid var(--accent)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px", marginBottom: "14px" }}>
          <div>
            <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--accent)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "4px" }}>
              {businessModel.tag}
            </div>
            <h2 style={{ fontSize: "22px", margin: 0, letterSpacing: "-0.02em" }}>{businessModel.headline}</h2>
          </div>
          <div style={{ fontSize: "26px", fontWeight: 800, color: "var(--accent)", lineHeight: 1 }}>
            {businessModel.statNumber} <span style={{ fontSize: "14px", fontWeight: 500, color: "var(--muted)" }}>{businessModel.statLabel}</span>
          </div>
        </div>
        <p style={{ fontSize: "15px", lineHeight: 1.6, margin: "0 0 16px", color: "var(--fg)" }}>
          {businessModel.body}
        </p>
        <div style={{ fontSize: "13px", color: "var(--muted)" }}>
          {businessModel.sources}
        </div>
      </section>

      {/* 5. Private by Design Section */}
      <section style={{ marginBottom: "40px" }}>
        <h2 style={{ fontSize: "22px", marginBottom: "18px", letterSpacing: "-0.02em" }}>{privacy.title}</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "18px" }}>
          {privacy.columns.map((col, i) => (
            <div key={i} className="card" style={{ padding: "24px", borderTop: `3px solid ${i === 0 ? "var(--ok)" : "var(--accent)"}` }}>
              <h3 style={{ fontSize: "18px", margin: "0 0 12px" }}>{col.title}</h3>
              <p className="muted" style={{ fontSize: "14px", lineHeight: 1.55, margin: "0 0 16px" }}>
                {col.summary}
              </p>
              <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "13.5px", lineHeight: 1.7, color: "var(--fg)" }}>
                {col.bullets.map((b, j) => (
                  <li key={j}>{b}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* 6. Closing CTA Banner */}
      <section className="card hero" style={{ padding: "36px 32px", textAlign: "center", marginBottom: "20px" }}>
        <h2 style={{ fontSize: "24px", margin: "0 0 10px", letterSpacing: "-0.02em" }}>
          {closing.headline}
        </h2>
        <p className="muted" style={{ fontSize: "15px", maxWidth: "540px", margin: "0 auto 22px", lineHeight: 1.5 }}>
          {closing.subhead}
        </p>
        <div style={{ display: "inline-flex", gap: "12px", justifyContent: "center", flexWrap: "wrap" }}>
          <Link className="button" href={closing.primaryCta.href}>
            {closing.primaryCta.text}
          </Link>
          <Link className="button secondary" href={closing.secondaryCta.href}>
            {closing.secondaryCta.text}
          </Link>
        </div>
      </section>
    </main>
  );
}
