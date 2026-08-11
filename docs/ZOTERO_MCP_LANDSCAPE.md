# Zotero MCP Landscape

> Status checked: 2026-08-11. This document distinguishes project ownership from registry or connector distribution.

## Short answer

We did not find a Zotero-organization repository or Zotero documentation that publishes an official Zotero MCP server. A listing in an MCP registry, a curated connector catalog, or an app marketplace does not make a project an official Zotero product.

[`54yyyu/zotero-mcp`](https://github.com/54yyyu/zotero-mcp) is a feature-rich community server listed in the MCP Registry. It is not maintained by the Zotero organization. An OpenAI-curated Zotero connector is a separate connector product; it must not be described as Zotero's official MCP server, and this repository does not invent or promise a tool schema for it.

## Compared surfaces

| Surface | Ownership / status | Verified positioning | Installation boundary |
|---------|--------------------|----------------------|-----------------------|
| Zotero Keeper 2.0.0 | This repository | Local Zotero workflow with 24 default tools, including `import_pdf`; 6 concrete resources; collection validation, duplicate checks, saved searches, Connector-based imports, and the PubMed-to-Zotero handoff | Installed with PubMed Search MCP 0.6.1 in the v0.6.0 VSIX managed environment |
| `54yyyu/zotero-mcp` | Community project; MCP Registry-listed | Its own documentation describes library/collection/tag browsing, metadata and full-text access, semantic search, annotations and notes, adding records/files, and library-maintenance operations. Consult that project for its current tool contract | Must use a separate virtual environment and MCP process from Keeper |
| OpenAI-curated Zotero connector | Curated connector product; not a Zotero-organization server | Treat only its installed, discoverable connector contract as authoritative | Configure independently; do not assume its tools match either Python server |
| Zotero Web API | Official Zotero HTTPS API | Authenticated remote library access and supported CRUD operations | Preferred foundation for remote access |
| Zotero Local / Connector APIs | Official Zotero Desktop local interfaces | Local reading plus limited Connector save/attachment operations used by Keeper | Loopback only; never expose port 23119 directly |

## Why the Python environments must be separate

Zotero Keeper and the community `54yyyu/zotero-mcp` distribution both expose the Python module/package name `zotero_mcp`. Installing them into one environment can overwrite or shadow imports and console entry points. Version constraints alone cannot make two distributions safely own the same import namespace.

Use two isolated environments and two MCP server definitions:

```text
VS Code / MCP client
├─ Zotero Keeper process
│  └─ VSIX-managed venv: Keeper 2.0.0 + PubMed Search MCP 0.6.1
└─ Optional community Zotero MCP process
   └─ separate venv owned by that project
```

Do not add the community distribution to the VSIX-managed environment. Reinstalling or upgrading either project in the shared environment could silently change which `zotero_mcp` module starts.

## What the v0.6.0 VSIX guarantees

- Zotero Keeper 2.0.0 on `mcp>=2.0,<3`, using the SDK v2 `MCPServer` API.
- 24 default Keeper tools and 6 concrete resources; four parameterized resource templates are advertised separately.
- Fail-closed collection routing: exact-key or double-confirmed `ROOT` for `interactive_save`, and explicit `allow_library_root=true` after user confirmation for non-interactive root saves.
- PubMed Search MCP 0.6.1 pinned to commit `ad85dde`, with 45 tools in 16 categories.
- `build_research_chronicle` and `read_research_chronicle` in place of the former three timeline tools.
- An isolated Python 3.12 environment. MCP SDK 1.x and 2.x are not mixed.

The separately published PyPI/`uvx` package can remain on an older release line. Use the Marketplace VSIX when you need this exact paired runtime.

## Remote-access safety

Zotero's Local and Connector APIs are unauthenticated and intended for local applications. Keep them bound to loopback and run Keeper beside Zotero Desktop on the same trusted host. Do not expose or forward port 23119 to a LAN or the Internet.

For remote access, use the [official Zotero Web API](https://www.zotero.org/support/dev/web_api/v3/start) over authenticated HTTPS, or a purpose-built authenticated service with TLS, authorization, auditing, and explicit network access control.

## Source links

- [Zotero organization on GitHub](https://github.com/zotero)
- [Zotero developer documentation](https://www.zotero.org/support/dev/start)
- [Zotero Local API](https://www.zotero.org/support/dev/web_api/v3/local_api)
- [`54yyyu/zotero-mcp` community project](https://github.com/54yyyu/zotero-mcp)
- [Model Context Protocol Registry](https://registry.modelcontextprotocol.io/)
- [Zotero Web API v3](https://www.zotero.org/support/dev/web_api/v3/start)
