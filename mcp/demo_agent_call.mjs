#!/usr/bin/env node
// Acts like an AI shopping agent: connects to the TrustLedger brand verification MCP server,
// discovers its tools and asks the brand whether a product may be sold at a store.
//
//   node demo_agent_call.mjs                                   # X123 / NMB-P8-128 at store_b
//   node demo_agent_call.mjs --store store_a --serial NMB100003 --sku NMB-P8-128
//   MCP_URL=http://localhost:3333/mcp node demo_agent_call.mjs
//
// Only calls verifyProduct (never confirmSale), so it never marks a serial sold.
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

const MCP_URL = process.env.MCP_URL || "http://localhost:3333/mcp";

function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
}

const request = {
  serial: arg("serial", "X123"),
  sku: arg("sku", "NMB-P8-128"),
  store_id: arg("store", "store_b"),
  requested_at: new Date().toISOString(),
};

const color = process.stdout.isTTY && !process.env.NO_COLOR;
const paint = (code) => (s) => (color ? `\x1b[${code}m${s}\x1b[0m` : s);
const bold = paint("1");
const dim = paint("2");
const green = paint("1;32");
const red = paint("1;31");
const cyan = paint("36");

const line = dim("─".repeat(60));
const step = (n, text) => console.log(`\n${cyan(`[${n}]`)} ${bold(text)}`);

console.log(line);
console.log(bold("TrustLedger · AI agent → brand verification over MCP"));
console.log(line);

const client = new Client({ name: "trustledger-demo-agent", version: "1.0.0" });
const transport = new StreamableHTTPClientTransport(new URL(MCP_URL));

try {
  step(1, `Connecting to MCP server ${MCP_URL}`);
  await client.connect(transport);
  const info = client.getServerVersion();
  console.log(`    connected to ${info?.name} v${info?.version}`);

  step(2, "Discovering tools");
  const { tools } = await client.listTools();
  for (const t of tools) {
    console.log(`    • ${t.name.padEnd(14)} ${dim(t.description.split("\n")[0].slice(0, 70) + "…")}`);
  }

  step(3, "Calling verifyProduct");
  for (const [k, v] of Object.entries(request)) console.log(`    ${k.padEnd(13)} ${v}`);
  const result = await client.callTool({ name: "verifyProduct", arguments: { requestBody: request } });
  const text = result.content?.find((c) => c.type === "text")?.text ?? "";

  step(4, "Brand verdict");
  const status = text.match(/Status: (\d+)/)?.[1];
  const jsonStart = text.indexOf("{");
  if (status !== "200" || jsonStart < 0) {
    console.log(red(`    ${text}`));
    process.exitCode = 1;
  } else {
    const verdict = JSON.parse(text.slice(jsonStart));
    const ok = verdict.result === "VERIFIED";
    console.log(`    result           ${ok ? green("✔ VERIFIED") : red("✘ NOT_VERIFIED")}`);
    console.log(`    reason_code      ${verdict.reason_code ?? dim("null")}`);
    console.log(`    verification_id  ${verdict.verification_id}`);
    console.log(
      "\n    " +
        (ok
          ? green("→ Safe to create the PayPal order (verification_id goes in custom_id).")
          : red("→ Do not take payment: no PayPal order is created.")),
    );
    console.log(`\n${dim("Raw MCP tool result:")}\n${dim(text)}`);
  }
} catch (err) {
  console.error(red(`\nMCP call failed: ${err.message}`));
  process.exitCode = 1;
} finally {
  await transport.terminateSession().catch(() => {});
  await client.close().catch(() => {});
}
console.log(line);
