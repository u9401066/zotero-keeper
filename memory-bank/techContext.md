# Technical Context

## Technologies

### Core Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.12+ (managed baseline) | Both MCP runtimes; Keeper requires 3.12+ |
| MCP Python SDK | `>=2.0,<3` | SDK v2 `mcp.server.MCPServer` |
| httpx | `>=0.27` (Keeper) | Async Zotero / external HTTP client |
| Pydantic | `>=2.0` | Data validation and settings |
| uv | extension-bundled/current | Resolver, venv and package installer |
| Node.js | 18+ | VS Code extension development/runtime tooling |
| TypeScript | repository lock | VS Code Extension API integration |

SDK v1 `FastMCP` 與 SDK v2 不相容。Keeper `2.1.0` 與 PubMed Search MCP
`0.6.1` 必須共用同一個 SDK v2 runtime；`mcp-types` 等 v2 transitive packages
由 `uv.lock` / resolver 管理，不在兩套應用間另行分叉版本。

### Development Tools

| Tool | Purpose |
|------|---------|
| pytest / pytest-asyncio / pytest-xdist | Python unit, async, integration tests |
| ruff / mypy | Python lint and type checks |
| tsc / ESLint / Mocha | Extension compile, lint and unit tests |
| `vsce` | VSIX package and Marketplace publish |

### Target Environment

| Component | Specification |
|-----------|---------------|
| Zotero | 7.0+ desktop；10+ 才提供 authorized Local API writes |
| OS | Linux / Windows / macOS |
| Managed Python | 3.12+ |
| VS Code | 1.99+ MCP provider API |

## Release Runtime Sets

| Line | Component set | Runtime surface | Status |
|------|---------------|-----------------|--------|
| `v0.6.0-ext` | extension `0.6.0`, Keeper `2.0.0`, PubMed `0.6.1` | 24 Keeper tools / 6 resources; 45 PubMed tools; MCP SDK v2 | published 2026-08-11 |
| `v0.7.0-ext` | extension `0.7.0`, Keeper `2.1.0`, PubMed `0.6.1` | 32 Keeper tools / 6 resources; 45 PubMed tools; Zotero 10+ Local API writes | release in progress |
| PubMed fixed source | commit `ad85dde08269dbb59eff69d2e92f4d3c5b5bf21d` | upstream `0.6.1` release commit | unchanged |

Previous lines `v0.5.35-ext` (Keeper `1.14.0`, PDF import) and `v0.6.0-ext`
(Keeper `2.0.0`, SDK v2 migration) are complete. The current release task is
`v0.7.0-ext`; it must not be described as published until its tag workflow and distribution
checks complete.

## VSIX Managed-install Invariants

- Package sources are centralized in `zoteroKeeperPackage.ts` and
  `pubmedSearchPackage.ts`; fixed direct URLs are checked through package metadata /
  `direct_url.json` and `install-state.json`.
- Both packages form one install unit in one writable extension-managed venv, including
  system/custom Python fallback flows. They must be resolved and installed together,
  not upgraded one at a time.
- Stop old MCP processes before replacing the environment. Mark the venv ready only
  after both versions and sources pass verification.
- Installation smoke must instantiate both concrete SDK v2 servers and call
  `list_tools` (Keeper 32, PubMed 45); importing modules alone does not detect a v1/v2
  runtime conflict.
- Assistant harness assets shipped in the VSIX include Copilot instructions, root
  `AGENTS.md`, `.codex/skills`, `.cline/skills`, `.clinerules`, and curated PubMed
  Claude skills. `npm run sync-assets` is required before packaging; PubMed v0.6.1 adds the
  `pubmed-research-chronicle` skill.
- The release process first passes version, managed-install, tag-archive and Local API
  smoke gates. The tag workflow then packages one named VSIX exactly once and inspects its
  content; both `vsce publish --packagePath` and GitHub Release consume that same file.

## Runtime Dependencies

Keeper's direct runtime dependencies:

```toml
dependencies = [
  "mcp>=2.0,<3",
  "httpx>=0.27.0",
  "pydantic>=2.0.0",
  "pydantic-settings>=2.0.0",
  "rapidfuzz>=3.0.0",
  "structlog>=24.4.0",
]

[project.optional-dependencies]
pubmed = ["pubmed-search-mcp>=0.6.1"]
```

PubMed Search MCP v0.6.1 independently declares `mcp>=2.0,<3` and Python
`>=3.10`; the combined VSIX environment follows Keeper's stricter Python 3.12+
baseline.

## API Specifications

### Zotero Local API (Zotero 10+ writes, port 23119)

**Origin**: `http://localhost:23119`（API base path 為 `/api`）

| Endpoint | Method | Use |
|----------|--------|-----|
| `/api/` | GET | discover API/schema versions and Zotero Server-ID |
| `/api/local/authorize` | POST | request runtime local-write authorization |
| `/api/users/0/items` | GET | item search/list |
| `/api/users/0/items` | POST | create items, notes or attachments (batch max 50) |
| `/api/users/0/items/{key}` | GET/PATCH | item metadata and local-version update |
| `/api/users/0/items/{key}/fulltext` | GET | indexed full text + response-bound library cursor |
| `/api/users/0/fulltext` | POST | Keeper bulk full-text write (max 10) with library-version precondition |
| `/api/users/0/items/{key}/file/view/url` | GET | official local attachment path resolution |
| `/api/users/0/collections` | GET/POST | collection discovery/create |
| `/api/users/0/collections/{key}` | PATCH | collection update with local version |
| `/api/users/0/searches` | GET/POST | saved-search list/create; local execution is supported |
| `/api/users/0/tags` | GET | tag discovery |
| `/api/itemTypes` | GET | available Zotero item types |

