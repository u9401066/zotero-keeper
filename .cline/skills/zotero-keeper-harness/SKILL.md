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

- Keep Keeper 2.x and PubMed Search MCP 0.7.x on the same MCP SDK v2 runtime;
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
- Use the response-bound object version for exact updates/single-object deletes.
  Use the library cursor for `delete_tags`, `set_attachment_fulltext`, and
  `set_attachment_fulltexts`. For `replace_attachment_file`, bind the exact
  attachment version and previous MD5 to the reviewed identity. Never replay 412.
- Keep port 23119 on loopback and the Local API key private. Require
  `authorize_local_writes(require_remembered=true)` plus **Always Allow** before
  `attach_file_to_item` or `replace_attachment_file`.
- Do not bypass the NCBI email policy; use explicit settings or the git email fallback.
- Treat VSIX install as a first-class path: bundled repo assets must be synced before compile/package.

## Zotero 10.0.2 / Keeper 2.3 Contract

- Default surface: 48 tools; use `get_item_schema` before creator/field edits and `get_item_annotations` for raw annotation data.
- Use `update_item_tags`, `update_item_creators`, `update_note`, and `batch_update_item_fields` for their narrow tasks. Batches contain 1–50 exact keys/object versions; inspect partial results, never replay blindly.
- Prefer reversible `set_item_trashed` to permanent `delete_item`. Confirm restore operations too.
- Saved searches support nested groups and resultLevel item/attachment/note/annotation. Keep child results by default; paginate using start/limit. Search modes serialize as condition/mode; required=true is rejected because Zotero JSON ignores it.
- Workspace harness installation is opt-in (`zoteroMcp.autoUpdateHarness=false`). Never infer ownership from headings or delete skills by prefix. Preserve unknown/edited/deleted files and whole custom skills; hash-matched upgrades require backups and a newer extension version.
- Source workspaces are not installation targets. `sync-assets:check` is read-only; run `sync-assets` explicitly before packaging.
- A harness pending-transaction marker blocks installation. Do not delete it or break a stale lock to force an update; inspect the journal, verified backups and concurrent edits using the [recovery guide](https://github.com/u9401066/zotero-keeper/blob/main/docs/HARNESS_UPGRADES.md) first.
- Ownership scans discard partial results on identity/version drift. Statistics may return unknown counts with warnings; never interpret these as an empty library.
- Read the [tool audit](https://github.com/u9401066/zotero-keeper/blob/main/docs/ZOTERO_10_TOOL_AUDIT.md) for coverage and deliberate API boundaries.
