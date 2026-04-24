---
name: uv-enforcer
description: "Enforce uv-only package management policy. Reject all pip usage in code, docs, CI. Triggers: UV, uv, pip, package, 套件, 安裝, install, 環境, environment, dependency, 依賴."
---

# uv 唯一套件管理技能

## 描述
確保專案中所有 Python 套件管理操作僅使用 uv，禁止任何 pip 使用。
涵蓋程式碼、文件、CI/CD、設定檔。

## 觸發條件
- 出現 `pip install`、`pip freeze`、`pip list` 等 pip 指令
- 建立新的 Python 環境或安裝套件
- 撰寫安裝文件或 README
- CI/CD 設定
- 任何套件管理相關操作

## 核心規則

### 🚫 禁止事項（絕對不可出現）

| 禁止指令 | 替代指令 |
|----------|----------|
| `pip install package` | `uv add package` 或 `uv pip install package` |
| `pip install -r requirements.txt` | `uv pip install -r requirements.txt` 或 `uv sync` |
| `pip install -e .` | `uv pip install -e .` |
| `pip install -e ".[dev]"` | `uv pip install -e ".[dev]"` |
| `pip freeze` | `uv pip freeze` |
| `pip list` | `uv pip list` |
| `pip uninstall` | `uv pip uninstall` |
| `pip show` | `uv pip show` |
| `python -m pip` | `uv pip` |
| `python -m venv .venv` | `uv venv` |

### ✅ 標準指令

```bash
# 環境建立
uv venv                          # 建立虛擬環境
uv python pin 3.12               # 固定 Python 版本

# 套件安裝
uv add package                   # 新增依賴到 pyproject.toml
uv add --dev package             # 新增開發依賴
uv sync                          # 從 uv.lock 同步安裝
uv pip install -e ".[dev]"       # 傳統方式安裝（仍使用 uv）

# 套件管理
uv lock                          # 鎖定依賴
uv lock --upgrade                # 更新依賴
uv remove package                # 移除依賴

# 執行
uv run pytest                    # 透過 uv 執行指令
uvx ruff check .                 # 臨時執行工具（類似 npx）
```

## 檢查程序

### Step 1: 掃描 pip 引用
```bash
# 在專案中搜尋所有 pip 引用
grep -rn "pip install\|pip freeze\|pip list\|pip show\|pip uninstall" \
  --include="*.md" --include="*.py" --include="*.ts" --include="*.yml" --include="*.yaml" \
  --include="*.toml" --include="*.cfg" --include="*.txt" --include="*.sh" \
  --include="*.ps1" --include="*.bat" --include="Dockerfile*"
```

### Step 2: 逐一替換
對每個找到的 pip 引用：
1. 判斷上下文（文件說明 or 實際指令）
2. 替換為對應的 uv 指令
3. 確保語意一致

### Step 3: 驗證
- [ ] 所有 `pip install` → `uv pip install` 或 `uv add`
- [ ] 所有 `pip freeze` → `uv pip freeze`
- [ ] 所有 `python -m venv` → `uv venv`
- [ ] CI/CD 使用 `astral-sh/setup-uv@v4`
- [ ] Dockerfile 使用 uv（禁止 pip）
- [ ] TypeScript 程式碼中無 pip fallback

## 程式碼範例

### TypeScript（VS Code Extension）
```typescript
// ❌ 禁止
cmd = `"${pythonPath}" -m pip install --upgrade ${packages}`;

// ✅ 正確
const uvPath = this.getUvPath();
if (!uvPath) {
    this.log('❌ uv not found. Please install uv.');
    return false;
}
cmd = `"${uvPath}" pip install --upgrade --python "${pythonPath}" ${packages}`;
```

### Python（pyproject.toml）
```toml
# ✅ 正確的依賴管理
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "pytest>=9.0.2",
    "pytest-xdist>=3.3.0",
]
```

### Markdown（文件）
```markdown
<!-- ❌ 禁止 -->
pip install zotero-keeper

<!-- ✅ 正確 -->
uv pip install zotero-keeper
```

### GitHub Actions（CI/CD）
```yaml
# ✅ 正確
steps:
  - uses: astral-sh/setup-uv@v4
    with:
      version: "latest"
  - run: uv sync --all-extras
  - run: uv run pytest
```

### Dockerfile
```dockerfile
# ✅ 正確
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN uv pip install --system --no-cache -r pyproject.toml
```

## 法規依據
- 憲法第 7.2 條「環境即程式碼」
- 子法：`.github/bylaws/python-environment.md`
- Copilot 指令：`.github/copilot-instructions.md`
