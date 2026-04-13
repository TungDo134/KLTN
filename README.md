# 🇻🇳 Vietnam Travel ChatBot — RAG + LLM + React

Vietnam travel consulting chatbot using **LLM (Llama 3.1 - Present)** + **RAG** + **ChromaDB**, backend **FastAPI**, frontend **React + Vite + TailwindCSS**.

---

## 📁 Project Structure

```
Project/
├── BE_ChatBot/                        ← Backend (FastAPI + RAG)
│   ├── src/
│   │   ├── core/                      ← Factory Pattern — abstraction layer
│   │   │   ├── base.py                ← Abstract class ModelLLMPlatform (achat interface)
│   │   │   ├── base_embed_model.py    ← Factory: get_embedding_model() with EmbeddingProvider enum
│   │   │   └── llama_nvidia.py        ← (Planned) LlamaNvidia impl — currently unused
│   │   ├── pipeline/
│   │   │   ├── inference.py           ← RAG chain (Retriever → Prompt → LLM)
│   │   │   ├── llm.py                 ← Factory creating ChatNVIDIA object
│   │   │   └── rag_pipline.py         ← Ingestion & Retriever (uses core/base_embed_model)
│   │   ├── model/
│   │   │   └── embeddings/            ← HuggingFace embedding model cache (auto-downloaded)
│   │   ├── prompts/
│   │   │   └── system.txt             ← System prompt for LLM
│   │   ├── db/                        ← ChromaDB vector store (auto-created)
│   │   └── source_data/
│   │       └── docs/                  ← ⬅ Put PDF files here
│   ├── build_rag_vector_db.ipynb      ← Run once to create vector DB
│   ├── run.bat                        ← Windows: kill old process & restart
│   ├── .env                           ← Create from .env.example
│   └── requirements.txt
│
└── FE_ChatBot/                        ← Frontend (React + Vite + TailwindCSS)
    ├── src/
    │   ├── api/
    │   │   └── axiosClient.js         ← Axios instance (baseURL + auth interceptor)
    │   ├── services/
    │   │   └── chatApi.js             ← API calls (POST /chat)
    │   ├── features/
    │   │   ├── navigation/
    │   │   │   ├── Sidebar.jsx        ← Sidebar (chat history, user menu)
    │   │   │   ├── TopBar.jsx         ← Top navigation bar
    │   │   │   ├── ModelDropdown.jsx  ← Model selection dropdown
    │   │   │   └── PlusMenu.jsx       ← Plus action menu
    │   │   └── result-visualize/
    │   │       ├── ResultSwitcher.jsx ← Toggle between Text/Timeline/Mindmap
    │   │       ├── BotResult.jsx      ← Bot response wrapper
    │   │       ├── TextResult.jsx     ← Plain text display
    │   │       ├── TimelineResult.jsx ← Vertical timeline view
    │   │       └── MindmapResult.jsx  ← Mindmap / ReactFlow view
    │   ├── ui/
    │   │   ├── AppLayout.jsx          ← Root layout (Sidebar + Topbar + Outlet)
    │   │   ├── ChatArea.jsx           ← Main chat page (messages + input)
    │   │   ├── ChatInput.jsx          ← User input bar
    │   │   └── Message.jsx            ← Single message bubble
    │   ├── helper/
    │   │   └── extractJsonFromText.js ← Parse JSON trip plan from LLM response
    │   ├── App.jsx                    ← React Router setup
    │   ├── main.jsx                   ← Entry point
    │   └── index.css                  ← Global styles
    ├── index.html
    ├── vite.config.js
    └── package.json
```

---

## ⚙️ System Requirements

