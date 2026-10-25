"use client";

import Link from "next/link";
import { useState } from "react";
import { useDarkMode } from "@/components/cockpit/useDarkMode";
import styles from "./onboard.module.css";

export default function BrandOnboardingPage() {
  const isDark = useDarkMode();
  const [activeTab, setActiveTab] = useState<"python" | "curl">("python");
  const [copied, setCopied] = useState(false);

  const pythonSnippet = `# Run with uv run python examples/brand_onboarding/verify.py
import os
import httpx

api_url = os.environ.get("TRUSTLEDGER_API_URL", "http://localhost:8001")
token = os.environ.get("NODE_SHARED_TOKEN", "change-me")

response = httpx.post(
    f"{api_url}/v1/verify",
    headers={"X-Node-Token": token, "Content-Type": "application/json"},
    json={
        "serial": "XA000001",
        "sku": "NMB-P8-128",
        "store_id": "store_a"
    },
    timeout=10.0
)
verdict = response.json()
print("Result:", verdict["result"])  # VERIFIED or NOT_VERIFIED
print("Reason:", verdict.get("reason_code"))`;

  const curlSnippet = `curl -X POST http://localhost:8001/v1/verify \\
  -H "X-Node-Token: \${NODE_SHARED_TOKEN:-change-me}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "serial": "XA000001",
    "sku": "NMB-P8-128",
    "store_id": "store_a"
  }'`;

  const currentSnippet = activeTab === "python" ? pythonSnippet : curlSnippet;

  const handleCopy = () => {
    navigator.clipboard.writeText(currentSnippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <main className={styles.container}>
      <header className={styles.header}>
        <div className={styles.crumbs}>
          <Link href="/">TrustLedger</Link>
          <span>/</span>
          <Link href="/cockpit">Brand Console</Link>
          <span>/</span>
          <span>Onboarding</span>
        </div>
        <div className={styles.badge}>
          <span aria-hidden="true">⚡</span>
          <span>Brand Integration Guide</span>
        </div>
        <h1 className={styles.title}>Integrate in One Sitting</h1>
        <p className={styles.subtitle}>
          Connect your brand registry to TrustLedger. Verify authenticity at the point of checkout
          before any PayPal payment order is created.
        </p>
      </header>

      <div className={styles.steps}>
        {/* Step 1: Choose the brand */}
        <section className={styles.stepCard} id="step-1">
          <div className={styles.stepHeader}>
            <div className={styles.stepNumber}>1</div>
            <div className={styles.stepInfo}>
              <h2 className={styles.stepTitle}>Choose the brand</h2>
              <p className={styles.stepDesc}>
                In this reference deployment, tests and examples run against the fictional reference
                brand <strong>Nimbus</strong> from the seed registry.
              </p>
            </div>
          </div>
          <div className={styles.brandGrid}>
            <div className={styles.brandBox}>
              <div className={styles.brandMetaRow}>
                <span className={styles.brandName}>Nimbus Mobile</span>
                <span className={styles.brandTag}>Fictional Seed</span>
              </div>
              <p style={{ margin: "0 0 8px", fontSize: "13px", color: "var(--muted)" }}>
                Brand ID: <code>nimbus</code>
              </p>
              <p style={{ margin: 0, fontSize: "13px", color: "var(--muted)" }}>
                SKU catalog: <code>NMB-P8-128</code> (Nimbus Phone 8, 128GB)
              </p>
            </div>
            <div className={styles.brandBox}>
              <div className={styles.brandMetaRow}>
                <span className={styles.brandName}>Brand Node Boundary</span>
                <span className={styles.brandTag}>Isolation</span>
              </div>
              <p style={{ margin: 0, fontSize: "13px", color: "var(--muted)", lineHeight: 1.45 }}>
                Brand inventory and serial registries remain isolated inside the brand node database.
                No customer identity or raw buyer records ever enter the brand node.
              </p>
            </div>
          </div>
        </section>

        {/* Step 2: Get a sandbox key */}
        <section className={styles.stepCard} id="step-2">
          <div className={styles.stepHeader}>
            <div className={styles.stepNumber}>2</div>
            <div className={styles.stepInfo}>
              <h2 className={styles.stepTitle}>Get a sandbox key</h2>
              <p className={styles.stepDesc}>
                The brand node enforces pre-shared authentication on every incoming verification
                request via the <code>X-Node-Token</code> HTTP header.
              </p>
            </div>
          </div>
          <div className={styles.callout + " " + styles.calloutInfo}>
            <p style={{ margin: "0 0 6px", fontWeight: 650 }}>Authentication Mechanism</p>
            <p style={{ margin: 0 }}>
              The brand node verifies tokens against the <code>NODE_SHARED_TOKEN</code> environment
              variable. In local development and Docker Compose, this token is configured in your
              environment (defaults to <code>change-me</code> or <code>dev-token</code>).
            </p>
          </div>
          <div className={styles.codeBlock}>
            <pre># In your local .env or deployment configuration
NODE_SHARED_TOKEN=change-me</pre>
          </div>
        </section>

        {/* Step 3: Make the verify call */}
        <section className={styles.stepCard} id="step-3">
          <div className={styles.stepHeader}>
            <div className={styles.stepNumber}>3</div>
            <div className={styles.stepInfo}>
              <h2 className={styles.stepTitle}>Make the verify call</h2>
              <p className={styles.stepDesc}>
                Send a <code>POST /v1/verify</code> request containing the unit serial, catalog SKU,
                and requesting merchant store ID.
              </p>
            </div>
          </div>

          <div className={styles.tabBar}>
            <button
              type="button"
              className={`${styles.tabButton} ${activeTab === "python" ? styles.tabActive : ""}`}
              onClick={() => setActiveTab("python")}
            >
              Python (httpx)
            </button>
            <button
              type="button"
              className={`${styles.tabButton} ${activeTab === "curl" ? styles.tabActive : ""}`}
              onClick={() => setActiveTab("curl")}
            >
              cURL
            </button>
            <button
              type="button"
              onClick={handleCopy}
              style={{
                marginLeft: "auto",
                background: "transparent",
                border: "1px solid var(--line)",
                borderRadius: "var(--radius-sm)",
                padding: "4px 10px",
                fontSize: "12px",
                cursor: "pointer",
                color: "var(--muted)",
              }}
            >
              {copied ? "Copied!" : "Copy Snippet"}
            </button>
          </div>

          <div className={styles.codeBlock}>
            <pre>{currentSnippet}</pre>
          </div>

          <div className={styles.callout + " " + styles.calloutWarn}>
            <span style={{ fontWeight: 600 }}>SDK generated with APIMatic: coming</span>
            <p style={{ margin: "4px 0 0", fontSize: "12.5px" }}>
              Standard OpenAPI specifications are available in <code>openapi/brand-verification.yaml</code>.
              Pre-built language SDKs will be generated via APIMatic.
            </p>
          </div>
        </section>

        {/* Step 4: Read the answer */}
        <section className={styles.stepCard} id="step-4">
          <div className={styles.stepHeader}>
            <div className={styles.stepNumber}>4</div>
            <div className={styles.stepInfo}>
              <h2 className={styles.stepTitle}>Read the answer</h2>
              <p className={styles.stepDesc}>
                The brand node evaluates its registry and returns a definitive plain-language verdict.
              </p>
            </div>
          </div>

          <div className={styles.verdictGrid}>
            <div className={styles.verdictCard}>
              <span className={styles.verdictBadgeOk}>VERIFIED</span>
              <p style={{ margin: "0 0 8px", fontSize: "13px", fontWeight: 600, color: "var(--fg)" }}>
                Authentic & authorized for sale
              </p>
              <p style={{ margin: 0, fontSize: "12.5px", color: "var(--muted)", lineHeight: 1.45 }}>
                Returns a unique <code>verification_id</code>. The point-of-sale system proceeds to
                create the PayPal payment order, attaching this verification ID to the order custom ID.
              </p>
            </div>

            <div className={styles.verdictCard}>
              <span className={styles.verdictBadgeBad}>NOT_VERIFIED</span>
              <p style={{ margin: "0 0 8px", fontSize: "13px", fontWeight: 600, color: "var(--fg)" }}>
                Verification refused with reason code
              </p>
              <p style={{ margin: 0, fontSize: "12.5px", color: "var(--muted)", lineHeight: 1.45 }}>
                Reason codes indicate exact policy failures:
                <code> NOT_IN_CHANNEL</code> (diverted inventory),
                <code> ALREADY_SOLD</code> (duplicate or clone),
                <code> UNKNOWN_SERIAL</code> (unregistered unit), or
                <code> SKU_MISMATCH</code>.
              </p>
            </div>
          </div>
        </section>

        {/* Step 5: What a "no" does */}
        <section className={styles.stepCard} id="step-5">
          <div className={styles.stepHeader}>
            <div className={styles.stepNumber}>5</div>
            <div className={styles.stepInfo}>
              <h2 className={styles.stepTitle}>What a &quot;no&quot; does</h2>
              <p className={styles.stepDesc}>
                TrustLedger prevents invalid transactions before any funds or orders are committed.
              </p>
            </div>
          </div>

          <div style={{ display: "grid", gap: "12px", marginTop: "12px" }}>
            <div style={{ padding: "14px", borderRadius: "8px", background: "var(--bg)", border: "1px solid var(--line)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                <span style={{ color: "var(--bad)", fontWeight: 700 }}>✗ Zero PayPal Order Created</span>
              </div>
              <p style={{ margin: 0, fontSize: "13px", color: "var(--muted)", lineHeight: 1.45 }}>
                When verification answers <code>NOT_VERIFIED</code>, checkout is immediately halted. No PayPal
                order or authorization is generated.
              </p>
            </div>

            <div style={{ padding: "14px", borderRadius: "8px", background: "var(--bg)", border: "1px solid var(--line)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                <span style={{ color: "var(--accent)", fontWeight: 700 }}>🔍 Incident Case Opened</span>
              </div>
              <p style={{ margin: 0, fontSize: "13px", color: "var(--muted)", lineHeight: 1.45 }}>
                The refusal event is logged to the incident registry. Brand analysts can inspect the failure
                pattern in the Brand Cockpit without exposing any customer identity.
              </p>
            </div>
          </div>
        </section>
      </div>

      <footer className={styles.footerNote}>
        <strong>Need offline testing?</strong> Run the self-contained verification client at{" "}
        <code>examples/brand_onboarding/verify.py</code> against your local brand container or mock stack.
      </footer>
    </main>
  );
}
