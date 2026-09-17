# Workspace harness upgrades (VSIX 0.9.0)

## Why files kept changing

The previous activation path ran directory synchronization with overwrite enabled.
It guessed ownership from headings, refreshed files on every activation, removed
unlisted pubmed-/pipeline-prefixed skill directories, and removed old backups.
That allowed an older installed VSIX to revert newly edited source harness files.

## New contract

- Automatic installation is **off** by default (`zoteroMcp.autoUpdateHarness`).
  The Zotero MCP: Install Official Assistant Assets command is the explicit entry point. Enabling
  automatic updates uses exactly the same preservation rules as manual installs.
- Trusted workspaces only; Keeper/PubMed source repositories are skipped.
- `.vscode/zotero-mcp-assets.json` records extension version and per-file SHA-256.
  Never delete/edit this ledger merely to force an overwrite.
- New files can be installed. Existing unknown/edited files, including empty
  files, are preserved; a familiar heading is not evidence of ownership.
- A managed file updates only when its bytes still match the recorded hash and
  the incoming extension version is newer. Same-version divergent bundles and
  downgrades cannot replace it. Unchanged installs do not touch file timestamps.
- Before an update, previous bytes are backed up under
  `.vscode/zotero-mcp-backups/<version>/<sha256>/<relative-path>`.
- Skills are units: an unknown skill, changed/deleted managed file, or extra
  user file preserves the whole skill, including scripts and references.
- User-deleted managed files are not resurrected. Retired skills and old backups
  are not deleted. Review obsolete assets manually after upgrading.
- Symlink destinations fail before installation. A lock prevents competing
  VS Code windows from updating the ledger concurrently. A stale lock is reported
  for manual review; it is never automatically broken.

## Upgrading an existing custom workspace

Install 0.9.0, reload VS Code, and invoke Zotero MCP: Install Official Assistant Assets. Review the
preserved-file count. Existing pre-ledger custom skills will deliberately remain
unchanged. Compare them with `resources/repo-assets/` from the installed extension
and merge the desired new tool contracts; keep your changes and backups. An
older extension in another VS Code/remote profile must also be upgraded or
disabled: new code cannot stop a separately running old installer.

PubMed 0.7.3 retires the earlier PICO/session calls. Use agent-extracted P/I/C/O
with `validate_pico_plan`, then pass its pipeline to `unified_search`. Read state
with `read_session(request={"action":"pmids"})`, `article`, `summary`, or `log`.

## Maintainers

Edit canonical `.codex`, `.cline`, `.clinerules`, `AGENTS.md` and curated
`.github` sources. PubMed user skills/hooks come from the pinned submodule.
Run `npm run sync-assets` before packaging; `npm run sync-assets:check` generates
into a temporary directory and compares without rewriting the checked bundle.
Python caches are excluded. Do not import user-installed unrelated skills into
the release. Run harness preservation tests and validate the packaged sources.
