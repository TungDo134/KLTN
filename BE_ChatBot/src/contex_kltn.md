**Onboarding BE_ChatBot**

`BE_ChatBot` là backend FastAPI cho chatbot RAG du lịch. Kiến trúc trong graph chia backend thành 4 nhóm chính: `Backend API`, `Backend Core`, `RAG Pipeline`, `Recommendation and Planning`.

Điểm quan trọng trước khi đọc code: flow đang chạy hiện tại là **history-aware RAG chatbot**. Phần recommend + planning đã có khung class/file, nhưng nhiều method vẫn `TODO/pass` và chưa được nối vào runtime đầy đủ.

**1. Entry Point**

File bắt đầu nên đọc: [main.py](D:/KLTN/Project/BE_ChatBot/src/main.py:28)

Các class/function chính:
- `lifespan(app)` khởi tạo `RAGInference()` một lần khi app start.
- `ChatRequest` nhận body `{ prompt: str }`.
- `ChatResponse` trả `{ response: str }`.
- `get_inference_service()` lấy `app.state.inference`; nếu chưa sẵn sàng thì trả `503`.
- `chat()` là endpoint `POST /chat`.
- `gradio_predict()` phục vụ Gradio UI mounted tại `/`.

Flow tại API:

```text
POST /chat
 -> ChatRequest.prompt
 -> get_inference_service()
 -> RAGInference.predict_async(prompt)
 -> ChatResponse(response=...)
```

**2. Backend Core**

Các file nền tảng nằm trong `src/core`.

[schemas.py](D:/KLTN/Project/BE_ChatBot/src/core/schemas.py:14) định nghĩa DTO/dataclass dùng xuyên suốt pipeline:
- `TripRequest`: query đã được LLM extract, gồm `region`, `days`, `tags`, `budget`, `start_date`.
- `Place`: địa điểm lấy từ docs/ChromaDB, có `lat`, `lon`, `tags`, `rating`, `rag_score`, `rerank_score`, `recommend_score`.
- `RecommendResult`: output của recommender.
- `ScheduledPlace`, `DayPlan`, `TripPlan`: output của planning.

[base_llm_model.py](D:/KLTN/Project/BE_ChatBot/src/core/base_llm_model.py:27) là factory LLM:
- `LLMProvider`: enum provider.
- `_NvidiaLLM`, `_OllamaLLM`, `_GeminiLLM`, `_GroqLLM`: adapter từng provider.
- `get_llm_model()` tạo LangChain chat model.

[base_embed_model.py](D:/KLTN/Project/BE_ChatBot/src/core/base_embed_model.py:26) là factory embedding:
- `EmbeddingProvider`
- `get_embedding_model()`

[llm_container.py](D:/KLTN/Project/BE_ChatBot/src/core/llm_container.py:16) là singleton/cache layer:
- `_load_system_prompt()` đọc prompt từ env `SYSTEM_PROMPT`.
- `get_llm()` cache LLM theo provider/model/temperature.
- `get_system_prompt()`
- `get_model_info()`

**3. RAG Runtime Pipeline**

File runtime chính: [inference.py](D:/KLTN/Project/BE_ChatBot/src/pipeline/inference.py:37)

Class chính:
- `RAGInference`

Khi khởi tạo:
```text
RAGInference.__init__()
 -> get_llm()                         # LLM chính trả lời user
 -> get_llm(REWRITE_LLM_PROVIDER)     # LLM rewrite câu hỏi theo history
 -> TripOrchestrator(llm=self.llm)
 -> get_system_prompt()
 -> init memory history defaultdict(list)
```

Khi user hỏi:
```text
predict_async(question, session_id="default")
 -> _get_history(session_id)
 -> _rewrite_question(question, history)
 -> orchestrator.run(search_question)
 -> context = join(reranked_docs.page_content)
 -> _build_messages(history, context, original_question)
 -> self.llm.ainvoke(messages)
 -> _save_turn(session_id, question, answer)
 -> return answer
```

Nói ngắn gọn: `RAGInference` là lớp điều phối cho chatbot thực tế: quản lý history, rewrite query, gọi RAG retrieval/rerank, build prompt, gọi LLM trả lời.

