# Zotero Local API 開發文檔

> 這份文檔記錄了 Zotero Local API 的官方文件與我們實際探索的結果。
> 對於開發 zotero-keeper 非常重要！

## 目錄

- [概述](#概述)
- [API 端點](#api-端點)
  - [Local API (Read)](#local-api-read)
  - [Connector API (Write)](#connector-api-write)
- [實際測試結果](#實際測試結果)
- [已知限制](#已知限制)
- [開發注意事項](#開發注意事項)

---

## 概述

Zotero 提供兩種本地 API：

| API 類型 | 基礎路徑 | 用途 | 方法 |
|----------|----------|------|------|
| **Local API** | `/api/users/0/...` | 讀取資料 | GET only |
| **Connector API** | `/connector/...` | 寫入資料 | POST |

**預設端口**: `23119` (localhost)

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

### 1. 無法將現有文獻加入 Collection

**問題**: 當文獻已存在 Zotero 時，無法透過 API 將它加入新的 collection。

**原因**: 
- Connector API 的 `saveItems` 只能在新建時指定 collection
- Local API 不支援 PATCH/PUT

**解決方案**: 
- 使用 `skip_duplicates=false` 強制重新匯入（會產生重複）
- 或在 Zotero GUI 中手動操作

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
- [zotero-keeper ARCHITECTURE.md](../ARCHITECTURE.md)

---

## 更新日誌

| 日期 | 更新內容 |
|------|----------|
| 2024-12-14 | 初始版本，記錄 Local API 與 Connector API 測試結果 |
| 2024-12-14 | 確認 collections 欄位在 saveItems 中有效 |
| 2024-12-14 | 記錄 Local API 不支援寫入 (501) |
| 2024-12-14 | v1.8.0: 新增 collection 防呆機制 (collection_name 驗證) |
| 2024-12-14 | v1.8.0: 新增 include_citation_metrics 參數 (RCR 寫入 extra) |

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
