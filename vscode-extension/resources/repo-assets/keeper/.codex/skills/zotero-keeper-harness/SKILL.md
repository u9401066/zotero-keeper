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

- Keep Keeper 2.x and PubMed Search MCP 0.6.x on the same MCP SDK v2 runtime;
  managed-environment upgrades must resolve both packages together.
- Keep Zotero local-library behavior separate from PubMed literature-search behavior.
- Use `import_articles` as the preferred bridge from PubMed results/RIS into Zotero.
- Require a confirmed collection; set `allow_library_root=true` only after the
  user explicitly approves a My Library root import.
- Do not bypass NCBI email policy; use explicit settings or git email fallback.
- Treat VSIX install/update as a first-class path: bundled repo assets must be synced before package.
