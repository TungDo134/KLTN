# Vietnam Travel ChatBot - RAG + LLM + React

## Tổng quan

Dự án này là chatbot tư vấn du lịch Việt Nam, được xây dựng quanh backend Retrieval-Augmented Generation (RAG) và frontend React. Runtime đang hoạt động hiện tại là một **history-aware RAG chatbot**:

```text
User question
 -> FastAPI /chat
 -> RAGInference
 -> optional history-aware query rewrite
 -> Multi-query hybrid retrieval
 -> Cross-encoder reranking
 -> LLM answer generation
 -> React / Gradio response
```

Repository cũng có các module khung cho recommendation, route planning và crawler/ingestion workflow. Các module này quan trọng cho hướng phát triển của dự án, nhưng hiện chưa được nối hoàn chỉnh vào runtime.

## Trạng thái hiện tại

| Khu vực               | Trạng thái              | Ghi chú                                                                            |
| --------------------- | ----------------------- | ---------------------------------------------------------------------------------- |
| FastAPI backend       | Đang hoạt động          | Endpoint chính là `POST /chat`.                                                    |
| RAG retrieval         | Đang hoạt động          | Dùng ChromaDB, vector search, BM25, multi-query retrieval và cross-encoder rerank. |
| Chat history          | Đang hoạt động          | `RAGInference` lưu lịch sử hội thoại ngắn trong memory theo session.               |
| React frontend        | Đang hoạt động          | Vite + React UI gọi backend `/chat`.                                               |
| Place data ingestion  | Đang dùng               | Dữ liệu JSON trong `places_data` đã được ingest vào Chroma.                        |
| Recommendation module | Skeleton                | Class đã có, các method vẫn đang`TODO/pass`.                                       |
| Planning module       | Skeleton                | Graph/route/schedule facade đã có, các method vẫn đang `TODO/pass`.                |
| Crawler module        | Skeleton / data support | Cấu trúc folder và data đã có, nhiều crawler/validator/ingest method vẫn là TODO.  |

## Tech Stack

- Backend: FastAPI, LangChain, ChromaDB
- LLM providers: mặc định dùng NVIDIA NIM, có adapter cho Groq, Gemini và Ollama
- Retrieval: Chroma vector search + BM25 hybrid retriever
- Reranking: HuggingFace CrossEncoder (`BAAI/bge-reranker-v2-m3`)
- Frontend: React 19, Vite 7, TailwindCSS 4, Axios, ReactFlow
- Data: place JSON files và document/text sources

## Cấu trúc repository

```text
Project/
├── BE_ChatBot/
│   ├── src/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── schemas.py
│   │   │   ├── base_embed_model.py
│   │   │   ├── base_llm_model.py
│   │   │   └── llm_container.py
│   │   ├── pipeline/
│   │   │   ├── inference.py
│   │   │   ├── orchestrator.py
│   │   │   ├── query_analyzer.py
│   │   │   ├── rag_pipline.py
│   │   │   └── reranker.py
│   │   ├── recommend/
│   │   │   ├── base_recommender.py
│   │   │   ├── content_based.py
│   │   │   ├── location_based.py
│   │   │   └── hybrid_recommender.py
│   │   ├── planning/
│   │   │   ├── graph_builder.py
│   │   │   ├── route_optimizer.py
│   │   │   ├── scheduler.py
│   │   │   └── planner.py
│   │   ├── eval/
│   │   ├── prompts/
│   │   │   └── system_prompt.md
│   │   ├── source_data/
│   │   │   ├── docs/
│   │   │   └── places_data/
│   │   └── static/
│   ├── build_rag_vector_db.ipynb
│   ├── README_BE.md
│   ├── Testing.py
│   ├── run.bat
│   └── requirements.txt
├── FE_ChatBot/
│   ├── src/
│   │   ├── api/
│   │   ├── services/
│   │   ├── features/
│   │   ├── helper/
│   │   ├── ui/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
└── CRAWL_DATA_CHATBOT/
    ├── crawlers/
    ├── validators/
    ├── ingest/
    ├── data/
    ├── data_pipeline.py
    └── README_CRAWL_DATA_CHATBOT.md
```

## Flow runtime của backend

### 1. FastAPI entry point

`BE_ChatBot/src/main.py` tạo FastAPI app và khởi tạo `RAGInference` một lần trong lifespan của app.

```text
uvicorn src.main:app --reload
 -> lifespan()
 -> app.state.inference = RAGInference()
```

Endpoint API chính là:

```text
POST /chat
body: { "prompt": "..." }
response: { "response": "..." }
```

