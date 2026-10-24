import s from "./checkout.module.css";

export default function AuthenticityStamp({ className = "" }: { className?: string }) {
  return (
    <div className={`${s.stamp} ${className}`} role="img" aria-label="Authenticity verified · Brand verified">
      <div className={s.stampInner}>
        <div className={s.stampIcon}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
        <div className={s.stampText}>
          <span className={s.stampTitle}>Authenticity verified ✓</span>
          <span className={s.stampSub}>Brand verified</span>
        </div>
      </div>
    </div>
  );
}
