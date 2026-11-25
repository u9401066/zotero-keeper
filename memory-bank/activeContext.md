# Active Context

## 當前焦點

準備 VS Code extension / VSIX **0.12.0**（分支 `feat/pubmed-summary-records`，尚未推送、
尚未打 tag；tag 為 `v0.12.0-ext`）。Zotero Keeper 升為 **2.4.1**（patch：摘要紀錄拒絕與
null `urls` 修正），經 `v0.12.0-ext` tag archive 隨 VSIX 安裝，不另發 PyPI。
PubMed Search MCP 固定於正式 **0.12.0** release commit
`5842d229733d3f62ded49e033a97aacd8b006126`（tag `v0.12.0`），兩個 server 共用 MCP SDK v2。
Keeper 50 個預設 tools、6 個 resources、4 個 URI templates；PubMed 44 tools / 16 類
（0.12.0 新增 `register_fulltext`）。

## 本輪（0.12.0 / 2.4.1）完成

- PubMed 0.12.0：`unified_search` JSON/TOON 預設回傳摘要紀錄（`record_detail`；
  `options="full_records"` 取回完整紀錄）、`get_fulltext` 的 `fulltext_plan` 與
  `register_fulltext`、單篇 PMC 網頁備援、暫時性 NCBI 失敗重試並標示 retryable、
  PubMed 紀錄帶文章類型／PMCID／OA。Pin、submodule、managed-install smoke（44 tools、
  `register_fulltext`）、repo-assets 同步；curated skills 仍為 12 個。
- Keeper 2.4.1：`import_articles` / `import_pdf` 以 `abstract_snippet`、`abstract_truncated`、
  `author_count`（且未同時帶 `authors` 與 `abstract`）辨識摘要紀錄，逐筆拒絕
  （`code: "summary_record"`、`summary_records.next_commands`），全為摘要時在任何 Zotero
  呼叫前回 `error_code: "summary_records"`；完整紀錄 `urls` 含 null（無 PMCID/DOI/PMID）
  不再被 schema 拒絕。新模組 `infrastructure/mcp/unified_record_detail.py`；契約測試以
  submodule 的真實 0.12.0 builders 產生摘要／完整紀錄驗證分類。
- Server instructions、harness、research agent、Copilot 指令與文件：匯入前用
  `options="full_records"` 或 `fetch_article_details`；描述 44-tool 介面、retryable sources、
  `fulltext_plan` → `register_fulltext`（`zotero_attachment` 步驟用 `check_articles_owned`
  與 `get_item_attachments`）。

## 上一輪（0.11.0）完成

- 合併 `feature/claude-code-mcp-config`：extension 為 Claude Code 在 `~/.claude.json`
  註冊兩個 server；`zoteroMcp.claudeCodeMcpScope` = `local`（預設，依工作區資料夾）/
  `user` / `off`。SHA-256 ownership ledger、Claude Code 自己的 lock、原子寫入、
  `~/.claude.json.zotero-mcp.bak` 備份；永不寫入 `.mcp.json`。
- PubMed pin 與 submodule 升到 0.11.0（`eb7b2ee`）：exhaustive pipeline + PRISMA-S、
  `block_analysis`、`pipeline_screening`；精準優先 `unified_search` 並揭露放寬結果；
  MeSH 精確對應與自動修正；參考文獻更正；NCBI PMC 全文備援；Chronicle 研究設計標示。
- 同步 12 個 curated PubMed skills（新增 `pubmed-research-workspace`）、hook 工具政策、
  research agent、Copilot 指令、Codex/Cline harness 與文件到 43-tool 介面。
- `npm audit fix`（非 breaking）更新 vsce 3.9.2、msal-node、markdown-it，
  `npm audit --audit-level=high` 重新通過；VSIX 不含 npm 套件。
- `test_tool_reference_contract` 以 UTF-8 讀取 `docs/tools-reference.md`
  （cp950 等非 UTF-8 Windows locale 原本會失敗）。

## 上一輪（0.10.0 / 2.4.0）完成

- 本地閘門：`python scripts/pretest.py [--full]`（pre-push hook）；GitHub CI 只留
  clean install（lock/npm ci）、Windows+Linux runtime smoke、VSIX 打包、tag 發布；macOS 手動。
