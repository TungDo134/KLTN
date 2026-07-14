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

> ⏳ Chưa triển khai. Kết quả kiểm tra sẽ được cập nhật sau khi hoàn thành Phase 2.

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

> ⏳ Chưa triển khai. Kết quả kiểm tra sẽ được cập nhật sau khi hoàn thành Phase 3.

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

> ⏳ Chưa triển khai. Kết quả kiểm tra sẽ được cập nhật sau khi hoàn thành Phase 4.

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

> ⏳ Chưa triển khai. Kết quả kiểm tra sẽ được cập nhật sau khi hoàn thành Phase 5.

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

> ⏳ Chưa triển khai. Kết quả kiểm tra sẽ được cập nhật sau khi hoàn thành Phase 7.

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

> ⏳ Chưa triển khai. Kết quả kiểm tra sẽ được cập nhật sau khi hoàn thành Phase 8.

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
