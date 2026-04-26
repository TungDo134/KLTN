# Vietnam Travel ChatBot — RAG + LLM + Recommend + Planning + React

## ✨ Overview

This repo is an intelligent travel consulting chatbot that combines the power of Generative AI with optimized planning systems. The project leverages the **latest state-of-the-art** to deliver a highly personalized experience for travelers

- **Core AI:** `Llama 3.1` (via **NVIDIA NIM**)
- **Knowledge Base:** `RAG` + `ChromaDB`
- **Intelligence:** `Recommender System` + `Graph-based Planning`
- **Backend:** `FastAPI`
- **Frontend:** `React` + `Vite` + `TailwindCSS`

## 🗺️ Roadmap

[ ] `Recommend + Planning` Module: Currently a skeleton framework slated for intensive development. The underlying algorithms are provisional and subject to change as we optimize the system logic in upcoming phases.

---

## 📁 Project Structure

```
Project/
├── BE_ChatBot/                              ← Backend (FastAPI + Full Pipeline)
│   ├── src/
│   │   ├── core/                            ← Shared schemas / DTOs
│   │   │   ├── schemas.py                   ← TripRequest, Place, TripPlan, DayPlan, ...
│   │   │   ├── base_embed_model.py          ← Factory: get_embedding_model() + EmbeddingProvider
│   │   │   ├── base_llm_model.py            ← Factory Class to create LLM models (NVIDIA, GROQ, GEMINI, OLLAMA)
│   │   │   └── llm_container.py             ← Singleton for loading LLM & System Prompt
│   │   │
│   │   ├── pipeline/                        ← Orchestration layer
│   │   │   ├── orchestrator.py              ← Master pipeline (6 bước đầy đủ)
│   │   │   ├── query_analyzer.py            ← LLM extract: raw query → TripRequest
│   │   │   ├── reranker.py                  ← RAG top-20 → multi-signal rerank → top-15
│   │   │   ├── inference.py                 ← Backward-compatible wrapper cho FastAPI
│   │   │   ├── llm.py                       ← (UNUSED) Change to llm_container.py
│   │   │   └── rag_pipline.py               ← Ingestion & Retriever (ChromaDB)
│   │   │
│   │   ├── recommend/                       ← Recommender System module
│   │   │   ├── base_recommender.py          ← Abstract base (Strategy Pattern)
│   │   │   ├── content_based.py             ← Content-Based: Jaccard similarity trên tags
│   │   │   ├── location_based.py            ← Location-Based: Haversine centroid proximity
│   │   │   └── hybrid_recommender.py        ← Hybrid: content (0.6) + location (0.4)
│   │   │
│   │   ├── planning/                        ← Graph-based Planning module
│   │   │   ├── graph_builder.py             ← Xây weighted graph (adjacency dict)
│   │   │   ├── route_optimizer.py           ← Greedy / Dijkstra / 2-opt
│   │   │   ├── scheduler.py                 ← Chia ngày + gán giờ HH:MM
│   │   │   └── planner.py                   ← Facade: Graph → Route → Schedule → TripPlan
│   │   │
│   │   ├── model/
│   │   │   └── embeddings/                  ← HuggingFace embedding model cache
│   │   ├── prompts/
│   │   │   └── system_prompt.md             ← System prompt cho LLM
│   │   ├── db/
│   │   │   └── chroma_db/                   ← ChromaDB vector store (auto-created)
│   │   └── source_data/
│   │       └── docs/                        ← ⬅ Đặt file PDF/TXT tại đây
│   │
│   ├── build_rag_vector_db.ipynb            ← Chạy một lần để tạo vector DB
│   ├── run.bat                              ← Windows: kill process cũ & restart
│   ├── .env                                 ← Tạo từ .env.example
│   └── requirements.txt
│
└── FE_ChatBot/                              ← Frontend (React + Vite + TailwindCSS)
    ├── src/
    │   ├── api/
    │   │   └── axiosClient.js               ← Axios instance (baseURL + auth interceptor)
    │   ├── services/
    │   │   └── chatApi.js                   ← API calls (POST /chat)
    │   ├── features/
    │   │   ├── navigation/
    │   │   │   ├── Sidebar.jsx
    │   │   │   ├── TopBar.jsx
    │   │   │   ├── ModelDropdown.jsx
    │   │   │   └── PlusMenu.jsx
    │   │   └── result-visualize/
    │   │       ├── ResultSwitcher.jsx        ← Toggle Text / Timeline / Mindmap
    │   │       ├── BotResult.jsx
    │   │       ├── TextResult.jsx
    │   │       ├── TimelineResult.jsx
    │   │       └── MindmapResult.jsx
    │   ├── ui/
    │   │   ├── AppLayout.jsx
    │   │   ├── ChatArea.jsx
    │   │   ├── ChatInput.jsx
    │   │   └── Message.jsx
    │   ├── helper/
    │   │   └── extractJsonFromText.js       ← Parse JSON trip plan từ LLM response
    │   ├── App.jsx
    │   ├── main.jsx
    │   └── index.css
    ├── index.html
    ├── vite.config.js
    └── package.json
```

