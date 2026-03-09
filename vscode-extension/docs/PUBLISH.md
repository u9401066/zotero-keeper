# VS Code Extension 發布指南

目前此專案的 VS Code 擴充功能**只發布到官方 VS Code Marketplace**，並由 GitHub Actions 自動執行封裝與發布。

## 發布流程

### 1. 同步版本號

發布前請同步更新下列檔案：

- `vscode-extension/package.json`
- `vscode-extension/src/statusBar.ts`
- `vscode-extension/CHANGELOG.md`

### 2. 本地驗證

```bash
cd vscode-extension
npm ci
npm run lint
npm run compile
```

如需先測試封裝結果，可額外執行：

```bash
npx @vscode/vsce package
```

### 3. 建立 release commit 與 tag

```bash
git add -A
git commit -m "release: vX.Y.Z - short summary"
git tag -a vX.Y.Z-ext -m "Release vX.Y.Z"
git push
git push origin vX.Y.Z-ext
```

`vX.Y.Z-ext` 是目前 extension CI workflow 的唯一觸發格式。

## CI 會做什麼

`.github/workflows/publish-extension.yml` 會自動執行：

1. 安裝相依套件
2. `npm run lint`
3. `npm run compile`
4. `vsce package`
5. 發布到 VS Code Marketplace
6. 建立 GitHub Release

## 驗證發布成功

### GitHub Actions

```bash
curl -s "https://api.github.com/repos/u9401066/zotero-keeper/actions/runs?per_page=10" | \
   python3 -c "import sys,json; d=json.load(sys.stdin); print('\n'.join([f\"{r['name']:30} | {r['head_branch']:15} | {r['conclusion']}\" for r in d['workflow_runs'][:8]]))"
```

看到 `Publish VS Code Extension | vX.Y.Z-ext | success` 即表示 workflow 成功。

### VS Code Marketplace

- URL: `https://marketplace.visualstudio.com/items?itemName=u9401066.vscode-zotero-mcp`

```bash
curl -s "https://marketplace.visualstudio.com/items?itemName=u9401066.vscode-zotero-mcp" | \
   grep -o '"version":"[^"]*"' | head -1
```

## 必要 secrets

- `VSCE_PAT`: VS Code Marketplace Personal Access Token

## 常見問題

### `version already exists`

Marketplace 已存在相同版本號，請先升版再重新發布。

### CI 沒有觸發

請確認 tag 使用 `vX.Y.Z-ext` 格式。

### 發布成功但 Marketplace 尚未更新

Marketplace 頁面通常會有幾分鐘延遲，可稍後重新整理再確認。
