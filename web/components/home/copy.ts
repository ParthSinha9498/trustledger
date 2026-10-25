export const LANDING_COPY = {
  hero: {
    eyebrow: "Authenticity before payment",
    headline: "Verify the product. Then pay.",
    subhead: "TrustLedger checks a product with its brand before PayPal creates an order. Failed checks open an investigation instead.",
    primaryCta: "Try the checkout demo",
    secondaryCta: "Explore the brand cockpit",
  },
  heroFlow: {
    steps: [
      { title: "Product serial scanned", body: "Brand verification requested", badge: "Step 1" },
      { title: "Brand confirms the unit", body: "A deterministic yes or no", badge: "Verified" },
      { title: "PayPal order created", body: "Verification ID stored with the order", badge: "Paid" },
    ],
    blocked: { title: "Blocked at another store", body: "No PayPal order exists. An investigation opens.", badge: "Blocked" },
  },
  how: {
    title: "How it works",
    steps: [
      { title: "Scan the serial", body: "The store's checkout sends the product serial before payment starts." },
      { title: "Ask the brand", body: "The brand's own system decides whether this unit belongs at this store. No AI here." },
      { title: "Pay or investigate", body: "Verified: PayPal creates the order. Blocked: no order exists, and an AI agent investigates." },
    ],
  },
  features: {
    title: "What you can try",
    cards: [
      { title: "Checkout gate", body: "Verification runs before a PayPal order exists. The verification ID is stored on the order.", href: "/pos", image: "/media/01_pos_verified.png", size: "large" },
      { title: "AI investigations", body: "An agent questions brand and PayPal data, never sees a record, and cites every step.", href: "/cockpit", image: "/media/04_cockpit_case.png", size: "large" },
      { title: "Brand Insights", body: "Ask in plain English. Answers come from verified purchases in seconds.", href: "/cockpit/console" },
      { title: "Supply-chain timeline", body: "See which batches went where, and where units were sold off-route.", href: "/cockpit/supply-chain" },
      { title: "Privacy", body: "Two separate data nodes. Only group-level answers come back.", href: "/privacy" },
    ],
  },
  business: {
    title: "Why brands pay for this",
    subhead: "The check is free for shoppers. Brands pay for what verified purchases tell them.",
    reasons: [
      { title: "Real buyers, not panels", body: "Answers come from verified purchases, not self-reported surveys." },
      { title: "Seconds, not weeks", body: "Ask a business question in plain English and get an answer in seconds." },
      { title: "Leaks they can act on", body: "Every blocked sale opens a cited investigation into where units left the route." },
    ],
    chain: ["Verified purchases", "Privacy-safe insights", "Brand revenue", "Free checks for shoppers"],
    lines: [
      "Brands pay for answers from verified purchases, so the authenticity check stays free for shoppers.",
    ],
  },
  privacy: {
    title: "Private by design",
    columns: [
      {
        title: "Data never leaves its owner",
        bullets: [
          "Brand records stay with the brand.",
          "PayPal records stay with PayPal.",
          "Questions travel to the data; only group answers return.",
        ],
      },
      {
        title: "No buyer is identifiable",
        bullets: [
          "Answers about buyers carry calibrated noise.",
          "Small groups are hidden.",
          "Each brand has a fixed lifetime privacy allowance; repeats reveal nothing new.",
        ],
      },
    ],
    footnote: "Differential privacy (OpenDP). Details on the Privacy page.",
  },
  closing: {
    headline: "See what happens before payment.",
    body: "Run a verified checkout and a blocked one, then follow the investigation.",
    cta: "Start the guided demo",
  },
};
