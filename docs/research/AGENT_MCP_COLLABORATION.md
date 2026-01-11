# Agent-MCP 協作模式設計

> 本文件是 `UNIFIED_SEARCH_RESEARCH.md` 的補充章節

## 🤖 核心洞察

**Search MCP 本質是 Search Aggregation Middle Layer（搜尋聚合中間層）**

```
┌─────────────────────────────────────────────────────────────────┐
│                    SEARCH AGGREGATION MIDDLE LAYER              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│   │   Query     │ → │  Dispatch   │ → │  Aggregate  │        │
│   │ Enhancement │    │ (轉包)      │    │  (彙整)     │        │
│   └─────────────┘    └─────────────┘    └─────────────┘        │
│         ↑                                     ↓                 │
│         │              需要思考？              │                 │
│         └──────────── Agent 協助 ─────────────┘                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

三個階段都可能需要「思考」：
- **Query Enhancement**（查詢增強）→ 需要「理解」意圖
- **Multi-source Dispatch**（轉包分發）→ 需要「策略」決定
- **Result Aggregation**（結果彙整）→ 需要「判斷」品質

---

## 設計哲學：MCP 是工具，Agent 是大腦

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ITERATIVE PROTOCOL                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   Agent                          MCP                                    │
│     │                             │                                     │
│     │──── unified_search() ──────▶│                                     │
│     │                             │                                     │
│     │                        ┌────┴────┐                                │
│     │                        │ 簡單查詢？│                               │
│     │                        └────┬────┘                                │
│     │                             │                                     │
│     │         Yes ────────────────┼──────────────── No                  │
│     │              ↓              │              ↓                      │
│     │         直接處理            │         返回建議                     │
│     │              ↓              │              ↓                      │
│     │◀──── 結果 ─────────────────│◀──── needs_decision ───────────────│
│     │                             │                                     │
│     │                             │      {                              │
│     │                             │        "status": "needs_input",     │
│     │                             │        "suggestions": [...],        │
│     │                             │        "question": "..."            │
│     │                             │      }                              │
│     │                             │                                     │
│     │──── unified_search(         │                                     │
│     │       decision=chosen) ────▶│                                     │
│     │                             │                                     │
│     │◀──── 最終結果 ──────────────│                                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 三種協作模式

| 模式 | 適用場景 | MCP 行為 | Agent 負擔 |
|------|---------|---------|-----------|
| **Auto** | 簡單查詢 ("remimazolam") | 完全自主處理 | 無 |
| **Suggest** | 模糊查詢 ("covid treatment") | 返回建議選項 | 選擇 |
| **Delegate** | 複雜分析 (PICO 問題) | 返回原始資料 | 分析+決策 |

---

## 1. Query Enhancement（查詢增強）

### 何時需要 Agent 協助？

```python
class QueryComplexity(Enum):
    SIMPLE = "simple"        # "remimazolam" → 直接搜尋
    AMBIGUOUS = "ambiguous"  # "covid treatment" → 需要澄清範圍
    COMPLEX = "complex"      # PICO 問題 → 需要拆解

class QueryAnalyzer:
    def analyze(self, query: str) -> QueryAnalysisResult:
        complexity = self._assess_complexity(query)
        
        if complexity == QueryComplexity.SIMPLE:
            return QueryAnalysisResult(mode="auto", strategy=self._build_strategy(query))
        
        elif complexity == QueryComplexity.AMBIGUOUS:
            return QueryAnalysisResult(
                mode="suggest",
                suggestions=[
                    {"label": "COVID-19 藥物治療", "query": "COVID-19 drug therapy"},
                    {"label": "COVID-19 疫苗", "query": "COVID-19 vaccines"},
                ],
                question="您想搜尋哪個方向？"
            )
        
        else:  # COMPLEX
            return QueryAnalysisResult(
                mode="delegate",
                parsed_elements=self._extract_elements(query),
                question="這是一個 PICO 問題，請確認拆解是否正確？"
            )
