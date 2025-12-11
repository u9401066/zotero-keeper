# Zotero MCP Server

Python MCP Server for managing local Zotero libraries through the MCP Bridge plugin.

## Architecture (DDD)

```
src/zotero_mcp/
├── domain/              # Domain Layer (核心業務邏輯)
│   ├── entities/        # 實體
│   ├── value_objects/   # 值物件
│   ├── repositories/    # Repository 介面
│   └── services/        # Domain Services
│
├── application/         # Application Layer (用例)
│   ├── use_cases/       # 應用程式用例
│   └── dto/             # Data Transfer Objects
│
├── infrastructure/      # Infrastructure Layer (基礎設施)
│   ├── zotero_client/   # Zotero HTTP Client
│   └── repositories/    # Repository 實作
│
└── interface/           # Interface Layer (MCP 介面)
    └── tools/           # MCP Tools 定義
```

## Installation

```bash
cd mcp-server
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

### Run MCP Server

```bash
zotero-mcp
```

### Configure in VS Code MCP

```json
{
  "servers": {
    "zotero": {
      "command": "/path/to/mcp-server/.venv/bin/zotero-mcp"
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `add_reference` | 新增文獻到 Zotero |
| `get_reference` | 取得文獻詳細資訊 |
| `list_collections` | 列出所有文獻夾 |
| `create_collection` | 建立新文獻夾 |
| `add_to_collection` | 將文獻加入文獻夾 |
| `export_references` | 匯出參考文獻 |
| `check_connection` | 檢查 Zotero 連線狀態 |

## Development

```bash
# Run tests
pytest

# Type checking
mypy src/

# Linting
ruff check src/
```
