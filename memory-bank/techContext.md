# Technical Context

## Technologies

### Core Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.12+ | Primary language |
| FastMCP | 0.4.0+ | MCP SDK |
| httpx | 0.27+ | Async HTTP client |
| Pydantic | 2.0+ | Data validation |

### Development Tools

| Tool | Purpose |
|------|---------|
| pytest | Unit/integration testing |
| pytest-asyncio | Async test support |
| ruff | Linting |
| mypy | Type checking |

### Target Environment

| Component | Specification |
|-----------|---------------|
| Zotero | 7.0+ (desktop client) |
| OS | Linux/Windows/macOS |
| Python | 3.12+ |

### VSIX Install Baseline

- Extension release line: `0.5.28` / `v0.5.28-ext`.
- Python baseline: 3.12+.
- Package installation uses `uv` into extension-managed venvs, including
  system/custom Python fallback paths.
- Runtime package sources are pinned in `zoteroKeeperPackage.ts` and
  `pubmedSearchPackage.ts` and verified with `direct_url.json`.
- Assistant harness assets shipped in the VSIX include Copilot instructions,
  root `AGENTS.md`, `.codex/skills`, `.cline/skills`, `.clinerules`, and the
  curated PubMed Claude skills.

## Dependencies

### Runtime Dependencies

```toml
[project.dependencies]
fastmcp = ">=0.4.0"
httpx = ">=0.27.0"
pydantic = ">=2.0.0"
pydantic-settings = ">=2.0.0"
```

### Development Dependencies

```toml
[project.optional-dependencies.dev]
pytest = ">=7.0.0"
pytest-asyncio = ">=0.21.0"
pytest-cov = ">=4.0.0"
ruff = ">=0.1.0"
mypy = ">=1.0.0"
```

## API Specifications

### Zotero Local API (port 23119)

**Base URL**: `http://{host}:23119`

| Endpoint | Method | Response |
|----------|--------|----------|
| `/api/users/0/items` | GET | JSON array of items |
| `/api/users/0/items/{key}` | GET | Single item JSON |
| `/api/users/0/collections` | GET | JSON array of collections |
| `/api/users/0/tags` | GET | JSON array of tags |
| `/api/itemTypes` | GET | Available item types |

### Zotero Connector API

| Endpoint | Method | Body | Response |
|----------|--------|------|----------|
| `/connector/ping` | GET | - | HTML status |
| `/connector/saveItems` | POST | Items JSON | Save result |

### MCP Protocol

Transport: stdio (default) or SSE

Tools registered:
- `search_items`
- `get_item`
- `list_items`
- `list_collections`
- `list_tags`
- `add_reference`
- `create_item`

## Network Requirements

### Local Setup
- Zotero running on same machine
- Access to localhost:23119

### Remote Setup
- Port proxy on Windows: `netsh interface portproxy`
- Firewall rule for port 23119
- Host header override required

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZOTERO_HOST` | `localhost` | Zotero machine IP |
| `ZOTERO_PORT` | `23119` | Zotero HTTP port |
| `ZOTERO_TIMEOUT` | `30` | Request timeout (seconds) |

### MCP Client Configuration

**VS Code Copilot** (`settings.json`):
```json
{
  "github.copilot.chat.agent.mcpServers": {
    "zotero-keeper": {
      "command": "python",
      "args": ["-m", "zotero_mcp"]
    }
  }
}
```

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "zotero-keeper": {
      "command": "python",
      "args": ["-m", "zotero_mcp"]
    }
  }
}
```

## Constraints

1. **Zotero Local API**: READ-only by design
2. **Network Binding**: Zotero binds to 127.0.0.1 only
3. **Authentication**: No auth on Local API
4. **Concurrency**: Single Zotero instance per user
