# Copilot 自定義指令 - Zotero Keeper

## 專案概述
這是一個整合 PubMed 文獻搜尋與 Zotero 書目管理的 AI 輔助研究工具組。

## 開發哲學 💡
> **「想要寫文件的時候，就更新 Memory Bank 吧！」**
> 
> **「想要零散測試的時候，就寫測試檔案進 tests/ 資料夾吧！」**

## 法規遵循
你必須遵守以下法規層級：
1. **憲法**：`CONSTITUTION.md` - 最高原則
2. **子法**：`.github/bylaws/*.md` - 細則規範
3. **技能**：`.claude/skills/*/SKILL.md` - 操作程序

## 架構原則
- 採用 DDD (Domain-Driven Design)
- DAL (Data Access Layer) 必須獨立
- 參見子法：`.github/bylaws/ddd-architecture.md`

## Python 環境（uv 優先）
- 新專案必須使用 uv 管理套件
- 必須建立虛擬環境（禁止全域安裝）
- 參見子法：`.github/bylaws/python-environment.md`

## Memory Bank 同步
每次重要操作必須更新 Memory Bank：
- 參見子法：`.github/bylaws/memory-bank.md`
- 目錄：`memory-bank/`

## Git 工作流
提交前必須執行檢查清單：
- 參見子法：`.github/bylaws/git-workflow.md`

## MCP Server 開發
- pubmed-search-mcp: `external/pubmed-search-mcp/`
- zotero-keeper: `mcp-server/`
- 使用 FastMCP 框架

## VS Code Extension 開發
- 位置: `vscode-extension/`
- 使用 TypeScript
- 發布到 VS Code Marketplace 與 Open VSX

### 發布流程

#### 1. 版本更新檢查清單
發布前必須同步更新以下檔案的版本號：
- `vscode-extension/package.json` - `version` 欄位
- `vscode-extension/src/statusBar.ts` - `private version` 欄位（fallback 用）
- `vscode-extension/CHANGELOG.md` - 新增版本區塊

#### 2. 編譯驗證
```bash
cd vscode-extension
npm run compile  # 確保無 TypeScript 錯誤
```

#### 3. 提交與發布
```bash
# 提交變更
git add -A && git commit -m "release: vX.Y.Z - 簡短描述"

# 建立 tag 並推送（觸發 CI 自動發布）
git tag -a vX.Y.Z-ext -m "Release vX.Y.Z"
git push && git push origin vX.Y.Z-ext
```

**重要**：tag 格式必須為 `vX.Y.Z-ext`，CI workflow 才會觸發發布

#### 4. 驗證發布成功

**GitHub Actions（最即時）**
```bash
# 檢查 workflow 狀態
curl -s "https://api.github.com/repos/u9401066/zotero-keeper/actions/runs?per_page=5" | \
  grep -E '"(name|status|conclusion|head_branch)"' | head -20
```
- `Publish VS Code Extension` - `conclusion: success` 表示成功

**VS Marketplace（1-5 分鐘後更新）**
- URL: https://marketplace.visualstudio.com/items?itemName=u9401066.vscode-zotero-mcp
```bash
npx @vscode/vsce show u9401066.vscode-zotero-mcp --json | grep version
```

**Open VSX（可能需要更長時間）**
- URL: https://open-vsx.org/extension/u9401066/vscode-zotero-mcp
```bash
npx ovsx get u9401066.vscode-zotero-mcp --json | grep version
```

#### 5. 常見問題排除

| 問題 | 原因 | 解決方案 |
|------|------|----------|
| "version already exists" | Marketplace 已有此版本 | 升級版本號重新發布 |
| "Repository signing failed" | Open VSX 暫時性錯誤 | 等待後重試或檢查 `OVSX_PAT` |
| Open VSX "Extension Not Found" | Token 權限或首次發布審核 | 檢查 workflow log |
| CI 未觸發 | tag 格式錯誤 | 確保使用 `vX.Y.Z-ext` 格式 |

#### 6. Secrets 設定（Repository Settings）
- `VSCE_PAT` - VS Code Marketplace Personal Access Token
- `OVSX_PAT` - Open VSX Personal Access Token

### 平台支援
擴充功能支援以下平台：
- `win32-x64`, `win32-ia32` (Windows)
- `linux-x64`, `linux-arm64` (Linux)
- `darwin-x64`, `darwin-arm64` (macOS)

## 回應風格
- 使用繁體中文
- 提供清晰的步驟說明
- 引用相關法規條文
