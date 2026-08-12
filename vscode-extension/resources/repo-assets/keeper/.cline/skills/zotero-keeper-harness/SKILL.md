---
name: zotero-keeper-harness
description: "Cline harness for Zotero Keeper and the bundled VS Code extension. Triggers: zotero keeper, zotero mcp, full check, release checklist, workflow, vsix, Cline."
---

# Zotero Keeper: Cline Harness Skill

Use this skill when working in this repository with Cline and you need the reliable loop:
understand the Zotero/PubMed boundary, make a scoped change, verify it, and keep the
VSIX install path healthy.

## What To Use First

- Rules: `.clinerules/`
- Workflows: `.clinerules/workflows/`
  - Run `/zotero-full-check.md` for local gates.
  - Run `/zotero-release-publish.md` for a guided extension release.
  - Run `/zotero-skills-audit.md` after changing skills or rules.
- Existing skills: `.claude/skills/`
  - If a `.claude/skills` instruction conflicts with current repo behavior, prefer `.clinerules/`.

## Canonical Commands

- Keeper Python package: `cd mcp-server && uv run pytest`
- Keeper lint/type smoke: `cd mcp-server && uv run ruff check . && uv run mypy src --ignore-missing-imports`
- Extension: `cd vscode-extension && npm run sync-assets && npm run compile && npm test`
- VSIX package smoke: `cd vscode-extension && npm run package`
- PubMed submodule smoke: `cd external/pubmed-search-mcp && uv run pytest tests/test_mcp_server.py tests/test_settings.py`

## Product Guardrails

- Keep Keeper 2.x and PubMed Search MCP 0.6.x on the same MCP SDK v2 runtime;
  managed-environment upgrades must resolve both packages together.
- Keep Zotero local-library behavior separate from PubMed literature-search behavior.
- Use `import_articles` as the preferred bridge from PubMed results/RIS into Zotero.
- Require a confirmed collection; set `allow_library_root=true` only after the
  user explicitly approves a My Library root import.
- For Zotero 10+ Local API mutations, first obtain a response-bound `server_id`
  from a read or authorization and include it as `expected_server_id` in the
  `confirm=false` preview. Execute the unchanged proposal only after approval;
  every confirmed mutation requires that identity, and a changed authorization
  identity requires a fresh read, preview, and approval.
- Use a response-bound item object version for `update_item_fields`; use the
  response-bound library cursor for `set_attachment_fulltext`. Never substitute
  the attachment object version or replay a 412 conflict.
- Keep port 23119 on loopback and the Local API key private. Require
  `authorize_local_writes(require_remembered=true)` plus **Always Allow** before
  `attach_file_to_item`.
- Do not bypass the NCBI email policy; use explicit settings or the git email fallback.
- Treat VSIX install as a first-class path: bundled repo assets must be synced before compile/package.
