"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/pos", label: "Store checkout" },
  { href: "/cockpit", label: "Investigations", exact: true },
  { href: "/cockpit/console", label: "Insights", alias: "/cockpit/insights" },
  { href: "/cockpit/supply-chain", label: "Supply chain" },
  { href: "/privacy", label: "Privacy" },
];

export default function Nav() {
  const path = usePathname() ?? "/";
  if (path.startsWith("/story")) return null;
  const active = (href: string, exact?: boolean, alias?: string) =>
    exact ? path === href || path.startsWith(`${href}/cases`) : path.startsWith(href) || (!!alias && path.startsWith(alias));
  return (
    <nav className="topnav">
      <Link href="/" className="brand"><span className="logo" aria-hidden>◆</span>TrustLedger</Link>
      <div className="navlinks">
        {LINKS.map((l, i) => (
          <span key={l.href} className="navgroup">
            {(i === 1 || i === 4) && <span className="navsep" aria-hidden />}
            <Link href={l.href} className={active(l.href, l.exact, l.alias) ? "active" : undefined}>{l.label}</Link>
          </span>
        ))}
      </div>
    </nav>
  );
}