**4. Orchestrator**

File: [orchestrator.py](D:/KLTN/Project/BE_ChatBot/src/pipeline/orchestrator.py:31)

Class chính:
- `TripOrchestrator`

Trong `__init__()` nó tạo:
- `QueryAnalyzer`
- `Reranker`
- `HybridRecommender`
- `TripPlanner`
- `RAGStorage().get_multi_query_retriever()` trả về:
  - `MultiQueryRetriever`
  - `CrossEncoderReranker`

Flow comment mô tả đầy đủ:

```text
raw_query
 -> QueryAnalyzer -> TripRequest
 -> RAGStorage -> docs
 -> Reranker -> Place[]
 -> HybridRecommender -> RecommendResult
 -> TripPlanner -> TripPlan
 -> LLM Generation -> response
```

Nhưng flow đang chạy thực tế trong `run()` hiện tại:

```text
raw_query
 -> QueryAnalyzer.extract(raw_query)
 -> retriever.ainvoke(raw_query)
 -> cross_encoder_reranker.compress_documents(raw_docs, raw_query)
 -> return reranked_docs
```

Điểm cần chú ý: [orchestrator.py](D:/KLTN/Project/BE_ChatBot/src/pipeline/orchestrator.py:78) đang `return reranked_docs` sớm. Các bước `_docs_to_places`, metadata rerank, recommend, planning, generation phía dưới vẫn là TODO/commented.

**5. Query Analyzer**

File: [query_analyzer.py](D:/KLTN/Project/BE_ChatBot/src/pipeline/query_analyzer.py:31)

Class:
- `QueryAnalyzer`

Mục tiêu thiết kế:
```text
raw natural language query
 -> LLM extract JSON
 -> TripRequest
```

Nó định extract:
- `region`
- `days`
- `tags`
- `budget`
- `start_date`

Nhưng hiện tại:
- `extract()` đang `pass`
- `_parse_response()` đang `pass`

Rủi ro runtime: `TripOrchestrator.run()` gọi `await self.analyzer.extract(raw_query)`. Nếu code chạy đúng nhánh này, `trip_request` sẽ là `None`, nhưng hiện tại chưa dùng tiếp vì flow return docs sớm. Nếu sau này bật recommend/planning mà chưa implement `QueryAnalyzer`, sẽ lỗi.

**6. RAG Storage + Multi Query**

File lớn nhất và phức tạp nhất: [rag_pipline.py](D:/KLTN/Project/BE_ChatBot/src/pipeline/rag_pipline.py:60)

Các phần chính:

`load_documents()`:
- đọc `.pdf` và `.txt` trong `SOURCE_DATA`
- dùng `PyPDFLoader`, `TextLoader`

`split_documents()`:
- dùng `RecursiveCharacterTextSplitter`
- chunk size `1000`, overlap `150`

`create_vector_store()`:
- tạo/load ChromaDB
- collection name `kltn_chatbot`
- insert theo batch `100`
- lọc trùng theo `source`

`QueryVariations`:
- Pydantic schema cho output multi-query LLM.

`MultiQueryRetriever`:
```text
original query
 -> LLM sinh 3 query variations
 -> mỗi variation gọi hybrid retriever
 -> gom docs
 -> deduplicate theo page_content prefix
 -> return unique docs
```

`RAGStorage`:
- đọc `PERSIST_DIRECTORY`
- tạo embedding model
- `get_retriever()` cho vector-only retrieval
- `get_hybrid_retriever()` kết hợp:
  - Chroma vector retriever, weight `0.6`
  - BM25 retriever, weight `0.4`
- `_build_multi_query_retriever()` tạo `MultiQueryRetriever`
- `_build_cross_encoder_reranker()` tạo BGE reranker `BAAI/bge-reranker-v2-m3`
- `get_multi_query_retriever()` trả `(retriever, reranker)`

Điểm cần cẩn thận: đầu file có check GPU:
```python
if not torch.cuda.is_available():
    raise EnvironmentError(...)
```
Nghĩa là import `rag_pipline.py` trên máy không có CUDA có thể fail ngay, trước cả khi app chạy.

