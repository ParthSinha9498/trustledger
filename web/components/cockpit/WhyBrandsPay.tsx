"use client";
import { useId, useState } from "react";
import styles from "./WhyBrandsPay.module.css";

/**
 * "Why brands pay": a traditional survey next to a TrustLedger answer.
 * Self-contained (design tokens only) so other surfaces can reuse it.
 * Every sentence maps to a row in notes/CLAIMS.md; do not add numbers here without one.
 *
 * `seconds` is the time the page actually measured for the last answer. When nothing has been
 * measured yet, the panel says "Answered in seconds" and never invents a number.
 */
export default function WhyBrandsPay({ seconds = null, title = "Why brands pay for this" }: { seconds?: number | null; title?: string }) {
  const [open, setOpen] = useState(false);
  const bodyId = useId();
  const answered = seconds != null && Number.isFinite(seconds)
    ? `Answered in ${seconds.toFixed(seconds < 1 ? 2 : 1)} s`
    : "Answered in seconds";

  return (
    <section className={styles.panel} aria-labelledby={`${bodyId}-title`}>
      <div className={styles.head}>
        <h2 id={`${bodyId}-title`} className={styles.title}>{title}</h2>
        <button type="button" className={styles.toggle} aria-expanded={open} aria-controls={bodyId}
                onClick={() => setOpen((v) => !v)}>
          {open ? "Hide" : "Show"} comparison
          <svg className={styles.chevron} data-open={open} width="14" height="14" viewBox="0 0 16 16" aria-hidden="true">
            <path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>

      <div id={bodyId} className={styles.body} data-open={open}>
        <div className={styles.cols}>
          <div className={`${styles.col} ${styles.survey}`}>
            <h3 className={styles.colTitle}>Survey</h3>
            <ul className={styles.list}>
              <li><strong>Weeks to field</strong></li>
              <li><strong>Self-reported</strong></li>
              <li>
                In a Pew survey (Nov 2024 survey of 11,114 US adults), 18% of cases were flagged as bogus.
                <span className={styles.src}>Pew Research Center, 2026</span>
              </li>
            </ul>
          </div>
          <div className={`${styles.col} ${styles.tl}`}>
            <h3 className={styles.colTitle}>TrustLedger</h3>
            <ul className={styles.list}>
              <li><strong>{answered}</strong></li>
              <li><strong>From verified purchases</strong></li>
              <li>Privacy-protected, with 95% intervals (±) on buyer estimates (brand-side counts are exact)</li>
            </ul>
          </div>
        </div>
        <p className={styles.foot}>Brands spend USD 150B+ a year on market insights (ESOMAR, 2024 data).</p>
      </div>
    </section>
  );
}
