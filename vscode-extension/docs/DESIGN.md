# VS Code Extension Design — Zotero Keeper + PubMed Search MCP

> **Active contract (v0.8.0, 2026-08-19):** the VSIX manages one isolated
> Python 3.12 environment containing Zotero Keeper 2.2.0 and PubMed Search MCP
> 0.6.3 at release commit `febf53a`. Both servers use MCP SDK 2.x; SDK 1.x is not
> compatible with this environment.

## 1. Product boundary

The extension is the installer and runtime coordinator. It does not reimplement
Zotero or PubMed operations:

- Zotero Keeper owns the 41 default Zotero tools, 5 legacy opt-in tools,
  6 concrete resources, and 4 resource templates.
- PubMed Search MCP owns its 45-tool discovery, full-text, export, and research
  chronicle workflow.
- The extension owns Python provisioning, exact package-source installation,
  MCP server definitions, consumer configuration, settings, status, and bundled
  assistant assets.

```text
VS Code / Copilot       Cline                  Codex CLI
        │                 │                        │
        └─────────────────┴────────────────────────┘
                          │ stdio MCP
                          ▼
       extension-managed Python 3.12 environment
          ├── Zotero Keeper 2.2.0 (MCP SDK v2)
          └── PubMed Search MCP 0.6.3 @ febf53a
                    │                    │
                    │ loopback HTTP     └── biomedical APIs
                    ▼
              Zotero Desktop :23119
          ├── Local API v3
          └── Connector compatibility endpoints
```

## 2. Runtime components

| Component | Responsibility |
|---|---|
| `extension.ts` | Activation, setup orchestration, commands, status, consumer and assistant-asset synchronization |
| `UvPythonManager` | Download pinned `uv`, provision Python 3.12, create the global-storage venv, and atomically install/verify both packages |
| `PythonEnvironment` | System-Python fallback while still installing into an extension-managed writable venv |
| `ZoteroMcpServerProvider` | Register enabled stdio servers through VS Code's `McpServerDefinitionProvider` API |
| `clineMcpConfig.ts` | Synchronize only extension-managed Cline server entries |
| `codexMcpConfig.ts` | Synchronize delimited extension-managed Codex configuration blocks |
| `statusBar.ts` | Connection, setup, package, and API-setting status |

The extension requires VS Code 1.99 or newer for the MCP provider API.

## 3. Activation and installation flow

```text
activate
  │
  ├── register commands and status UI
  ├── resolve Python
  │     ├── default: uv-managed Python 3.12
  │     └── fallback: validated system Python + managed venv
  ├── verify install-state, distribution metadata, and direct_url source
  │     └── stale/missing state → atomically reinstall both pinned packages
  ├── register native VS Code MCP definitions
  ├── synchronize extension-owned Cline/Codex entries
  ├── probe Zotero without blocking activation
  └── install/update official assistant assets without replacing user-owned files
```

`UvPythonManager` installs the two Python distributions in one resolver
invocation. This avoids an observable intermediate environment containing one
SDK generation or only one server. Its install-state records Python and exact
package specifications; runtime verification also checks installed distribution
versions and PEP 610 source metadata.

The active package pins are:

- `zotero-keeper` 2.2.0 from the `v0.8.0-ext` GitHub tag archive,
  `#subdirectory=mcp-server`.
- `pubmed-search-mcp` 0.6.3 from release commit
  `febf53a8ff1ee253a625869ba251365f73a23c68`.

## 4. MCP registration

The provider starts both servers with the same resolved Python interpreter:

| Label | Entrypoint | Advertised version | Environment boundary |
|---|---|---|---|
| Zotero Keeper | `python -m zotero_mcp` | `2.2.0` | `ZOTERO_HOST`, `ZOTERO_PORT` only |
| PubMed Search | `python -m pubmed_search.presentation.mcp_server` | `0.6.3` | NCBI/source/proxy/OpenURL settings and optional workspace path |

VS Code consumes these definitions natively. Cline and Codex use their own
configuration formats, so activation updates only entries/blocks that the
extension can identify as its own. Disabling a server removes only that managed
entry; unrelated user configuration is preserved.

## 5. Zotero API and authorization boundary

The extension supplies only the loopback host and port. Zotero Keeper performs
all capability discovery, user authorization, and writes at runtime:

1. `GET /api/` discovers the Local API/schema versions and
   `Zotero-Server-ID` without prompting.
2. Zotero 10+ write tools use `/api/local/authorize`. The resulting API key is
   held only in Keeper process memory; it is never placed in extension settings,
   stdio MCP messages, logs, or URLs.
3. Mutations propose first, require explicit `confirm=true`, bind to the
   discovered Server-ID, and use local object-version/write-token preconditions.
4. A conflict, Zotero identity change, timeout, or ambiguous failure stops the
   operation without automatic mutation replay.
