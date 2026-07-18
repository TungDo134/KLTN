# Mục lục

- [Kế hoạch triển khai Railway Free theo từng phase](#kế-hoạch-triển-khai-railway-free-theo-từng-phase)
  - [Tổng quan](#tổng-quan)
  - [Phase 0 — Chốt baseline trước khi thay đổi](#phase-0--chốt-baseline-trước-khi-thay-đổi)
  - [Phase 1 — Làm deployment runtime thuần API](#phase-1--làm-deployment-runtime-thuần-api)
  - [Phase 2 — Chuẩn bị dữ liệu và cấu hình cloud](#phase-2--chuẩn-bị-dữ-liệu-và-cấu-hình-cloud)
  - [Phase 3 — Đóng gói Docker](#phase-3--đóng-gói-docker)
  - [Phase 4 — Test container hoàn chỉnh trên local](#phase-4--test-container-hoàn-chỉnh-trên-local)
  - [Phase 5 — Tạo hạ tầng Railway Free](#phase-5--tạo-hạ-tầng-railway-free)
  - [Phase 6 — Khai báo biến và deploy backend](#phase-6--khai-báo-biến-và-deploy-backend)
  - [Phase 7 — Kết nối Netlify với Railway](#phase-7--kết-nối-netlify-với-railway)
  - [Phase 8 — Kiểm tra Serverless và chi phí Free](#phase-8--kiểm-tra-serverless-và-chi-phí-free)
  - [Phase 9 — Ổn định trước khi upgrade](#phase-9--ổn-định-trước-khi-upgrade)
  - [Public interface và cấu hình mới](#public-interface-và-cấu-hình-mới)
  - [Tiêu chí hoàn thành toàn bộ](#tiêu-chí-hoàn-thành-toàn-bộ)

---

# Kế hoạch triển khai Railway Free theo từng phase

## Tổng quan

Thực hiện tuần tự:

```text
Phase 0: Chốt baseline
    ↓
Phase 1: Làm backend thuần API
    ↓
Phase 2: Chuẩn bị Chroma, Firebase, PostgreSQL
    ↓
Phase 3: Đóng gói Docker
    ↓
Phase 4: Test container local
    ↓
Phase 5: Tạo hạ tầng Railway
    ↓
Phase 6: Deploy backend
    ↓
Phase 7: Kết nối Netlify
    ↓
Phase 8: Test sleep và chi phí
    ↓
Phase 9: Ổn định và quyết định upgrade
```

Chỉ chuyển sang phase tiếp theo khi toàn bộ tiêu chí của phase hiện tại đã pass.

---

## Phase 0 — Chốt baseline trước khi thay đổi

### Mục tiêu

Xác nhận phiên bản local hiện tại hoạt động và ghi lại trạng thái để so sánh sau khi tối ưu.

### Thực hiện

1. Chạy backend hiện tại bằng môi trường local.
2. Đăng nhập từ frontend.
3. Gửi một truy vấn du lịch.
4. Kiểm tra ChromaDB hiện tại.
5. Kiểm tra Git không theo dõi secret và model.

Context cần ghi nhận:

```text
Embedding: Google models/gemini-embedding-001
ChromaDB: 600 vectors, dimension 3072
Core LLM: Ollama Cloud
Rewrite/Multi-query: Groq
Reranker: Cohere
```

### Cách test

Tại `D:\KLTN\Project`:

```powershell
sqlite3 -header -column `
  "BE_ChatBot\src\db\chroma_db\chroma.sqlite3" `
  "SELECT name, dimension FROM collections; SELECT COUNT(*) AS embeddings FROM embeddings;"
```

Kiểm tra file nhạy cảm:

```powershell
git -c safe.directory=D:/KLTN/Project check-ignore -v `
  "BE_ChatBot/.env" `
  "BE_ChatBot/config/firebase-service-account.json" `
  "BE_ChatBot/src/model/README.md"
```

### Expected output

```text
name          dimension
kltn_chatbot  3072

embeddings
600
```

Các file sau phải hiển thị là đang bị Git ignore:

```text
BE_ChatBot/.env
BE_ChatBot/config/firebase-service-account.json
BE_ChatBot/src/model/
```

### Điều kiện hoàn thành

- Backend local trả lời được ít nhất một travel query.
- Embedding configuration khớp ChromaDB.
- Secret và local model không bị Git track.

### Kết quả/tiến độ Phase 0

**Trạng thái: ✅ Hoàn thành — 6/6 PASS**

| #   | Nội dung kiểm tra                            | Kết quả | Kết quả chính                                                                                                          |
| --- | -------------------------------------------- | ------- | ---------------------------------------------------------------------------------------------------------------------- |
| 1   | Working directory và các đường dẫn cần thiết | ✅ PASS | Backend chạy từ `D:\KLTN\Project\BE_ChatBot`; các đường dẫn ChromaDB, system prompt và Firebase tồn tại.               |
| 2   | Cấu hình environment path                    | ✅ PASS | Các đường dẫn runtime dùng biến môi trường và giá trị tương đối, phù hợp khi chạy từ thư mục backend.                  |
| 3   | ChromaDB và embedding metadata               | ✅ PASS | Collection `kltn_chatbot`, 600 vectors, dimension 3072; embedding Google `models/gemini-embedding-001`.                |
| 4   | Git ignore cho secret và dữ liệu local       | ✅ PASS | `.env`, Firebase credentials, local model và virtual environment không bị Git theo dõi.                                |
| 5   | Backend startup                              | ✅ PASS | Uvicorn và toàn bộ provider khởi tạo thành công; ChromaDB/BM25 tải đủ 600 documents; không có traceback hoặc HTTP 5xx. |
| 6   | Query du lịch end-to-end                     | ✅ PASS | `POST /chat/stream` trả HTTP 200; retrieval, Cohere rerank, recommendation và sinh lịch trình hoàn tất trên UI.        |

Kết quả kiểm tra ngày 13/07/2026:

- [Startup và query log](<../../LOG TERMINAL (13072026)/LOG TERMINAL (13072026).txt>)
- [Ảnh kết quả trả về cho end user](<../../LOG TERMINAL (13072026)/LOG TERMINAL (13072026).png>)

---

## Phase 1 — Làm deployment runtime thuần API

### Mục tiêu

Loại các dependency local AI khỏi Docker image và RAM runtime mà không thay đổi luồng RAG.

### Thực hiện

1. Tạo `requirements.deploy.txt` dành riêng cho Docker.
2. Không cài các package sau trong deployment:

```text
torch
sentence-transformers
transformers
langchain-huggingface
rerankers[transformers]
gradio
gradio-client
hf-gradio
```

3. Giữ các dependency runtime:

```text
FastAPI + Uvicorn
ChromaDB + LangChain retrieval
Google embedding API
Groq
Ollama Cloud
Cohere
rank-bm25
SQLAlchemy + PostgreSQL driver
Firebase Admin
```

4. Chuyển local-provider imports thành lazy import.
5. Không import `torch` ở module level.
6. Cohere rerank gọi API trực tiếp, không khởi tạo cross-encoder.
7. Loại Gradio khỏi production FastAPI entrypoint.
8. Các hàm ingestion/notebook không được load dependency nặng khi backend startup.

### Cách test

Tạo virtual environment sạch:

```powershell
cd D:\KLTN\Project\BE_ChatBot

py -3.12 -m venv .venv-deploy

.\.venv-deploy\Scripts\python.exe -m pip install `
  -r requirements.deploy.txt
```

Kiểm tra import:

```powershell
.\.venv-deploy\Scripts\python.exe -c `
  "import src.main, sys; print([x for x in ['torch','transformers','gradio'] if x in sys.modules])"
```

### Expected output

Cài dependency:

```text
Successfully installed ...
```

Kiểm tra module:

```text
[]
```

Không được xuất hiện:

```text
CUDA is not available
Downloading model...
Loading HuggingFace model...
Initializing local reranker...
```

### Điều kiện hoàn thành

- Import được `src.main` trong môi trường không có Torch.
- Không có Torch, Transformers hoặc Gradio trong runtime modules.
- Luồng Google embedding và Cohere rerank vẫn được giữ nguyên.

### Kết quả/tiến độ Phase 1

**Trạng thái: ✅ Hoàn thành — 8/8 PASS**

| Hạng mục                                              | Tiến độ                                                      |
| ----------------------------------------------------- | ------------------------------------------------------------ |
| Tạo dependency riêng cho deployment                   | ✅ Đã tạo `requirements.deploy.txt`                          |
| Lazy import Torch và HuggingFace embedding            | ✅ Đã implement                                              |
| Loại module-level Torch khỏi RAG pipeline             | ✅ Đã implement                                              |
| Cohere gọi API trực tiếp, local reranker lazy import  | ✅ Đã implement                                              |
| Loại Gradio khỏi production FastAPI entrypoint        | ✅ Đã implement                                              |
| Ignore `.venv-deploy/`                                | ✅ Đã implement                                              |
| Cài dependency và import `src.main` trong deploy venv | ✅ PASS — `IMPORT_OK`, không load dependency local           |
| Backend startup và travel query bằng deploy venv      | ✅ PASS — startup đủ 600 documents, FE nhận response ổn định |

Kết quả kiểm tra: [Result Test Phase 1](<../../LOG TERMINAL (13072026)/Result Test Phase 1.md>).

---

## Phase 2 — Chuẩn bị dữ liệu và cấu hình cloud

### Mục tiêu

Đảm bảo ChromaDB, Firebase và PostgreSQL có thể hoạt động trong container mà không phụ thuộc đường dẫn máy cá nhân.

### 2.1. ChromaDB

#### Thực hiện

- Unignore riêng:

```text
BE_ChatBot/src/db/chroma_db/**
```

- Tiếp tục ignore:

```text
BE_ChatBot/src/model/
```

- Đóng gói ChromaDB 13.3 MB vào Docker image.
- Không tạo Railway volume cho backend.

#### Cách test

```powershell
git -c safe.directory=D:/KLTN/Project check-ignore `
  "BE_ChatBot/src/db/chroma_db/chroma.sqlite3"
```

Sau đó:

```powershell
git -c safe.directory=D:/KLTN/Project status --short `
  "BE_ChatBot/src/db/chroma_db"
```

#### Expected output

Lệnh `check-ignore` không trả về file ChromaDB.

Git status hiển thị ChromaDB là file mới có thể commit:

```text
?? BE_ChatBot/src/db/chroma_db/
```

Model vẫn phải bị ignore.

### 2.2. Firebase

#### Thực hiện

Thêm hỗ trợ biến:

```text
FIREBASE_CREDENTIALS_JSON
```

Cách đọc:

```text
Railway → FIREBASE_CREDENTIALS_JSON
Local   → FIREBASE_CREDENTIALS_PATH
```

Không copy `firebase-service-account.json` vào image.

#### Cách test

Chạy backend với `FIREBASE_CREDENTIALS_JSON` và tạm bỏ `FIREBASE_CREDENTIALS_PATH`, sau đó đăng nhập Google.

#### Expected output

```text
Firebase initialized successfully
```

Endpoint:

```http
GET /auth/me
Authorization: Bearer <firebase-token>
```

Trả về HTTP 200 cùng thông tin user.

### 2.3. PostgreSQL

#### Thực hiện

- Tạo module init database.
- Import ba model trước khi gọi `Base.metadata.create_all()`:

```text
User
Conversation
Message
```

- Dùng `NullPool` cho workload ít request.
- Database Railway sẽ là database mới, không migrate dữ liệu local.

#### Cách test

Tạo một database local riêng:

```text
kltn_chatbot_deploy
```

Cấu hình:

```text
DATABASE_URL=postgresql://.../kltn_chatbot_deploy
```

Chạy:

```powershell
.\.venv-deploy\Scripts\python.exe -m src.db.init_db
```

Kiểm tra bảng:

```sql
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

#### Expected output

```text
conversations
messages
users
```

Chạy `init_db` lần thứ hai vẫn thành công và không tạo bảng trùng.

### Điều kiện hoàn thành Phase 2

- ChromaDB được Git nhận diện.
- Model và secrets vẫn bị ignore.
- Firebase hoạt động từ JSON environment variable.
- PostgreSQL schema tạo được từ database rỗng.

### Kết quả/tiến độ Phase 2

**Trạng thái: ✅ Hoàn thành — 5/5 PASS**

| # | Nội dung kiểm tra | Kết quả | Kết quả chính |
|---|---|---|---|
| 1 | Git và ChromaDB | ✅ PASS | Git nhận diện `src/db/chroma_db/` để commit; local model và Firebase credentials file vẫn bị ignore. |
| 2 | Firebase bằng JSON environment | ✅ PASS | Backend khởi động với `FIREBASE_CREDENTIALS_JSON` và đăng nhập Firebase thành công. |
| 3 | Firebase local path fallback | ✅ PASS | Backend đọc credentials từ đường dẫn local; `POST /auth/firebase-login` trả HTTP 200. |
| 4 | Tạo PostgreSQL schema | ✅ PASS | `src.db.init_db` chạy thành công hai lần; database có đủ 3 bảng và 2 bản ghi test vẫn còn sau lần chạy thứ hai, xác nhận không xóa database, bảng hoặc dữ liệu. |
| 5 | SQLAlchemy `NullPool` | ✅ PASS | Engine runtime trả về pool type `NullPool`. |

Kết quả kiểm tra: [Result Test Phase 2](<../../LOG TERMINAL (13072026)/Result Test Phase 2.md>).

---

## Phase 3 — Đóng gói Docker

### Mục tiêu

Tạo image nhỏ, không chứa secret hoặc local model.

### Thực hiện

1. Tạo Dockerfile với:

```text
Base image: python:3.12-slim
Working directory: /app
Requirements: requirements.deploy.txt
Worker: 1
Port: Railway $PORT
```

2. Start command:

```text
uvicorn src.main:app \
  --host 0.0.0.0 \
  --port ${PORT:-8000} \
  --workers 1
```

3. Tạo `.dockerignore` loại:

```text
.env
.venv/
src/model/
src/source_data/
src/eval/
test/
utils/
config/firebase-service-account.json
.ipynb_checkpoints/
.pytest_cache/
.idea/
```

4. Thêm endpoint:

```http
GET /health
```

Không gọi embedding, LLM hoặc reranker từ healthcheck.

### Cách test

Mở Docker Desktop rồi build:

```powershell
cd D:\KLTN\Project\BE_ChatBot

docker build -t be-chatbot:railway-free .
```

Kiểm tra image:

```powershell
docker images be-chatbot:railway-free
```

Kiểm tra file bên trong:

```powershell
docker run --rm --entrypoint sh be-chatbot:railway-free `
  -c "du -sh /app; test ! -f /app/.env; test ! -f /app/config/firebase-service-account.json"
```

### Expected output

Build:

```text
Successfully built ...
Successfully tagged be-chatbot:railway-free
```

Kích thước:

```text
Mục tiêu: dưới 1 GB
Bắt buộc: dưới 4 GB
```

Không tồn tại:

```text
/app/.env
/app/config/firebase-service-account.json
/app/src/model/embeddings
/app/src/model/reranker
```

Có tồn tại:

```text
/app/src/db/chroma_db/chroma.sqlite3
```

### Điều kiện hoàn thành

- Docker build thành công.
- Image dưới 4 GB.
- Không chứa model hoặc secret.
- Có ChromaDB và system prompt.

### Kết quả/tiến độ Phase 3

**Trạng thái: ✅ Hoàn thành — 7/7 PASS**

| # | Nội dung kiểm tra | Kết quả | Kết quả chính |
|---|---|---|---|
| 1 | Docker Client và Server | ✅ PASS | Docker Desktop hoạt động với Linux container engine. |
| 2 | Build image | ✅ PASS | Build hoàn thành và tạo image `be-chatbot:railway-free`. |
| 3 | Kích thước image | ✅ PASS | Image có kích thước `201.57 MB`, thấp hơn mục tiêu 1 GB. |
| 4 | Nội dung image | ✅ PASS | Có ChromaDB và system prompt; không có `.env`, Firebase credentials, local model hoặc deploy venv. |
| 5 | Local AI dependency | ✅ PASS | `torch`, `transformers` và `gradio` đều không tồn tại trong image. |
| 6 | Container startup | ✅ PASS | Các API provider khởi tạo thành công; ChromaDB/BM25 tải đủ 600 documents; không có traceback. |
| 7 | Healthcheck | ✅ PASS | `GET /health` trả `status: ok`. |

Kết quả kiểm tra: [Result Test Phase 3–4](<../../LOG TERMINAL (13072026)/Rsult Test Phase 3-4.md>).

---

## Phase 4 — Test container hoàn chỉnh trên local

### Mục tiêu

Mô phỏng gần giống Railway trước khi tốn thời gian deploy.

### Thực hiện

Chạy container:

```powershell
docker run --rm `
  --name be-chatbot-deploy `
  --env-file .env `
  -e PORT=8000 `
  -p 8000:8000 `
  be-chatbot:railway-free
```

### Test 1 — Startup

Mở:

```text
http://127.0.0.1:8000/health
```

#### Expected output

```json
{ "status": "ok" }
```

Logs phải có:

```text
Embedding provider: google
Embedding model: models/gemini-embedding-001
BM25 index built: 600 docs
Reranker provider: cohere
Application startup complete
```

Không được có:

```text
CUDA
torch
HuggingFace download
local reranker
```

### Test 2 — RAM

```powershell
docker stats be-chatbot-deploy --no-stream
```

#### Expected output

```text
MEM USAGE dưới khoảng 430 MiB
```

Tiếp tục kiểm tra sau một chat request. RAM vẫn phải nằm dưới giới hạn an toàn, không tăng liên tục.

### Test 3 — Full chat flow

Cấu hình frontend local:

```text
VITE_FASTAPI_URL=http://127.0.0.1:8000
```

Thực hiện:

1. Đăng nhập Google.
2. Gửi một câu hỏi du lịch.
3. Đợi streaming hoàn tất.
4. Refresh trang.
5. Mở lại conversation.

#### Expected output

- Login thành công.
- Network request `/chat/stream` trả HTTP 200.
- Response được stream dần.
- Kết quả có text và JSON trip plan.
- Conversation vẫn đọc lại được từ PostgreSQL.
- Không có CORS error.

### Điều kiện hoàn thành

- Healthcheck pass.
- Full chat flow pass.
- RAM mục tiêu dưới 430 MiB.
- Không có local AI model trong runtime.

### Kết quả/tiến độ Phase 4

**Trạng thái: ✅ Hoàn thành — 5/5 PASS**

| # | Nội dung kiểm tra | Kết quả | Kết quả chính |
|---|---|---|---|
| 1 | Startup và healthcheck | ✅ PASS | Container chạy ổn định, tải đủ 600 documents và healthcheck thành công. |
| 2 | RAM trước chat | ✅ PASS | Sử dụng `227.4 MiB / 512 MiB`; container `running`, `OOMKilled=false`. |
| 3 | Firebase login | ✅ PASS | Đăng nhập thành công khi container sử dụng database host `host.docker.internal`. |
| 4 | Full chat và PostgreSQL persistence | ✅ PASS | Luồng chat hoạt động; runtime đã xác nhận kết nối `host.docker.internal:5432/kltn_chatbot_deploy` và có dữ liệu trong `users`, `conversations`, `messages`. |
| 5 | RAM sau chat | ✅ PASS | Sau nhiều lần đo, RAM ổn định trong khoảng `227.7–228.6 MiB / 512 MiB`, thấp hơn mục tiêu `430 MiB`; container `running`, `OOMKilled=false`, `ExitCode=0`. |

Kiểm tra tách database local/Docker ngày 14/07/2026: **✅ PASS** — `run_docker_be.ps1` đọc `DOCKER_DATABASE_URL`, chuyển host sang `host.docker.internal` và truyền vào container dưới tên `DATABASE_URL`; cấu hình local tiếp tục dùng database `kltn`.

Kết quả kiểm tra: [Result Test Phase 3–4](<../../LOG TERMINAL (13072026)/Rsult Test Phase 3-4.md>).

---

## Phase 5 — Tạo hạ tầng Railway Free

### Mục tiêu

Tạo đúng hai service và dùng volume Free hợp lý.

### Thực hiện

### 5.1. Tạo project

1. Đăng nhập Railway bằng GitHub.
2. Hoàn thành account verification.
3. Tạo project mới.
4. Thêm PostgreSQL service.
5. Thêm backend từ GitHub repository.

Project canvas:

```text
Railway Project
├── BE_ChatBot
└── PostgreSQL
```

### 5.2. Backend settings

Root Directory:

```text
/BE_ChatBot
```

Resource:

```text
Replicas: 1
CPU:      tối đa 1 vCPU
RAM:      tối đa 0.5 GB
Volume:   không tạo
```

Pre-deploy command:

```text
python -m src.db.init_db
```

Healthcheck:

```text
/health
```

Bật:

```text
Serverless
Restart on failure
```

### 5.3. PostgreSQL settings

- Dùng volume 0.5 GB duy nhất của project.
- Bật Serverless.
- Không public database nếu không cần truy cập từ local.

### Cách test

Kiểm tra Railway canvas và service settings trước khi deploy.

### Expected output

```text
2 services
1 volume gắn với PostgreSQL
0 volume gắn với BE_ChatBot
```

Backend reference variable phải hiển thị:

```text
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

### Điều kiện hoàn thành

- Có đúng backend và PostgreSQL service.
- Root directory đúng.
- Backend không chiếm volume.
- PostgreSQL dùng private `DATABASE_URL`.

### Kết quả/tiến độ Phase 5

**Trạng thái: ✅ Hoàn thành — 8/8 PASS**

| # | Nội dung kiểm tra | Kết quả | Kết quả chính |
|---|---|---|---|
| 1 | Project và services | ✅ PASS | Project `Vietnam Travel ChatBot` có đúng hai service: `BE_ChatBot` và `Postgres`. |
| 2 | PostgreSQL volume | ✅ PASS | Có đúng một volume `postgres-volume`, dung lượng `500 MB`, mount tại `/var/lib/postgresql/data`. |
| 3 | Backend volume | ✅ PASS | `BE_ChatBot` không gắn volume; ChromaDB tiếp tục được đóng gói trong Docker image. |
| 4 | Monorepo settings | ✅ PASS | Root Directory là `/BE_ChatBot`; Watch Patterns là `/BE_ChatBot/**`. |
| 5 | Database reference | ✅ PASS | Backend dùng private reference `DATABASE_URL=${{Postgres.DATABASE_URL}}`; không dùng public database URL. |
| 6 | Deployment settings | ✅ PASS | Pre-deploy command là `python -m src.db.init_db`; Healthcheck Path là `/health`, timeout `300` giây. |
| 7 | Serverless và restart | ✅ PASS | Serverless bật cho cả `BE_ChatBot` và `Postgres`; Restart Policy là `On Failure`, tối đa `10` lần thử. |
| 8 | Áp dụng hạ tầng | ✅ PASS | Staged changes được áp dụng thành công; Postgres redeploy và trở lại trạng thái `Online` trước khi được tắt thủ công. |

Kết quả kiểm tra ngày 15/07/2026:

- Region: `US West (California, USA)`; số replica: `1`.
- Tài khoản đang ở Trial nên giao diện chỉ hiển thị plan limit `2 vCPU / 1 GB` và không cho chỉnh thủ công. Backend chưa có active deployment nên chưa phát sinh compute; khi chuyển sang Free, giới hạn plan sẽ là `1 vCPU / 0.5 GB`.
- Sau khi xác nhận cấu hình thành công, active deployment của Postgres được `Remove` thủ công để dừng compute trước Phase 6. Service `Postgres`, variables và volume `postgres-volume` vẫn được giữ nguyên.
- `BE_ChatBot` đang offline vì chưa kết nối GitHub source; PostgreSQL chưa có bảng là trạng thái đúng trước khi pre-deploy command chạy ở Phase 6.

---

## Phase 6 — Khai báo biến và deploy backend

### Mục tiêu

Backend Railway khởi động thành công và có public URL.

### Environment variables

```text
DATABASE_URL=${{Postgres.DATABASE_URL}}
SQL_ECHO=false

FRONTEND_URL=https://<netlify-domain>

PERSIST_DIRECTORY=src/db/chroma_db
SYSTEM_PROMPT=src/prompts/system_prompt.md

EMBEDDING_PROVIDER=google
EMBEDDING_MODEL=models/gemini-embedding-001
GEMINI_API_KEY=<secret>

LLM_PROVIDER=ollama_cloud
LLM_MODEL=gemma4:cloud
OLLAMA_API_KEY=<secret>

REWRITE_LLM_PROVIDER=groq
REWRITE_LLM_MODEL=llama-3.1-8b-instant
GROQ_API_KEY=<secret>

RERANKER_PROVIDER=cohere
RERANKER_MODEL_NAME=rerank-v3.5
RERANKER_TOP_N=20
COHERE_API_KEY=<secret>

FIREBASE_CREDENTIALS_JSON=<minified-service-account-json>
```

Không thêm:

```text
HF_TOKEN
NVIDIA_API_KEY
CACHE_FOLDER
HF_HOME
HUGGINGFACE_HUB_CACHE
```

### Thực hiện deploy

Do giới hạn Railway Free vùng Southeast Asia, nên deploy ngoài khoảng **07:00–19:00 giờ Bangkok**. [Railway deployment limits](https://docs.railway.com/deployments/reference)

Sau khi deploy thành công:

```text
Settings
→ Networking
→ Generate Domain
```

### Cách test

Mở Deploy Logs.

### Expected output

Pre-deploy:

```text
Database tables initialized successfully
Process exited with code 0
```

Runtime:

```text
Embedding provider: google
Embedding model: models/gemini-embedding-001
BM25 index built: 600 docs
Application startup complete
Uvicorn running on http://0.0.0.0:<PORT>
```

Railway deployment status:

```text
ACTIVE
HEALTHY
```

Mở:

```text
https://<railway-domain>/health
```

Kết quả:

```json
{ "status": "ok" }
```

### Điều kiện hoàn thành

- Build thành công.
- Pre-deploy thành công.
- Không OOM.
- Railway healthcheck pass.
- Có public Railway domain.

### Kết quả/tiến độ Phase 6

> ⏳ Chưa triển khai. Kết quả kiểm tra sẽ được cập nhật sau khi hoàn thành Phase 6.

---

## Phase 7 — Kết nối Netlify với Railway

### Mục tiêu

Frontend production gọi được backend Railway qua HTTPS.

### Thực hiện

Trong Netlify:

```text
Site configuration
→ Environment variables
→ VITE_FASTAPI_URL
```

Giá trị:

```text
https://<railway-domain>
```

Trong Railway:

```text
FRONTEND_URL=https://<netlify-domain>
```

Không thêm `/` ở cuối hai URL nếu frontend hiện tại không sử dụng.

Trigger redeploy Netlify.

### Test 1 — Authentication

1. Mở frontend Netlify.
2. Đăng nhập Google.
3. Kiểm tra request `/auth/firebase-login`.

#### Expected output

```text
HTTP 200
User information returned
```

### Test 2 — Streaming chat

Gửi một câu hỏi:

```text
Lập lịch trình du lịch Đà Lạt trong 2 ngày
```

#### Expected output

Browser Network:

```text
POST /chat/stream
Status: 200
Content-Type: text/event-stream
```

UI:

- Text xuất hiện dần.
- Không chờ toàn bộ response mới hiển thị.
- Timeline/mindmap nhận được trip-plan JSON.
- Không có CORS error.

### Test 3 — PostgreSQL persistence

1. Gửi chat để tạo conversation.
2. Redeploy backend Railway.
3. Refresh frontend.
4. Mở lại conversation.

#### Expected output

- Conversation vẫn còn.
- Messages vẫn còn.
- ChromaDB vẫn báo 600 documents sau redeploy.

### Điều kiện hoàn thành

- Netlify gọi được Railway.
- Firebase auth pass.
- SSE streaming pass.
- PostgreSQL giữ dữ liệu qua redeploy.

### Kết quả/tiến độ Phase 7

**Trạng thái: 🟡 Hoàn tất cấu hình production — 6/8 PASS, 2/8 DEFERRED**

| # | Nội dung kiểm tra | Kết quả | Kết quả chính |
|---|---|---|---|
| 1 | Netlify build | ✅ PASS | Builds được kích hoạt lại; frontend build và publish thành công từ code mới trên branch `main`. |
| 2 | Monorepo settings | ✅ PASS | Base directory `FE_ChatBot`, build command `npm run build`, publish directory `FE_ChatBot/dist`. |
| 3 | Backend URL | ✅ PASS | Netlify dùng `VITE_FASTAPI_URL=https://bechatbot-production.up.railway.app`; Railway `/health` trả `{"status":"ok"}`. |
| 4 | Firebase Web config | ✅ PASS | Sáu biến `VITE_FIREBASE_*` được khai báo trên Netlify; frontend không còn lỗi `Missing Firebase config`. |
| 5 | Firebase authorized domain | ✅ PASS | Domain `mellowai.netlify.app` được thêm vào Firebase Authentication Authorized domains. |
| 6 | Authentication | ✅ PASS | Frontend production hiển thị bình thường và đăng nhập Google thành công. |
| 7 | SSE streaming chat | ⏸️ DEFERRED | Chưa chạy test `/chat/stream`; Railway backend chỉ bật khi cần integration test hoặc demo. |
| 8 | PostgreSQL persistence | ⏸️ DEFERRED | Chưa chạy test tạo conversation rồi redeploy; không đánh dấu PASS khi chưa có bằng chứng runtime. |

Kết quả triển khai ngày 15–16/07/2026:

- Frontend production: `https://mellowai.netlify.app`.
- Backend production: `https://bechatbot-production.up.railway.app`.
- Dependency `react-markdown` được chuyển vào đúng manifest `FE_ChatBot/package.json`; local Vite build và Netlify build đều thành công.
- Google login chỉ hoạt động sau khi thêm Netlify domain vào Firebase Authorized domains.
- Hai test SSE và persistence được chủ động hoãn vì workflow chính là dev/test local bằng backend Docker; Railway được deploy theo nhu cầu.

---

## Phase 8 — Kiểm tra Serverless và chi phí Free

### Mục tiêu

Đảm bảo service không chạy liên tục và không vượt $1 monthly credit.

### Thực hiện

1. Không gửi request trong 15 phút.
2. Kiểm tra trạng thái backend và PostgreSQL.
3. Gửi request `/health` lại.
4. Theo dõi Metrics và Usage.

Thiết lập:

```text
Usage email alert:   $0.50
Compute hard limit:  $1.00
```

### Expected output

Sau thời gian idle:

```text
Backend: asleep/serverless inactive
PostgreSQL: asleep hoặc không phát sinh compute đáng kể
```

Request đầu tiên:

```text
Có cold-start delay
Sau đó GET /health trả HTTP 200
```

Usage:

```text
Projected monthly usage <= $1
```

### Nếu không đạt

| Hiện tượng             | Xử lý                                                       |
| ---------------------- | ----------------------------------------------------------- |
| Backend không sleep    | Kiểm tra connection pool, telemetry hoặc background request |
| PostgreSQL không sleep | Xem xét external free serverless PostgreSQL                 |
| RAM vượt 0.5 GB        | Quay lại Phase 1 để loại dependency                         |
| OOM liên tục           | Railway Free không phù hợp, chuyển Hobby                    |
| Credit gần hết         | Tạm remove deployment hoặc nâng cấp sau khi ổn định         |

### Điều kiện hoàn thành

- Backend có thể sleep và wake.
- Cold start chấp nhận được.
- Usage dự kiến nằm trong $1 credit.
- Không có restart hoặc memory leak.

### Kết quả/tiến độ Phase 8

**Trạng thái: 🟡 Xác nhận một phần — 2/5 PASS, 3/5 DEFERRED**

| # | Nội dung kiểm tra | Kết quả | Kết quả chính |
|---|---|---|---|
| 1 | PostgreSQL serverless sleep | ✅ PASS | Postgres tự chuyển sang trạng thái sleep khi không có traffic. |
| 2 | Runtime resource baseline | ✅ PASS | Backend dùng khoảng `235.49 MB` RAM, CPU gần `0 vCPU` khi idle, request error rate `0%`, không OOM hoặc restart. |
| 3 | Backend sleep/wake | ⏸️ DEFERRED | Không test tự sleep/wake; active deployment được `Remove` và chỉ deploy lại khi cần test hoặc demo. |
| 4 | Backend cold start | ⏸️ DEFERRED | Chưa đo thời gian cold start vì không dùng backend Railway cho dev/test hằng ngày. |
| 5 | Usage và budget limits | ⏸️ DEFERRED | Chưa xác nhận projected monthly usage, email alert `$0.50` hoặc hard limit `$1.00`; không ghi nhận PASS khi chưa cấu hình/đo. |

### Quyết định vận hành

- Dev/test hằng ngày dùng backend Docker local và PostgreSQL local; không cần giữ Railway chạy liên tục.
- Khi cần integration test hoặc demo cloud: deploy Postgres trước, chờ `Online`, sau đó deploy `BE_ChatBot` và kiểm tra `/health`.
- Sau khi test xong: `Remove` active deployment của backend; Postgres có thể tự sleep hoặc được `Remove` thủ công. Service, variables và `postgres-volume` vẫn được giữ lại.
- Cách vận hành này giảm Railway compute usage nhưng không thay thế bằng chứng cho backend auto sleep, cold start và monthly usage; các mục đó tiếp tục ở trạng thái `DEFERRED`.

### Flow dev/test Docker local

Mở Docker Desktop và PostgreSQL local, sau đó vào backend:

```powershell
cd D:\KLTN\Project\BE_ChatBot
docker version
Test-NetConnection localhost -Port 5432
```

Nếu code backend và environment không đổi, container cũ vẫn tồn tại:

```powershell
docker start be-chatbot-deploy
```

Nếu container đã bị xóa hoặc cần nạp lại `.env`/Firebase credentials, dùng image hiện tại:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_docker_be.ps1
```

Nếu code backend, `Dockerfile`, `requirements.deploy.txt`, system prompt hoặc ChromaDB thay đổi:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_docker_be.ps1 -Build
```

Khởi tạo bảng khi dùng database mới:

```powershell
docker exec be-chatbot-deploy python -m src.db.init_db
```

Kiểm tra backend:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
docker logs -f --tail 100 be-chatbot-deploy
docker stats be-chatbot-deploy --no-stream
```

Mở terminal khác để chạy frontend local:

```powershell
cd D:\KLTN\Project\FE_ChatBot
npm.cmd run dev
```

Luồng dữ liệu local:

```text
FE localhost:5173
→ BE Docker localhost:8000
→ PostgreSQL local qua host.docker.internal:5432
→ database kltn_chatbot_deploy
```

Kết thúc phiên test:

```powershell
docker stop be-chatbot-deploy
```

Nếu muốn xóa container nhưng giữ image và PostgreSQL local:

```powershell
docker rm -f be-chatbot-deploy
```

---

## Phase 9 — Ổn định trước khi upgrade

### Mục tiêu

Chứng minh deployment workflow đủ ổn định trước khi chuyển Hobby.

### Quy trình kiểm tra sau mỗi lần đổi logic

```text
1. Test local Python
2. Build Docker
3. Test /health
4. Test một chat request
5. Push Git
6. Railway deploy
7. Test Netlify production
8. Kiểm tra RAM và logs
```

### Expected output sau ba lần cập nhật liên tiếp

```text
Docker build pass:       3/3
Railway deploy pass:     3/3
Healthcheck pass:        3/3
Firebase login pass:     3/3
SSE chat pass:           3/3
PostgreSQL persistence:  pass
OOM/restart:             0
```

### Chỉ upgrade Hobby khi

- RAM cần lớn hơn 0.5 GB.
- Cần deploy trong giờ Railway Free bị giới hạn.
- Cold start ảnh hưởng demo.
- PostgreSQL hoặc backend không sleep.
- Monthly usage vượt $1.
- Cần uptime ổn định hoặc nhiều người dùng đồng thời.

### Kết quả/tiến độ Phase 9

> ⏳ Chưa triển khai. Kết quả kiểm tra sẽ được cập nhật sau khi hoàn thành Phase 9.

---

## Public interface và cấu hình mới

### API mới

```http
GET /health
```

### Environment variable mới

```text
FIREBASE_CREDENTIALS_JSON
```

### Không thay đổi

```text
POST /chat
POST /chat/stream
POST /auth/firebase-login
GET/PATCH/DELETE /conversations
```

## Tiêu chí hoàn thành toàn bộ

Deployment được xem là hoàn thành khi:

- Backend không cài hoặc load local AI model.
- Docker image dưới 4 GB và mục tiêu dưới 1 GB.
- Runtime RAM mục tiêu dưới 430 MiB.
- Railway healthcheck pass.
- Netlify đăng nhập và chat streaming thành công.
- ChromaDB giữ đúng 600 vectors.
- PostgreSQL giữ conversation sau redeploy.
- Backend sleep/wake được.
- Chi phí dự kiến nằm trong $1 Railway Free credit.
