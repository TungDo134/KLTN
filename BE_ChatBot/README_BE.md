# 🇻🇳 Vietnam Travel ChatBot --- RAG + LLM

Vietnam travel consulting chatbot using **LLM (Llama 3.1- Present)** + **RAG** +
**ChromaDB**, backend **FastAPI**, interface **Gradio**.

------------------------------------------------------------------------

## 📁 Project structure

    ChatBot_Travel_Demo/
    ├── src/
    │   ├── pipeline/
    │   │   ├── inference.py       ← RAG chain (Retriever → Prompt → LLM)
    │   │   ├── llm.py             ← Factory creating ChatNVIDIA object
    │   │   └── rag_pipeline.py    ← Ingestion & Retriever
    │   ├── model/
    │   │   └── llama_nvidia.py    ← (Legacy, not used)
    │   ├── prompts/
    │   │   └── system.txt         ← System prompt for LLM
    │   └── source_data/
    │       └── docs/              ← ⬅ Put PDF files here
    ├── notebooks/
    │   └── build_vector_db.ipynb  ← Run once to create vector DB
    ├── db/                        ← Auto-created after running notebook
    ├── .env                       ← Create from .env.example
    ├── .env.example
    ├── requirements.txt
    └── main.py

------------------------------------------------------------------------

