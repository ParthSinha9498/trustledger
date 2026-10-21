# APIMatic: SDKs, docs portal and Context Plugin for the brand verification API

APIMatic (hackathon sponsor) turns `openapi/brand-verification.yaml` into SDKs, a brand onboarding docs
portal, a Context Plugin for AI coding assistants and, in alpha, an MCP server. This folder is the
docs-as-code project for its CLI. Everything is set up; the commands that call APIMatic need an
`APIMATIC_API_KEY`, which we don't have yet.

Until then, the MCP server in `../mcp/` (generated with openapi-mcp-generator) covers the agent use case.

## Layout

Follows [apimatic/sample-docs-as-code-portal](https://github.com/apimatic/sample-docs-as-code-portal),
`master` branch (the layout for CLI v1):

```
apimatic/
  src/
    APIMATIC-BUILD.json          portal title, languages (HTTP, TypeScript, Python, C#), theme, MCP setting
    plugin-config.json           Context Plugin metadata (languages are filled in by `sdk:publish`)
    spec/
      brand-verification.yaml    copy of ../openapi/brand-verification.yaml (the only API spec)
      APIMATIC-META.json         import and codegen settings
    content/
      toc.yml                    portal navigation
      guides/brand-onboarding.md
    static/images/               logo and favicon
```

The CLI writes `portal/`, `sdk/` and `plugin/` next to `src/` (gitignored).

**Keep the spec copy in sync** after regenerating the spec with `scripts/export_openapi.py`:

```bash
cp openapi/brand-verification.yaml apimatic/src/spec/brand-verification.yaml
cmp openapi/brand-verification.yaml apimatic/src/spec/brand-verification.yaml && echo in sync
```

## Which CLI version

We use **`@apimatic/cli` 1.5.0** (`latest`). It runs on our Node 22 (needs Node 20 or newer) and has every
command we need, including `plugin:generate` for Context Plugins. `@apimatic/cli@beta` (2.0.0-beta.6)
needs Node 24 or newer and a different project layout (`apimatic.json`, `nav.json`, the sample repo's
`v2` branch). It offers nothing we need over 1.5.0, so we stay on v1.

The CLI doesn't read an environment variable for the key. Pass it with `--auth-key "$APIMATIC_API_KEY"` on
each command, or log in once (stored in the CLI's config directory):

```bash
npx -y @apimatic/cli@1.5.0 auth:login --auth-key "$APIMATIC_API_KEY"
```

The commands below pass `--auth-key` explicitly so they also work in CI. Run them from the repo root.
Optional: `export APIMATIC_CLI_TELEMETRY_OPTOUT=1`.

```bash
alias apimatic='npx -y @apimatic/cli@1.5.0'
```

## Commands

| # | Step | Command | Needs `APIMATIC_API_KEY` |
| --- | --- | --- | --- |
| 1 | Validate the spec (APIMatic's validator) | `apimatic api:validate --file apimatic/src/spec/brand-verification.yaml --auth-key "$APIMATIC_API_KEY"` | **Yes** |
| 1b | Lint the spec locally (independent OpenAPI 3.1 linter, not APIMatic) | `npx -y @redocly/cli@2 lint apimatic/src/spec/brand-verification.yaml` | No |
| 2 | Generate the TypeScript SDK | `apimatic sdk:generate --language typescript --input apimatic --auth-key "$APIMATIC_API_KEY"` | **Yes** |
| 3 | Generate the Python SDK | `apimatic sdk:generate --language python --input apimatic --auth-key "$APIMATIC_API_KEY"` | **Yes** |
| 4 | Generate the C# SDK (if the plan allows it) | `apimatic sdk:generate --language csharp --input apimatic --auth-key "$APIMATIC_API_KEY"` | **Yes** |
| 5 | Serve the portal locally with hot reload (http://localhost:23513) | `apimatic portal:serve --input apimatic --open --auth-key "$APIMATIC_API_KEY"` | **Yes** (the portal is built by APIMatic's service) |
| 6 | Generate the static portal into `apimatic/portal/` | `apimatic portal:generate --input apimatic --auth-key "$APIMATIC_API_KEY"` | **Yes** |
| 7 | Publish an SDK (needed before step 8) | `apimatic sdk:publish --input apimatic --language typescript --version 0.1.0 --publish-type sourcecode --update-plugin-config --auth-key "$APIMATIC_API_KEY"` (add `--profile-id` from `apimatic publishing:profile:list`; `--dry-run` to only generate) | **Yes**, plus a publishing profile set up in the APIMatic app and a Git repo for the SDK source |
| 8 | Generate the Context Plugin into `apimatic/plugin/` | `apimatic plugin:generate --input apimatic --auth-key "$APIMATIC_API_KEY"` | **Yes** for the generation itself. Without published SDKs it stops locally and prints the next steps (no key needed for that) |
| 9 | Print the git commands to publish the plugin | `apimatic plugin:publish --input apimatic` | No (it only prints commands), but it needs the `plugin/` folder from step 8 |

SDKs land in `apimatic/sdk/<language>/`. `--zip` downloads a zip instead; `--codegen-version v4` tries the
newer generator.

### Context Plugin

`src/plugin-config.json` already holds the plugin identity (`trustledger-brand-verification`, version
0.1.0, MIT). A Context Plugin teaches AI coding assistants (Claude Code, Cursor, VS Code) how to use the
**published** SDKs, so the CLI needs at least one SDK with a source repository or package before it
generates anything. `sdk:publish --update-plugin-config` records that in the `languages` block.

### APIMatic MCP server (alpha)

`APIMATIC-BUILD.json` contains APIMatic's experimental `mcpServer` setting, switched off:

```json
"mcpServer": { "$type": "nonNull", "isEnabled": false, "preferPublishedSdk": false }
```

Once APIMatic grants alpha access, set `"isEnabled": true` and run step 6. Its schema says the MCP server
is built on the TypeScript SDK, which is already configured. It's off for now so a normal account doesn't
fail on a feature it can't use. This is the intended production replacement for `../mcp/`.

## What was checked without an account (2026-10-21)

- `APIMATIC-BUILD.json` validates against APIMatic's published build schema
  (`https://titan.apimatic.io/api/build/schema`). One caveat: that schema uses discriminator base types
  (`McpServerConfigBase`, `AiAssistMenuConfigBase`) with `additionalProperties: false`, which a strict
  JSON Schema validator rejects even for APIMatic's own documented shape. With that relaxed there are 0
  errors. The sample repo's build file passes as-is.
- `npx @redocly/cli@2 lint` on the spec: valid, 1 warning (`servers[0]` is localhost, which is intended
  for the reference brand).
- CLI 1.5.0 `plugin:generate`: reads `src/plugin-config.json`, accepts the metadata, and stops with "no
  published SDKs config yet" (expected).
- CLI 1.5.0 `api:validate`, `sdk:generate`, `portal:generate`, `portal:toc:new`, `auth:status`: all
  stop with "Authorization has been denied", so they need the key. Nothing APIMatic-side (SDK output,
  portal rendering, how the spec imports) has been checked yet.
