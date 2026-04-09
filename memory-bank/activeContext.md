# Active Context

> 🎯 目前工作焦點與下一步行動

## 當前狀態: 將本地 release work 整合回 origin/main，完成後再重新發版

### 已確認 (2026-04-09)

1. ✅ 遠端主線已前進到 VS Code Extension `v0.5.19-ext`
   - 目前 `origin/main` 在 commit `2e7e4ec`
   - 不能直接把基於舊歷史的本地 release 分支推上去

2. ✅ 本地仍有 4 個需要保留的提交
   - `chore(submodule): advance pubmed-search pointer`
   - `fix(mcp-server): harden collaboration-safe import workflow`
   - `docs(collaboration): sync workflow and guardrails`
   - `feat(vscode-extension): package official copilot assets`

3. ✅ 發版前驗證已完成
   - docs guard 通過
   - `mcp-server` 全量 pytest 通過（369 passed）
   - extension lint 通過
   - extension package 通過

4. ✅ dirty submodule blocker 已解除
   - `external/pubmed-search-mcp/.github/agents/research.agent.md` 已提交到 submodule 上游 `origin/master`
   - upstream commit: `23fb483`

5. ⚠️ 下一版 release 仍需先處理版本與發布順序
   - 既有 extension tag 已到 `v0.5.19-ext`
   - 後續 extension tag 必須大於 `v0.5.19-ext`
   - keeper 版本、extension 依賴門檻與實際可安裝來源必須一致

### 目前正在做

1. 將本地 4 個提交 rebase 到 `origin/main`
2. 解決 Memory Bank 與版本號漂移
3. rebase 完成後再決定新的 keeper / extension release tag

### 下一步

- 完成 rebase
- 重新檢查版本同步與必要 smoke test
- push 主線變更
- 建立新的 release tag 觸發自動發布

---
*Updated: 2026-04-09*
*工作模式: Release Integration*
