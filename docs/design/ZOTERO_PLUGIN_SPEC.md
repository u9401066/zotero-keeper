# Zotero Keeper Plugin — 完整規劃規格書

> **版本**: v0.1.0 (Draft)
> **日期**: 2025-07-18
> **作者**: u9401066
> **狀態**: 📋 規劃中

---

## 目錄

1. [執行摘要](#1-執行摘要)
2. [動機與問題分析](#2-動機與問題分析)
3. [技術架構](#3-技術架構)
4. [功能規格](#4-功能規格)
5. [Plugin API 可用能力清單](#5-plugin-api-可用能力清單)
6. [專案結構](#6-專案結構)
7. [開發工具鏈](#7-開發工具鏈)
8. [實作分期計畫](#8-實作分期計畫)
9. [安全性考量](#9-安全性考量)
10. [測試策略](#10-測試策略)
11. [發布與分發](#11-發布與分發)
12. [風險與緩解](#12-風險與緩解)
13. [附錄](#13-附錄)

---

## 1. 執行摘要

### 1.1 一句話描述

**Zotero Keeper Plugin** 是一個 Zotero 7/8 原生外掛，透過暴露 Zotero 完整內部 JavaScript API（包括檔案系統、全文索引、PDF 內容、附件管理等），為外部 AI Agent（如 MCP Server）提供一個高權限的 HTTP Bridge，徹底解決 Local API 的功能限制。

### 1.2 核心價值

| 現有限制 (Local API) | Plugin 解決方案 |
|---|---|
| ❌ 無法讀取 PDF 內容 | ✅ `attachment.attachmentText` 直接取得全文 |
| ❌ 無法更新現有項目 (501) | ✅ `item.setField()` + `item.saveTx()` |
| ❌ 無法刪除項目 | ✅ `Zotero.Items.trashTx()` / `eraseTx()` |
| ❌ 無法上傳附件 | ✅ `Zotero.Attachments.importFromFile()` |
| ❌ 無法存取檔案系統 | ✅ `Zotero.File` + `IOUtils` + `PathUtils` |
| ❌ 無法讀取 Annotations | ✅ `item.getAnnotations()` |
| ❌ 無法操作 Saved Searches | ✅ `new Zotero.Search()` 完整 CRUD |
| ❌ 無法批量修改 | ✅ `Zotero.DB.executeTransaction()` |

### 1.3 架構定位

```
┌─────────────────────────────────────────────────────────┐
│                    AI Agent Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ VS Code Ext  │  │ Claude/GPT   │  │ Other Agents │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                 │                 │            │
│  ┌──────┴─────────────────┴─────────────────┴──────┐    │
│  │            MCP Server (zotero-keeper)            │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐ │    │
│  │  │ Read Tools │  │Write Tools │  │Batch Tools │ │    │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘ │    │
│  └────────┼───────────────┼───────────────┼────────┘    │
│           │               │               │             │
│  ┌────────┴───────────────┴───────────────┴────────┐    │
│  │            HTTP Bridge Client (DAL)              │    │
│  │     GET/POST http://localhost:24119/keeper/*     │    │
│  └────────────────────┬────────────────────────────┘    │
└───────────────────────┼─────────────────────────────────┘
                        │ HTTP (localhost only)
┌───────────────────────┼─────────────────────────────────┐
│  Zotero Desktop App   │                                 │
│  ┌────────────────────┴────────────────────────────┐    │
│  │     🆕 Zotero Keeper Plugin (本規格書)           │    │
│  │  ┌──────────────────────────────────────────┐   │    │
│  │  │   HTTP Server (port 24119)               │   │    │
│  │  │   ┌──────┐ ┌──────┐ ┌──────┐ ┌────────┐ │   │    │
│  │  │   │Items │ │Files │ │Full  │ │Annota- │ │   │    │
│  │  │   │CRUD  │ │Mgmt  │ │Text  │ │tions   │ │   │    │
│  │  │   └──┬───┘ └──┬───┘ └──┬───┘ └──┬─────┘ │   │    │
│  │  └──────┼────────┼────────┼────────┼────────┘   │    │
│  │         │        │        │        │            │    │
│  │  ┌──────┴────────┴────────┴────────┴────────┐   │    │
│  │  │     Zotero Internal JavaScript API       │   │    │
│  │  │  Zotero.Items | Zotero.File | Zotero.DB  │   │    │
│  │  └──────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Existing: Local API (port 23119) — Read-only   │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## 2. 動機與問題分析

### 2.1 現有 Local API 限制（實測結果）

根據 `docs/ZOTERO_LOCAL_API.md` 的實測：

| API 操作 | 端點 | 狀態 | 回應 |
|---|---|---|---|
| 讀取項目 | `GET /api/users/0/items` | ✅ 200 | 正常 |
| 建立項目 | `POST /connector/saveItems` | ✅ 200 | 正常（Connector API） |
| 更新項目 | `PATCH /api/users/0/items/:key` | ❌ 501 | Not Implemented |
| 刪除項目 | `DELETE /api/users/0/items/:key` | ❌ 不支援 | — |
| 讀取附件內容 | — | ❌ 不存在 | 沒有此端點 |
| 上傳附件 | — | ❌ 不存在 | 沒有此端點 |
| 全文搜尋 | — | ❌ 不存在 | 沒有此端點 |
| Annotations | — | ❌ 不存在 | 沒有此端點 |

### 2.2 為什麼選擇 Plugin 而非 Web API

| 面向 | Plugin | Web API |
|---|---|---|
| 延遲 | < 1ms（同進程內） | 100-500ms（網路往返） |
| 認證 | 不需要 API Key | 需要 API Key + OAuth |
| 檔案存取 | 直接讀寫本地檔案 | 無法存取本地附件 |
| 全文內容 | `attachment.attachmentText` | 僅 fulltext 索引 API |
| 離線能力 | 完全離線可用 | ❌ 需要網路 |
| 資料即時性 | 即時（同進程） | 需等待 sync |
| PDF Annotations | 直接讀取 | 部分支援 |
| 安全性 | 限制 localhost | 需公開 key |

### 2.3 對 zotero-keeper 生態系的補完

```
zotero-keeper 生態系完整圖:

┌─ pubmed-search-mcp ──── PubMed/Europe PMC/CORE 文獻搜尋
│
├─ zotero-keeper MCP ──── Zotero 讀寫（目前受 Local API 限制）
│   │
│   └─ 🆕 Zotero Keeper Plugin ── 解鎖完整 Zotero 能力
│
└─ VS Code Extension ──── 一鍵安裝、環境管理、狀態欄
```

---

## 3. 技術架構

### 3.1 Zotero 7/8 Plugin 基礎架構

Zotero 7+ 使用 **bootstrapped plugin** 架構（非 WebExtension、非 XUL Overlay）：

```
Plugin 組成要素:
├── manifest.json          ← WebExtension-style 清單（metadata）
├── bootstrap.js           ← 生命週期鉤子（startup/shutdown/install/uninstall）
├── prefs.js               ← 預設偏好設定
├── locale/                ← Fluent 多語言檔案 (.ftl)
│   ├── en-US/
│   └── zh-TW/
└── content/               ← UI、scripts、styles
```

**生命週期鉤子**：
```javascript
// bootstrap.js
function startup({ id, version, rootURI }, reason) { /* 初始化 */ }
function shutdown({ id, version, rootURI }, reason) { /* 清理 */ }
function install({ id, version, rootURI }, reason) { /* 首次安裝 */ }
function uninstall({ id, version, rootURI }, reason) { /* 解除安裝 */ }

// Window hooks (Zotero 7+)
function onMainWindowLoad({ window }) { /* 主視窗載入 */ }
function onMainWindowUnload({ window }) { /* 主視窗卸載 */ }
```

### 3.2 核心設計：HTTP Bridge Server

Plugin 的核心功能是在 Zotero 進程內啟動一個輕量 HTTP 伺服器，為外部工具提供 REST API。

```javascript
// 設計理念：
// 1. Zotero 已有 Local API server (port 23119)，我們參考其架構
// 2. 使用獨立 port (24119) 避免衝突
// 3. 僅綁定 localhost，不接受外部連線
// 4. JSON-RPC 或 REST 風格

// Zotero 內建 HTTP server 使用 nsIServerSocket
// 我們可以同樣使用 Zotero.Server 機制或直接使用 nsIServerSocket
```

**Port 設計**：
- Zotero Local API: `23119`
- Zotero Keeper Plugin: `24119`（可透過 prefs 設定）

### 3.3 技術選型

| 選項 | 方案 | 理由 |
|---|---|---|
| 語言 | TypeScript → ESBuild 編譯 | 類型安全、與 template 一致 |
| 模板 | windingwind/zotero-plugin-template | 成熟（784 ⭐、169 forks），包含開發工具鏈 |
| HTTP Server | Zotero 內建 `nsIServerSocket` | 零依賴，與 Zotero 整合 |
| 類型定義 | zotero-types | 完整的 Zotero API TypeScript 類型 |
| 建構工具 | zotero-plugin-scaffold | 自動化 build/release |
| UI 工具 | zotero-plugin-toolkit | 簡化 UI 操作 |

### 3.4 API 設計

所有 API endpoint 都位於 `http://localhost:24119/keeper/v1/` 下：

```
GET    /keeper/v1/status                    # 健康檢查
GET    /keeper/v1/items                     # 列出項目
GET    /keeper/v1/items/:key                # 取得項目詳情
PATCH  /keeper/v1/items/:key                # 更新項目
DELETE /keeper/v1/items/:key                # 刪除項目（移至垃圾桶）
POST   /keeper/v1/items                     # 建立項目
GET    /keeper/v1/items/:key/fulltext       # 取得全文內容
GET    /keeper/v1/items/:key/annotations    # 取得 Annotations
GET    /keeper/v1/items/:key/attachments    # 列出附件
GET    /keeper/v1/items/:key/file           # 下載附件檔案
POST   /keeper/v1/items/:key/attachments    # 上傳附件
GET    /keeper/v1/items/:key/notes          # 取得筆記
POST   /keeper/v1/items/:key/notes          # 建立筆記
GET    /keeper/v1/collections               # 列出 Collections
POST   /keeper/v1/collections               # 建立 Collection
PATCH  /keeper/v1/collections/:key          # 更新 Collection
POST   /keeper/v1/items/:key/collections    # 加入 Collection
GET    /keeper/v1/searches                  # 列出 Saved Searches
POST   /keeper/v1/searches                  # 建立 Saved Search
POST   /keeper/v1/search                    # 即時搜尋
POST   /keeper/v1/fulltext-search           # 全文搜尋
POST   /keeper/v1/batch                     # 批量操作
GET    /keeper/v1/tags                      # 列出標籤
POST   /keeper/v1/export                    # 匯出（BibTeX/RIS/CSL JSON）
```

**API 回應格式**：
```json
{
  "ok": true,
  "data": { ... },
  "meta": {
    "total": 42,
    "took_ms": 12
  }
}
```

**錯誤格式**：
```json
{
  "ok": false,
  "error": {
    "code": "ITEM_NOT_FOUND",
    "message": "Item with key ABC12345 not found"
  }
}
```

---

## 4. 功能規格

### 4.1 Phase 1：核心讀寫（MVP）

#### 4.1.1 項目 CRUD

```typescript
// GET /keeper/v1/items/:key
// 回傳完整項目資訊，包含所有欄位
interface ItemResponse {
  key: string;
  version: number;
  itemType: string;
  title: string;
  creators: Creator[];
  date: string;
  abstractNote: string;
  DOI: string;
  PMID: string;
  // ... 所有 Zotero 欄位
  tags: Tag[];
  collections: string[];
  relations: Record<string, string[]>;
  dateAdded: string;
  dateModified: string;
}

// PATCH /keeper/v1/items/:key
// 更新項目欄位（只需傳要更新的欄位）
interface ItemUpdateRequest {
  title?: string;
  date?: string;
  abstractNote?: string;
  tags?: Tag[];
  // ... 任何可更新的欄位
}

// DELETE /keeper/v1/items/:key?permanent=false
// 預設移至垃圾桶（permanent=true 永久刪除）
```

**實作方式**：
```javascript
// 讀取
const item = Zotero.Items.get(itemID);
// 或
const item = Zotero.Items.getByLibraryAndKey(libraryID, key);

// 更新
item.setField('title', 'New Title');
item.setField('date', '2024-01-15');
await item.saveTx();

// 刪除
await Zotero.Items.trashTx(itemIDs); // 移至垃圾桶
// 或
await Zotero.Items.eraseTx(itemIDs); // 永久刪除
```

#### 4.1.2 附件與檔案存取

```typescript
// GET /keeper/v1/items/:key/attachments
// 列出項目的所有附件
interface AttachmentInfo {
  key: string;
  title: string;
  contentType: string;    // e.g., "application/pdf"
  filename: string;
  path: string;           // 本地檔案路徑
  dateAdded: string;
  fileSize: number;
  md5: string;
}

// GET /keeper/v1/items/:key/file
// 下載附件檔案（二進位）
// Content-Type 根據附件類型自動設定

// POST /keeper/v1/items/:parentKey/attachments
// 上傳附件（multipart/form-data）
```

**實作方式**：
```javascript
// 列出附件
const attachmentIDs = item.getAttachments();
for (const id of attachmentIDs) {
  const attachment = Zotero.Items.get(id);
  const path = attachment.getFilePath();
  const contentType = attachment.attachmentContentType;
  const filename = attachment.attachmentFilename;
}

// 讀取檔案
const path = attachment.getFilePath();
const data = await Zotero.File.getBinaryContentsAsync(path);

// 匯入附件
const attachmentItem = await Zotero.Attachments.importFromFile({
  file: filePath,
  parentItemID: parentItem.id,
  title: 'My PDF',
  contentType: 'application/pdf'
});
```

#### 4.1.3 全文內容存取

```typescript
// GET /keeper/v1/items/:key/fulltext
// 取得附件的全文內容（PDF 文字、HTML 內容等）
interface FulltextResponse {
  key: string;
  contentType: string;
  content: string;        // 全文文字內容
  indexedChars: number;
  totalChars: number;
  indexedPages: number;
  totalPages: number;
}
```

**實作方式**：
```javascript
// 取得全文
const fulltext = await attachment.attachmentText;

// 或使用 Zotero.Fulltext
const content = await Zotero.Fulltext.getItemContent(attachmentID);
// 回傳 { content, indexedChars, totalChars, indexedPages, totalPages }
```

#### 4.1.4 健康檢查

```typescript
// GET /keeper/v1/status
interface StatusResponse {
  plugin: string;           // "zotero-keeper-plugin"
  version: string;          // "0.1.0"
  zoteroVersion: string;    // "7.0.15"
  port: number;             // 24119
  libraryID: number;
  itemCount: number;
  uptime: number;           // seconds
}
```

### 4.2 Phase 2：進階功能

#### 4.2.1 Annotations（PDF 標註）

```typescript
// GET /keeper/v1/items/:key/annotations
interface Annotation {
  key: string;
  type: 'highlight' | 'note' | 'image' | 'ink' | 'underline';
  text: string;           // 標註文字
  comment: string;        // 使用者註解
  color: string;          // 顏色代碼
  pageLabel: string;      // 頁碼
  position: object;       // PDF 位置資訊
  tags: Tag[];
  dateAdded: string;
  dateModified: string;
}
```

**實作方式**：
```javascript
const annotations = item.getAnnotations();
for (const ann of annotations) {
  const annItem = Zotero.Items.get(ann);
  const type = annItem.annotationType;
  const text = annItem.annotationText;
  const comment = annItem.annotationComment;
  const color = annItem.annotationColor;
  const pageLabel = annItem.annotationPageLabel;
  const position = JSON.parse(annItem.annotationPosition);
}
```

#### 4.2.2 筆記操作

```typescript
// GET /keeper/v1/items/:key/notes
// POST /keeper/v1/items/:key/notes
// PATCH /keeper/v1/notes/:key
interface Note {
  key: string;
  parentKey: string;
  content: string;        // HTML 格式
  tags: Tag[];
}
```

**實作方式**：
```javascript
// 讀取筆記
const noteIDs = item.getNotes();
for (const id of noteIDs) {
  const note = Zotero.Items.get(id);
  const htmlContent = note.getNote();
}

// 建立筆記
const note = new Zotero.Item('note');
note.parentID = parentItem.id;
note.setNote('<p>My note content</p>');
await note.saveTx();
```

#### 4.2.3 全文搜尋

```typescript
// POST /keeper/v1/fulltext-search
interface FulltextSearchRequest {
  query: string;           // 搜尋詞
  libraryID?: number;
}

interface FulltextSearchResult {
  itemKey: string;
  parentKey: string;
  title: string;
  matches: {
    text: string;          // 匹配的文字片段
    pageLabel?: string;    // PDF 頁碼
  }[];
}
```

**實作方式**：
```javascript
const s = new Zotero.Search();
s.libraryID = Zotero.Libraries.userLibraryID;
s.addCondition('fulltextContent', 'contains', query);
const itemIDs = await s.search();
```

#### 4.2.4 批量操作

```typescript
// POST /keeper/v1/batch
interface BatchRequest {
  operations: BatchOperation[];
}

interface BatchOperation {
  method: 'GET' | 'PATCH' | 'DELETE' | 'POST';
  path: string;
  body?: Record<string, unknown>;
}

interface BatchResponse {
  results: {
    status: number;
    body: Record<string, unknown>;
  }[];
}
```

**實作方式**：
```javascript
// 批量操作使用事務包裹
await Zotero.DB.executeTransaction(async () => {
  for (const op of operations) {
    // 執行各項操作
  }
});
```

#### 4.2.5 匯出格式

```typescript
// POST /keeper/v1/export
interface ExportRequest {
  keys: string[];
  format: 'bibtex' | 'ris' | 'csljson' | 'refer' | 'csv';
}
```

**實作方式**：
```javascript
// 使用 Zotero.QuickCopy
const items = keys.map(k => Zotero.Items.getByLibraryAndKey(libraryID, k));
const format = Zotero.Prefs.get("export.quickCopy.setting");
const result = Zotero.QuickCopy.getContentFromItems(items, format);
```

### 4.3 Phase 3：UI 整合

#### 4.3.1 偏好設定面板

```
┌─────────────────────────────────────┐
│  Zotero Keeper Plugin Settings      │
├─────────────────────────────────────┤
│  HTTP Bridge                        │
│  ┌──────────────────────────────┐   │
│  │ Port: [24119]                │   │
│  │ ☑ Auto-start on launch      │   │
│  │ ☐ Require auth token        │   │
│  └──────────────────────────────┘   │
│                                     │
│  Security                           │
│  ┌──────────────────────────────┐   │
│  │ Bind: localhost only         │   │
│  │ Auth Token: [••••••••]       │   │
│  │ CORS Origins: [localhost]    │   │
│  └──────────────────────────────┘   │
│                                     │
│  Logging                            │
│  ┌──────────────────────────────┐   │
│  │ Level: [Info ▾]              │   │
│  │ ☐ Log API requests          │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

#### 4.3.2 狀態指示（Item Pane Section）

在 Item Pane 中新增一個 "Keeper" section，顯示：
- MCP 連線狀態
- 最近的 AI 操作紀錄
- 全文索引狀態

#### 4.3.3 右鍵選單

- "Copy Item Key for MCP" — 複製 item key
- "Re-index Full Text" — 重新索引全文
- "Export to MCP Format" — 匯出為 MCP 格式

### 4.4 Phase 4：進階整合

#### 4.4.1 Notification Bridge（即時事件推送）

利用 Zotero 的 Notifier 系統，將事件即時推送給 MCP Server：

```javascript
// 註冊 Observer
const notifierID = Zotero.Notifier.registerObserver({
  notify: (event, type, ids, extraData) => {
    // event: 'add', 'modify', 'delete', 'remove'
    // type: 'item', 'collection', 'tag', 'collection-item'
    // 推送到 SSE 或 WebSocket
    broadcastEvent({ event, type, ids });
  }
}, ['item', 'collection', 'tag', 'collection-item']);
```

```typescript
// GET /keeper/v1/events (SSE)
// 支援 Server-Sent Events，讓 MCP Server 即時接收變更通知
```

#### 4.4.2 Related Items Graph

```typescript
// GET /keeper/v1/items/:key/related
// 取得相關項目圖（基於 Zotero 的 Related 功能）

// POST /keeper/v1/items/:key/related
// 建立兩個項目的關聯
```

---

## 5. Plugin API 可用能力清單

### 5.1 Zotero 官方 Plugin API（穩定）

| API | 功能 | 版本要求 |
|---|---|---|
| `Zotero.ItemTreeManager.registerColumn()` | 自訂欄位 | Zotero 7+ |
| `Zotero.ItemPaneManager.registerSection()` | 項目面板區塊 | Zotero 7+ |
| `Zotero.ItemPaneManager.registerInfoRow()` | 資訊列 | Zotero 7+ |
| `Zotero.PreferencePanes.register()` | 偏好設定面板 | Zotero 7+ |
| `Zotero.Reader.registerEventListener()` | PDF 閱讀器事件 | Zotero 7+ |
| `Zotero.MenuManager.registerMenu()` | 選單項目 | Zotero 8+ |
| `Zotero.Notifier.registerObserver()` | 資料變更通知 | Zotero 5+ |

### 5.2 Zotero 內部 API（非公開但穩定）

| API | 功能 |
|---|---|
| `Zotero.Items` | 項目 CRUD |
| `Zotero.Collections` | 收藏夾 CRUD |
| `Zotero.Tags` | 標籤操作 |
| `Zotero.Search` | 搜尋功能 |
| `Zotero.Attachments` | 附件管理 |
| `Zotero.File` | 檔案 I/O |
| `Zotero.Fulltext` | 全文索引 |
| `Zotero.DB` | 資料庫事務 |
| `Zotero.QuickCopy` | 匯出格式 |
| `Zotero.Styles` | 引用格式 |
| `Zotero.Libraries` | 圖書館管理 |
| `Zotero.Prefs` | 偏好設定 |

### 5.3 Zotero 內部 XPCOM API

| API | 功能 |
|---|---|
| `IOUtils` | 非同步檔案 I/O |
| `PathUtils` | 路徑操作 |
| `Services.io` | URI 處理 |
| `ChromeUtils.importESModule()` | ESM 模組匯入 |

---

## 6. 專案結構

### 6.1 目錄規劃

```
zotero-plugin/                          # 新的子專案目錄
├── addon/                              # 靜態資源（Zotero plugin scaffold 格式）
│   ├── manifest.json                   # Plugin 清單
│   ├── bootstrap.js                    # 生命週期鉤子（由 scaffold 生成）
│   ├── prefs.js                        # 預設偏好設定
│   ├── content/
│   │   ├── icons/
│   │   │   ├── icon.svg
│   │   │   ├── icon@16.png
│   │   │   └── icon@48.png
│   │   ├── preferences.xhtml          # 偏好設定面板 UI
│   │   └── zoteroPane.css             # 主視窗樣式
│   └── locale/
│       ├── en-US/
│       │   ├── addon.ftl              # 通用字串
│       │   ├── preferences.ftl        # 偏好設定字串
│       │   └── mainWindow.ftl         # 主視窗字串
│       └── zh-TW/
│           ├── addon.ftl
│           ├── preferences.ftl
│           └── mainWindow.ftl
├── src/                               # TypeScript 原始碼
│   ├── index.ts                       # 主入口
│   ├── addon.ts                       # Plugin 基礎類別
│   ├── hooks.ts                       # 生命週期鉤子 dispatcher
│   ├── modules/
│   │   ├── bridge/                    # HTTP Bridge 模組
│   │   │   ├── server.ts             # HTTP Server 實作
│   │   │   ├── router.ts             # 路由解析
│   │   │   ├── middleware.ts          # 認證、CORS、日誌
│   │   │   └── handlers/             # 各 endpoint handler
│   │   │       ├── items.ts          # /items/*
│   │   │       ├── collections.ts    # /collections/*
│   │   │       ├── attachments.ts    # /items/:key/attachments
│   │   │       ├── fulltext.ts       # /items/:key/fulltext
│   │   │       ├── annotations.ts    # /items/:key/annotations
│   │   │       ├── notes.ts          # /items/:key/notes
│   │   │       ├── search.ts         # /search, /fulltext-search
│   │   │       ├── export.ts         # /export
│   │   │       ├── batch.ts          # /batch
│   │   │       └── status.ts         # /status
│   │   ├── ui/                        # UI 模組
│   │   │   ├── preferenceScript.ts   # 偏好設定邏輯
│   │   │   ├── itemPane.ts           # Item Pane Section
│   │   │   └── contextMenu.ts        # 右鍵選單
│   │   └── notifier/                  # Zotero 事件監聽
│   │       └── observer.ts           # Notifier Observer
│   └── utils/
│       ├── locale.ts                  # 多語言工具
│       ├── prefs.ts                   # 偏好設定工具
│       ├── logger.ts                  # 日誌工具
│       └── serializer.ts             # Zotero Item → JSON 序列化
├── typings/
│   └── global.d.ts                    # 全域類型定義
├── test/
│   ├── bridge/
│   │   ├── server.test.ts
│   │   ├── items.test.ts
│   │   └── fulltext.test.ts
│   └── utils/
│       └── serializer.test.ts
├── .env.example
├── package.json
├── tsconfig.json
├── eslint.config.mjs
└── zotero-plugin.config.ts            # Scaffold 設定
```

### 6.2 manifest.json

```json
{
  "manifest_version": 2,
  "name": "Zotero Keeper",
  "version": "0.1.0",
  "description": "HTTP Bridge for AI-powered Zotero library management. Exposes full Zotero API to external tools like MCP servers.",
  "author": "u9401066",
  "homepage_url": "https://github.com/u9401066/zotero-keeper",
  "icons": {
    "48": "content/icons/icon@48.png",
    "96": "content/icons/icon@96.png"
  },
  "applications": {
    "zotero": {
      "id": "zotero-keeper@u9401066",
      "update_url": "https://github.com/u9401066/zotero-keeper/releases/download/release/update.json",
      "strict_min_version": "6.999",
      "strict_max_version": "8.0.*"
    }
  }
}
```

### 6.3 prefs.js

```javascript
pref("extensions.zotero.keeper.bridge.port", 24119);
pref("extensions.zotero.keeper.bridge.autoStart", true);
pref("extensions.zotero.keeper.bridge.requireAuth", false);
pref("extensions.zotero.keeper.bridge.authToken", "");
pref("extensions.zotero.keeper.logging.level", "info");
pref("extensions.zotero.keeper.logging.logRequests", false);
```

---

## 7. 開發工具鏈

### 7.1 基於 zotero-plugin-template

| 工具 | 版本 | 用途 |
|---|---|---|
| Node.js | LTS (22.x) | Runtime |
| TypeScript | 5.x | 語言 |
| ESBuild | 0.25.x | 建構（由 scaffold 管理） |
| zotero-plugin-scaffold | latest | 建構/打包/發布 |
| zotero-plugin-toolkit | latest | UI 輔助工具 |
| zotero-types | latest | TypeScript 類型定義 |
| ESLint | 9.x | Linting |
| Prettier | 3.x | 格式化 |

### 7.2 開發流程

```bash
# 1. 建立專案（從 template）
npx degit windingwind/zotero-plugin-template zotero-plugin
cd zotero-plugin

# 2. 安裝依賴
npm install

# 3. 設定環境變數
cp .env.example .env
# 編輯 .env 設定 Zotero Beta 路徑

# 4. 開發（Hot Reload）
npm start
# → 自動編譯、自動載入到 Zotero、檔案變更自動重載

# 5. 建構
npm run build
# → 輸出 .xpi 到 .scaffold/build/

# 6. 發布
npx bumpp
# → 自動版本號 bump、git tag、push → GitHub Actions 自動發布
```

### 7.3 與主專案的整合

```
zotero-keeper/                    # 主 repo
├── external/
│   └── pubmed-search-mcp/       # submodule
├── mcp-server/                  # MCP Server
├── vscode-extension/            # VS Code Extension
├── zotero-plugin/               # 🆕 Zotero Plugin（新目錄）
└── ...
```

---

## 8. 實作分期計畫

### Phase 1：HTTP Bridge MVP

**目標**：建立基本的 HTTP Bridge，實現 Local API 無法做到的核心操作。

| 功能 | 優先級 | 估計複雜度 |
|---|---|---|
| HTTP Server 啟動/關閉 | P0 | 中 |
| `GET /status` — 健康檢查 | P0 | 低 |
| `GET /items/:key` — 讀取項目 | P0 | 低 |
| `PATCH /items/:key` — 更新項目 | P0 | 中 |
| `DELETE /items/:key` — 刪除項目 | P0 | 低 |
| `GET /items/:key/fulltext` — 全文 | P0 | 中 |
| `GET /items/:key/file` — 檔案下載 | P0 | 中 |
| `POST /items/:key/attachments` — 附件上傳 | P1 | 高 |
| 偏好設定面板（Port/Auth） | P1 | 中 |
| 基本認證（Bearer Token） | P1 | 低 |
| 基本錯誤處理 | P0 | 低 |

**交付物**：
- 可安裝的 .xpi 檔案
- MCP Server 可連線並呼叫 Bridge API
- 基本偏好設定面板

### Phase 2：進階功能

| 功能 | 優先級 | 估計複雜度 |
|---|---|---|
| `GET /items/:key/annotations` | P0 | 中 |
| `GET /items/:key/notes` + CRUD | P0 | 中 |
| `POST /fulltext-search` | P0 | 中 |
| `POST /search` — 進階搜尋 | P1 | 中 |
| `POST /batch` — 批量操作 | P1 | 高 |
| `POST /export` — 匯出 | P2 | 中 |
| Collections 完整 CRUD | P1 | 中 |
| Tags 操作 | P2 | 低 |

### Phase 3：UI 整合

| 功能 | 優先級 | 估計複雜度 |
|---|---|---|
| Item Pane Section | P2 | 中 |
| 右鍵選單 | P2 | 低 |
| Toolbar Button | P2 | 低 |
| 狀態欄指示 | P2 | 低 |

### Phase 4：事件系統

| 功能 | 優先級 | 估計複雜度 |
|---|---|---|
| Notifier → SSE Bridge | P2 | 高 |
| Related Items API | P3 | 中 |
| Custom Column（AI 指標） | P3 | 中 |

### Phase 5：MCP Server 整合

| 功能 | 優先級 | 估計複雜度 |
|---|---|---|
| 新增 Bridge Client 到 MCP DAL | P0 | 中 |
| 優先使用 Bridge、fallback 到 Local API | P0 | 中 |
| 新增基於 Bridge 的 MCP 工具 | P1 | 中 |
| VS Code Extension 自動檢測 Plugin | P2 | 低 |

---

## 9. 安全性考量

### 9.1 威脅模型

| 威脅 | 風險 | 緩解措施 |
|---|---|---|
| 未授權存取 HTTP Bridge | 高 | 僅綁定 `127.0.0.1`，不接受外部連線 |
| 惡意程式存取 Bridge | 中 | 可選的 Bearer Token 認證 |
| 路徑遍歷（檔案 API） | 高 | 限制檔案存取範圍在 Zotero storage 內 |
| 注入攻擊（搜尋 API） | 中 | 參數驗證、使用 Zotero 安全 API |
| 資料洩漏（錯誤訊息） | 低 | 不在錯誤訊息中暴露內部路徑 |
| 資源耗盡（批量 API） | 中 | 限制批量操作數量（上限 100） |

### 9.2 安全實作

```typescript
// 1. 僅 localhost
const serverSocket = Cc["@mozilla.org/network/server-socket;1"]
  .createInstance(Ci.nsIServerSocket);
serverSocket.init(port, true, -1); // loopbackOnly = true

// 2. Bearer Token 認證
function authenticate(request: nsIHttpRequest): boolean {
  if (!Zotero.Prefs.get('extensions.zotero.keeper.bridge.requireAuth')) {
    return true;
  }
  const token = Zotero.Prefs.get('extensions.zotero.keeper.bridge.authToken');
  const authHeader = request.getHeader('Authorization');
  return authHeader === `Bearer ${token}`;
}

// 3. 路徑驗證
function validateFilePath(path: string): boolean {
  const storageDir = Zotero.DataDirectory.dir;
  const resolved = PathUtils.normalize(path);
  return resolved.startsWith(storageDir);
}

// 4. 請求大小限制
const MAX_BODY_SIZE = 50 * 1024 * 1024; // 50 MB
const MAX_BATCH_SIZE = 100;
```

### 9.3 CORS 設定

```typescript
// 預設只允許 localhost
const ALLOWED_ORIGINS = [
  'http://localhost',
  'http://127.0.0.1',
  'vscode-webview://',
];

function setCORSHeaders(response: nsIHttpResponse, origin: string) {
  if (ALLOWED_ORIGINS.some(o => origin.startsWith(o))) {
    response.setHeader('Access-Control-Allow-Origin', origin, false);
    response.setHeader('Access-Control-Allow-Methods', 'GET, POST, PATCH, DELETE, OPTIONS', false);
    response.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization', false);
  }
}
```

---

## 10. 測試策略

### 10.1 測試層級

| 層級 | 工具 | 涵蓋範圍 |
|---|---|---|
| 單元測試 | vitest / jest | Serializer, Router, Middleware |
| 整合測試 | Zotero test runner | HTTP Bridge ↔ Zotero API |
| E2E 測試 | curl / httpie | 完整 API 流程 |
| Manual 測試 | Zotero Dev Tools | UI 整合 |

### 10.2 測試用例範例

```typescript
// 單元測試：序列化器
describe('ItemSerializer', () => {
  it('should serialize a Zotero item to JSON', () => {
    const mockItem = createMockZoteroItem({
      key: 'ABC12345',
      itemType: 'journalArticle',
      title: 'Test Article',
    });
    const result = serializeItem(mockItem);
    expect(result.key).toBe('ABC12345');
    expect(result.itemType).toBe('journalArticle');
  });
});

// 整合測試：HTTP Bridge
describe('Bridge API', () => {
  it('should update an item', async () => {
    const response = await fetch('http://localhost:24119/keeper/v1/items/ABC12345', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: 'Updated Title' }),
    });
    expect(response.status).toBe(200);
    const item = Zotero.Items.getByLibraryAndKey(1, 'ABC12345');
    expect(item.getField('title')).toBe('Updated Title');
  });
});
```

---

## 11. 發布與分發

### 11.1 發布管道

```
開發者                    CI/CD                     分發
  │                        │                        │
  ├── npx bumpp            │                        │
  │   └── git tag v0.1.0   │                        │
  │       └── git push ────┤                        │
  │                        ├── npm run build         │
  │                        ├── 產生 .xpi             │
  │                        ├── GitHub Release ───────┤
  │                        │                        ├── .xpi 下載
  │                        │                        ├── update.json
  │                        │                        └── update-beta.json
  │                        │                        │
  │                        │        Zotero 自動更新 ◄──┘
  │                        │        (via update.json)
```

### 11.2 版本策略

- 遵循 [SemVer](https://semver.org/)
- `0.x.y` — 開發階段
- `1.0.0` — 首個穩定版
- Beta 版本：`0.1.0-beta.1`

### 11.3 分發方式

1. **GitHub Releases** — 主要分發管道
   - `.xpi` 下載
   - `update.json` 自動更新清單
2. **Zotero Plugins 頁面** — 申請收錄
3. **VS Code Extension** — 整合下載提示

---

## 12. 風險與緩解

| 風險 | 影響 | 可能性 | 緩解措施 |
|---|---|---|---|
| Zotero 內部 API 變更 | 高 | 中 | 使用官方 Plugin API 優先；訂閱 zotero-dev 郵件列表 |
| Zotero 8 ESM 遷移 | 中 | 已確認 | 使用 migrate-fx140 腳本；支援 Zotero 7+8 |
| HTTP Bridge 效能問題 | 中 | 低 | 使用非同步 I/O；批量操作加入限流 |
| 安全漏洞 | 高 | 低 | localhost-only；Token 認證；路徑驗證 |
| Plugin 審核被拒 | 低 | 低 | 遵循官方指南；不做危險操作 |
| 與其他 Plugin 衝突 | 低 | 低 | 使用命名空間隔離（keeper-*） |

---

## 13. 附錄

### 13.1 參考資源

| 資源 | URL |
|---|---|
| Zotero 7 Plugin 開發指南 | https://www.zotero.org/support/dev/zotero_7_for_developers |
| Zotero 8 Plugin 開發指南 | https://www.zotero.org/support/dev/zotero_8_for_developers |
| Zotero JavaScript API | https://www.zotero.org/support/dev/client_coding/javascript_api |
| Zotero Plugin Template | https://github.com/windingwind/zotero-plugin-template |
| zotero-plugin-toolkit | https://github.com/windingwind/zotero-plugin-toolkit |
| zotero-types | https://github.com/windingwind/zotero-types |
| Make It Red（官方範例） | https://github.com/zotero/make-it-red |
| Zotero 原始碼 | https://github.com/zotero/zotero |
| Zotero pluginAPI 目錄 | https://github.com/zotero/zotero/tree/main/chrome/content/zotero/xpcom/pluginAPI |
| Zotero data 層 | https://github.com/zotero/zotero/tree/main/chrome/content/zotero/xpcom/data |

### 13.2 參考 Plugin

| Plugin | 參考理由 |
|---|---|
| Better BibTeX | LaTeX 整合、HTTP 端點暴露模式 |
| zotxt | REST API 暴露模式（cite-as-you-write） |
| PDF Translate | PDF 閱讀器 event handler 範例 |
| Better Notes | Item Pane Section 範例 |
| Zotero OCR | 檔案處理 + 附件操作範例 |
| Cita | Citation 網路 + 外部 API 整合 |

### 13.3 Zotero xpcom 關鍵原始碼

| 檔案 | 功能 |
|---|---|
| `xpcom/data/item.js` | Item 資料模型（所有欄位操作） |
| `xpcom/data/items.js` | Items 集合管理 |
| `xpcom/data/collection.js` | Collection 資料模型 |
| `xpcom/attachments.js` | 附件管理 |
| `xpcom/fulltext.js` | 全文索引 |
| `xpcom/annotations.js` | PDF Annotations |
| `xpcom/file.js` | 檔案 I/O 工具 |
| `xpcom/db.js` | SQLite 資料庫連線 |
| `xpcom/notifier.js` | 事件通知系統 |
| `xpcom/api.js` | 內建 Local API server |
| `xpcom/server/` | HTTP Server 端點實作 |
| `xpcom/pluginAPI/` | 官方 Plugin API（ItemTreeManager 等） |

### 13.4 與 MCP Server 的整合方案

```
MCP Server 改動摘要:

1. 新增 BridgeClient (DAL 層)
   mcp-server/src/zotero_mcp/infrastructure/dal/bridge_client.py
   - HTTP client 連接 localhost:24119
   - 自動探測 Bridge 是否可用
   - fallback 到現有 Local API client

2. 更新現有工具使用 Bridge
   - get_item() → 優先使用 Bridge（取得更完整資訊）
   - 新增 update_item() 工具（之前不可能）
   - 新增 get_fulltext() 工具（之前不可能）
   - 新增 get_annotations() 工具（之前不可能）
   - 新增 upload_attachment() 工具（之前不可能）
   - 新增 delete_item() 工具（之前不可能）

3. VSCode Extension 整合
   - StatusBar 顯示 Bridge 連線狀態
   - 自動偵測 Zotero Plugin 是否安裝
```

---

## 變更紀錄

| 日期 | 版本 | 變更 |
|---|---|---|
| 2025-07-18 | v0.1.0 | 初版規格書 |
