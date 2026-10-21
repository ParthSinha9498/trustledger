import Link from "next/link";

export default function Home() {
  return (
    <main>
      <div className="card hero">
        <h1>TrustLedger makes product authenticity a condition of payment.</h1>
        <p className="muted">
          The brand verifies the product before the PayPal order exists. Verified: the buyer pays.
          Not verified: no payment is created, and an investigation opens for the brand.
        </p>
        <div className="row">
          <Link className="button" href="/pos">Open the store checkout</Link>
          <Link className="button secondary" href="/cockpit">Open the brand cockpit</Link>
        </div>
        <p className="muted">Demo serial X123 belongs to Store A&apos;s supply chain. Try it at Store A, then at Store B.</p>
      </div>
      <div className="tiles">
        <Link href="/cockpit" className="tile card"><b>Investigations</b><span className="muted">Agent steps, cited findings, privacy budget.</span></Link>
        <Link href="/cockpit/console" className="tile card"><b>Question console</b><span className="muted">Ask, review the planned queries, run them privately.</span></Link>
        <Link href="/cockpit/supply-chain" className="tile card"><b>Supply chain</b><span className="muted">Batches by week, with off-channel sales in red.</span></Link>
      </div>
    </main>
  );
}
