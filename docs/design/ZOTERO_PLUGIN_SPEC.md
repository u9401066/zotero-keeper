# Zotero Keeper Plugin — 選配擴充規格書

> **規格版本**: v0.2.0 (Draft)
> **日期**: 2026-08-12
> **作者**: u9401066
> **狀態**: 📋 選配 Plugin 規劃中；官方基本 CRUD transport 不依賴 Plugin
> **產品基線**: VSIX 0.7.0 / Zotero Keeper 2.1.0 / MCP SDK v2 / 32 個預設 tools

---

## 目錄

1. [執行摘要](#1-執行摘要)
2. [目前架構與 Plugin 定位](#2-目前架構與-plugin-定位)
3. [歷史附錄：pre-Zotero-10 HTTP Bridge 技術架構](#3-歷史附錄pre-zotero-10-http-bridge-技術架構)
4. [功能規格（目前目標與歷史參考）](#4-功能規格目前目標與歷史參考)
5. [Plugin API 可用能力清單](#5-plugin-api-可用能力清單)
6. [歷史附錄：pre-Zotero-10 Bridge 專案結構](#6-歷史附錄pre-zotero-10-bridge-專案結構)
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

**Zotero Keeper Plugin** 是一個選配的 Zotero 原生外掛，補足官方 Local API
不適合承載的 Zotero-native 能力：PDF annotation 語意、Reader/Notifier
事件、原生 UI 與少數經 allowlist 審核的 internal-only 操作；它也可以作為
Zotero 7–9 的相容 fallback，但不再是 Zotero 10+ 基本 CRUD、全文寫入或
stored-file upload 的必要元件。

### 1.2 核心價值

Zotero Keeper 2.1.0 已在 MCP SDK v2 上提供 32 個預設 tools。新增的 8 個
Local API tools 包含 runtime write authorization、collection/item/note/saved
search 操作、全文寫入與 stored-file upload。Plugin 的價值因此集中於：

| 優先級 | Plugin 適合提供的能力 | 原因 |
|---|---|---|
| P0 | Annotation/Reader 語意 | 需要 Zotero Reader 與 annotation 內部物件語境 |
| P0 | Notifier 事件串流 | Local API 是 request/response；Plugin 可主動送出變更事件 |
| P1 | Zotero-native UI | Item Pane、右鍵選單、狀態與使用者可見的操作入口 |
| P1 | 經審核的 internal-only 操作 | 只暴露明確 allowlist，不提供任意 JavaScript/SQL/路徑存取 |
| P2 | Zotero 7–9 fallback | 舊版沒有 Zotero 10 runtime-authorized Local writes 時的選配相容層 |

以下能力**不應再列為 Plugin 的核心理由**：Zotero 10+ 的官方 item、collection、
note、saved search CRUD transport、versioned fulltext write 與三階段 stored-file
upload。Keeper 2.1 已透過官方 Local API v3 提供受限且需確認的 allowlist；它並未
因此暴露任意 raw Local API 或通用 delete tool。

### 1.3 目前架構定位

```
AI Agent / VSIX 0.7.0
        │ MCP SDK v2
        ▼
Zotero Keeper 2.1.0 (32 default tools)
        ├── Local API v3 : reads + Zotero 10+ authorized writes
        ├── Connector API: create/import compatibility path (Zotero 7–10+)
        └── Optional Plugin
              ├── annotations / Reader events
              ├── Notifier event stream
              ├── Zotero-native UI
              ├── reviewed internal-only operations
              └── Zotero 7–9 write fallback
```

---

## 2. 目前架構與 Plugin 定位

### 2.1 官方 Local API v3（Keeper 2.1 的主要路徑）

Zotero 10+ 已提供 runtime-authorized Local API v3 writes。Keeper 在
`GET /api/` discovery 後記錄 `Zotero-API-Version`、
`Zotero-Schema-Version` 與 `Zotero-Server-ID`，並將 authorization、local
object versions 與 cache 綁定該 Server-ID。

- Reads 不需認證，但只能走 literal loopback。
- Writes 先由 `authorize_local_writes` 觸發 Zotero 的 Allow / Always Allow /
  Deny 視窗；Local API key 僅存於 process memory，不會成為 MCP 參數、結果、
  log、URL query 或專案檔案。
- 每次 mutation 都帶 Server-ID 及 local version precondition
  (`If-Unmodified-Since-Version`)；`412` conflict 不自動重播。
- Stored-file upload 使用官方三階段流程。upload URL 必須仍是設定中的 loopback
  host/port，傳送檔案 bytes 時不得夾帶 Local API key。
- `attach_file_to_item` 需要 Always Allow，因為流程包含多次 authenticated writes。

這些是目前正式架構；不能再以「Local API read-only」、「更新固定回傳 501」或
「等待官方 write API」描述 Zotero 10+。

### 2.2 Connector 相容路徑

`/connector/*` 與 `/api/*` 是兩個不同 contract。Keeper 保留 Connector 的
create/import 能力供 Zotero 7–9 使用，在 Zotero 10+ 也維持向後相容；它不是
Zotero 10+ Local API write 能力的替代規格。

### 2.3 Plugin 的界線

Plugin 不應：

- 複製 Zotero 10+ 已正式支援的基本 CRUD/upload 作為預設 transport；
- 暴露任意 Zotero JavaScript、SQLite、檔案路徑或 raw HTTP proxy；
- 規避 Keeper 的 proposal → user confirmation → mutation 流程；
- 重用或外洩 Local API runtime key；Plugin token 必須是獨立 credential；
- 自動重播可能已成功的 mutation，或用新版本覆蓋使用者先前確認的狀態。

| Zotero 版本 | Local reads | Connector import | Authorized Local writes | Plugin 定位 |
|---|:---:|:---:|:---:|---|
| 7–8 | ✅ | ✅ | ❌ | 選配 write fallback、UI、events |
| 9 | ✅（依 Local API 設定） | ✅ | ❌ | 選配 write fallback、UI、events |
| 10+ | ✅ | ✅（相容路徑） | ✅ | annotations/events/UI/internal-only ops |

---

## 3. 歷史附錄：pre-Zotero-10 HTTP Bridge 技術架構

> **Historical — not the current architecture.** 本節保留 2025 年、Zotero 10
> authorized Local writes 公開前的 `localhost:24119` 高權限 HTTP Bridge
> 草案，供設計脈絡與考古使用。以下「Local API read-only／501／Plugin 負責
> CRUD」等敘述只描述當時假設，不能套用到 Keeper 2.1 或 Zotero 10+。

### 3.1 Zotero 7/8/9 Plugin 基礎架構

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

## 4. 功能規格（目前目標與歷史參考）

> **Historical boundary:** 4.1–4.2 保留 pre-Zotero-10 HTTP Bridge 的 CRUD、
> file、fulltext、notes、search 與 batch endpoint 草案；這些不是目前 Plugin
> 的實作優先級。4.3–4.4 的 Zotero-native UI、annotations/Reader 與 Notifier
> events 才是目前核心方向。

### 4.1 Historical Phase 1：核心讀寫 Bridge（pre-Zotero-10）

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

### 4.2 Historical Phase 2：通用 Bridge 功能（pre-Zotero-10）

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

### 4.3 Current target：Zotero-native UI 整合

#### 4.3.1 偏好設定面板

```
┌─────────────────────────────────────┐
│  Zotero Keeper Plugin Settings      │
├─────────────────────────────────────┤
│  HTTP Bridge                        │
│  ┌──────────────────────────────┐   │
│  │ Port: [24119]                │   │
│  │ ☑ Auto-start on launch      │   │
│  │ ☑ Require auth token        │   │
│  └──────────────────────────────┘   │
│                                     │
│  Security                           │
│  ┌──────────────────────────────┐   │
│  │ Bind: localhost only         │   │
│  │ Auth Token: [••••••••]       │   │
│  │ Browser CORS: [disabled]     │   │
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

### 4.4 Current target：Annotations 與事件整合

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

### 5.2 Zotero 內部 API（非公開、需逐版驗證）

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

## 6. 歷史附錄：pre-Zotero-10 Bridge 專案結構

> 本節保留原始 HTTP-centric 目錄、manifest 與 prefs 草案。若開始實作，應先
> 依第 8 節目前 roadmap 縮減 scope，且不得直接複製未審核的 CRUD handlers。

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
pref("extensions.zotero.keeper.bridge.requireAuth", true); // mandatory
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

### Phase 0：契約與安全邊界（P0）

- 定義只包含 annotations、Reader/Notifier events、UI action 與經審核
  internal-only operations 的 allowlist；不提供 raw Zotero API proxy。
- Plugin endpoint 僅 bind literal loopback，所有 request 強制帶獨立的高熵
  bearer token，CORS 預設完全關閉。
- 明確區隔 Plugin token 與 Zotero Local API runtime key；兩者不得互用、回傳
  給 MCP 或寫入 workspace。
- 所有 mutation 保留 Keeper 的 proposal → explicit confirmation → mutation
  模式，並定義 conflict/partial-result contract。

### Phase 1：Annotations、Reader 與 Notifier events（P0）

| 功能 | 優先級 | 驗收重點 |
|---|---|---|
| 讀取結構化 PDF annotations | P0 | 類型、頁碼、位置、顏色與註解語意穩定 |
| Reader event listener | P0 | 只發布 allowlisted event 與最小必要 payload |
| Notifier → SSE event stream | P0 | reconnect、backpressure、shutdown 與資料庫切換安全 |
| Plugin health/capability discovery | P0 | 回報版本與能力，不回報 secrets |

### Phase 2：Zotero-native UI（P1）

| 功能 | 優先級 | 驗收重點 |
|---|---|---|
| Item Pane Section | P1 | 顯示 MCP/Plugin 狀態與最近操作，不洩漏 token |
| Context menu actions | P1 | 使用者可見、可取消、目標 item 清楚 |
| Preference Pane | P1 | 認證固定開啟；可輪替 token、停用 bridge |
| Reader actions | P1 | annotation/selection 操作有明確 UI 回饋 |

### Phase 3：Internal-only operations（P1/P2）

每個 operation 必須先證明官方 Local API v3 或 Connector 無法安全表達，再加入
最小 allowlist。Internal API 必須有 Zotero 版本相容測試、失敗關閉策略與移除
計畫。Generic item/collection/note/saved-search CRUD、fulltext write 與 stored-file
upload 不屬於此 phase，因為 Zotero 10+ 已有正式 transport。

### Phase 4：Zotero 7–9 fallback（P2）

只有在確認仍需支援 legacy desktop writes 時才啟動。Fallback 必須 capability-
gated，且不得在 Zotero 10+ 攔截 Keeper 的 Local API v3 正常路徑。Connector
create/import 仍為 7–9 的第一相容選擇；Plugin 只補 Connector 無法覆蓋且經使用者
確認的操作。

### Phase 5：Keeper / VSIX 整合（P2）

- Keeper 在現有 Local API 與 Connector discovery 之外，選配偵測 Plugin
  capability；沒有 Plugin 時 32-tool 基線仍正常。
- VSIX 只顯示選配安裝/診斷狀態，不把 Plugin 當成 Keeper 2.1 啟動前置條件。
- MCP tools 依能力路由：Zotero 10+ basic writes → Local API v3；create/import
  compatibility → Connector；annotations/events/internal-only ops → Plugin。

### Historical：pre-Zotero-10 優先順序

2025 草案原先把 HTTP server、item CRUD、全文、檔案下載/上傳與 Bridge-first
DAL 設為 Phase 1，再依序加入 annotations/notes/search/batch、UI、events 與 MCP
整合。相關 endpoint、型別與目錄設計完整保留在第 3、4、6 節，但此優先順序已
由 Zotero 10 Local API v3 與 Keeper 2.1 的正式能力取代。

---

## 9. 安全性考量

### 9.1 威脅模型

| 威脅 | 風險 | 緩解措施 |
|---|---|---|
| 未授權的本機程序呼叫 Plugin | 高 | literal loopback + **mandatory** bearer token；無匿名模式 |
| Plugin token 或 Local API key 洩漏 | 高 | 分離 credential；不進 MCP、log、URL、workspace；可輪替 |
| 任意 internal API / SQL / filesystem 存取 | 高 | 固定 operation allowlist 與 schema；不提供 raw proxy |
| 路徑遍歷或任意檔案 exfiltration | 高 | 不接受 raw path；只處理已解析且屬於 Zotero storage 的 item |
| 跨資料庫或 stale mutation | 高 | 驗證 active database identity/version；conflict fail closed |
| Browser/CORS drive-by request | 高 | CORS 預設關閉；不接受 wildcard、prefix 或任意 WebView origin |
| 資源耗盡或 event flood | 中 | request/body/queue limits、backpressure、rate limit |
| Internal API 隨 Zotero 版本變更 | 中 | capability discovery、逐版 integration tests、失敗關閉 |

### 9.2 Credential 與 transport 規則

Zotero 10+ 的官方 Local API authorization 仍由 Keeper 直接處理：先讀
`Zotero-Server-ID`，再由 Zotero UI 核准 runtime key；object writes 使用 local
version precondition，stored-file bytes 只送往經驗證的 loopback upload URL。
Plugin 不得代理、記錄或重用該 key。

若選配 HTTP Bridge 實作，token 認證是不可關閉的基線：

```typescript
// Concept only: exact APIs depend on the selected Zotero plugin scaffold.
const serverSocket = Cc["@mozilla.org/network/server-socket;1"]
  .createInstance(Ci.nsIServerSocket);
serverSocket.init(port, true, -1); // loopbackOnly = true

function authenticate(request: nsIHttpRequest): boolean {
  const token = Zotero.Prefs.get('extensions.zotero.keeper.bridge.authToken');
  const authHeader = request.getHeader('Authorization');
  return token.length >= 32 && constantTimeEqual(authHeader, `Bearer ${token}`);
}
```

### 9.3 CORS 設定

非 browser 的 local MCP client 不需要 CORS。預設不送
`Access-Control-Allow-Origin`；若未來 Zotero UI 以外確有 browser client，必須
新增 exact-origin allowlist 與獨立 threat-model review，不能以 `startsWith()` 或
wildcard 放行 localhost/WebView。

### 9.4 Mutation 與 upload

- Bridge mutation 仍需 MCP proposal/confirmation，不因已通過 token 認證而省略。
- 任何可觀察版本衝突都回傳給使用者，不自動 refetch-and-overwrite 或 replay。
- Zotero 10+ stored-file upload 維持 Keeper → Local API 三階段路徑：需要
  remembered authorization，upload URL 限制在設定中的 loopback port，bytes
  request 不帶 Local API key。
- 若 Zotero 7–9 fallback 日後需要 Plugin 檔案操作，必須另訂大小、來源、父 item
  與 partial-failure contract；不可把歷史任意 file endpoint 直接上線。

---

## 10. 測試策略

### 10.1 測試層級

| 層級 | 工具 | 涵蓋範圍 |
|---|---|---|
| 單元測試 | vitest | capability、serializer、auth、event filtering、limits |
| 整合測試 | Zotero test runner | Reader/Notifier/UI ↔ allowlisted Plugin operations |
| E2E 測試 | authenticated local client | 啟動、capability discovery、annotations、SSE、shutdown |
| 相容性測試 | Zotero 7/8/9/10 matrix | fallback gating；Zotero 10+ basic writes 不改走 Plugin |
| 安全負向測試 | local adversarial client | 無 token、錯 token、CORS、path、oversize、event flood |
| Manual 測試 | Zotero Dev Tools | UI、授權失敗與使用者取消 |

### 10.2 測試用例範例

```typescript
describe('Plugin security and annotation contract', () => {
  it('rejects anonymous requests', async () => {
    const response = await fetch(
      'http://127.0.0.1:24119/keeper/v1/capabilities'
    );
    expect(response.status).toBe(401);
  });

  it('returns allowlisted annotation fields to an authenticated client', async () => {
    const response = await fetch(
      'http://127.0.0.1:24119/keeper/v1/items/ABC12345/annotations',
      { headers: { Authorization: `Bearer ${testToken}` } },
    );
    expect(response.status).toBe(200);
    expect(await response.json()).toMatchSchema(annotationResponseSchema);
  });
});
```

Keeper integration tests另需證明：Zotero 10+ 的
`authorize_local_writes`、versioned mutation、fulltext write 與三階段 upload
持續直接走 Local API v3；Plugin 未安裝或停用時，32 個預設 tools 的基線不變。

---

## 11. 發布與分發

### 11.1 發布管道

```
開發者                    CI/CD                     分發
  │                        │                        │
  ├── npx bumpp            │                        │
  │   └── git tag v0.x.y   │                        │
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
| Zotero 內部 API 變更 | 高 | 中 | 官方 Plugin API 優先；capability gate；逐版測試；失敗關閉 |
| Zotero 7–10 lifecycle 差異 | 中 | 中 | 版本矩陣；fallback 與 Zotero 10+ transport 分離 |
| Event flood / SSE backpressure | 中 | 中 | 有界 queue、coalescing、rate limit、可觀察 dropped count |
| Bridge credential 洩漏 | 高 | 低 | 強制高熵 token、輪替、不進 MCP/log/workspace、constant-time compare |
| Internal-only operation scope creep | 高 | 中 | 每個 endpoint 個別 threat-model/allowlist；禁止 raw proxy |
| Plugin 審核被拒 | 中 | 低 | 最小權限、透明 UI、遵循官方指南、不提供任意破壞性操作 |
| 與其他 Plugin 衝突 | 低 | 低 | 使用命名空間隔離（keeper-*）；完整 startup/shutdown cleanup |

---

## 13. 附錄

### 13.1 參考資源

| 資源 | URL |
|---|---|
| Zotero 7 Plugin 開發指南 | https://www.zotero.org/support/dev/zotero_7_for_developers |
| Zotero 8 Plugin 開發指南 | https://www.zotero.org/support/dev/zotero_8_for_developers |
| Zotero Local API v3 | https://www.zotero.org/support/dev/web_api/v3/local_api |
| Zotero API v3 Write Requests | https://www.zotero.org/support/dev/web_api/v3/write_requests |
| Zotero File Upload | https://www.zotero.org/support/dev/web_api/v3/file_upload |
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
Keeper 2.1 routing:

1. Local API v3 client (Zotero 10+)
   - discovery: API/schema version + Zotero-Server-ID
   - runtime authorization held only in memory
   - versioned basic CRUD/fulltext + three-phase stored-file upload

2. Connector client (Zotero 7–10+ compatibility)
   - existing create/import workflow
   - remains distinct from the Local API write contract

3. Optional Plugin client
   - authenticated capability discovery on literal loopback
   - annotations / Reader / Notifier events / Zotero-native UI
   - reviewed internal-only operations and optional Zotero 7–9 fallback
   - never becomes a prerequisite for the 32-tool Keeper baseline

4. VSIX integration
   - optional installation/health status only
   - no Plugin credential in settings, logs, status text, or MCP definitions
```

---

## 變更紀錄

| 日期 | 版本 | 變更 |
|---|---|---|
| 2026-08-12 | v0.2.0 | 對齊 VSIX 0.7 / Keeper 2.1 / 32 tools 與 Zotero 10 Local API v3；Plugin 重新定位為 annotations/events/UI/internal-only ops/Zotero 7–9 fallback；舊 HTTP Bridge 明標歷史 |
| 2025-07-18 | v0.1.0 | 初版規格書 |
