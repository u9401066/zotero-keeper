# Contributing to Zotero Keeper

First off, thank you for considering contributing to Zotero Keeper! 🎉

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
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

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (required package manager)
- Zotero 7.0+ (for testing)
- Git

### Setup Steps

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/zotero-keeper.git
cd zotero-keeper

# 2. Create virtual environment with uv
cd mcp-server
uv venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# 3. Install in development mode
uv pip install -e ".[dev]"

# 4. Copy environment config
cp ../.env.example .env
# Edit .env with your Zotero settings

# 5. Run tests
pytest

# 6. Run linting
ruff check src/
mypy src/
```

### Testing with Zotero

1. Ensure Zotero 7+ is running
2. Enable Local API in Zotero:
   ```javascript
   // Run in Zotero console (Tools > Developer > Run JavaScript)
   Zotero.Prefs.set("httpServer.localAPI.enabled", true)
   ```
3. Run the test script:
   ```bash
   python test_mcp_tools.py
   ```

---

## Pull Request Process

### Before Submitting

- [ ] Code follows project style guidelines
- [ ] Tests pass locally (`pytest`)
- [ ] Linting passes (`ruff check src/`)
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
