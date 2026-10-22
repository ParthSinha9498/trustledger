"use client";
import type { ReactNode } from "react";
import s from "./checkout.module.css";

export function IdleVerdict() {
  return (
    <div className={`${s.panel} ${s.idle}`}>
      <div style={{ fontSize: 34 }} aria-hidden>⌁</div>
      <h3>Scan a product to start</h3>
      <p>The brand checks the serial before any PayPal payment exists.</p>
    </div>
  );
}

export function VerifyingVerdict({ serial, storeName }: { serial: string; storeName: string }) {
  return (
    <div className={`${s.panel} ${s.verifying}`} role="status" aria-live="polite">
      <div className={s.spinner} aria-hidden />
      <h3 style={{ margin: 0 }}>Verifying with the brand…</h3>
      <p className="muted">Serial <code>{serial}</code> at {storeName}. No payment exists yet.</p>
    </div>
  );
}

export function VerifiedVerdict({ verificationId, paypalOrderId, children }: {
  verificationId: string;
  paypalOrderId: string;
  children?: ReactNode;
}) {
  return (
    <div className={`${s.panel} ${s.verified}`} role="status" aria-live="polite">
      <div className={s.verdictHead}>
        <div className={`${s.badge} ${s.badgeOk}`} aria-hidden>✓</div>
        <div>
          <h3 className={s.verdictTitle}>Brand verified</h3>
          <div className="muted">The brand confirmed this unit belongs to this store.</div>
        </div>
      </div>
      <div className={s.flow}>
        <div className={`${s.step} ${s.stepOk}`}><strong>✓ Brand check</strong>Authorized & in-channel</div>
        <span className={s.arrow} aria-hidden>→</span>
        <div className={`${s.step} ${s.stepCenter} ${s.stepCenterOk}`}><strong>✓ PayPal order created</strong>custom_id = verification ID</div>
        <span className={s.arrow} aria-hidden>→</span>
        <div className={s.step}><strong>Pay with PayPal</strong>Buyer approves</div>
      </div>
      <dl className={s.facts}>
        <dt>Verification ID</dt><dd>{verificationId}</dd>
        <dt>PayPal order</dt><dd>{paypalOrderId}</dd>
      </dl>
      <p className={s.note}>The PayPal order was created with this verification ID in its <code>custom_id</code>, so the payment record points directly to the verification event.</p>
      {children}
    </div>
  );
}

export function BlockedVerdict({ reason, reasonCode, caseId, storeName, serial }: {
  reason: string;
  reasonCode?: string;
  caseId?: string;
  storeName: string;
  serial: string;
}) {
  return (
    <div className={`${s.panel} ${s.blocked}`} role="alert">
      <div className={s.verdictHead}>
        <div className={`${s.badge} ${s.badgeBad}`} aria-hidden>✕</div>
        <div>
          <h3 className={s.verdictTitle}>Payment Blocked</h3>
          <div className="muted">Authenticity condition failed at {storeName}</div>
        </div>
      </div>
      <p className={s.reason}>{reason}</p>
      <p className="muted" style={{ margin: 0 }}>Tell the buyer before any money moves. Do not sell this unit.</p>
      <div className={s.flow}>
        <div className={`${s.step} ${s.stepBad}`}><strong>✕ Brand check</strong>{reasonCode ?? "Not verified"}</div>
        <span className={s.arrow} aria-hidden>→</span>
        <div className={`${s.step} ${s.stepCenter} ${s.stepCenterBlocked} ${s.stepNever}`}><strong>PayPal order</strong>Never created</div>
        <span className={s.arrow} aria-hidden>→</span>
        <div className={`${s.step} ${s.stepBad}`}><strong>Investigation</strong>Opened in cockpit</div>
      </div>
      <p className={s.noPayment}>
        No PayPal order or transaction was created. Stopped before any money moves.
      </p>
      <dl className={s.facts}>
        <dt>Serial</dt><dd>{serial}</dd>
        {reasonCode && (<><dt>Reason code</dt><dd>{reasonCode}</dd></>)}
        {caseId && (<><dt>Case</dt><dd>{caseId}</dd></>)}
      </dl>
      {caseId && (
        <div className={s.links}>
          <a href={`/cockpit/cases/${caseId}`}>Open the case in the brand cockpit →</a>
        </div>
      )}
    </div>
  );
}