---

## 🏗️ System Architecture

```
User (Browser)
    ↓  http://localhost:5173
React Frontend (Vite)
    ├── ChatArea → ChatInput → gửi prompt
    ↓  POST http://127.0.0.1:8000/chat
FastAPI Backend
    ↓
TripOrchestrator.run()
    │
    ├── [1] QueryAnalyzer
    │       └── LLM extract: region, days, tags, budget → TripRequest
    │
    ├── [2] RAGStorage (ChromaDB)
    │       └── Embedding search → top-20 Place
    │
    ├── [3] Reranker
    │       └── rag_score + rating + tag_overlap → top-15 Place
    │
    ├── [4] HybridRecommender
    │       ├── ContentBasedRecommender  (Example: Jaccard similarity, weight 0.6)
    │       └── LocationBasedRecommender (Example: Haversine proximity, weight 0.4)
    │           → top-10 Place
    │
    ├── [5] TripPlanner
    │       ├── GraphBuilder      → weighted adjacency graph
    │       ├── RouteOptimizer    → Example: Greedy Nearest Neighbor / Dijkstra
    │       └── Scheduler         → DayPlan với giờ HH:MM cụ thể → TripPlan
    │
    └── [6] LLM Generation
            └── TripPlan → natural language response (tiếng Việt) + JSON
                ↓
JSON Response → Frontend
    ├── TextResult      (plain text)
    ├── TimelineResult  (structured trip plan)
    └── MindmapResult   (node graph)
```

---

## ⚙️ System Requirements