| Requirement | Details |
|---|---|
| Python | >= 3.10 |
| pip | >= 23.0 |
| Node.js | >= 18.x |
| npm | >= 9.x |
| RAM | >= 4GB |
| API Key | [NVIDIA NIM](https://build.nvidia.com) (required) |
| HF Token | [HuggingFace](https://huggingface.co/settings/tokens) (recommended) |

---

## 🚀 Installation Guide (End-to-End)

### Step 1 — Clone Project

```bash
git clone https://github.com/<your-username>/Vietnam-Travel-ChatBot.git
cd Vietnam-Travel-ChatBot
```

---

## 🐍 Backend Setup (BE_ChatBot)

### Step 2 — Create & Activate Virtual Environment

```bash
cd BE_ChatBot

# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

> ✅ After activation, the terminal will display `(.venv)` at the beginning of the line.

---

### Step 3 — Install Backend Dependencies

```bash
pip install -r requirements.txt
```

> ⏳ First time may take 3–5 minutes (LangChain, ChromaDB, HuggingFace...).

---

### Step 4 — Create `.env` File

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` and fill in:

```env
# === REQUIRED ===
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxx   # Get at https://build.nvidia.com

# === RECOMMENDED ===
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx            # Get at https://huggingface.co/settings/tokens

# === PATH CONFIGURATION ===
PERSIST_DIRECTORY=db/                       # Where ChromaDB stores vectors
SOURCE_DATA=src/source_data/docs            # Folder containing PDF files

# === SYSTEM PROMPT (optional) ===
SYSTEM_PROMPT=src/prompts/system.txt

# === FRONTEND (React frontend URL for CORS) ===
FRONTEND_URL=http://localhost:5173
```

---

### Step 5 — Add PDF Data

Put travel document PDF files into:

```
src/source_data/docs/
├── dia_diem_ha_noi.pdf
├── da_lat_travel.pdf
└── ...
```

> 📌 Only `.pdf` files are supported. At least 1 file is required to build the vector DB.

---

### Step 6 — Build Vector Database (run once only)

Open and run the entire notebook:

```
build_rag_vector_db.ipynb
```

Or via command line:

```bash
jupyter nbconvert --to notebook --execute build_rag_vector_db.ipynb
```

**Expected output:**

```
Loading embedding model on device using: 'cpu'...
Loading document from src/source_data/docs
Splitting documents into chunks...
Creating embeddings and storing in ChromaDB...
📦 DB does not exist, creating new...
Total inserted: XX chunks
✅ Ingestion complete! Your documents are stored in Chroma DB and ready for RAG queries.
```

> ⚠️ Only re-run when adding new PDFs to the `docs/` folder.

---

### Step 7 — Start API Server

```bash
uvicorn src.main:app --reload
```

**Expected output:**

```
App starting — loading RAG Pipeline...
Loading embedding model on device using: 'cpu'...
Loading Chroma database from db/...
✅ System prompt loaded from: src/prompts/system.txt
App is ready to serve requests.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

## ⚛️ Frontend Setup (FE_ChatBot)

### Step 8 — Install Frontend Dependencies

```bash
cd ../FE_ChatBot
npm install
```

---

### Step 9 — Start Development Server

```bash
npm run dev
```

**Expected output:**

```
  VITE v7.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

> ✅ Open `http://localhost:5173` in your browser to use the chatbot UI.

---

## 🌐 Endpoints (after running backend)

| URL | Description |
|---|---|
| `http://127.0.0.1:8000/` | Chat interface **Gradio** (legacy) |
| `http://127.0.0.1:8000/chat` | REST API endpoint `(POST)` |
| `http://127.0.0.1:8000/docs` | Swagger UI — test API directly |
| `http://127.0.0.1:8000/redoc` | ReDoc documentation |
| `http://localhost:5173/` | React Frontend (main UI) |

### Example REST API Call

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Famous tourist destinations in Da Lat?"}'
```

---

## 🖥️ Frontend Features

The React frontend (`FE_ChatBot`) provides a modern chat interface with the following capabilities:

### 💬 Chat Interface
- **ChatArea** — Main conversation page. Sends user messages to `POST /chat` and renders responses.
- **ChatInput** — Text input bar with send button. Disabled while waiting for a bot response.
- **Message** — Renders each message bubble (user vs bot), with error state styling.

### 🗂️ Navigation
- **Sidebar** — Displays chat history list, search bar, and user account menu (upgrade, settings, logout).
- **TopBar** — Top action bar with model selector and additional controls.
- **ModelDropdown** — Lets the user switch between available LLM models.
- **PlusMenu** — Quick-action menu for starting new conversations or uploading files.

### 📊 Result Visualization
When the LLM returns a structured JSON trip plan, the UI can render it in multiple views:

| View | Component | Description |
|---|---|---|
| **Text** | `TextResult.jsx` | Plain markdown/text response |
| **Timeline** | `TimelineResult.jsx` | Vertical timeline (react-vertical-timeline-component) |
| **Mindmap** | `MindmapResult.jsx` | Interactive node graph (ReactFlow) |

The `ResultSwitcher` component provides toggle buttons to switch between views.

### 🔌 API Integration
- **axiosClient** — Axios instance pointing to `http://127.0.0.1:8000`. Automatically attaches `Authorization: Bearer <token>` from `localStorage` on every request.
- **chatApi** — Thin service wrapper: `chatApi.sendMessage(prompt)` → `POST /chat`.

### 🌐 Tech Stack (Frontend)

| Technology | Version | Purpose |
|---|---|---|
| React | ^19.2.0 | UI framework |
| Vite | ^7.x | Build tool & dev server |
| TailwindCSS | ^4.x | Utility-first styling |
| React Router DOM | ^7.x | Client-side routing |
| Axios | ^1.x | HTTP client |
| React Icons | ^5.x | Icon library |
| ReactFlow | ^11.x | Mindmap / node graph |
| react-vertical-timeline-component | ^4.x | Timeline visualization |

---

## 🔄 Add New Documents to the DB

1. Add a new PDF file into `BE_ChatBot/src/source_data/docs/`
2. Re-run the notebook or call directly in Python:

```python
from src.pipeline.rag_pipline import RAGStorage
RAGStorage().build_vector_db()  # Automatically detects existing DB and only adds new data
```

---

## 📦 Regenerate `requirements.txt`

If you install new Python packages:

```bash
pip freeze > requirements.txt
```

---

## ❓ Common Troubleshooting

**`ModuleNotFoundError: No module named 'src'`**
```bash
# Run from the root of BE_ChatBot (where src/ is located)
cd BE_ChatBot
uvicorn src.main:app --reload
```

**`PERSIST_DIRECTORY not set`** → Check that `.env` has been created and `PERSIST_DIRECTORY=db/` is filled.

**`Documents directory does not exist`** → Check that `SOURCE_DATA` in `.env` points to the correct folder containing PDFs.

**`NVIDIA_API_KEY environment variable not set`** → Fill `NVIDIA_API_KEY` in `.env`. Get the key at https://build.nvidia.com.

**Embedding model freezes on first run** → Normal — the model (~90MB) is downloading to `src/model/embeddings/`. Add `HF_TOKEN` to `.env` to speed up.

**CORS error in browser** → Make sure `FRONTEND_URL=http://localhost:5173` is set in `BE_ChatBot/.env` and the FastAPI app has CORS middleware configured for that origin.

**Cannot shutdown with Ctrl+C / Port 8000 already in use** → Use `run.bat` (Windows):

```bat
@echo off
echo Killing all Python processes...
taskkill /IM python.exe /F >nul 2>&1

echo Starting FastAPI...
uvicorn src.main:app --reload
```

**Frontend blank screen / cannot connect** → Make sure the backend is running on `http://127.0.0.1:8000` before starting the frontend. Check `axiosClient.js` if the base URL differs.

---

## 🏗️ System Architecture

```
User (Browser)
    ↓  http://localhost:5173
React Frontend (Vite)
    ├── ChatArea → ChatInput → sends prompt
    ↓  POST http://127.0.0.1:8000/chat
FastAPI Backend
    ↓
RAGInference.predict_async()
    ↓
[1] ChromaDB Retriever
    └── Question embedding → find top-k chunks
    ↓
[2] Prompt Template
    └── {context} + {question}
    ↓
[3] Llama 3.1 405B (NVIDIA NIM API)
    └── Generate Vietnamese answer
    ↓
JSON Response → Frontend
    ├── TextResult     (plain text)
    ├── TimelineResult (structured trip plan)
    └── MindmapResult  (node graph)
```

---

## 📄 License

This project is for academic/thesis (KLTN) purposes.
