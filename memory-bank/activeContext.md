# Active Context

## 當前焦點

準備 VS Code extension / VSIX **0.10.0**、Zotero Keeper **2.4.0**（尚未打 tag 發布）。
PubMed Search MCP 固定於正式 **0.7.7** release commit
`8247af2a5bc53e218c1f1e5b310c45535e11368c`，兩個 server 共用 MCP SDK v2。
Keeper 提供 50 個預設 tools、6 個 resources、4 個 URI templates；PubMed 41 tools
（介面自 0.7.3 起未變，0.7.4–0.7.7 為速率限制、統一輸入驗證、fulltext prefetch、測試整修）。

## 本輪（0.10.0 / 2.4.0）完成

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
推送 main 後使用 `v0.10.0-ext` tag，由 workflow 驗證 release archive、打包，
將同一 artifact 發布到 Marketplace 與 GitHub Release；確認 Pages 部署。
不可在 workflow 完成前宣稱正式發布成功；PyPI 是獨立發布管道。

每次 Zotero mutation 仍須完整 zero-I/O preview、使用者核准、response-bound
Server-ID 與正確 object/library version。上傳前 Always Allow；不自動重試
412，不轉送 port 23119，不讀取／記錄授權 key。此輪測試不修改使用者真實文獻庫。

## 更新時間

2026-10-02 UTC
