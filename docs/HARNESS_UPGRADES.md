# Workspace harness upgrades (VSIX 0.9.1)

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
- Files and ledger are planned together, backups are verified, and each file is
  replaced atomically. Ordinary failures roll back the applied changes. A user
  edit made during the update or rollback is never replaced by recovery code.
- `.vscode/zotero-mcp-assets.pending.json` records an interrupted transaction,
  including before/after hashes and backup paths. Its presence blocks subsequent
  updates even if the lock is removed; no repeated overwrite attempts occur.

## Interrupted-update recovery

Close other VS Code windows using the workspace before reviewing a stale lock.
Keep a copy of the pending record and any edited files. Each journal entry lists
the destination, its previous hash (`null` means newly installed), incoming hash,
and the recovery backup when a previous file existed.

To roll back manually, restore only files still matching the journal's incoming
hash from their verified backups, including the previous ownership ledger.
Review newly installed files individually before removing them; never remove
edited files or a whole skills directory. Files with neither recorded hash are
user changes and require manual merging. If the old ledger did not exist, do not
invent ownership for pre-existing files.

Alternatively, when every installed file and the ledger already match the
completed new bundle, retain that consistent state. Only after checking the
whole transaction should you archive/remove the pending record and stale lock,
then run the explicit installer again. Never clear these files just to force an
upgrade over unresolved edits. Backups and retired assets are not auto-deleted.

## Upgrading an existing custom workspace

Install 0.9.1, reload VS Code, and invoke Zotero MCP: Install Official Assistant Assets. Review the
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
