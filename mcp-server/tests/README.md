# Tests

This directory contains tests for Zotero Keeper MCP Server.

## Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=zotero_mcp --cov-report=html

# Run specific test file
pytest tests/test_client.py -v
```

## Test Categories

- `test_client.py` - Zotero HTTP client tests
- `test_tools.py` - MCP tools tests
- `test_smart.py` - Smart features tests (duplicate detection, validation)

## Note

Some tests require a running Zotero instance. These are marked with `@pytest.mark.integration`.
