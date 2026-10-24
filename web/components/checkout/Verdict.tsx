"use client";
import type { ReactNode } from "react";
import s from "./checkout.module.css";

const HUMAN_LABELS: Record<string, string> = {
  UNKNOWN_SERIAL: "This serial isn't in the brand's records",
  NOT_IN_CHANNEL: "This product is not in this store's supply chain",
  ALREADY_SOLD: "This serial was already registered as sold",
  SKU_MISMATCH: "This serial belongs to a different product",
  WRONG_BRAND: "This serial belongs to a different brand",
};

export function IdleVerdict() {
  return (
    <div className={`${s.panel} ${s.idle}`} role="status">
      <div style={{ fontSize: 32, marginBottom: 8 }} aria-hidden>⌁</div>
      <h3 style={{ margin: "0 0 4px", fontSize: 18 }}>Scan a product to start</h3>
      <p className="muted" style={{ margin: "0 0 16px", fontSize: 13.5 }}>The brand checks unit authenticity before any PayPal payment exists.</p>
      <div className={s.flow}>
        <div className={s.step}>
          <strong>1. Scan</strong>
          <span>Scan or enter serial</span>
        </div>
        <span className={s.arrow} aria-hidden>→</span>
        <div className={`${s.step} ${s.stepCenter}`} style={{ borderStyle: "solid" }}>
          <strong>2. Brand checks</strong>
          <span>Real-time provenance</span>
        </div>
        <span className={s.arrow} aria-hidden>→</span>
        <div className={s.step}>
          <strong>3. PayPal order</strong>
          <span>Created only if verified</span>
        </div>
      </div>
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
  const humanLabel = reasonCode ? (HUMAN_LABELS[reasonCode] ?? reason) : reason;

  return (
    <div className={`${s.panel} ${s.blocked}`} role="alert">
      <div className={s.verdictHead}>
        <div className={`${s.badge} ${s.badgeBad}`} aria-hidden>✕</div>
        <div>
          <h3 className={s.verdictTitle}>Payment Blocked</h3>
          <div className="muted">Authenticity condition failed at {storeName}</div>
        </div>
      </div>
      <div className={s.reasonRow}>
        <span className={s.reason}>{humanLabel}</span>
        {reasonCode && (
          <span className={s.codeTag}>
            <code>{reasonCode}</code>
          </span>
        )}
      </div>
      <p className="muted" style={{ margin: "4px 0 0" }}>Tell the buyer before any money moves. Do not sell this unit.</p>
      <div className={s.flow}>
        <div className={`${s.step} ${s.stepBad}`}>
          <strong>✕ Brand check</strong>
          <span>Not verified</span>
        </div>
        <span className={s.arrow} aria-hidden>→</span>
        <div className={`${s.step} ${s.stepCenter} ${s.stepCenterBlocked} ${s.stepNever}`}>
          <strong>PayPal order</strong>
          <span>Never created</span>
        </div>
        <span className={s.arrow} aria-hidden>→</span>
        <div className={`${s.step} ${s.stepBad}`}>
          <strong>Investigation</strong>
          <span>Opened in cockpit</span>
        </div>
      </div>
      <p className={s.noPayment}>
        No PayPal order or transaction was created. Stopped before any money moves.
      </p>
      <dl className={s.facts}>
        <dt>Serial</dt><dd>{serial}</dd>
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
