# TrustLedger brand verification MCP server

An [MCP](https://modelcontextprotocol.io) server for the brand verification API
(`openapi/brand-verification.yaml`). It lets AI shopping agents, POS assistants or any MCP client ask
a brand "may this serialized product be sold at this store?" before a PayPal order exists.

Generated with [openapi-mcp-generator](https://github.com/harsha-iiiv/openapi-mcp-generator) (v4.1.0);
APIMatic's MCP generator (alpha) is the intended production path once access is granted.

| Tool | API call | What it does |
| --- | --- | --- |
| `verifyProduct` | `POST /v1/verify` | Returns `VERIFIED`, or `NOT_VERIFIED` with a `reason_code` (`NOT_IN_CHANNEL`, `ALREADY_SOLD`, `UNKNOWN_SERIAL`, `SKU_MISMATCH`). |
| `confirmSale` | `POST /v1/verify/{verification_id}/confirm` | Marks the serial sold after the PayPal capture. Has side effects; agents normally only need `verifyProduct`. |

The server is a thin proxy: the verdict still comes from the brand's deterministic logic in the brand node.
Nothing about the decision is AI.

## Layout

```
mcp/
  brand-verification/     generated server (TypeScript, MCP SDK, Streamable HTTP on :3333)
    src/index.ts          tool definitions + HTTP calls to the brand API
    src/streamable-http.ts
    public/index.html     small browser test client served at http://localhost:3333/
  demo_agent_call.mjs     demo MCP client: connects, lists tools, calls verifyProduct
  package.json            dependency for the demo client (@modelcontextprotocol/sdk)
```

## Run it

Node 20+ is required (tested on Node 22.20).

```bash
cd mcp/brand-verification
npm install
npm run build

# Point it at a brand node. The token is the brand node's NODE_SHARED_TOKEN and is sent as X-Node-Token.
export API_BASE_URL=http://localhost:8001                # local uvicorn; the demo docker stack uses :8101
export API_KEY_NODETOKEN=...                             # e.g. $(docker exec tl-demo-brand-node-1 printenv NODE_SHARED_TOKEN)
npm run start:http                                       # MCP endpoint: http://localhost:3333/mcp
```

Instead of exporting variables you can copy `.env.example` to `.env` (it is gitignored).

| Env var | Default | Meaning |
| --- | --- | --- |
| `API_BASE_URL` | `http://localhost:8001` | Brand verification API base URL. |
| `API_KEY_NODETOKEN` | none | Value of the `X-Node-Token` header (the `NodeToken` security scheme). Missing or wrong gives a 401 from the brand, which the tool returns as an error. |
| `PORT` | `3333` | MCP HTTP port. |
| `HOST` | `127.0.0.1` | Listen address. The MCP endpoint itself has no auth and carries the brand token, so it listens on loopback only. Set `HOST=0.0.0.0` only behind your own auth/network boundary. |

Health check: `curl http://localhost:3333/health`.

### Demo agent call

With the server running:

```bash
cd mcp
npm install
node demo_agent_call.mjs                                          # X123 / NMB-P8-128 at store_b -> NOT_VERIFIED / NOT_IN_CHANNEL
node demo_agent_call.mjs --store store_a --serial NMB100003 --sku NMB-P8-128   # an unsold seeded serial -> VERIFIED
MCP_URL=http://localhost:3333/mcp node demo_agent_call.mjs        # other server URL
```

The demo only calls `verifyProduct`, never `confirmSale`, so it never marks a serial sold. Each verify call
does add a row to the brand's verification log, like any checkout scan. Don't run it for `X123` at
`store_a` right before recording the main demo; that is the demo serial.

You can also call the tool with the official MCP Inspector, headless:

```bash
npx -y @modelcontextprotocol/inspector --cli http://localhost:3333/mcp --transport http \
  --method tools/call --tool-name verifyProduct \
  --tool-arg 'requestBody={"serial":"X123","sku":"NMB-P8-128","store_id":"store_b"}'
```

## Use it from Claude

Start the server as above first.

**Claude Code** (Streamable HTTP is supported directly):

```bash
claude mcp add --transport http trustledger-brand http://localhost:3333/mcp
```

or in a project `.mcp.json`:

```json
{
  "mcpServers": {
    "trustledger-brand": { "type": "http", "url": "http://localhost:3333/mcp" }
  }
}
```

**Claude Desktop** (`claude_desktop_config.json`; Desktop launches local servers over stdio, so bridge
to the HTTP endpoint with `mcp-remote`):

```json
{
  "mcpServers": {
    "trustledger-brand": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost:3333/mcp"]
    }
  }
}
```

Then ask, for example: "Is serial X123 (SKU NMB-P8-128) OK to sell at store_b?"

## Regenerating

```bash
npx -y openapi-mcp-generator@4 --input openapi/brand-verification.yaml --output mcp/brand-verification \
  --transport=streamable-http --port=3333 --server-name trustledger-brand-verification \
  --base-url http://localhost:8001 --force
```

The generator handled our OpenAPI 3.1 spec without changes. `--base-url` is needed because the spec lists two
servers. After regenerating, re-apply these small patches (each is marked `TrustLedger patch` in the source):

1. `src/streamable-http.ts`: clone the request before parsing it. With MCP SDK 1.32 the generated code
   crashed the process on the first request ("ReadableStream is locked").
2. `src/index.ts` + `src/streamable-http.ts`: create one MCP `Server` per session (`createServer()`).
   The generated single shared instance only served the first client; every later client got a 500
   ("Already connected to a transport").
3. `src/streamable-http.ts`: a `DELETE /mcp` handler so clients can end their session.
4. `src/streamable-http.ts`: listen on `HOST` (default `127.0.0.1`) instead of all interfaces.
5. `src/streamable-http.ts`: fixed the `public/` path so the browser test client loads.
6. `src/index.ts`: read `PORT` from the environment (the generator hardcodes 3333). `.env.example` defaults updated.

## Production path

APIMatic (hackathon sponsor) generates SDKs, the docs portal and, in alpha, MCP servers from the same spec.
Once we have access, its MCP output replaces this folder. See `../apimatic/README.md`.
