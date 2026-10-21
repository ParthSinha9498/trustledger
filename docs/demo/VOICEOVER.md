# Demo voice-over script (v2, agreed with Antigravity in DEMO-3)

Target: about 2:25 of picture, read at a calm ~150 words per minute (about 330 words). Each block matches one
scene; the seconds are the scene's length. Rule: a scene lasts at least words ÷ 2.5 + 0.5 s, so static
cards are held as long as the narration needs. Captions on screen
stay short; the voice carries the explanation.

| # | Scene (seconds) | Narration |
|---|---|---|
| 1 | Hook (4) | One phone. One serial number. Two stores. |
| 2 | Problem (7) | Counterfeits are a four-hundred-and-sixty-seven-billion-dollar trade. In smartphones, one sale in eight is lost to fakes. |
| 3 | Gap (8) | Brands offer verification. But it's optional, separate from paying, and different for every brand. So nobody uses it. |
| 4 | Idea (8) | TrustLedger makes authenticity a condition of payment. If the brand doesn't verify the product, the PayPal payment never exists. |
| 5 | Scenario 1 (20) | Store A is an authorized retailer. It scans serial X123. The brand confirms the unit belongs to this store, and only then does PayPal create the order, with the verification ID stored in the order itself. The buyer approves in PayPal, and the receipt is brand verified. |
| 6 | Scenario 2 (12) | Now Store B scans the same serial. This unit was never shipped to Store B. The checkout stops before any money moves: no PayPal order is ever created. |
| 7 | Compare (4) | Same serial. One payment exists. One never does. |
| 8 | Scenario 3 (24) | The failure opens a case for the brand. An AI agent investigates on its own: it chooses each query, weighs the privacy cost, and works only from aggregates. Never a single buyer record. It ends with findings that name where the evidence diverges, and cites the steps behind each one. |
| 9 | Scenario 4 (18) | Analysts can ask their own questions under the same rules. Ask for individual buyers, and the question becomes a privacy-protected count, with noise, confidence intervals and a budget that every query spends. |
| 10 | Red team (6) | We attacked it two hundred and twenty times. Nothing confident got out. |
| 11 | Scenario 5 (14) | The same check works for AI shopping agents. Over MCP, an agent asks the brand before it pays, and stops when the answer is no. |
| 12 | Onboard (12) | Brands implement one API. From that spec, APIMatic generates SDKs, a docs portal and an MCP server. And our own PayPal integration runs on the APIMatic PayPal Server SDK. |
| 13 | Close (8) | Trust at checkout for buyers. Intelligence for brands. A more trusted network for PayPal. This is TrustLedger. |

## Accuracy notes (must stay true to the product)

- "one sale in eight" = 12.9% (EUIPO/ITU, 2015 data); the card shows the source and year.
- Scenario 3 narration must not name a store or distributor: the live agent's finding varies by run, and the
  caption and ring follow what it actually found in the take we use.
- "Nothing confident got out" = 220 of 220 scripted attempts blocked, best guesses at chance
  (evals/results/redteam_repeated.md). Don't say "nothing leaked".
- Scenario 5: the MCP server is generated with openapi-mcp-generator today; APIMatic's MCP generator is in
  alpha. Narration says "from its spec, APIMatic generates SDKs, a docs portal and an MCP server" only if we
  have alpha access by recording day; otherwise: "SDKs and a docs portal, and an MCP server for agents."
