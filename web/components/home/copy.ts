/**
 * Landing Page Copy Constants.
 * Centralized so that final ChatGPT copy from user can be dropped in with zero layout changes.
 */

export const LANDING_COPY = {
  hero: {
    badge: "Authenticity as a Condition of Payment",
    headline: "Authenticity, checked before payment.",
    explanation: "Before PayPal creates an order, the brand confirms the product is genuine. If it isn't, there is no order, and an AI agent investigates where it came from.",
    primaryCta: { text: "Try the checkout →", href: "/pos" },
    secondaryCta: { text: "Explore the brand cockpit", href: "/cockpit" },
    verdictVerified: {
      tag: "VERIFIED · Store A",
      serial: "serial: X123",
      title: "Authenticity confirmed at Store A",
      subtitle: "PayPal payment order created",
    },
    verdictBlocked: {
      tag: "BLOCKED · Store C",
      serial: "serial: X123",
      title: "Serial not assigned to Store C",
      subtitle: "No order created · Investigation opened",
    },
  },
  howItWorks: {
    title: "How It Works",
    steps: [
      {
        step: "Step 1",
        title: "Scan at checkout",
        description: "The store's barcode scanner sends the serial number through the TrustLedger API before payment begins.",
      },
      {
        step: "Step 2",
        title: "Brand verifies",
        description: "The brand confirms the unit is genuine and in its authorized channel before any payment transaction exists.",
      },
      {
        step: "Step 3",
        title: "PayPal pays or AI investigates",
        description: "If verified, PayPal creates the payment order. If unverified, no order is created and an autonomous agent investigates the divergence.",
      },
    ],
  },
  features: {
    title: "Product Features",
    cards: [
      {
        title: "Point-of-Sale Gate",
        badge: "Checkout",
        description: "Verify before paying. Unverified items never create an order, preventing unverified sales before money moves.",
        href: "/pos",
      },
      {
        title: "Autonomous AI Investigations",
        badge: "Cockpit",
        description: "When a scan fails, an AI agent investigates supply chain batches and cites every step of its evidence.",
        href: "/cockpit",
      },
      {
        title: "Brand Insights",
        badge: "Console",
        description: "Ask business questions in plain English and receive answers from verified purchases in seconds with privacy protection.",
        href: "/cockpit/console",
      },
      {
        title: "Supply Chain Timeline",
        badge: "Schedule",
        description: "Track shipments and identify unauthorized stock diversions across distributor channels on an interactive timeline.",
        href: "/cockpit/supply-chain",
      },
      {
        title: "Privacy Protections",
        badge: "Architecture",
        description: "Two separate data nodes answer questions with privacy protection; raw records never move.",
        href: "/privacy",
      },
    ],
  },
  businessModel: {
    tag: "Business Model",
    headline: "Self-sustaining: Intelligence pays for the protection.",
    statNumber: "$150B+",
    statLabel: "market",
    body: "Brands pay for privacy-safe insights from verified purchases; the authenticity check is free for shoppers. Brands spend over USD 150B a year on market insights (ESOMAR, 2024 data). Traditional surveys take weeks, and in a Pew survey (Nov 2024, 11,114 US adults), 18% of cases were flagged as bogus. TrustLedger delivers answers from verified purchases in seconds, and that revenue pays for the free check.",
    sources: "Data sources: ESOMAR Insights Industry report · Pew Research Center",
  },
  privacy: {
    title: "Private by Design",
    columns: [
      {
        title: "Data never leaves its owner",
        summary: "Brand serials and supply logs stay in the brand node. Transactions and buyer accounts stay in the PayPal node.",
        bullets: [
          "Brand serials and shipment logs stay with the brand.",
          "Transactions and buyer accounts stay with PayPal.",
          "Questions travel to the data as structured query specs; raw records never move.",
        ],
      },
      {
        title: "No buyer is identifiable",
        summary: "The AI analyst only answers about groups with mathematically guaranteed privacy protections.",
        bullets: [
          "Answers about buyers carry calibrated noise (differential privacy, OpenDP).",
          "Every buyer answer shows a 95% interval (±); brand counts are exact.",
          "Small groups are hidden.",
        ],
      },
    ],
  },
  closing: {
    headline: "Experience authenticity gating in action",
    subhead: "Follow the step-by-step interactive walkthrough or test a live transaction at the store checkout.",
    primaryCta: { text: "Interactive walkthrough →", href: "/story" },
    secondaryCta: { text: "Store checkout", href: "/pos" },
  },
};