## ⚙️ System requirements

  -------------------------------------------------------------------------------------------
  Requirement                         Details
  ----------------------------------- -------------------------------------------------------
  Python                              \>= 3.10

  pip                                 \>= 23.0

  RAM                                 \>= 4GB

  API Key                             [NVIDIA NIM](https://build.nvidia.com) (required)

  HF Token                            [HuggingFace](https://huggingface.co/settings/tokens)
                                      (recommended)
  -------------------------------------------------------------------------------------------

------------------------------------------------------------------------

## 🚀 Installation guide from scratch (End-to-End)

### Step 1 --- Clone project

``` bash
git clone https://github.com/<your-username>/ChatBot_Travel_Demo.git
cd ChatBot_Travel_Demo
```

------------------------------------------------------------------------

### Step 2 --- Create and activate Virtual Environment

``` bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

> ✅ After activation, the terminal will display `(.venv)` at the
> beginning of the line.

------------------------------------------------------------------------

### Step 3 --- Install dependencies

``` bash
pip install -r requirements.txt
```

> ⏳ The first time may take 3--5 minutes because LangChain, ChromaDB,
> HuggingFace... need to be installed.

------------------------------------------------------------------------

### Step 4 --- Create `.env` file

``` bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Open the newly created `.env` file and fill in the values:

``` env
# === REQUIRED ===
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxx   # Get at https://build.nvidia.com

# === RECOMMENDED ===
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx            # Get at https://huggingface.co/settings/tokens
                                            # Helps speed up embedding model download

# === PATH CONFIGURATION ===
PERSIST_DIRECTORY=db/                       # Where ChromaDB stores vectors
SOURCE_DATA=src/source_data/docs            # Folder containing PDF files

# === SYSTEM PROMPT (optional) ===
SYSTEM_PROMPT=src/prompts/system.txt        # Leave empty if not used

# === FRONTEND (if using separate React frontend) ===
FRONTEND_URL=http://localhost:5173
```

------------------------------------------------------------------------

### Step 5 --- Add PDF data

Put travel document PDF files into the folder:

    src/source_data/docs/
    ├── dia_diem_ha_noi.pdf
    ├── da_lat_travel.pdf
    └── ...

> 📌 The system only reads `.pdf` files. At least 1 file is required to
> build the vector DB.

------------------------------------------------------------------------

### Step 6 --- Build Vector Database (run once only)

Open and run the entire notebook:

    notebooks/build_vector_db.ipynb

Or run using the command:

``` bash
jupyter nbconvert --to notebook --execute notebooks/build_vector_db.ipynb
```

**Expected result when successful:**

    Loading embedding model on device using: 'cpu'...
    Loading document from src/source_data/docs
    Splitting documents into chunks...
    Creating embeddings and storing in ChromaDB...
    📦 DB does not exist, creating new...
    Total inserted: XX chunks
    ✅ Ingestion complete! Your documents are stored in Chroma DB and ready for RAG queries.

After this step, the folders `db/` and `src/model/embeddings/` will be
created automatically.

> ⚠️ Only rerun when adding new PDFs into the `docs/` folder.

------------------------------------------------------------------------

### Step 7 --- Start API Server

``` bash
uvicorn src.main:app --reload
```

**Expected result:**

    App starting — loading RAG Pipeline...
    Loading embedding model on device using: 'cpu'...
    Loading Chroma database from db/...
    ✅ System prompt loaded from: src/prompts/system.txt
    App is ready to serve requests.
    INFO:     Uvicorn running on http://127.0.0.1:8000

------------------------------------------------------------------------

## 🌐 Endpoints after running

  URL                           Description
  ----------------------------- ----------------------------------
  http://127.0.0.1:8000/        Chat interface **Gradio**
  http://127.0.0.1:8000/chat    REST API endpoint (POST)
  http://127.0.0.1:8000/docs    Swagger UI --- test API directly
  http://127.0.0.1:8000/redoc   ReDoc documentation

### Example calling REST API

``` bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Famous tourist destinations in Da Lat?"}'
```

------------------------------------------------------------------------

## 🔄 Add new documents to DB

1.  Add a new PDF file into `src/source_data/docs/`
2.  Run the notebook again or call directly in Python:

``` python
from src.pipeline.rag_pipline import RAGStorage
RAGStorage().build_vector_db()  # Automatically detects existing DB and only adds new data
```

------------------------------------------------------------------------

## 📦 Regenerate `requirements.txt`

If you install new packages:

``` bash
pip freeze > requirements.txt
```

------------------------------------------------------------------------

## ❓ Common troubleshooting

**`ModuleNotFoundError: No module named 'src'`**

``` bash
# Run from the root directory of the project (where main.py is located)
# Do not run from inside the src/ directory
cd ChatBot_Travel_Demo
uvicorn src.main:app --reload --port
```

**`PERSIST_DIRECTORY not set`** → Check whether the `.env` file has been
created and `PERSIST_DIRECTORY=db/` is filled.

**`Documents directory does not exist`** → Check that `SOURCE_DATA` in
`.env` points to the correct folder containing PDFs.

**`NVIDIA_API_KEY environment variable not set`** → Fill
`NVIDIA_API_KEY` in the `.env` file. Get the key at
https://build.nvidia.com.

**Embedding model freezes on first run** → Normal --- the model (\~90MB)
is downloading to `src/model/embeddings/`. Add `HF_TOKEN` to `.env` to
speed up.

**Cannot shutdown with Ctrl+C** → Use a `run.bat` file to kill the old
process and restart:
## Create run.bat (Windows) if don't have

``` bash
@echo off
echo Killing all Python processes...
taskkill /IM python.exe /F >nul 2>&1

:: Start FastAPI
echo Starting FastAPI...
uvicorn src.main:app --reload
```

**Port 8000 already in used → Use a `run.bat`**



------------------------------------------------------------------------

## 🏗️ System architecture

    User Input
        ↓
    FastAPI /chat  ──────────────────────────────┐
        ↓                                        │
    RAGInference.predict_async()                 │
        ↓                                        │
    [1] ChromaDB Retriever                       │
        └── Question embedding → find top-4 chunks │
        ↓                                        │
    [2] Prompt Template                          │
        └── {context} + {question}               │
        ↓                                        │
    [3] Llama 3.1 405B (NVIDIA API)              │
        └── Generate Vietnamese answer           │
        ↓                                        │
    Response → Client ───────────────────────────┘
