# Progress (Updated: 2026-04-09)

## Done

- 已將 `external/pubmed-search-mcp/.github/agents/research.agent.md` 提交到 submodule 上游 `origin/master`（commit `23fb483`），解除 dirty submodule blocker
- 已在本地整理出 4 個待推送提交：
  - `chore(submodule): advance pubmed-search pointer`
  - `fix(mcp-server): harden collaboration-safe import workflow`
  - `docs(collaboration): sync workflow and guardrails`
  - `feat(vscode-extension): package official copilot assets`
- keeper collaboration-safe 匯入路徑補強完成：duplicate check、async fetch、schema 驗證、batch import、legacy bridge 共用 client / API key
- 跨 repo 契約測試與 docs guard 已補齊，文件已同步到 collaboration-safe 工作流
- extension 官方 repo assets 打包流程已完成，auto mode 會刷新受管 assets，VSIX 也已排除 `.pytest_cache`
- 發版前完整驗證已完成：
  - docs guard 通過
  - version sync 通過（`0.5.20`）
  - `mcp-server` 全量 pytest `413 passed, 1 warning`
  - extension `npm test` 通過（47 passing，lint 僅 warnings）
  - extension `npm run package` 通過（`vscode-zotero-mcp-0.5.20.vsix`）
  - extension `tests/test_mac_compatibility.py` 通過（49 tests）
  - extension `tests/test_python_env_edge_cases.py` 通過（20/20）
- 已建立備援分支 `backup/release-120ef8f`

## Doing

- 正在把未提交的 mcp-server 依賴/測試修正與 extension 0.5.20 發布修正拆成邏輯 commit
- 正在同步 Memory Bank 與目前 release 驗證狀態，準備 push `main` 並建立新 tag

## Next

- 提交剩餘的 mcp-server / extension 發布修正
- push `main`
- 建立並推送 `v0.5.20-ext` tag 觸發自動發布