| Yêu cầu  | Chi tiết                                                            |
| -------- | ------------------------------------------------------------------- |
| Python   | >= 3.10                                                             |
| pip      | >= 23.0                                                             |
| Node.js  | >= 18.x                                                             |
| npm      | >= 9.x                                                              |
| RAM      | >= 4GB                                                              |
| API Key  | [NVIDIA NIM](https://build.nvidia.com) (bắt buộc)                   |
| HF Token | [HuggingFace](https://huggingface.co/settings/tokens) (khuyến nghị) |

---

## 🚀 Hướng Dẫn Cài Đặt

### Bước 1 — Clone Project

```bash
https://github.com/TungDo134/KLTN.git
cd KLTN
```

---

## 🐍 Backend Setup (BE_ChatBot)

### Bước 2 — Tạo & Kích hoạt Virtual Environment

```bash
cd BE_ChatBot

# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

> ✅ Sau khi kích hoạt, terminal sẽ hiển thị `(.venv)` ở đầu dòng.

---

### Bước 3 — Cài Đặt Dependencies

```bash
pip install -r requirements.txt
```

> ⏳ Lần đầu có thể mất 3–5 phút (LangChain, ChromaDB, HuggingFace...).

---

### Bước 4 — Tạo file `.env`

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Mở `.env` và điền thông tin:

```env
# === BẮT BUỘC ===
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxx   # Lấy tại https://build.nvidia.com

# === KHUYẾN NGHỊ ===
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx            # Lấy tại https://huggingface.co/settings/tokens

# === CẤU HÌNH ĐƯỜNG DẪN ===
PERSIST_DIRECTORY=db/
SOURCE_DATA=src/source_data/docs

# === SYSTEM PROMPT (tùy chọn) ===
SYSTEM_PROMPT=src/prompts/system_prompt.md

# === FRONTEND URL (cho CORS) ===
FRONTEND_URL=http://localhost:5173
```

---

### Bước 5 — Thêm Dữ Liệu PDF

Đặt file PDF tài liệu du lịch vào thư mục:

```
src/source_data/docs/
├── dia_diem_da_lat.pdf
├── ha_noi_travel.pdf
└── ...
```

> 📌 Chỉ hỗ trợ file `.pdf`. Cần ít nhất 1 file để build vector DB.
>
> ⚠️ **Lưu ý metadata:** Mỗi địa điểm trong PDF nên có thông tin `lat`, `lon`, `tags`, `rating`, `duration` để pipeline Recommend & Planning hoạt động chính xác.

---

### Bước 6 — Build Vector Database (chỉ chạy một lần)

Mở và chạy toàn bộ notebook:

```
build_rag_vector_db.ipynb
```

Hoặc qua command line:

```bash
jupyter nbconvert --to notebook --execute build_rag_vector_db.ipynb
```

**Output mong đợi:**

```
Loading embedding model on device using: 'cpu'...
Loading document from src/source_data/docs
Splitting documents into chunks...
Creating embeddings and storing in ChromaDB...
📦 DB does not exist, creating new...
Total inserted: XX chunks
✅ Ingestion complete! Your documents are stored in Chroma DB and ready for RAG queries.
```

> ⚠️ Chỉ chạy lại khi thêm PDF mới vào thư mục `docs/`.

---

### Bước 7 — Khởi Động API Server

```bash
uvicorn src.main:app --reload
```

**Output mong đợi:**

```
App starting — loading RAG Pipeline...
⚙️ Đang khởi tạo Full Trip Planning Pipeline...
Loading embedding model on device using: 'cpu'...
Loading Chroma database from db/...
✅ System prompt loaded from: src/prompts/system_prompt.md
App is ready to serve requests.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

## ⚛️ Frontend Setup (FE_ChatBot)

### Bước 8 — Cài Đặt Dependencies

```bash
cd ../FE_ChatBot
npm install
```

### Bước 9 — Khởi Động Dev Server

```bash
npm run dev
```

**Output mong đợi:**

```
  VITE v7.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
```

---

## 🌐 API Endpoints

| URL                           | Mô tả                          |
| ----------------------------- | ------------------------------ |
| `http://127.0.0.1:8000/`      | Chat interface Gradio (legacy) |
| `http://127.0.0.1:8000/chat`  | REST API endpoint `(POST)`     |
| `http://127.0.0.1:8000/docs`  | Swagger UI                     |
| `http://127.0.0.1:8000/redoc` | ReDoc documentation            |
| `http://localhost:5173/`      | React Frontend (main UI)       |

### Ví dụ gọi API

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Tôi muốn đi Đà Lạt 2 ngày, thích cafe và thác nước, budget 3 triệu"}'
```

**Response:**

```json
{
  "response": "Đây là lịch trình 2 ngày tại Đà Lạt dành cho bạn...",
  "trip_plan": {
    "days": [
      {
        "day": 1,
        "places": [
          {
            "name": "Thác Datanla",
            "arrival": "08:30",
            "departure": "10:00",
            "tags": ["thác nước", "thiên nhiên"]
          },
          {
            "name": "Cafe The Married Beans",
            "arrival": "10:30",
            "departure": "11:30",
            "tags": ["cafe", "view"]
          }
        ]
      }
    ]
  }
}
```

---

## 🧩 Module Chi Tiết

### Pipeline Flow

```
raw_query (str)
    ↓ [1] QueryAnalyzer     → TripRequest {region, days, tags, budget}
    ↓ [2] RAGStorage        → top-20 Place (ChromaDB cosine similarity)
    ↓ [3] Reranker          → top-15 Place (rag_score + rating + tag_overlap)
    ↓ [4] HybridRecommender → top-10 Place (content + location scoring)
    ↓ [5] TripPlanner       → TripPlan (graph + route + schedule)
    ↓ [6] LLM Generation    → text response + JSON trip plan
```

### Recommender System

| Chiến lược     | File                    | Mô tả                                                        |
| -------------- | ----------------------- | ------------------------------------------------------------ |
| Content-Based  | `content_based.py`      | Jaccard similarity giữa tags của place và tags trong request |
| Location-Based | `location_based.py`     | Haversine distance đến centroid — ưu tiên địa điểm gần nhau  |
| Hybrid         | `hybrid_recommender.py` | Kết hợp: `content × 0.6 + location × 0.4`                    |

### Graph-based Planning

| Component      | File                 | Mô tả                                                                  |
| -------------- | -------------------- | ---------------------------------------------------------------------- |
| GraphBuilder   | `graph_builder.py`   | Xây complete weighted graph — edge weight = thời gian di chuyển (phút) |
| RouteOptimizer | `route_optimizer.py` | Greedy Nearest Neighbor (mặc định), Dijkstra, 2-opt improvement        |
| Scheduler      | `scheduler.py`       | Chia places vào N ngày, gán giờ HH:MM từ 08:00 đến 21:00               |
| TripPlanner    | `planner.py`         | Facade kết hợp 3 component trên → `TripPlan`                           |

---

## 🖥️ Frontend Features

### 💬 Chat Interface

- **ChatArea** — Gửi prompt tới `POST /chat`, render phản hồi.
- **ChatInput** — Input bar, disable khi đang chờ bot.
- **Message** — Bubble user vs bot, có error state styling.

### 📊 Result Visualization

| View         | Component            | Mô tả                              |
| ------------ | -------------------- | ---------------------------------- |
| **Text**     | `TextResult.jsx`     | Plain markdown/text                |
| **Timeline** | `TimelineResult.jsx` | Vertical timeline theo ngày        |
| **Mindmap**  | `MindmapResult.jsx`  | Interactive node graph (ReactFlow) |

### 🌐 Tech Stack (Frontend)

| Technology                        | Version | Mục đích                |
| --------------------------------- | ------- | ----------------------- |
| React                             | ^19.x   | UI framework            |
| Vite                              | ^7.x    | Build tool & dev server |
| TailwindCSS                       | ^4.x    | Utility-first styling   |
| React Router DOM                  | ^7.x    | Client-side routing     |
| Axios                             | ^1.x    | HTTP client             |
| ReactFlow                         | ^11.x   | Mindmap / node graph    |
| react-vertical-timeline-component | ^4.x    | Timeline visualization  |

---

## 🔄 Thêm Tài Liệu Mới vào DB

1. Thêm file PDF vào `BE_ChatBot/src/source_data/docs/`
2. Chạy lại ingestion:

```python
from src.pipeline.rag_pipline import RAGStorage
RAGStorage().build_vector_db()
```

---

## 📦 Regenerate `requirements.txt`

```bash
pip freeze > requirements.txt
```

---

## ❓ Xử Lý Lỗi Thường Gặp

**`ModuleNotFoundError: No module named 'src'`**

```bash
cd BE_ChatBot
uvicorn src.main:app --reload
```

**`PERSIST_DIRECTORY not set`** → Kiểm tra `.env` đã có `PERSIST_DIRECTORY=db/`.

**`Documents directory does not exist`** → Kiểm tra `SOURCE_DATA` trong `.env` trỏ đúng thư mục chứa PDF.

**`NVIDIA_API_KEY environment variable not set`** → Điền `NVIDIA_API_KEY` trong `.env`. Lấy key tại https://build.nvidia.com.

**Embedding model treo lần đầu chạy** → Bình thường — model (~90MB) đang tải về `src/model/embeddings/`. Thêm `HF_TOKEN` vào `.env` để tăng tốc.

**CORS error trên browser** → Đảm bảo `FRONTEND_URL=http://localhost:5173` đã được set trong `.env`.

**Port 8000 đang bị chiếm** → Dùng `run.bat` (Windows):

```bat
@echo off
taskkill /IM python.exe /F >nul 2>&1
uvicorn src.main:app --reload
```

**Frontend blank screen** → Đảm bảo backend đang chạy trên `http://127.0.0.1:8000` trước khi start frontend.

---

## 📄 License

Dự án phục vụ mục đích học thuật / khóa luận tốt nghiệp (KLTN).