**7. Metadata Reranker**

File: [reranker.py](D:/KLTN/Project/BE_ChatBot/src/pipeline/reranker.py:18)

Class:
- `Reranker`

Thiết kế dự kiến:
```text
Place[]
 -> hard filter theo region/budget/opening hours
 -> tính rerank_score = rag_score + rating + tag overlap
 -> sort top_k
```

Hiện tại:
- `rerank()` đang `pass`
- `_hard_filter()` đang `pass`

Nó chưa nằm trong runtime hiện tại vì orchestrator return docs trước khi convert sang `Place`.

**8. Recommendation Module**

Files:
- [base_recommender.py](D:/KLTN/Project/BE_ChatBot/src/recommend/base_recommender.py:10)
- [content_based.py](D:/KLTN/Project/BE_ChatBot/src/recommend/content_based.py:19)
- [location_based.py](D:/KLTN/Project/BE_ChatBot/src/recommend/location_based.py:17)
- [hybrid_recommender.py](D:/KLTN/Project/BE_ChatBot/src/recommend/hybrid_recommender.py:16)

Classes:
- `BaseRecommender`: abstract strategy base.
- `ContentBasedRecommender`: dự kiến tính Jaccard similarity giữa `request.tags` và `place.tags`.
- `LocationBasedRecommender`: dự kiến tính proximity bằng centroid + Haversine.
- `HybridRecommender`: combine content `0.6` + location `0.4`.

Flow thiết kế:

```text
Place[]
 -> ContentBasedRecommender.score()
 -> LocationBasedRecommender.score()
 -> cộng recommend_score có trọng số
 -> sort top_k
 -> RecommendResult
```

Hiện trạng: các method score/recommend/filter vẫn `TODO/pass`.

**9. Planning Module**

Files:
- [graph_builder.py](D:/KLTN/Project/BE_ChatBot/src/planning/graph_builder.py:15)
- [route_optimizer.py](D:/KLTN/Project/BE_ChatBot/src/planning/route_optimizer.py:16)
- [scheduler.py](D:/KLTN/Project/BE_ChatBot/src/planning/scheduler.py:15)
- [planner.py](D:/KLTN/Project/BE_ChatBot/src/planning/planner.py:25)

Classes:
- `GraphBuilder`: dự kiến build weighted graph giữa các `Place`.
- `RouteOptimizer`: dự kiến optimize route bằng greedy/dijkstra/2-opt.
- `Scheduler`: dự kiến chia địa điểm theo ngày và gán giờ.
- `TripPlanner`: facade điều phối toàn bộ planning.

Flow thiết kế:

```text
RecommendResult
 -> GraphBuilder.build()
 -> RouteOptimizer.optimize()
 -> Scheduler.split_places_into_days()
 -> Scheduler.schedule()
 -> TripPlan
```

Hiện trạng: hầu hết method chính vẫn `TODO/pass`, nên planning chưa chạy thực tế.

**10. Evaluation**

Files:
- [config.py](D:/KLTN/Project/BE_ChatBot/src/eval/config.py:1)
- [ground_truth_builder.py](D:/KLTN/Project/BE_ChatBot/src/eval/ground_truth_builder.py:26)
- [metrics.py](D:/KLTN/Project/BE_ChatBot/src/eval/metrics.py:10)
- `rag_eval.ipynb`

Vai trò:
- build ground truth bằng LLM
- tính `precision@k`, `dcg`, `ndcg`, average metrics
- notebook để chạy evaluation pipeline

Đây là nhánh phụ, không nằm trong request `/chat` runtime.

**11. Source Data + Vector DB**

Data input:
- `src/source_data/docs/*.txt`
- `src/source_data/docs/*.pdf`

Vector DB:
- cấu hình qua `PERSIST_DIRECTORY`
- build bằng [build_rag_vector_db.ipynb](D:/KLTN/Project/BE_ChatBot/build_rag_vector_db.ipynb)

