"use client";
import Link from "next/link";
import type { Budget } from "@/lib/api";
import { budgetTotal, fmtNum } from "./format";
import styles from "./budget.module.css";

function Shield() {
  return (
    <svg className={styles.shieldIcon} viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
      <path d="M12 2.5 4.5 5.4v6.1c0 4.6 3.1 8.6 7.5 10 4.4-1.4 7.5-5.4 7.5-10V5.4L12 2.5Z"
            fill="currentColor" fillOpacity="0.14" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="m8.6 12.2 2.4 2.4 4.6-4.8" fill="none" stroke="currentColor" strokeWidth="1.9"
            strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/**
 * Buyer-data protection status.
 * Private release active (the normal case): a "Buyer data protected" badge, no meter: buyer answers come from a
 * one-time privacy-protected snapshot, so asking more costs nothing further.
 * Legacy per-query path: a plain meter of the brand's remaining privacy allowance.
 */
export default function BudgetMeter({ budget, compact = false }: { budget: Budget | null | undefined; compact?: boolean }) {
  if (budget?.private_release) {
    return (
      <div className={`${styles.badgeWrap} ${compact ? styles.compact : ""}`}>
        <Link href="/privacy" className={styles.badge} title="How buyer data is protected">
          <Shield />
          <span>Buyer data protected</span>
        </Link>
        {!compact && (
          <p className={styles.foot}>
            Buyer answers come from a privacy-protected snapshot: asking more reveals nothing new about any buyer.
          </p>
        )}
      </div>
    );
  }
  if (!budget) {
    return (
      <div className={`${styles.badgeWrap} ${compact ? styles.compact : ""}`}>
        <span className={`${styles.badge} ${styles.badgeMuted}`}><Shield /><span>Privacy status unavailable</span></span>
      </div>
    );
  }
  const total = budgetTotal(budget);
  const pctLeft = total > 0 ? Math.max(0, Math.min(1, budget.remaining / total)) : 0;
  const state = pctLeft <= 0.001 ? "empty" : pctLeft < 0.2 ? "low" : "ok";
  const left = budget.queries_left_estimate;
  return (
    <div className={`meter meter-${state}`} role="meter" aria-valuemin={0} aria-valuemax={total}
         aria-valuenow={budget.remaining} aria-label="Privacy allowance remaining">
      <div className="meter-head">
        <span>Privacy allowance</span>
        <span>
          {state === "empty" ? (
            <strong className="text-bad">Limit reached</strong>
          ) : left != null ? (
            <>≈ <strong>{fmtNum(left)}</strong> buyer questions left</>
          ) : (
            <>{Math.round(pctLeft * 100)}% left</>
          )}
        </span>
      </div>
      <div className="meter-track"><div className="meter-fill" style={{ width: `${pctLeft * 100}%` }} /></div>
      {!compact && (
        <div className="meter-foot muted" style={{ whiteSpace: "normal", lineHeight: 1.4 }}>
          {state === "empty"
            ? <>Privacy limit reached: buyer questions are paused. Brand-side questions still work.</>
            : <>Only buyer (PayPal-side) questions use it; brand-side questions are free.</>}
        </div>
      )}
    </div>
  );
}