```

### MCP 返回格式（需要決策時）

```json
{
    "status": "needs_input",
    "stage": "query_enhancement",
    "question": "查詢 'diabetes treatment' 範圍較廣，您想聚焦哪個面向？",
    "suggestions": [
        {
            "label": "Type 2 糖尿病藥物治療",
            "value": "type 2 diabetes mellitus drug therapy",
            "reason": "最常見的搜尋意圖"
        },
        {
            "label": "保持原查詢",
            "value": "diabetes treatment",
            "reason": "廣泛搜尋，結果較多"
        }
    ],
    "context": {
        "estimated_results": {"original": 50000, "narrowed": 5000}
    },
    "timeout_default": "diabetes treatment"
}
```

---

## 2. Multi-source Dispatch（轉包分發）

### 策略決策矩陣

```python
STRATEGY_MATRIX = {
    # 查詢類型 → (主要來源, 次要來源, 並行/序列)
    "doi_lookup": (["crossref"], ["pubmed"], "sequential"),
    "pmid_lookup": (["pubmed"], [], "sequential"),
    "gene_search": (["pubmed", "ncbi_gene"], ["openalex"], "parallel"),
    "drug_search": (["pubmed", "pubchem"], ["openalex"], "parallel"),
    "clinical_trial": (["pubmed", "clinicaltrials"], [], "parallel"),
    "preprint": (["biorxiv", "medrxiv"], ["openalex"], "parallel"),
    "open_access": (["core", "europe_pmc"], ["openalex"], "parallel"),
    "general_medical": (["pubmed"], ["crossref", "openalex"], "parallel"),
    "systematic_review": (["pubmed", "cochrane_via_epmc"], ["core"], "parallel"),
}
```

### Fallback 機制

```python
async def execute(self, plan: DispatchPlan, query: str) -> DispatchResult:
    results = {}
    errors = {}
    
    # 並行執行主要來源
    primary_tasks = [
        self._search_source(src, query, plan.timeout_per_source)
        for src in plan.primary_sources
    ]
    primary_results = await asyncio.gather(*primary_tasks, return_exceptions=True)
    
    # 處理結果
    for src, result in zip(plan.primary_sources, primary_results):
        if isinstance(result, Exception):
            errors[src] = str(result)
            # Fallback: 嘗試次要來源
            if plan.fallback_enabled and plan.secondary_sources:
                fallback_src = plan.secondary_sources[0]
                try:
                    results[fallback_src] = await self._search_source(
                        fallback_src, query, plan.timeout_per_source
                    )
                except Exception as e:
                    errors[fallback_src] = str(e)
        else:
            results[src] = result
    
    return DispatchResult(results=results, errors=errors)
```

---

## 3. Result Aggregation（結果彙整）

### 多維度排序演算法

借鑑 DW2-Cochrane-Chatbot 的品質評分模式：

```python
class ResultAggregator:
    def aggregate(self, results: Dict[str, List[Article]], query: str, 
                  ranking_preference: str = "balanced") -> AggregatedResult:
        
        # Step 1: 去重 (DOI/PMID/標題)
        unique_articles = self._deduplicate(results)
        
        # Step 2: 計算多維度分數
        scored_articles = []
        for article in unique_articles:
            scores = {
                "relevance": self._compute_relevance(article, query),  # 詞彙重疊
                "quality": self._compute_quality(article),              # PMID/DOI/文章類型
                "recency": self._compute_recency(article),              # 發表年份
                "impact": self._compute_impact(article),                # 引用數
                "source_trust": self._compute_source_trust(article),    # 來源可信度
            }
            final_score = self._weighted_score(scores, ranking_preference)
            scored_articles.append((article, scores, final_score))
        
        # Step 3: 排序
        scored_articles.sort(key=lambda x: x[2], reverse=True)
        
        # Step 4: 檢測品質斷崖 (Delta Cutoff)
        cutoff_index = self._detect_quality_drop(
            [s[2] for s in scored_articles], delta_threshold=0.15
        )
        
        return AggregatedResult(
            articles=[a[0] for a in scored_articles[:cutoff_index]],
            scores={...}
        )
