"use client";
import { usePathname } from "next/navigation";
import Nav from "@/components/cockpit/Nav";

export default function HeaderSwitcher() {
  const pathname = usePathname();
  const isBuyer = pathname?.startsWith("/pay") || pathname?.startsWith("/receipt");

  if (isBuyer) {
    return (
      <header className="buyer-header">
        <div className="buyer-header-inner">
          <div className="buyer-logo">
            <span className="buyer-logo-mark" aria-hidden>◆</span>
            <span className="buyer-logo-text">TrustLedger</span>
          </div>
          <span className="buyer-secure-badge">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
            Secured by TrustLedger
          </span>
        </div>
      </header>
    );
  }

  return <Nav />;
}