### 2. RAGInference

`BE_ChatBot/src/pipeline/inference.py` là runtime coordinator hiện tại.

Module này thực hiện các bước:

1. Load main LLM.
2. Load một rewrite LLM riêng.
3. Tạo `TripOrchestrator`.
4. Giữ chat history trong memory theo `session_id`.
5. Rewrite câu hỏi follow-up thành câu hỏi standalone khi có history.
6. Retrieve và rerank documents thông qua orchestrator.
7. Build final prompt từ system prompt, history, retrieved context và câu hỏi gốc.
8. Gọi main LLM và trả về answer.

### 3. TripOrchestrator

`BE_ChatBot/src/pipeline/orchestrator.py` được thiết kế để nối RAG, recommendation, planning và generation.

Runtime path hiện tại là:

```text
raw_query
 -> QueryAnalyzer.extract(raw_query)
 -> MultiQueryRetriever.ainvoke(raw_query)
 -> CrossEncoderReranker.compress_documents(...)
 -> return reranked_docs
```

Điểm quan trọng: function hiện đang trả về `reranked_docs` sớm. Các bước bên dưới đã có trong comment/TODO nhưng chưa active:

```text
docs -> Place[]
 -> metadata Reranker
 -> HybridRecommender
 -> TripPlanner
 -> LLM trip-plan generation
```

### 4. RAG pipeline

`BE_ChatBot/src/pipeline/rag_pipline.py` xử lý core retrieval logic:

- `RAGStorage` load ChromaDB từ `PERSIST_DIRECTORY`.
- `get_hybrid_retriever()` kết hợp:
  - Chroma vector retriever
  - BM25 retriever được build từ toàn bộ Chroma documents
- `MultiQueryRetriever` yêu cầu LLM tạo query variations.
- Duplicate documents được loại bỏ.
- BGE cross-encoder rerank các retrieved documents.
- `RerankerConfig.TOP_N` kiểm soát số documents được giữ lại sau rerank.

Reranker model hiện tại là:

```text
BAAI/bge-reranker-v2-m3
```

## Nguồn dữ liệu

### Document data

`BE_ChatBot/src/source_data/docs/` chứa raw text/PDF-style documents dùng cho RAG pipeline.

### Place data

`BE_ChatBot/src/source_data/places_data/` chứa các merged JSON place datasets, gồm:

```text
dalat_merged.json
danang_merged.json
hanoi_merged.json
hcm_merged.json
nhatrang_merged.json
vungtau_merged.json
```

Các file này chứa place records với các field như:

- `name`
- `region`
- `tags`
- `rating`
- `description`
- opening hours / duration / fee metadata nếu có

Dữ liệu này đã được ingest vào Chroma để test RAG. Vì nhiều generated descriptions có dạng template, chất lượng answer phụ thuộc khá nhiều vào metadata và reranker settings. Trong thực tế, `TOP_N` khoảng `5-8` thường cho câu trả lời gọn và sạch hơn so với việc trả về quá nhiều địa điểm tương tự nhau.

## Recommendation và Planning modules

Các module này là một phần của travel-planning pipeline dự kiến, hiện đang trong quá trình xây dựng.

### Recommendation

Files:

- `BE_ChatBot/src/recommend/base_recommender.py`
- `BE_ChatBot/src/recommend/content_based.py`
- `BE_ChatBot/src/recommend/location_based.py`
- `BE_ChatBot/src/recommend/hybrid_recommender.py`

Flow dự kiến:

```text
Place[]
 -> ContentBasedRecommender
 -> LocationBasedRecommender
 -> HybridRecommender
 -> RecommendResult
```

Trạng thái hiện tại: phần lớn scoring methods vẫn là `TODO/pass`.

### Planning

Files:

- `BE_ChatBot/src/planning/graph_builder.py`
- `BE_ChatBot/src/planning/route_optimizer.py`
- `BE_ChatBot/src/planning/scheduler.py`
- `BE_ChatBot/src/planning/planner.py`

Flow dự kiến:

```text
RecommendResult
 -> GraphBuilder.build()
 -> RouteOptimizer.optimize()
 -> Scheduler.schedule()
 -> TripPlan
```

Trạng thái hiện tại: facade và class structure đã có, nhưng các method chính vẫn là `TODO/pass`.

## Crawler / Data Pipeline

`CRAWL_DATA_CHATBOT` là một data-support module riêng, được thiết kế để collect, validate, transform và ingest place data.

Flow dự kiến:

