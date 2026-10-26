export const LANDING_COPY = {
  hero: {
    eyebrow: "Authenticity before payment",
    headline: "Verify the product. Then pay.",
    subhead: "For registered high-value categories, TrustLedger checks a product with its brand before PayPal creates an order. Failed checks open an investigation instead.",
    primaryCta: "Try the checkout demo",
    secondaryCta: "Explore the brand cockpit",
    scopeBadge: "Registered high-value categories · Real-time brand verification",
  },
  heroFlow: {
    steps: [
      { title: "Product serial scanned", body: "Store POS requests brand verification", badge: "Scan" },
      { title: "Brand confirms the unit", body: "Deterministic registry match at brand node", badge: "Brand Check" },
      { title: "PayPal order created", body: "Verification ID attached to payment record", badge: "Verified" },
    ],
    outcomes: {
      verified: {
        title: "Verified: Order created",
        body: "Brand confirms serial in authorized stock. PayPal captures payment.",
        badge: "VERIFIED",
        orderId: "ORDER-8JP97654EE",
        status: "Captured",
      },
      blocked: {
        title: "Blocked: No order created",
        body: "Serial not authorized for this store. Payment blocked; investigation opened.",
        badge: "BLOCKED",
        caseId: "CASE-2026-042",
        status: "Investigating",
      },
    },
  },
  how: {
    title: "How it works",
    subtitle: "Verification happens at the transaction boundary before any payment order is generated.",
    steps: [
      {
        step: 1,
        title: "Scan the serial",
        body: "For registered high-value categories, the store checkout transmits the product serial to TrustLedger before payment starts.",
      },
      {
        step: 2,
        title: "Brand checks the unit",
        body: "The brand's system verifies if this unit belongs in this channel. A deterministic registry check—never AI.",
      },
      {
        step: 3,
        title: "Order created or blocked",
        body: "Two distinct paths: verified units proceed to PayPal payment creation; blocked units halt payment and trigger an investigation.",
      },
    ],
  },
  features: {
    title: "What you can try",
    subtitle: "Explore the interactive tools powering the pre-payment verification network.",
    cards: [
      {
        title: "Checkout Gate",
        body: "Verification runs before a PayPal order exists. The verification ID is permanently linked to the payment.",
        href: "/pos",
        badge: "Live Checkout Demo",
        size: "large",
      },
      {
        title: "AI Investigations",
        body: "An agent questions brand and PayPal data, never sees a raw customer record, and cites every evidence step.",
        href: "/cockpit",
        badge: "Autonomous Case Agent",
        size: "large",
      },
      {
        title: "Brand Insights",
        body: "Ask in plain English. Answers aggregate verified purchases in seconds without exposing shopper identities.",
        href: "/cockpit/console",
        badge: "Differential Privacy",
      },
      {
        title: "Supply-chain Timeline",
        body: "Inspect batch logistics from manufacture to store shelves, identifying where diverted units left the route.",
        href: "/cockpit/supply-chain",
        badge: "Logistics Audit",
      },
      {
        title: "Privacy Architecture",
        body: "Separate data nodes for brands and PayPal. Questions travel to data; only group-level answers return.",
        href: "/privacy",
        badge: "Formal Guarantees",
      },
    ],
  },
  business: {
    title: "Why brands pay for this",
    subhead: "The authenticity check is free for shoppers. Brands pay for the high-fidelity intelligence verified purchases provide.",
    sampleQuery: {
      question: "What age group buys the P8 in Riverton?",
      result: "25–34: 48% (±3.2%) · 35–44: 31% (±2.8%)",
      timing: "Answered in 1.2s",
      note: "95% intervals apply strictly to buyer estimates; brand-side counts are exact.",
    },
    formula: "Brands pay for privacy-safe insights; shoppers get free authenticity checks.",
    reasons: [
      {
        title: "Real buyers, not panels",
        body: "Insights aggregate verified purchases at checkout—not self-reported surveys or opt-in panels.",
      },
      {
        title: "Seconds, not weeks",
        body: "Ask strategic questions in plain English and receive mathematically protected answers in seconds.",
      },
      {
        title: "Actionable leak detection",
        body: "Blocked check attempts trigger cited investigations showing where units diverged from authorized routes.",
      },
    ],
    marketStat: "The market-insights industry represents USD 150B+ annually (ESOMAR, 2024 data).",
    pewEvidence: "In a Pew survey fielded Nov 2024 (11,114 US adults), 18% of cases were flagged (Pew Research Center, 27 Aug 2026).",
    chain: ["Verified purchases", "Privacy-safe insights", "Brand intelligence", "Free checks for shoppers"],
  },
  privacy: {
    title: "Private by design",
    subtitle: "Built from the ground up on two balanced commitments to shopper and brand confidentiality.",
    columns: [
      {
        title: "Data never leaves its owner",
        bullets: [
          "Brand registry and shipment records stay within the brand's private node.",
          "PayPal customer records and payment tokens stay within PayPal's private node.",
          "Questions travel to the data as structured query specifications; only group-level answers return.",
        ],
      },
      {
        title: "No buyer is identifiable",
        bullets: [
          "Shopper demographic answers carry calibrated mathematical noise via OpenDP.",
          "Small cohort counts are suppressed to protect individual shopper identities.",
          "Each brand operates on a fixed lifetime privacy budget; repeating queries reveals nothing new.",
        ],
      },
    ],
    footnote: "Differential privacy guarantees backed by OpenDP and zero-concentrated differential privacy (zCDP). Details on the Privacy page.",
  },
  closing: {
    headline: "See what happens before payment.",
    body: "Run a verified checkout and a blocked one, then follow the cited autonomous investigation.",
    cta: "Start the guided demo",
  },
};
