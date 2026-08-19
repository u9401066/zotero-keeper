# Contributing to Zotero Keeper

First off, thank you for considering contributing to Zotero Keeper! 🎉

The current release baseline is Zotero Keeper 2.2.0 in VSIX v0.8.0: 41 default MCP SDK v2 tools, 6 concrete resources, and 4 parameterized URI templates.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Zotero Compatibility and Write Safety](#zotero-compatibility-and-write-safety)
- [Pull Request Process](#pull-request-process)
- [Style Guidelines](#style-guidelines)

---

## Code of Conduct

This project and everyone participating in it is governed by our commitment to providing a welcoming and inclusive environment. Please be respectful and constructive in all interactions.

---

## How Can I Contribute?

### 🐛 Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

- **Clear title** describing the issue
- **Steps to reproduce** the behavior
- **Expected behavior** vs actual behavior
- **Environment details** (Python version, OS, Zotero version)
- **Error messages** or logs if available

### 💡 Suggesting Features

Feature requests are welcome! Please:

- Check if the feature is already on our [ROADMAP.md](ROADMAP.md)
- Open an issue with the `enhancement` label
- Describe the use case and expected behavior
- Consider if it fits the project's scope

### 🔧 Pull Requests

We love PRs! Here's how to contribute code:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit with clear messages
6. Push and open a PR

---

## Development Setup

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (required package manager)
- Zotero 7–10+ (choose versions from the test matrix below)
- Git

### Setup Steps

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/zotero-keeper.git
cd zotero-keeper/mcp-server

# 2. Install development dependencies (uv manages the virtualenv)
uv sync --extra dev --extra all

# 3. Copy environment config
cp ../.env.example .env
# Edit .env with your Zotero settings

# 4. Run tests
uv run pytest tests/ -v --tb=short

# 5. Run linting / type checks
uv run ruff check src/
uv run mypy src/ --ignore-missing-imports
```

### Testing with Zotero

1. Ensure the Zotero version under test is running on the same machine
2. Enable Local API in Zotero:
   ```javascript
   // Run in Zotero console (Tools > Developer > Run JavaScript)
   Zotero.Prefs.set("httpServer.localAPI.enabled", true)
   ```
3. Run the test script:
   ```bash
   uv run python scripts/test_mcp_tools.py
   ```

## Zotero Compatibility and Write Safety

Keeper supports Zotero 7–10+ with feature gates:

| Test target | Required coverage |
|-------------|-------------------|
| Zotero 7 | Reads/resources and Connector-based save/import; Local write tools report unsupported |
| Zotero 8 | Zotero 7 coverage plus top-level annotation filtering |
| Zotero 9 | Zotero 7 compatibility coverage |
| Zotero 10+ | All earlier coverage plus runtime-authorized Local API v3 writes and file-view URLs |

The public Zotero 10+ write surface must retain these exact signatures:

```python
authorize_local_writes(require_remembered: bool = False)
create_collection(name, parent_collection_key=None, confirm=False, expected_server_id=None)
add_items_to_collection(item_keys, collection_key, confirm=False, expected_server_id=None)
update_item_fields(item_key, fields, expected_version, confirm=False, expected_server_id=None)
create_note(parent_item_key, note_html, confirm=False, expected_server_id=None)
create_saved_search(name, conditions, confirm=False, expected_server_id=None)
attach_file_to_item(item_key, file_path, title="Full Text PDF", confirm=False, expected_server_id=None)
set_attachment_fulltext(
    attachment_key,
    content,
    expected_library_version,
    indexed_pages=None,
    total_pages=None,
    indexed_chars=None,
    total_chars=None,
    confirm=False,
    expected_server_id=None,
)
```

Contributions to this surface must preserve the following invariants:

- Before preview, obtain a response-bound `server_id` from a Local API read or
  authorization. Every mutation called with `confirm=false` includes it as
  `expected_server_id`, returns a complete proposal, and makes zero client reads,
  authorization calls, filesystem probes, or writes. Never add identity after
  preview.
- The runtime key from `authorize_local_writes` is process memory only. It must never appear in MCP schemas, logs, exceptions, or tool results. `require_remembered=true` must enforce reusable **Always Allow** authorization before a multi-write attachment upload.
- Object keys use exact eight-character validation. Never accept a matching substring, prefix, URL, or path as an item/collection key.
- Authorization, caches, and optimistic-concurrency cursors are partitioned by
  `Zotero-Server-ID`. Every confirmed mutation requires the reviewed
  `expected_server_id`. If authorization returns a different identity, discard
  the proposal, reread the targets/cursors, preview again, and request approval
  again; a 412 conflict is returned without retry.
- `update_item_fields` requires a response-bound exact-item
  `expected_version`. `set_attachment_fulltext` instead requires the
  response-bound `expected_library_version` and uses bulk
  `POST /api/users/0/fulltext` with `If-Unmodified-Since-Version`; attachment
  object versions are not full-text write cursors.
- `add_items_to_collection` completes exact reads and payload validation for the destination and all one-to-50 items before its single batch write. It preserves the complete existing `collections` arrays and returns ordered per-item statuses for a partial result.
- `update_item_fields` only accepts a non-empty mapping of finite scalar metadata values. Identity, version, hierarchy, collections, tags, creators, relations, deletion state, notes, and attachment-storage structure stay behind dedicated code paths.
- `attach_file_to_item` uses Zotero's three-phase stored-file upload. Later-phase errors must preserve `attachment_key` and `partial=true` when a child was already created; never compensate with an unconfirmed delete.
- `get_item_attachments` prefers `/items/{key}/file/view/url`, safely parses and URL-decodes local `file://` URLs across supported platforms, and falls back to `ZOTERO_DATA_DIR` without failing the whole list.
- Write tools remain `readOnlyHint=false` and `openWorldHint=false`.
  `update_item_fields` and `set_attachment_fulltext` are replacement-style and
  therefore use `destructiveHint=true`; authorization and the five
  additive/create/upload mutations use `destructiveHint=false`. Keep
  `idempotentHint` aligned with the implementation. Keeper exposes no raw delete
  MCP tool.

The minimum automated matrix includes unit tests for validation and stable errors; schema/call smoke tests against an in-memory MCP client; zero-interaction tests for all seven `confirm=false` mutations; authorization denial/single-use/remembered behavior; Server-ID 428/412 paths; stale versions with no retry; collection batch prevalidation and partial results; three upload phases and partial failure; and Local file-URL parsing/fallback. Real Zotero mutation tests must use a disposable library and explicit operator confirmation, never a contributor's production library.

Use the official specifications as the protocol source of truth:

- [Local API v3](https://www.zotero.org/support/dev/web_api/v3/local_api)
- [Write requests and version preconditions](https://www.zotero.org/support/dev/web_api/v3/write_requests)
- [Three-phase file upload](https://www.zotero.org/support/dev/web_api/v3/file_upload)
- [Full-text content](https://www.zotero.org/support/dev/web_api/v3/fulltext_content)

---

## Pull Request Process

### Before Submitting

- [ ] Code follows project style guidelines
- [ ] Tests pass locally (`uv run pytest tests/ -v --tb=short`)
- [ ] Linting passes (`uv run ruff check src/`)
- [ ] Docs guard passes when documentation changes (`uv run python ../scripts/check_collaboration_safe_docs.py`)
- [ ] Documentation updated if needed
- [ ] CHANGELOG.md updated for notable changes

### PR Title Format

Use conventional commit format:

- `feat: add new feature`
- `fix: resolve bug in X`
- `docs: update README`
- `refactor: improve code structure`
- `test: add tests for X`
- `chore: update dependencies`

### Review Process

1. Maintainers will review your PR
2. Address any feedback
3. Once approved, PR will be merged
4. Your contribution will be in the next release! 🎉

---

## Style Guidelines

### Python Code Style

- Follow [PEP 8](https://pep8.org/)
- Use type hints for function signatures
- Maximum line length: 100 characters
- Use `ruff` for linting

```python
# Good
async def search_items(query: str, limit: int = 25) -> dict[str, Any]:
    """Search for items in Zotero library."""
    ...

# Avoid
async def search_items(query, limit=25):
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def add_reference(
    title: str,
    authors: list[str],
    doi: Optional[str] = None,
) -> dict[str, Any]:
    """
    Add a new reference to Zotero.

    Args:
        title: The reference title
        authors: List of author names
        doi: Optional DOI identifier

    Returns:
        Dictionary with success status and item key

    Raises:
        ZoteroConnectionError: If cannot connect to Zotero
    """
```

### Commit Messages

- Use present tense ("add feature" not "added feature")
- Use imperative mood ("move cursor" not "moves cursor")
- Keep first line under 72 characters
- Reference issues when relevant (`fixes #123`)

---

## Questions?

Feel free to:

- Open an issue for questions
- Start a discussion in GitHub Discussions
- Check existing documentation

Thank you for contributing! 🙏
