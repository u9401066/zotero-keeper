# Zotero API 開發文檔

> 這份文檔記錄了 Zotero 各種 API 的官方文件與我們實際探索的結果。
> 對於開發 zotero-keeper 非常重要！

## 目錄

- [概述](#概述)
- [API 比較](#api-比較)
- [API 端點](#api-端點)
  - [Local API (Read)](#local-api-read)
  - [Connector API (Write)](#connector-api-write)
  - [Web API (Full CRUD)](#web-api-full-crud)
- [pyzotero 整合](#pyzotero-整合)
- [實際測試結果](#實際測試結果)
- [已知限制](#已知限制)
- [開發注意事項](#開發注意事項)
- [未來規劃](#未來規劃)

---

## 概述

Zotero 提供**三種** API，各有不同的能力和限制：

| API 類型 | 基礎路徑 | 讀取 | 寫入 | 需求 |
|----------|----------|:----:|:----:|------|
| **Local API** | `localhost:23119/api/users/0/...` | ✅ | ❌ | Zotero 運行中 |
| **Connector API** | `localhost:23119/connector/...` | ❌ | ⚠️ 有限 | Zotero 運行中 |
| **Web API** | `api.zotero.org/users/{id}/...` | ✅ | ✅ **完整** | API Key |

**預設端口**: `23119` (localhost)

---

## API 比較

### 🔍 選擇哪個 API？

```
需要寫入/更新現有文獻？
├─ 是 → 使用 Web API (需 API Key)
└─ 否 → 使用 Local API (零設定)

需要從網頁匯入？
├─ 是 → 使用 Connector API
└─ 否 → 使用 Local API 或 Web API
```

### 📊 功能對照表

| 功能 | Local API | Connector API | Web API |
|------|:---------:|:-------------:|:-------:|
| 讀取文獻 | ✅ | ❌ | ✅ |
| 讀取 Collections | ✅ | ❌ | ✅ |
| 讀取 Saved Searches | ✅ | ❌ | ✅ |
| 執行 Saved Searches | ✅ | ❌ | ❌ |
| 新增文獻 | ❌ | ✅ | ✅ |
| 更新文獻 | ❌ | ❌ | ✅ |
| 刪除文獻 | ❌ | ❌ | ✅ |
| 加入 Collection | ❌ | ⚠️¹ | ✅ |
| 移除 Collection | ❌ | ❌ | ✅ |
| 上傳附件 | ❌ | ❌ | ✅ |
| 需要設定 | 無 | 無 | API Key |

> ¹ Connector API 只能在**新增時**指定 collection，無法修改現有文獻

---

## API 端點

### Local API (Read)

> 🔗 官方文檔: https://www.zotero.org/support/dev/web_api/v3/basics

#### Items

| 端點 | 方法 | 說明 | 測試結果 |
|------|------|------|----------|
| `/api/users/0/items` | GET | 列出所有文獻 | ✅ 正常 |
| `/api/users/0/items?q={query}` | GET | 搜尋文獻 | ✅ 正常 |
| `/api/users/0/items?limit={n}` | GET | 限制數量 | ✅ 正常 |
| `/api/users/0/items/{key}` | GET | 取得單一文獻 | ✅ 正常 |
| `/api/users/0/items/{key}/children` | GET | 取得附件 | ✅ 正常 |
| `/api/users/0/items/{key}` | PATCH | 更新文獻 | ❌ **501 未實作** |
| `/api/users/0/items/{key}` | PUT | 更新文獻 | ❌ **501 未實作** |
| `/api/users/0/items` | POST | 新增文獻 | ❌ **400 錯誤** |

#### Collections

| 端點 | 方法 | 說明 | 測試結果 |
|------|------|------|----------|
| `/api/users/0/collections` | GET | 列出所有收藏夾 | ✅ 正常 |
| `/api/users/0/collections/{key}` | GET | 取得單一收藏夾 | ✅ 正常 |
| `/api/users/0/collections/{key}/items` | GET | 收藏夾內的文獻 | ✅ 正常 |

#### Tags

| 端點 | 方法 | 說明 | 測試結果 |
|------|------|------|----------|
| `/api/users/0/tags` | GET | 列出所有標籤 | ✅ 正常 |

#### Saved Searches

| 端點 | 方法 | 說明 | 測試結果 |
|------|------|------|----------|
| `/api/users/0/searches` | GET | 列出已儲存搜尋 | ✅ 正常 |
| `/api/users/0/searches/{key}` | GET | 取得單一搜尋 | ✅ 正常 |
| `/api/users/0/searches/{key}/items` | GET | 執行搜尋 | ✅ 正常 (Local API 獨有!) |

#### Schema

| 端點 | 方法 | 說明 | 測試結果 |
|------|------|------|----------|
| `/api/itemTypes` | GET | 可用的文獻類型 | ✅ 正常 |
| `/api/itemTypeFields?itemType={type}` | GET | 類型的欄位 | ✅ 正常 |
| `/api/creatorTypes?itemType={type}` | GET | 作者類型 | ✅ 正常 |

---

### Connector API (Write)

> 這是 Zotero 瀏覽器擴充功能使用的 API

#### 健康檢查

| 端點 | 方法 | 說明 | 測試結果 |
|------|------|------|----------|
| `/connector/ping` | GET | 檢查 Zotero 是否運行 | ✅ 正常 |

#### 儲存文獻

| 端點 | 方法 | 說明 | 測試結果 |
|------|------|------|----------|
| `/connector/saveItems` | POST | 儲存文獻 | ✅ 正常 (有限制) |

##### saveItems 請求格式

```json
{
  "items": [
    {
      "itemType": "journalArticle",
      "title": "文章標題",
      "creators": [
        {"firstName": "名", "lastName": "姓", "creatorType": "author"}
      ],
      "abstractNote": "摘要",
      "publicationTitle": "期刊名",
      "DOI": "10.xxxx/xxxx",
      "date": "2024-01-15",
      "tags": [{"tag": "標籤1"}, {"tag": "標籤2"}],
      "collections": ["COLLECTION_KEY"]
    }
  ],
  "uri": "http://source.url",
  "title": "來源標題"
}
```

##### saveItems 回應格式

```json
{
  "items": [...]  // 儲存的項目（但不包含新 key！）
}
```

---

### Web API (Full CRUD)

> 🔗 官方文檔: [Write Requests](https://www.zotero.org/support/dev/web_api/v3/write_requests)

**2025-01 研究發現**：Zotero Web API 完整支援 CRUD 操作！

#### 設定需求

1. **取得 API Key**: [https://www.zotero.org/settings/keys](https://www.zotero.org/settings/keys)
2. **取得 User ID**: 在 Zotero 設定頁面可見
3. **設定權限**: 建議給予「讀寫」權限

#### 端點格式

```text
基礎 URL: https://api.zotero.org
用戶資料: /users/{userID}/...
群組資料: /groups/{groupID}/...
```

#### 寫入操作

| 端點 | 方法 | 說明 | 狀態 |
|------|------|------|------|
| `/users/{id}/items` | POST | 新增文獻 | ✅ 支援 |
| `/users/{id}/items/{key}` | PUT | 完整更新 | ✅ 支援 |
| `/users/{id}/items/{key}` | PATCH | 部分更新 | ✅ 支援 |
| `/users/{id}/items/{key}` | DELETE | 刪除文獻 | ✅ 支援 |

#### PATCH 部分更新 (重點功能！)

Web API 支援**只更新特定欄位**，不需要傳送完整物件：

```http
PATCH /users/12345/items/ABCD1234
Zotero-API-Key: your-api-key
If-Unmodified-Since-Version: 456
Content-Type: application/json

{
  "collections": ["BCDE3456", "CDEF4567"]
}
```

這解決了 Local API 的最大限制：**可以將現有文獻加入 Collection！**

#### Version 管理

所有寫入請求需要 `If-Unmodified-Since-Version` header：

```python
# 1. 先讀取物件，取得 version
response = requests.get(f"{BASE_URL}/items/{key}")
version = response.headers["Last-Modified-Version"]

# 2. 寫入時帶上 version
headers = {
    "If-Unmodified-Since-Version": version,
    "Zotero-API-Key": api_key
}
requests.patch(f"{BASE_URL}/items/{key}", json=data, headers=headers)
```

#### 回應碼

| 碼 | 意義 |
|----|------|
| 200 | 成功 (更新) |
| 201 | 成功 (新增) |
| 204 | 成功 (刪除) |
| 412 | 版本衝突 (需重新讀取) |
| 403 | 權限不足 |

---

## pyzotero 整合

> 🔗 GitHub: [urschrei/pyzotero](https://github.com/urschrei/pyzotero) (1.2k ⭐)
> 🔗 文檔: [pyzotero.readthedocs.io](https://pyzotero.readthedocs.io/)

### 為什麼選擇 pyzotero？

| 特點 | 說明 |
|------|------|
| **成熟穩定** | 持續維護 10+ 年，v1.7.6 (2025) |
| **完整功能** | 覆蓋 Web API 所有端點 |
| **Pythonic** | 設計良好的介面 |
| **雙模式** | 支援 Web API 和 Local API |

### 安裝

```bash
pip install pyzotero
# 或
uv add pyzotero
```

### 基本用法

```python
from pyzotero import zotero

# Web API 模式 (完整讀寫)
zot = zotero.Zotero(
    library_id="12345",
    library_type="user",  # or "group"
    api_key="your-api-key"
)

# Local API 模式 (僅讀取)
zot_local = zotero.Zotero(
    library_id="0",
    library_type="user",
    api_key="",
    local=True
)
```

### 寫入操作範例

```python
# 新增文獻
template = zot.item_template("journalArticle")
template["title"] = "新文章標題"
zot.create_items([template])

# 更新文獻
item = zot.item("ABCD1234")
item["data"]["title"] = "更新的標題"
zot.update_item(item)

# 加入 Collection (核心功能！)
zot.addto_collection("COLL1234", item)

# 從 Collection 移除
zot.deletefrom_collection("COLL1234", item)

# 上傳附件
zot.attachment_simple(["/path/to/file.pdf"], "PARENT_KEY")
```

### 批次操作

```python
# 批次新增 (自動分批)
items = [template1, template2, template3, ...]
zot.create_items(items)  # 自動處理 50 個一批

# 批次更新
for item in items_to_update:
    zot.update_item(item)
```

### 錯誤處理

```python
from pyzotero import zotero_errors

try:
    zot.update_item(item)
except zotero_errors.PreConditionFailed:
    # Version 衝突，需重新讀取
    item = zot.item(item["key"])
    # 重試...
except zotero_errors.UserNotAuthorised:
    # API Key 權限不足
    pass
```

---

## 實際測試結果

### ✅ `collections` 欄位在 saveItems 中有效

**測試日期**: 2024-12-14

當透過 `/connector/saveItems` 儲存文獻時，`collections` 欄位**確實有效**：

```python
item = {
    "itemType": "journalArticle",
    "title": "Test",
    "collections": ["MHT7CZ8U"]  # ← 這會生效！
}
```

**驗證方法**:
1. 匯入文章指定 `collection_key`
2. 用 `/api/users/0/items/{key}` 查詢文章
3. 確認 `collections` 欄位包含正確的 key
4. 用 `/api/users/0/collections/{key}/items` 確認文章在 collection 中

### ❌ Local API 不支援寫入

**測試日期**: 2024-12-14

```bash
# PATCH - 501 Not Implemented
curl -X PATCH "http://localhost:23119/api/users/0/items/ABC123" \
  -H "Content-Type: application/json" \
  -d '{"collections": ["XYZ789"]}'

# PUT - 501 Not Implemented  
curl -X PUT "http://localhost:23119/api/users/0/items/ABC123" ...

# POST - 400 Bad Request
curl -X POST "http://localhost:23119/api/users/0/items" ...
```

**結論**: Local API 是**唯讀**的，所有寫入必須透過 Connector API。

### ⚠️ Connector API 不回傳新建文獻的 Key

當透過 `/connector/saveItems` 新增文獻時，回應**不包含**新建立的 item key。

這意味著：
- 無法立即知道新文獻的 key
- 需要透過 PMID/DOI 搜尋來找到新文獻
- 或使用 `/api/users/0/items?limit=1&sort=dateAdded&direction=desc`

### ⚠️ Collection itemCount 不即時更新

`/api/users/0/collections` 回傳的 `itemCount` 可能不是最新的。

要取得準確數量，需要：
```
GET /api/users/0/collections/{key}/items
```
然後計算回傳的 items 數量。

---

## 已知限制

### 1. 無法將現有文獻加入 Collection (Local API 限制)

**問題**: 當文獻已存在 Zotero 時，無法透過 Local API 將它加入新的 collection。

**原因**: 
- Connector API 的 `saveItems` 只能在新建時指定 collection
- Local API 不支援 PATCH/PUT

**解決方案** (2025-01 更新):

| 方案 | 說明 | 推薦 |
|------|------|:----:|
| **Web API + pyzotero** | 使用 `zot.addto_collection()` | ✅ **推薦** |
| 強制重新匯入 | `skip_duplicates=false` | ⚠️ 會產生重複 |
| Zotero GUI | 手動拖曳操作 | 😅 |

```python
# 使用 pyzotero 的解決方案
from pyzotero import zotero

zot = zotero.Zotero(library_id, "user", api_key)
item = zot.item("EXISTING_KEY")
zot.addto_collection("TARGET_COLL", item)  # ✅ 完美解決！
```

### 2. 批次寫入限制

Connector API 沒有明確的批次大小限制，但建議：
- 每批不超過 50 個項目
- 批次之間加入適當延遲

### 3. RIS/BibTeX 匯入

`/connector/saveItems` 支援 `ris` 格式，但：
- 需要完整的 RIS 文字
- 解析可能不完整（缺少某些欄位）

---

## 開發注意事項

### 1. 端口設定

```python
# 預設端口
ZOTERO_PORT = 23119

# Windows 可能需要 port proxy
# netsh interface portproxy add v4tov4 listenport=23119 ...
```

### 2. 錯誤處理

```python
# 常見錯誤碼
200 - OK
400 - Bad Request (格式錯誤)
404 - Not Found (item/collection 不存在)
409 - Conflict (library 鎖定中)
501 - Not Implemented (Local API 不支援寫入)
```

### 3. 重複檢測策略

我們使用的策略：
1. 先用 `GET /api/users/0/items` 載入現有 PMID/DOI
2. 比對要匯入的文獻
3. 標記重複項目

```python
# 檢測重複
existing_pmids = set()
existing_dois = set()

for item in existing_items:
    extra = item.get("extra", "")
    if "PMID:" in extra:
        pmid = extract_pmid(extra)
        existing_pmids.add(pmid)
    if doi := item.get("DOI"):
        existing_dois.add(doi.lower())
```

### 4. Collection Key vs Name

- **Key**: 8 字元的唯一識別碼 (如 `MHT7CZ8U`)
- **Name**: 人類可讀的名稱 (如 `test1`)

API 只接受 **Key**，不接受 Name。需要先查詢 collection 列表來取得 key。

---

## 參考資料

- [Zotero Web API v3](https://www.zotero.org/support/dev/web_api/v3/start)
- [Zotero Web API Write Requests](https://www.zotero.org/support/dev/web_api/v3/write_requests)
- [Zotero Connector Development](https://www.zotero.org/support/dev/client_coding)
- [pyzotero GitHub](https://github.com/urschrei/pyzotero) - 1.2k ⭐ Python client
- [pyzotero Documentation](https://pyzotero.readthedocs.io/)
- [zotero-keeper ARCHITECTURE.md](../ARCHITECTURE.md)

---

## 未來規劃

### 🎯 Phase 1: pyzotero 整合 (優先)

目標：讓 zotero-keeper 支援雙模式運作

```text
┌─────────────────────────────────────────────────────┐
│  zotero-keeper                                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┐     ┌──────────────────────────┐ │
│  │ Local Mode   │     │ API Key Mode             │ │
│  │ (現有)       │     │ (新增)                   │ │
│  ├──────────────┤     ├──────────────────────────┤ │
│  │ 零設定       │     │ 需要 API Key             │ │
│  │ 僅讀取       │     │ 完整讀寫                 │ │
│  │ Connector    │     │ Web API + pyzotero       │ │
│  │ 寫入有限     │     │ 解決所有限制             │ │
│  └──────────────┘     └──────────────────────────┘ │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 📋 實作任務

1. **環境變數支援**
   - `ZOTERO_USER_ID`: 用戶 ID
   - `ZOTERO_API_KEY`: API 金鑰
   - `ZOTERO_MODE`: `local` (預設) 或 `api`

2. **新增 pyzotero 依賴**
   ```bash
   uv add pyzotero
   ```

3. **建立 ZoteroClient 抽象層**
   ```python
   class ZoteroClient(Protocol):
       def get_items(self) -> list[dict]: ...
       def add_to_collection(self, item_key: str, collection_key: str) -> bool: ...
   
   class LocalZoteroClient(ZoteroClient): ...  # 現有實作
   class WebZoteroClient(ZoteroClient): ...    # 新增，使用 pyzotero
   ```

4. **新增 MCP 工具**
   - `add_items_to_collection`: 將現有文獻加入 collection
   - `remove_items_from_collection`: 從 collection 移除
   - `update_item_metadata`: 更新文獻欄位

### 🚫 不可行的功能

| 功能 | 原因 |
|------|------|
| MCP 安裝 Zotero 套件 | 安全限制，需用戶手動確認 |
| 自動同步 | 需要 Zotero Sync 服務 |
| 本地檔案操作 | Zotero 資料庫格式私有 |

---

## 更新日誌

| 日期 | 更新內容 |
|------|----------|
| 2024-12-14 | 初始版本，記錄 Local API 與 Connector API 測試結果 |
| 2024-12-14 | 確認 collections 欄位在 saveItems 中有效 |
| 2024-12-14 | 記錄 Local API 不支援寫入 (501) |
| 2024-12-14 | v1.8.0: 新增 collection 防呆機制 (collection_name 驗證) |
| 2024-12-14 | v1.8.0: 新增 include_citation_metrics 參數 (RCR 寫入 extra) |
| **2025-01-12** | **重大更新：新增 Web API 完整文檔** |
| **2025-01-12** | **新增 pyzotero 整合指南** |
| **2025-01-12** | **更新已知限制的解決方案** |
| **2025-01-12** | **新增未來規劃章節** |

---

## v1.8.0 新功能

### Collection 防呆機制

`batch_import_from_pubmed` 現在支援：

1. **collection_name 參數** (推薦！)
   - 用名稱查找 collection，自動解析為 key
   - 找不到時回傳可用 collections 清單
   - 避免打錯 key 導致文獻跑錯位置

2. **驗證機制**
   - 無論用 name 或 key，都會先驗證是否存在
   - 回傳結果包含 `collection_info` 確認存到哪

```python
# ✅ 推薦用法
batch_import_from_pubmed(
    pmids="12345,67890",
    collection_name="test1"  # 自動驗證並解析
)

# ⚠️ 不推薦
batch_import_from_pubmed(
    pmids="12345,67890",
    collection_key="MHT7CZ8U"  # 容易打錯
)
```

### Citation Metrics (RCR) 支援

新增 `include_citation_metrics` 參數：

```python
batch_import_from_pubmed(
    pmids="12345,67890",
    include_citation_metrics=True  # 取得 RCR 並寫入 extra
)
```

會在 Zotero extra 欄位加入：
```
PMID: 12345678
PMCID: PMC1234567
RCR: 5.23
NIH Percentile: 85.2
Citations: 127
Citations/Year: 25.4
APT: 0.85
```

**注意**: 這會增加 API 呼叫時間（需要額外查詢 iCite）。
