"use client";
import type { Budget } from "@/lib/api";
import { budgetTotal, fmtNum } from "./format";

/** PayPal-side privacy budget (zCDP rho, per dataset). Brand-side queries never spend it. */
export default function BudgetMeter({ budget, compact = false }: { budget: Budget | null | undefined; compact?: boolean }) {
  if (!budget) {
    return (
      <div className="meter">
        <div className="meter-head"><span>Privacy budget (rho)</span><span className="muted">unavailable</span></div>
        <div className="meter-track"><div className="meter-fill" style={{ width: 0 }} /></div>
      </div>
    );
  }
  const total = budgetTotal(budget);
  const pctLeft = total > 0 ? Math.max(0, Math.min(1, budget.remaining / total)) : 0;
  const state = pctLeft <= 0.001 ? "empty" : pctLeft < 0.2 ? "low" : "ok";
  const left = budget.queries_left_estimate;
  return (
    <div className={`meter meter-${state}`} role="meter" aria-valuemin={0} aria-valuemax={total}
         aria-valuenow={budget.remaining} aria-label="Privacy budget remaining">
      <div className="meter-head">
        <span>Privacy budget (rho)</span>
        <span>
          {state === "empty" ? <strong className="text-bad">Exhausted</strong> :
            left != null ? <>≈ <strong>{fmtNum(left)}</strong> queries left</> :
              <>{Math.round(pctLeft * 100)}% left</>}
        </span>
      </div>
      <div className="meter-track"><div className="meter-fill" style={{ width: `${pctLeft * 100}%` }} /></div>
      {!compact && (
        <div className="meter-foot muted">
          {fmtNum(budget.spent, 3)} of {fmtNum(total, 3)} {budget.unit ?? "rho"} spent
          {budget.eps_equivalent_total != null && <> · ε ≈ {fmtNum(budget.eps_equivalent_total, 2)} total</>}
          {" "}· budget is per dataset, PayPal-side only
        </div>
      )}
    </div>
  );
}