- 移除未使用的 domain Reference/Collection、logging_config、collection_utils 與空洞測試；
  新增 stdio 真實行程 smoke 與 edge 測試；修正讀取路徑注入、RIS/creator 邊界、設定驗證。
- Extension 全面審查：argv 取代 shell 字串、uv 下載 SHA-256、Codex/Cline 設定保全、
  VSIX 檢查改用 package.json 版本。

- Submodule、pyproject（`>=0.7.7`）、extension pin、測試與文件全面升到 0.7.7。
- 新增唯讀 `export_items`、`get_bibliography`（`export_tools.py`）。
- Zotero 10.0.5 重新稽核：10.0.5 的 Local API 修正（client 自訂 key）不影響 Keeper；
  write-token 重送、原生 `POST /items` 建立已評估並刻意暫緩（見稽核文件）。
- 移除殘留的 `get_session_pmids` 等舊工具名稱；`HARNESS_UPGRADES.md` 加入舊→新工具對照。
- 同步 Codex/Cline harness skills、research agent、Copilot 指令、README、CHANGELOG。

## 上一輪（0.9.1 / 2.3.1）修正

- Zotero 10.0.2 功能稽核與 7 個 schema／annotation／編輯工具；saved search
  巢狀條件、四種 resultLevel、分頁與 response-bound identity。
- Harness 預設不在啟動時更新；以內容指紋判定所有權，保留自訂／已刪除檔案與
  整個自訂 skill，防降版、備份並跳過來源工作區。
- 0.9.1 將 assets 與 ledger 納入可復原更新：原子置換、失敗回復；並行使用者
  編輯仍保留，中斷紀錄阻止後續更新，見 `docs/HARNESS_UPGRADES.md`。
- Ownership 逐頁串流、檢查 Server-ID／library cursor／總數／重複 key；失敗
  不回傳部分結果。排除附件、筆記與 annotation 的假陽性。
- 統計保留 5,000 raw items 上限並揭露範圍；未知數量回傳 null + warnings，
  不冒充零。孤兒清單與 inclusive summary 一致。
- `read_contracts.py` 集中跨請求 identity 驗證；VSIX 排除編譯後測試檔案。
- README、架構、tool reference、Codex/Cline/Copilot harness 與 GitHub Pages
  同步；PubMed 功能仍在獨立網站介紹。

## 主要檔案

- `mcp-server/src/zotero_mcp/infrastructure/mcp/unified_import_tools.py` / `unified_record_detail.py`
- `mcp-server/src/zotero_mcp/infrastructure/mcp/item_edit_tools.py`
- `mcp-server/src/zotero_mcp/infrastructure/mcp/local_api_tools.py`
- `mcp-server/src/zotero_mcp/infrastructure/mcp/read_contracts.py`
- `mcp-server/src/zotero_mcp/infrastructure/zotero_client/client_read.py`
- `vscode-extension/src/harnessAssets.ts`
- `vscode-extension/src/zoteroKeeperPackage.ts` / `pubmedSearchPackage.ts`
- `docs/ZOTERO_10_TOOL_AUDIT.md` / `docs/HARNESS_UPGRADES.md`
- `.github/workflows/publish-extension.yml` / `.github/workflows/pages.yml`

## 發布與安全邊界

先跑 Keeper lint/type/tests、extension tests、metadata guards、managed-venv
smoke 與 VSIX 內容檢查。明確 stage 本輪檔案，保留工作區原有未提交修改。
推送 main、確認同一 commit 的 CI 成功後，再推送 `v0.12.0-ext` tag，由 workflow 驗證 release archive、打包，
將同一 artifact 發布到 Marketplace 與 GitHub Release；確認 Pages 部署。
不可在 workflow 完成前宣稱正式發布成功；PyPI 是獨立發布管道。

每次 Zotero mutation 仍須完整 zero-I/O preview、使用者核准、response-bound
Server-ID 與正確 object/library version。上傳前 Always Allow；不自動重試
412，不轉送 port 23119，不讀取／記錄授權 key。此輪測試不修改使用者真實文獻庫。

## 更新時間

2026-11-25 UTC
