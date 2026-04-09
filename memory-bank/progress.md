# Progress (Updated: 2026-04-09)

## Done

- 已將 `external/pubmed-search-mcp/.github/agents/research.agent.md` 提交到 submodule 上游 `origin/master`（commit `23fb483`），解除 dirty submodule blocker
- 已在本地整理出 4 個待整合提交：
  - `chore(submodule): advance pubmed-search pointer`
  - `fix(mcp-server): harden collaboration-safe import workflow`
  - `docs(collaboration): sync workflow and guardrails`
  - `feat(vscode-extension): package official copilot assets`
- keeper collaboration-safe 匯入路徑補強完成：duplicate check、async fetch、schema 驗證、batch import、legacy bridge 共用 client / API key
- 跨 repo 契約測試與 docs guard 已補齊，文件已同步到 collaboration-safe 工作流
- extension 官方 repo assets 打包流程已完成，auto mode 會刷新受管 assets，VSIX 也已排除 `.pytest_cache`
- 發版前驗證已完成：docs guard 通過、`mcp-server` 全量 pytest 369/369 通過、extension lint 成功、VSIX package 成功
- 已建立備援分支 `backup/release-120ef8f`

## Doing

- 正在把上述 4 個本地提交 rebase 到 `origin/main`
- 正在對齊 Memory Bank 與遠端主線目前的版本狀態（遠端 HEAD: `2e7e4ec` / `v0.5.19-ext`）

## Next

- 完成 rebase，確認所有本地提交都乾淨套用
- 重新檢查 keeper / extension 版本同步
- 決定新的 extension tag（必須大於 `v0.5.19-ext`）與對應 release 順序
- push 主線並推送新 tag 觸發自動發布
