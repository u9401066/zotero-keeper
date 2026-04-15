# Active Context

## 當前焦點
完成 VS Code extension 的 keeper icon 與 VSX / Marketplace banner 重製，最終採用手作 SVG source + `rsvg-convert` 穩定輸出 PNG。

## 相關檔案
- `vscode-extension/resources/icon.png` - 正式 extension icon，從 `resources/branding/keeper-icon.svg` 渲染而來
- `vscode-extension/resources/branding/keeper-icon.svg` - keeper icon 向量 source
- `vscode-extension/resources/branding/vsx-banner.png` - VSX / Marketplace README banner
- `vscode-extension/resources/branding/vsx-banner.svg` - banner 向量 source
- `vscode-extension/README.md` - 在頂部掛載 banner 圖
- `vscode-extension/package.json` - 保留 icon 路徑並新增 `galleryBanner` 配色
- `memory-bank/progress.md` - 任務進度追蹤

## 待解決問題
- [x] 重製成可控制文字與構圖的最終 icon / banner
- [x] 將新 icon / banner 接到 extension manifest 與 README

## 上下文
- 直接用 AFM 產生的圖會出現錯字與 generic infographic 風格，不適合 extension 品牌資產。
- 最終 icon 改為深藍底、紅色書冊、青色放大鏡與節點弧線，明確表達 Zotero Keeper + PubMed Search + MCP workflow。
- 最終 banner 參考 Academic Figures MCP / MedPaper Assistant 的系列語言，採深藍圓角 hero card + 強對比標題 + 右側文獻卡片與檢索插圖。
- 本機可用 `rsvg-convert`，因此最終 PNG 是從手作 SVG source 直接渲染，不再依賴 AFM 的文字生成品質。

## 更新時間
2026-04-15