```

### 排序偏好權重

```python
RANKING_WEIGHTS = {
    "balanced": {"relevance": 0.3, "quality": 0.25, "recency": 0.2, "impact": 0.15, "source_trust": 0.1},
    "latest": {"relevance": 0.2, "quality": 0.15, "recency": 0.5, "impact": 0.1, "source_trust": 0.05},
    "impactful": {"relevance": 0.2, "quality": 0.2, "recency": 0.1, "impact": 0.4, "source_trust": 0.1},
    "evidence": {"relevance": 0.25, "quality": 0.4, "recency": 0.15, "impact": 0.1, "source_trust": 0.1},
}
```

### 何時請求 Agent 協助？

```python
def should_request_agent_help(self, result: AggregatedResult) -> Optional[NeedsDecisionResponse]:
    
    # 情況 1: 結果過少
    if result.total_after_filter < 3:
        return NeedsDecisionResponse(
            stage="result_aggregation",
            question="搜尋結果較少，是否要擴展搜尋？",
            suggestions=[
                {"label": "擴展同義詞", "value": "expand_synonyms"},
                {"label": "放寬年份限制", "value": "relax_year"},
                {"label": "加入更多來源", "value": "add_sources"},
            ]
        )
    
    # 情況 2: 分數差異過大
    if self._high_variance(result.scores):
        return NeedsDecisionResponse(
            stage="result_aggregation",
            question="搜尋結果品質差異較大，您想如何處理？",
            suggestions=[
                {"label": "只保留高品質結果", "value": "filter_high_quality"},
                {"label": "顯示所有結果", "value": "show_all"},
            ]
        )
    
    return None  # 不需要協助
```

---

## 4. MCP 內建 Agent vs 外部 Agent

| 方案 | 優點 | 缺點 | 推薦場景 |
|------|------|------|---------|
| **外部 Agent（推薦）** | 輕量、靈活、可控成本 | 多輪交互、延遲 | 大多數情況 |
| **MCP 內建 LLM** | 單次調用、流暢體驗 | 成本高、複雜度高 | 簡單決策（如摘要） |
| **Hybrid** | 平衡兩者優點 | 實作複雜 | 未來優化方向 |

### 推薦模式：外部 Agent 協作

```python
class UnifiedSearchTool:
    async def unified_search(
        self,
        query: str,
        decision: Optional[str] = None,  # Agent 的決策回饋
        session_id: Optional[str] = None  # 多輪交互的 session
    ) -> Union[SearchResult, NeedsDecisionResponse]:
        
        # 如果是繼續之前的 session
        if session_id and decision:
            return await self._continue_session(session_id, decision)
        
        # Step 1: 分析查詢
        analysis = self.query_analyzer.analyze(query)
        if analysis.mode == "suggest":
            return NeedsDecisionResponse(session_id=..., **analysis.to_response())
        
        # Step 2: 分發搜尋
        dispatch_result = await self.dispatcher.execute(analysis.strategy.dispatch_plan, query)
        
        # Step 3: 彙整結果
        aggregated = self.aggregator.aggregate(dispatch_result.results, query)
        
        # Step 4: 檢查是否需要 Agent 協助
        help_needed = self.decision_maker.should_request_agent_help(aggregated)
        if help_needed:
            return help_needed
        
        # Step 5: 增強結果
        enriched = await self.enricher.enrich(aggregated)
        return SearchResult(articles=enriched.articles, metadata=...)
```

---

## 5. Spec 完整性自評

| 面向 | 狀態 | 說明 |
|------|------|------|
| 執行摘要 | ✅ | 問題、解決方案、關鍵決策 |
| 設計理念 | ✅ | 單一入口、智能分流、結果增強 |
| 競爭者分析 | ✅ | 商用工具、差異化定位 |
| API 資源 | ✅ | 已整合、待整合、不可用 |
| 架構設計 | ✅ | MCP 工具、查詢分析器 |
| 實作路線圖 | ✅ | Phase 1-3、工時估算 |
| 技術規格 | ✅ | 依賴、環境變數、程式碼結構 |
| 開源專案分析 | ✅ | 5 個專案、可借鑑模式 |
| **Agent-MCP 協作** | ✅ | **本文件** |
| 錯誤處理/Fallback | ✅ | Dispatch 章節 |
| 排序演算法 | ✅ | Aggregation 章節 |
| 測試策略 | 🔲 | 待補充 |
| 監控/可觀察性 | 🔲 | 待補充 |

### 待補充項目

1. **測試策略**
   - Unit tests for QueryAnalyzer, Dispatcher, Aggregator
   - Integration tests for cross-source search
   - E2E tests for Agent-MCP interaction

2. **監控/可觀察性**
   - Logging: 每個階段的輸入/輸出
   - Metrics: 搜尋延遲、來源成功率、Agent 協助頻率
   - Tracing: Session 追蹤

---

## 變更日誌

| 日期 | 版本 | 變更 |
|------|------|------|
| 2026-01-12 | 1.0.0 | 初始版本：Agent-MCP 協作模式設計 |