```text
Crawler
 -> schema validation
 -> text_builder
 -> ChromaDB ingestion
 -> BE_ChatBot RAG retrieval
```

Trạng thái hiện tại: chưa up code implement, nhưng data trong `CRAWL_DATA_CHATBOT/data/dataCrawl` đã xài được.

## Cài đặt

### Backend

```powershell
cd D:\KLTN\Project\BE_ChatBot
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Tạo file `.env` trong `BE_ChatBot/`:

```env
NVIDIA_API_KEY=nvapi-...
HF_TOKEN=hf_...

LLM_PROVIDER=nvidia
REWRITE_LLM_PROVIDER=groq

PERSIST_DIRECTORY=src/db/chroma_db
SOURCE_DATA=src/source_data/docs
JSON_DATA_DIR=src/source_data/places_data
SYSTEM_PROMPT=src/prompts/system_prompt.md

FRONTEND_URL=http://localhost:5173
```

Hãy chỉnh lại các path cho khớp với Chroma/data folders trên máy của bạn.

### Chạy backend

Chạy từ folder `BE_ChatBot/`:

```powershell
uvicorn src.main:app --reload
```

Không chạy trực tiếp bằng `python src/main.py`. `main.py` dùng package imports, nên direct execution có thể gây lỗi:

```text
ImportError: attempted relative import with no known parent package
```

### Frontend

```powershell
cd D:\KLTN\Project\FE_ChatBot
npm install
npm run dev
```

Frontend URL mặc định:

```text
http://localhost:5173
```

## API

### Chat

```http
POST http://127.0.0.1:8000/chat
Content-Type: application/json
```

Request:

```json
{
  "prompt": "Ở Đà Lạt có địa điểm nào phù hợp để chill hoặc thư giãn?"
}
```

Response:

```json
{
  "response": "..."
}
```

### Docs

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/redoc
```

## Câu hỏi test RAG gợi ý

Dùng các câu sau để kiểm tra Chroma retrieval và reranking có hoạt động ổn trên `places_data` không:

```text
Ở Đà Lạt có địa điểm nào phù hợp để chill hoặc thư giãn?
Trả về tối đa 5 địa điểm, mỗi địa điểm gồm tên, tags, rating và lý do ngắn dựa trên dữ liệu.
```

```text
Tôi muốn đi Hà Nội để tham quan các địa điểm văn hóa hoặc tâm linh, có gợi ý nào không?
```

```text
Ở Nha Trang có những địa điểm biển hoặc nơi tham quan nổi bật nào?
```

Nếu model bắt đầu tự thêm các mô tả giàu chi tiết nhưng không tồn tại trong source data, hãy siết generation prompt:

```text
Chỉ dùng thông tin có trong dữ liệu. Không tự thêm chi tiết ngoài context.
```

## Lỗi thường gặp

### `ImportError: attempted relative import with no known parent package`

Chạy backend bằng Uvicorn từ folder `BE_ChatBot/`:

```powershell
cd D:\KLTN\Project\BE_ChatBot
uvicorn src.main:app --reload
```

### `PERSIST_DIRECTORY environment variable is not set`

Kiểm tra `.env` và đảm bảo `PERSIST_DIRECTORY` trỏ đúng tới ChromaDB folder.

### CUDA requirement

Một số backend modules hiện đang yêu cầu CUDA:

- `core/base_embed_model.py`
- `pipeline/rag_pipline.py`

Nếu CUDA không khả dụng, import/runtime có thể fail sớm. Hoặc chạy trên môi trường có CUDA, hoặc chỉnh lại device logic trước khi dùng CPU.

### Repetitive RAG answers

Nếu câu trả lời lặp lại nhiều địa điểm tương tự nhau:

- giảm `RerankerConfig.TOP_N`
- yêu cầu trả về tối đa 5 places
- yêu cầu model hiển thị `name`, `tags` và `rating`
- tránh yêu cầu model diễn giải dài nếu descriptions trong data có dạng template

## Ghi chú phát triển

- Graph và onboarding context được generate bằng Understand Anything trong `.understand-anything/`.
- `BE_ChatBot/src/contex_kltn.md` có vẻ là tài liệu giải thích thủ công/onboarding cho backend flow.
- Hiện dự án đang ưu tiên chất lượng RAG answer hơn là complete planning automation.
- Giữ README khớp với code đã implement. Recommendation/planning modules khá tiềm năng, nhưng nên tiếp tục được document như roadmap cho tới khi các TODO methods được implement và nối vào `TripOrchestrator.run()`.

## License

Dự án phục vụ mục đích học thuật / khóa luận tốt nghiệp.
