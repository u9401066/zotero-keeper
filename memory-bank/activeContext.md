# Active Context

## 當前焦點
整理文件 PR，更新 README / 開發文件，讓安裝流程、tool surface 與文件入口對齊目前的 collaboration-safe 架構。

## 相關檔案
- `README.md` - 英文主 README，補文件導覽、工具清單與安裝說明
- `README.zh-TW.md` - 繁中 README，同步英文版的重要資訊
- `CONTRIBUTING.md` - 開發者 setup 與提交前檢查
- `mcp-server/README.md` - MCP server 專用工具文件
- `ARCHITECTURE.md` - 架構圖與模組/tool count
- `memory-bank/progress.md` - 任務進度追蹤

## 待解決問題
- [ ] 完成文件修改後跑一致性檢查
- [ ] 將先前 `report_progress` 誤提交刪除的 extension 資產一併恢復
- [ ] 建立文件 PR

## 上下文
- 根 README 先前仍有 `uv pip install` 舊指令與過時的未來規劃描述。
- 繁中 README 未列出 analytics / attachment tools，工具總數也過期。
- `CONTRIBUTING.md` 仍寫 Python 3.11 與舊的 `uv pip install -e` 流程。
- sandbox 目前沒有 `uv` 可執行檔，因此完整 `uv run` 驗證無法在本地重跑；本次以可用的文件 guard、extension asset sync 與差異檢查為主。

## 更新時間
2026-04-13 15:45