Runtime retrieval sẽ load ChromaDB từ `PERSIST_DIRECTORY`; nếu DB chưa build hoặc env sai, RAG sẽ fail khi khởi tạo `RAGStorage`.

**12. Flow Tổng Thể Hiện Tại**

```text
User / React / Gradio
 -> FastAPI POST /chat
 -> main.chat()
 -> RAGInference.predict_async()
 -> lấy history
 -> rewrite question nếu có history
 -> TripOrchestrator.run()
 -> MultiQueryRetriever sinh query variations
 -> Hybrid Search: Chroma vector + BM25
 -> deduplicate docs
 -> CrossEncoder rerank top docs
 -> RAGInference build context từ docs
 -> LLM generate answer
 -> save chat history
 -> return ChatResponse
```

**13. Flow Dự Kiến Khi Hoàn Thiện Recommend + Planning**

```text
User query
 -> QueryAnalyzer.extract()
 -> TripRequest

RAG:
 -> MultiQueryRetriever
 -> CrossEncoder rerank
 -> docs_to_places()
 -> Place[]

Recommendation:
 -> metadata Reranker
 -> HybridRecommender
 -> RecommendResult

Planning:
 -> GraphBuilder
 -> RouteOptimizer
 -> Scheduler
 -> TripPlan

Generation:
 -> _build_generation_prompt()
 -> LLM response
 -> return { text, trip_plan }
```

**14. Những Điểm Nên Đọc Theo Thứ Tự**

1. [main.py](D:/KLTN/Project/BE_ChatBot/src/main.py:28): app lifecycle + endpoint.
2. [inference.py](D:/KLTN/Project/BE_ChatBot/src/pipeline/inference.py:37): flow chatbot thực tế.
3. [orchestrator.py](D:/KLTN/Project/BE_ChatBot/src/pipeline/orchestrator.py:31): nơi nối các module.
4. [rag_pipline.py](D:/KLTN/Project/BE_ChatBot/src/pipeline/rag_pipline.py:220): retrieval, multi-query, Chroma, BM25, reranker.
5. [schemas.py](D:/KLTN/Project/BE_ChatBot/src/core/schemas.py:14): data model toàn hệ thống.
6. [hybrid_recommender.py](D:/KLTN/Project/BE_ChatBot/src/recommend/hybrid_recommender.py:16) và [planner.py](D:/KLTN/Project/BE_ChatBot/src/planning/planner.py:25): hiểu roadmap recommend/planning, nhưng nhớ là chưa chạy.

**15. Hotspots / Rủi Ro Khi Dev**

- [rag_pipline.py](D:/KLTN/Project/BE_ChatBot/src/pipeline/rag_pipline.py:1) là hotspot lớn nhất: nhiều dependency nặng, ChromaDB, BM25, LLM structured output, CrossEncoder, CUDA check.
- [orchestrator.py](D:/KLTN/Project/BE_ChatBot/src/pipeline/orchestrator.py:78) có `return reranked_docs` sớm; đừng assume recommend/planning đã hoạt động.
- [query_analyzer.py](D:/KLTN/Project/BE_ChatBot/src/pipeline/query_analyzer.py:39), [reranker.py](D:/KLTN/Project/BE_ChatBot/src/pipeline/reranker.py:23), [hybrid_recommender.py](D:/KLTN/Project/BE_ChatBot/src/recommend/hybrid_recommender.py:25), [planner.py](D:/KLTN/Project/BE_ChatBot/src/planning/planner.py:38) đều còn TODO.
- Env rất quan trọng: `LLM_PROVIDER`, `REWRITE_LLM_PROVIDER`, `NVIDIA_API_KEY`, `PERSIST_DIRECTORY`, `SOURCE_DATA`, `SYSTEM_PROMPT`, `FRONTEND_URL`.
- Import style đang lẫn giữa relative import trong `main.py` và absolute `src...` trong các module khác; khi chạy cần đúng working directory/module path.

Nếu muốn biến hướng dẫn này thành tài liệu team, nên lưu thành `BE_ChatBot/docs/ONBOARDING.md` hoặc `docs/BE_CHATBOT_ONBOARDING.md` rồi commit vào repo.