Local API reads remain unauthenticated on the desktop loopback listener. Every
`/api/local/authorize` and write request carries the Server-ID. The
response-bound identity is obtained before preview and included as
`expected_server_id`; all seven confirmed mutations require that reviewed value.
If authorization returns another identity, reread, preview, and obtain approval
again. The authorization key is runtime-only and unscoped; Keeper never persists
or returns it. Missing/mismatched identity (including 428/412), denial/rate
limits and 401 reauthorization are surfaced rather than blindly retried.

Item metadata uses the object version paired with the exact-item response.
Full-text replacement instead uses the response-bound library cursor and bulk
`POST /api/users/0/fulltext` with `If-Unmodified-Since-Version`; the attachment
object version is not interchangeable. Never combine a cursor with another
Server-ID, a Web API version, or another Zotero profile/process. PATCH arrays are
complete replacements, not merge operations; Keeper's public update tool
therefore exposes only an allowlist of scalar fields.

Attachment upload uses the official three phases: create the attachment item; request an
upload using `md5`, filename, filesize and mtime, then stream `prefix + file + suffix` to
the returned loopback upload URL; finally register the returned `uploadKey`. Full-file
uploads must remain below 4 GB. A late failure reports the already-created attachment key.

### Zotero Connector API

| Endpoint | Method | Use |
|----------|--------|-----|
| `/connector/ping` | GET | desktop/Connector capability probe |
| `/connector/saveItems` | POST | create mapped bibliographic items |
| `/connector/saveAttachment` | POST | attach PDF to an item created in the session |
| `/connector/saveStandaloneAttachment` | POST | standalone PDF / auto-recognize flow |

Zotero 7–9 continue to use this Connector path for imports and PDF workflows. Local API
reads, authorized Zotero 10+ writes and Connector writes all use the desktop user's Zotero
process and do not require a Zotero Web API key. Collection selection, confirmation and
duplicate checks remain product guardrails; absence of Web API credentials is not
permission to choose a destination for the user.

### MCP Runtime

- Concrete registration type: `mcp.server.MCPServer`
- Default extension transport: stdio
- Keeper also exposes SDK-supported SSE / streamable HTTP entrypoints, but remote use
  requires a separate security review and explicit configuration
- PubMed local mode defaults to stdio (or loopback-only HTTP); service mode supports
  authenticated, tenant-aware HTTP with transport security controls

## Network and Security Requirements

### Local / Connector Mode
- Zotero normally listens on loopback `127.0.0.1:23119`
- Never bind, proxy, tunnel or forward `localhost:23119` to another host; runtime Local API
  authorization is not remote-service authentication
- Local writes reject non-loopback Zotero hosts; runtime keys stay in process memory and
  Server-ID binds each write to the discovered desktop instance
- The VSIX launches both MCP servers over stdio in a user-owned managed venv
- Preserve `NCBI_EMAIL`, optional NCBI API key, OpenURL/institutional access settings
- Remote Zotero access requires a separate design; port forwarding is outside the supported
  Local API trust boundary

### Authenticated Service Mode
- Require an explicit credential/token policy and stable tenant identity
- Restrict bind host plus allowed Host/Origin values; retain DNS-rebinding protection
- Isolate session/cache/chronicle/workspace data per tenant
- Do not infer authentication from an MCP transport session id and do not reuse local
  stdio assumptions for an Internet-reachable endpoint

### Zotero MCP Ecosystem Isolation
- As of 2026-08-11, the Zotero official organization has not published an MCP server
- `54yyyu/zotero-mcp` is an MCP Registry-listed community project, not an official
  Zotero server
- It distributes the same `zotero_mcp` Python namespace as Keeper. Never install it in
  the VSIX managed venv; evaluation requires a separate interpreter/venv and distinct
  MCP server definition

## Configuration

### Core Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZOTERO_HOST` | `localhost` | Zotero Desktop host |
| `ZOTERO_PORT` | `23119` | Zotero HTTP port |
| `ZOTERO_TIMEOUT` | `30` | request timeout in seconds |
| `NCBI_EMAIL` | none | NCBI contact identity; preserve across upgrades |
| `NCBI_API_KEY` | none | optional NCBI API key; preserve across upgrades |
| `PUBMED_WORKSPACE_DIR` | workspace-specific | PubMed artifacts / project context |
| `ZOTERO_KEEPER_ENABLE_LEGACY_PUBMED_TOOLS` | disabled | opt-in legacy bridge surface |

There is intentionally no environment variable for a Zotero Local API write key. Keeper
obtains it at runtime from Zotero Desktop and does not persist it.

### MCP Client Command

The extension registers the managed interpreter directly. Manual clients use the same
entrypoints with an environment that satisfies the complete v2 package set:

```json
{
  "mcpServers": {
    "zotero-keeper": {
      "command": "/path/to/managed-venv/python",
      "args": ["-m", "zotero_mcp"]
    },
    "pubmed-search": {
      "command": "/path/to/managed-venv/python",
      "args": ["-m", "pubmed_search.presentation.mcp_server"]
    }
  }
}
```

---
*Updated: 2026-08-12*
