# Active Context

> 🎯 目前工作焦點與下一步行動

## 當前狀態: 完整驗證已綠，正在整理剩餘 release 修正並準備 push/tag

### 已確認 (2026-04-09)

1. ✅ 遠端主線已前進到 VS Code Extension `v0.5.19-ext`
   - 目前 `origin/main` 在 commit `2e7e4ec`
   - 下一個 extension release tag 必須大於 `v0.5.19-ext`

2. ✅ 本地仍有 4 個需要保留的提交
   - `chore(submodule): advance pubmed-search pointer`
   - `fix(mcp-server): harden collaboration-safe import workflow`
   - `docs(collaboration): sync workflow and guardrails`
   - `feat(vscode-extension): package official copilot assets`

3. ✅ 發版前驗證已完成
   - docs guard 通過
   - version sync 通過（`0.5.20`）
   - `mcp-server` 全量 pytest 通過（`413 passed, 1 warning`）
   - extension `npm test` 通過（47 passing，lint 僅 warnings）
   - extension `tests/test_mac_compatibility.py` 通過（49 tests）
   - extension `tests/test_python_env_edge_cases.py` 通過（20/20）
   - extension package 通過（`vscode-zotero-mcp-0.5.20.vsix`）

4. ✅ dirty submodule blocker 已解除
   - `external/pubmed-search-mcp/.github/agents/research.agent.md` 已提交到 submodule 上游 `origin/master`
   - upstream commit: `23fb483`

5. ⚠️ 下一版 release 仍需先處理版本與發布順序
   - 既有 extension tag 已到 `v0.5.19-ext`
   - keeper 版本、extension 依賴門檻與實際可安裝來源必須一致
   - 已補齊 Windows cross-platform test runner 與 pre-tag edge-case 驗證

### 目前正在做

1. 提交剩餘的 mcp-server 依賴/測試修正
2. 提交 extension 0.5.20 發布與測試鏈修正
3. push `main` 並建立 `v0.5.20-ext` tag

### 下一步

- 完成 commit 分段後再次確認工作樹乾淨
- push 主線變更
- 建立新的 release tag 觸發自動發布

---
*Updated: 2026-04-09*
*工作模式: Release Integration*
