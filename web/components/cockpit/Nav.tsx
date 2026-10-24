"use client";

import { Suspense, useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";

const LINKS = [
  { href: "/pos", label: "Store checkout" },
  { href: "/cockpit", label: "Investigations", exact: true },
  { href: "/cockpit/console", label: "Insights", alias: "/cockpit/insights" },
  { href: "/cockpit/supply-chain", label: "Supply chain" },
  { href: "/privacy", label: "Privacy" },
];

function NavContent() {
  const path = usePathname() ?? "/";
  const searchParams = useSearchParams();
  const [open, setOpen] = useState(false);

  // Close mobile drawer on route change
  useEffect(() => {
    setOpen(false);
  }, [path]);

  // Hide nav on full-screen presentation cards, but show on /story index
  const isStoryCard = path === "/story" && !!searchParams.get("card");
  if (isStoryCard || (path.startsWith("/story/") && path !== "/story")) return null;

  const active = (href: string, exact?: boolean, alias?: string) =>
    exact
      ? path === href || path.startsWith(`${href}/cases`)
      : path.startsWith(href) || (!!alias && path.startsWith(alias));

  return (
    <>
      <nav className="topnav">
        <Link href="/" className="brand" onClick={() => setOpen(false)}>
          <span className="logo" aria-hidden>◆</span>TrustLedger
        </Link>
        
        {/* Desktop Links */}
        <div className="navlinks desktopOnly">
          {LINKS.map((l, i) => (
            <span key={l.href} className="navgroup">
              {(i === 1 || i === 4) && <span className="navsep" aria-hidden />}
              <Link href={l.href} className={active(l.href, l.exact, l.alias) ? "active" : undefined}>
                {l.label}
              </Link>
            </span>
          ))}
        </div>

        {/* Mobile Hamburger Button */}
        <button
          type="button"
          className="navToggle"
          aria-label={open ? "Close navigation menu" : "Open navigation menu"}
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          <span className="navToggleIcon" aria-hidden>{open ? "✕" : "☰"}</span>
        </button>
      </nav>

      {/* Mobile Menu Sheet */}
      {open && (
        <div className="mobileMenuBackdrop" onClick={() => setOpen(false)}>
          <div className="mobileMenuSheet" onClick={(e) => e.stopPropagation()}>
            {LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={`mobileNavLink ${active(l.href, l.exact, l.alias) ? "active" : ""}`}
                onClick={() => setOpen(false)}
              >
                {l.label}
              </Link>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

export default function Nav() {
  return (
    <Suspense fallback={null}>
      <NavContent />
    </Suspense>
  );
}
