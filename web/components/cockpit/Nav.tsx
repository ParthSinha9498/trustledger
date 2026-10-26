"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/pos", label: "Store checkout" },
  { href: "/cockpit", label: "Investigations", exact: true },
  { href: "/cockpit/console", label: "Insights", alias: "/cockpit/insights" },
  { href: "/cockpit/supply-chain", label: "Supply chain" },
  { href: "/cockpit/studio", label: "Studio" },
  { href: "/privacy", label: "Privacy" },
];

export default function Nav() {
  const path = usePathname() ?? "/";
  const [open, setOpen] = useState(false);
  const toggleRef = useRef<HTMLButtonElement>(null);

  // Close mobile drawer on route change
  useEffect(() => {
    setOpen(false);
  }, [path]);

  // Handle Escape key to close mobile menu and return focus to toggle button
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        toggleRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open]);

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
              {(i === 1 || i === 5) && <span className="navsep" aria-hidden />}
              <Link
                href={l.href}
                className={
                  l.href === "/pos"
                    ? `navCta ${active(l.href, l.exact, l.alias) ? "active" : ""}`
                    : active(l.href, l.exact, l.alias)
                    ? "active"
                    : undefined
                }
              >
                {l.label}
              </Link>
            </span>
          ))}
        </div>

        {/* Mobile Hamburger Button */}
        <button
          ref={toggleRef}
          type="button"
          className="navToggle"
          aria-label={open ? "Close navigation menu" : "Open navigation menu"}
          aria-expanded={open}
          aria-controls="mobile-nav-sheet"
          onClick={() => {
            const next = !open;
            setOpen(next);
            if (!next) toggleRef.current?.focus();
          }}
        >
          <span className="navToggleIcon" aria-hidden>{open ? "✕" : "☰"}</span>
        </button>
      </nav>

      {/* Mobile Menu Sheet */}
      {open && (
        <div className="mobileMenuBackdrop" onClick={() => { setOpen(false); toggleRef.current?.focus(); }}>
          <nav
            id="mobile-nav-sheet"
            className="mobileMenuSheet"
            aria-label="Mobile navigation"
            onClick={(e) => e.stopPropagation()}
          >
            {LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={`mobileNavLink ${l.href === "/pos" ? "mobileCta" : ""} ${active(l.href, l.exact, l.alias) ? "active" : ""}`}
                onClick={() => { setOpen(false); toggleRef.current?.focus(); }}
              >
                {l.label}
              </Link>
            ))}
          </nav>
        </div>
      )}
    </>
  );
}
