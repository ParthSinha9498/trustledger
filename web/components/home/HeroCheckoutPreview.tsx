"use client";

import { useState } from "react";
import Link from "next/link";

export default function HeroCheckoutPreview() {
  const [outcome, setOutcome] = useState<"verified" | "blocked">("verified");

  return (
    <div
      className="card elevated"
      style={{
        borderRadius: "var(--radius-lg)",
        border: "1px solid var(--line)",
        padding: "24px",
        background: "var(--card)",
        boxShadow: "var(--shadow-md)",
        display: "flex",
        flexDirection: "column",
        gap: "18px",
        width: "100%",
      }}
    >
      {/* Top Header & Outcome Switcher */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span
            style={{
              width: "10px",
              height: "10px",
              borderRadius: "50%",
              background: outcome === "verified" ? "var(--ok)" : "var(--bad)",
              boxShadow: outcome === "verified" ? "var(--shadow-glow-ok)" : "var(--shadow-glow-bad)",
            }}
          />
          <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--fg)", letterSpacing: "0.02em" }}>
            CHECKOUT VERIFICATION GATE
          </span>
        </div>

        {/* Interactive toggle */}
        <div
          role="tablist"
          aria-label="Simulation outcome"
          style={{
            display: "inline-flex",
            background: "var(--chip)",
            borderRadius: "var(--radius-pill)",
            padding: "3px",
            border: "1px solid var(--line)",
          }}
        >
          <button
            type="button"
            role="tab"
            aria-selected={outcome === "verified"}
            onClick={() => setOutcome("verified")}
            style={{
              border: "none",
              background: outcome === "verified" ? "var(--ok)" : "transparent",
              color: outcome === "verified" ? "#ffffff" : "var(--muted)",
              fontSize: "12px",
              fontWeight: 650,
              padding: "4px 12px",
              borderRadius: "var(--radius-pill)",
              cursor: "pointer",
              transition: "all var(--transition-fast)",
            }}
          >
            Verified sale
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={outcome === "blocked"}
            onClick={() => setOutcome("blocked")}
            style={{
              border: "none",
              background: outcome === "blocked" ? "var(--bad)" : "transparent",
              color: outcome === "blocked" ? "#ffffff" : "var(--muted)",
              fontSize: "12px",
              fontWeight: 650,
              padding: "4px 12px",
              borderRadius: "var(--radius-pill)",
              cursor: "pointer",
              transition: "all var(--transition-fast)",
            }}
          >
            Blocked attempt
          </button>
        </div>
      </div>

      {/* Scanned Item Bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "12px 14px",
          borderRadius: "var(--radius-md)",
          background: "var(--bg)",
          border: "1px solid var(--line)",
          fontSize: "13px",
        }}
      >
        <div>
          <div style={{ fontWeight: 650, color: "var(--fg)" }}>Lumina P8 Pro · 256GB</div>
          <div className="muted" style={{ fontSize: "11.5px", marginTop: "2px" }}>
            Store: TechVault Retail (#ST-BER-01)
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontWeight: 700, color: "var(--fg)" }}>$899.00</div>
          <code
            style={{
              fontSize: "11px",
              background: "var(--chip)",
              padding: "2px 6px",
              borderRadius: "4px",
              color: "var(--muted)",
            }}
          >
            {outcome === "verified" ? "SN-P8-88319" : "SN-P8-99042"}
          </code>
        </div>
      </div>

      {/* 3-Step Verification Sequence */}
      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        {/* Step 1: Scan */}
        <div style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "2px 8px",
              borderRadius: "6px",
              fontSize: "11px",
              fontWeight: 700,
              background: "var(--chip)",
              color: "var(--fg)",
              border: "1px solid var(--line)",
              minWidth: "62px",
              textAlign: "center",
            }}
          >
            1. SCAN
          </span>
          <div style={{ fontSize: "12.5px", lineHeight: 1.45, color: "var(--fg)" }}>
            POS reads barcode serial · Requests verification before invoking payment
          </div>
        </div>

        {/* Step 2: Brand Decision */}
        <div style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "2px 8px",
              borderRadius: "6px",
              fontSize: "11px",
              fontWeight: 700,
              background: outcome === "verified" ? "var(--ok-bg)" : "var(--bad-bg)",
              color: outcome === "verified" ? "var(--ok)" : "var(--bad)",
              border: `1px solid ${outcome === "verified" ? "var(--ok-border)" : "var(--bad-border)"}`,
              minWidth: "62px",
              textAlign: "center",
            }}
          >
            2. BRAND
          </span>
          <div style={{ fontSize: "12.5px", lineHeight: 1.45, color: "var(--fg)" }}>
            {outcome === "verified" ? (
              <span>
                <strong>Brand system confirms:</strong> Serial valid & authorized for TechVault.
              </span>
            ) : (
              <span>
                <strong>Brand system rejects:</strong> Serial assigned to UK logistics hub; unverified for Berlin.
              </span>
            )}
          </div>
        </div>

        {/* Step 3: Transaction Outcome */}
        <div style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "2px 8px",
              borderRadius: "6px",
              fontSize: "11px",
              fontWeight: 700,
              background: outcome === "verified" ? "var(--accent-bg)" : "var(--bad)",
              color: outcome === "verified" ? "var(--accent)" : "#ffffff",
              border: `1px solid ${outcome === "verified" ? "var(--accent-border)" : "var(--bad)"}`,
              minWidth: "62px",
              textAlign: "center",
            }}
          >
            3. PAYPAL
          </span>
          <div style={{ fontSize: "12.5px", lineHeight: 1.45, color: "var(--fg)" }}>
            {outcome === "verified" ? (
              <span>
                <strong>PayPal order created:</strong> Verification ID <code>tl_ver_9f2a7</code> permanently attached.
              </span>
            ) : (
              <span>
                <strong>No PayPal order created:</strong> Payment stopped. Autonomous investigation opened.
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Outcome Status Box */}
      <div
        style={{
          padding: "14px",
          borderRadius: "var(--radius-md)",
          background: outcome === "verified" ? "var(--ok-bg)" : "var(--bad-bg)",
          border: `1px solid ${outcome === "verified" ? "var(--ok-border)" : "var(--bad-border)"}`,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "10px",
        }}
      >
        <div>
          <div
            style={{
              fontSize: "13px",
              fontWeight: 700,
              color: outcome === "verified" ? "var(--ok)" : "var(--bad)",
            }}
          >
            {outcome === "verified" ? "Outcome: Verified & Paid" : "Outcome: Blocked & Investigated"}
          </div>
          <div
            style={{
              fontSize: "11.5px",
              color: outcome === "verified" ? "var(--ok-hover)" : "var(--bad-hover)",
              marginTop: "2px",
            }}
          >
            {outcome === "verified"
              ? "Order ID: 8JP97654EE881554L"
              : "Case #INV-2026-042 triggered for security review"}
          </div>
        </div>

        <Link
          href={outcome === "verified" ? "/pos" : "/cockpit"}
          className="button sm"
          style={{
            fontSize: "12px",
            padding: "5px 12px",
            background: outcome === "verified" ? "var(--ok)" : "var(--bad)",
            color: "#ffffff",
            borderColor: "transparent",
            textDecoration: "none",
          }}
        >
          {outcome === "verified" ? "Try in checkout →" : "Inspect case →"}
        </Link>
      </div>
    </div>
  );
}
