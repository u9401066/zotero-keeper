---
name: zotero-keeper-harness
description: "Codex harness for Zotero Keeper and the bundled VS Code extension. Triggers: zotero keeper, zotero mcp, full check, release checklist, workflow, vsix, Codex."
---

# Zotero Keeper: Codex Harness Skill

Use this skill when working with Codex on Zotero Keeper, the VS Code extension,
or the installed Zotero + PubMed MCP workspace harness.

## What To Read First

- `AGENTS.md` for Codex workspace instructions.
- `.github/zotero-research-workflow.md` for the end-user research flow.
- `.clinerules/` for repo and release guardrails that also apply to Codex.
- `.claude/skills/pubmed-*` for user-facing research skills.

## Canonical Commands

- Keeper Python package: `cd mcp-server && uv run pytest`
- Keeper lint/type smoke: `cd mcp-server && uv run ruff check . && uv run mypy src --ignore-missing-imports`
- Extension: `cd vscode-extension && npm run sync-assets && npm run compile && npm test`
- VSIX package smoke: `cd vscode-extension && npm run package`
- VSIX contents: `cd vscode-extension && powershell -NoProfile -ExecutionPolicy Bypass -File ./scripts/check-vsix-contents.ps1`

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
- Do not bypass NCBI email policy; use explicit settings or git email fallback.
- Treat VSIX install/update as a first-class path: bundled repo assets must be synced before package.

## Zotero 10.0.2 / Keeper 2.3 Contract

- Default surface: 48 tools; use `get_item_schema` before creator/field edits and `get_item_annotations` for raw annotation data.
- Use `update_item_tags`, `update_item_creators`, `update_note`, and `batch_update_item_fields` for their narrow tasks. Batches contain 1–50 exact keys/object versions; inspect partial results, never replay blindly.
- Prefer reversible `set_item_trashed` to permanent `delete_item`. Confirm restore operations too.
- Saved searches support nested groups and resultLevel item/attachment/note/annotation. Keep child results by default; paginate using start/limit. Search modes serialize as condition/mode; required=true is rejected because Zotero JSON ignores it.
- Workspace harness installation is opt-in (`zoteroMcp.autoUpdateHarness=false`). Never infer ownership from headings or delete skills by prefix. Preserve unknown/edited/deleted files and whole custom skills; hash-matched upgrades require backups and a newer extension version.
- Source workspaces are not installation targets. `sync-assets:check` is read-only; run `sync-assets` explicitly before packaging.
- Read the [tool audit](https://github.com/u9401066/zotero-keeper/blob/main/docs/ZOTERO_10_TOOL_AUDIT.md) for coverage and deliberate API boundaries.