5. Stored attachments use Zotero's three-phase protocol. Upload bytes go only
   to a validated loopback upload URL and never carry the API-key header.

The Connector endpoints remain a supported create/import compatibility path.
They are the available write path on Zotero 7–9 and may still be used by
existing import tools on Zotero 10+. A custom Zotero plugin is not required for
the official basic CRUD transport or stored-file upload on Zotero 10+; Keeper's
MCP surface deliberately exposes only confirmed, versioned task tools and no
general raw-API escape hatch.

## 6. Settings surface

Settings are grouped by concern:

- Runtime: `useEmbeddedPython`, `pythonPath`, `autoInstallPackages`.
- Zotero: `zoteroHost`, `zoteroPort`, `enableZoteroKeeper`.
- PubMed and sources: `ncbiEmail`, API keys, proxy settings, and OpenURL
  resolver/preset.
- Consumers: `enablePubmedSearch`, `installCodexConfig`.
- Diagnostics: `logLevel`.

`useEmbeddedPython=true` is the default. A custom Python path is considered only
when embedded Python is disabled or provisioning falls back. Port 23119 is a
loopback-only trust boundary and must not be forwarded to a LAN or the Internet.

## 7. Assistant assets

The VSIX packages canonical repository assets under
`resources/repo-assets/**`. `npm run sync-assets` regenerates that packaged
mirror before packaging. Installation/update logic:

- installs the official Zotero Keeper and PubMed harnesses and supported PubMed
  skills;
- updates files the extension owns;
- cleans only explicitly known stale extension-owned asset names; and
- preserves custom `AGENTS.md`, Copilot instructions, Cline settings, Codex
  content outside managed blocks, and unrelated user skills.

The source assets and packaged mirror are release-gated for byte-for-byte
synchronization.

## 8. Failure and recovery model

- Provisioning failure leaves the MCP provider unregistered and displays a
  repair action; it does not install into system site-packages.
- Package version or source drift invalidates readiness and triggers a managed
  refresh.
- A package upgrade is attempted in the existing healthy venv before a full
  environment rebuild.
- Setup is serialized so two activation/command paths cannot mutate the venv at
  the same time.
- Zotero being closed does not corrupt setup: package/provider readiness and
  desktop connectivity are distinct status states.

## 9. Release and packaging contract

The release workflow must produce one explicit VSIX path and use that same file
for every downstream action:

1. synchronize assistant assets;
2. compile and run extension tests;
3. validate Keeper/VSIX/package-source/version pins;
4. package once to the requested VSIX path;
5. inspect the packaged `package.json`, compiled Keeper version/source tag,
   required assets, and forbidden files;
6. publish that exact VSIX through `vsce --packagePath`; and
7. attach the same path to the GitHub release.

The release tag is `v<extension-version>-ext` (for this release,
`v0.8.0-ext`). The tagged archive must be installable by the managed-install
smoke test and report Keeper 2.2.0 with all 41 default tools, including
`authorize_local_writes`, `delete_item`, and `replace_attachment_file`.

## 10. Compatibility matrix

| Desktop | Reads | Create/import | Authorized Local API writes | Plugin requirement |
|---|---|---|---|---|
| Zotero 7–9 | Local API | Connector | Not available | Optional future fallback for operations beyond Connector |
| Zotero 10+ | Local API v3 | Connector or Local API v3 | Runtime-authorized, Server-ID/version guarded | Not required for the official basic CRUD/upload transport; MCP remains allowlisted |
| Remote library | Authenticated HTTPS Web API or separately secured service | Same | Never forward local port 23119 | Local plugin/Connector paths are not remote APIs |

## 11. Historical pre-v0.7 design context

> **Historical only:** the original v0.1–v0.3 sketches assumed a
> `pythonSetup.ts` detector, optional installation into a user-selected Python,
> and pre-bundled wheel directories. Those sketches also showed Keeper 2.0.0,
> 24 default tools, VSIX 0.6.0, and Local/Connector endpoints as wholly
> unauthenticated. They describe the pre-Zotero-10 and pre-uv-managed design,
> not the active v0.8.0 contract.

The early roadmap proposed these phases:

| Historical phase | Original idea | Current disposition |
|---|---|---|
| v0.1 MVP | Basic provider, Python detection, settings | Delivered through the current provider and setup flow |
| v0.2 polish | Status, errors, walkthrough, bundled wheels | Status/walkthrough delivered; source-pinned uv install replaced bundled wheels |
| v0.3 advanced | Collection browser, quick-pick, inline citation | Not part of the current installer contract |

The old layout sketch is retained here solely to explain the migration:

```text
vscode-zotero-mcp/                 # historical sketch, never the active v0.7 layout
├── src/extension.ts
├── src/pythonSetup.ts
├── bundled/*.whl
└── scripts/install.py
```

The current implementation instead uses `UvPythonManager`, exact GitHub archive
pins, distribution/source verification, atomic installation, and the official
VS Code MCP provider API.
