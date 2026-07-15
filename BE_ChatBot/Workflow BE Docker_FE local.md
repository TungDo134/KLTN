# Workflow BE Docker + FE local

## Mục lục

- [Quick Start](#quick-start)
- [Lần đầu clone/pull code](#lần-đầu-clonepull-code)
- [1. Khởi động Docker và PostgreSQL](#1-khởi-động-docker-và-postgresql)
- [2. Chuẩn bị environment cho container](#2-chuẩn-bị-environment-cho-container)
- [3. Trường hợp BE không thay đổi code](#3-trường-hợp-be-không-thay-đổi-code)
- [4. Kiểm tra backend sẵn sàng](#4-kiểm-tra-backend-sẵn-sàng)
- [5. Khởi động FE local](#5-khởi-động-fe-local)
- [Khi BE thay đổi code](#khi-be-thay-đổi-code-hoặc-logic)
- [Khi nào cần rebuild?](#khi-nào-cần-rebuild)
- [Theo dõi trong lúc test](#theo-dõi-trong-lúc-test)
- [Kết thúc phiên làm việc](#kết-thúc-phiên-làm-việc)

## Quick Start (dành cho đã setup build code deploy trước đó)

> Các lệnh dưới đây chỉ chạy được sau khi đã có `.env`, Firebase credentials,
> PostgreSQL local và database `kltn_chatbot_deploy`. Xem mục
> [Lần đầu clone/pull code](#lần-đầu-clonepull-code) nếu máy chưa từng chạy project.

- `run_docker_be.ps1`: xóa container cũ → tạo container mới từ image hiện tại → chạy BE bằng Docker.

```powershell
powershell -ExecutionPolicy Bypass -File .\run_docker_be.ps1
```

- `run.bat`: chạy BE trực tiếp trên máy cá nhân bằng Python/venv, không qua Docker.

- `run_docker_be.ps1 -Build`: build lại image theo code mới → xóa container cũ → tạo container mới từ image vừa cập nhật.

```powershell
powershell -ExecutionPolicy Bypass -File .\run_docker_be.ps1 -Build
```

- `Stop/Start trong Docker Desktop`: chỉ tắt/mở lại container hiện có → không cập nhật code hoặc image.

## LƯU Ý:

- Dừng nhưng giữ container

```powershell
docker stop be-chatbot-deploy
```

- Chạy lại container đã dừng

```powershell
docker start be-chatbot-deploy
```

- Xóa container, vẫn giữ image và database

```powershell
docker rm -f be-chatbot-deploy
```

> `Có thể dùng nút Stop/Start trong Docker Desktop thay cho docker stop/start`

---

## Lần đầu clone/pull code

### Điều kiện cần

- Đã cài Git, Docker Desktop và PostgreSQL.
- Docker Desktop đang chạy Linux containers.
- PostgreSQL đang chạy tại `localhost:5432`.
- Đã nhận file `.env` và Firebase service account qua kênh an toàn. Hai file
  này không được commit lên Git.
- Repo đã chứa `src/db/chroma_db/chroma.sqlite3`.

Kiểm tra ChromaDB sau khi clone:

```powershell
Test-Path .\src\db\chroma_db\chroma.sqlite3
```

Expected:

```text
True
```

### Bước 1 — Clone và mở đúng thư mục

```powershell
git clone <repository-url>
cd <repository-folder>\BE_ChatBot
```

Nếu repo đã có sẵn:

```powershell
cd <repository-folder>
git pull
cd .\BE_ChatBot
```

### Bước 2 — Tạo database PostgreSQL

Tạo Database:

```sql
CREATE DATABASE kltn_chatbot_deploy;
```

Script Docker chỉ kết nối database; `script không tự tạo` database PostgreSQL.

### Bước 3 — Chuẩn bị `.env`

Repo hiện không có `.env` => cần nhận cấu hình từ người quản lý
project và tự tạo `BE_ChatBot/.env`. Không commit file này.

Ngoài các API key của project, cần phân biệt hai database:

```env
# Python local qua run.bat
DATABASE_URL=postgresql+psycopg2://postgres:<password>@localhost:5432/kltn

# Backend chạy trong Docker
DOCKER_DATABASE_URL=postgresql+psycopg2://postgres:<password>@host.docker.internal:5432/kltn_chatbot_deploy
```

Tên biến trong `.env` không được có khoảng trắng trước dấu `=`.

### Bước 4 — Thêm Firebase credentials (trước đó login = gg được rồi thì thoi)

Đặt service account tại:

```text
BE_ChatBot/config/firebase-service-account.json
```

`run_docker_be.ps1` tự đọc file này và truyền JSON vào container. Không cần set
`FIREBASE_CREDENTIALS_JSON` thủ công.

### Bước 5 — Kiểm tra Docker và PostgreSQL

```powershell
docker version
Test-NetConnection localhost -Port 5432
```

Expected:

```text
Docker có cả Client và Server
TcpTestSucceeded : True
```

### Bước 6 — Build image và chạy container lần đầu

```powershell
powershell -ExecutionPolicy Bypass -File .\run_docker_be.ps1 -Build
```

Script sẽ:

1. Build image `be-chatbot:railway-free`.
2. Xóa container `be-chatbot-deploy` cũ nếu có.
3. Đọc `DOCKER_DATABASE_URL` và Firebase credentials.
4. Tạo container mới với giới hạn `1 CPU / 512 MB RAM`.
5. Mở backend tại `http://127.0.0.1:8000`.

### Bước 7 — Khởi tạo bảng database một lần

```powershell
docker exec be-chatbot-deploy python -m src.db.init_db
```

Expected:

```text
Database tables initialized successfully
```

Lệnh sử dụng `create_all`, vì vậy chạy lại không xóa database hoặc dữ liệu cũ.

### Bước 8 — Kiểm tra backend

```powershell
docker logs --tail 100 be-chatbot-deploy
```

- Mở terminal mới paste:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected:

```text
BM25 index built: 600 docs
Application startup complete
status
------
ok
```

Sau khi hoàn tất các bước trên, những lần chạy tiếp theo không cần build lại
nếu code backend không thay đổi.

> `Hoàn thành Setup`

---

# Các mục dưới đây là để thao tác cụ thể với từng vấn đề

## 1. Khởi động Docker và PostgreSQL

Mở Docker Desktop, sau đó kiểm tra:

```powershell
docker version
```

Kiểm tra PostgreSQL local:

```powershell
Test-NetConnection localhost -Port 5432
```

Expected:

```text
TcpTestSucceeded : True
```

## 2. Chuẩn bị environment cho container

Mở PowerShell tại backend:

```powershell
cd D:\KLTN\Project\BE_ChatBot
```

Kiểm tra các file bắt buộc:

```powershell
Test-Path .\.env
Test-Path .\config\firebase-service-account.json
```

Expected:

```text
True
True
```

Trong `.env`, Docker phải có cấu hình riêng:

```env
DOCKER_DATABASE_URL=postgresql+psycopg2://postgres:<password>@host.docker.internal:5432/kltn_chatbot_deploy
```

`run_docker_be.ps1` tự nạp Firebase JSON và chuyển
`DOCKER_DATABASE_URL` thành `DATABASE_URL` bên trong container. Script cũng tự
khôi phục environment của PowerShell sau khi chạy.

## 3. Trường hợp BE không thay đổi code

### Nếu container cũ vẫn tồn tại

Kiểm tra:

```powershell
docker ps -a
```

Nếu thấy `be-chatbot-deploy`, chỉ cần:

```powershell
docker start be-chatbot-deploy
```

Container giữ nguyên environment và port từ lần tạo trước.

### Nếu container đã bị xóa

Tạo lại từ image có sẵn bằng script:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_docker_be.ps1
```

Script sẽ xóa container cùng tên nếu còn tồn tại và tạo lại từ image hiện tại.

## 4. Kiểm tra backend sẵn sàng

Xem log:

```powershell
docker logs -f be-chatbot-deploy
```

Khi thấy:

```text
BM25 index built: 600 docs
Application startup complete
Uvicorn running on http://0.0.0.0:8000
```

nhấn `Ctrl+C`.

Kiểm tra health:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected:

```text
status
------
ok
```

## 5. Khởi động FE local

Mở PowerShell khác:

```powershell
cd D:\KLTN\Project\FE_ChatBot

npm run dev
```

Mở:

```text
http://localhost:5173
```

Luồng hoạt động:

```text
FE localhost:5173
    ↓
BE Docker localhost:8000
    ↓
PostgreSQL trên Windows qua host.docker.internal:5432
```

# Khi BE thay đổi code hoặc logic

Container không tự cập nhật source code. Chạy một lệnh tại `BE_ChatBot`:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_docker_be.ps1 -Build
```

Script tự thực hiện theo thứ tự:

```text
Build image mới
→ xóa container cũ
→ đọc environment
→ tạo container mới
```

Docker sử dụng cache nên nếu `requirements.deploy.txt` không đổi, bước cài
dependency thường nhanh hơn lần đầu. Dữ liệu PostgreSQL không bị xóa vì database
chạy bên ngoài container.

Cuối cùng kiểm tra logs và `/health` theo mục 4.

# Khi nào cần rebuild?

| Thay đổi                      | Rebuild image?                      |
| ----------------------------- | ----------------------------------- |
| Sửa Python backend            | Có                                  |
| Sửa `Dockerfile`              | Có                                  |
| Sửa `requirements.deploy.txt` | Có                                  |
| Sửa system prompt             | Có                                  |
| Thay ChromaDB                 | Có                                  |
| Chỉ thay biến `.env`          | Không, nhưng phải tạo lại container |
| Đổi Firebase credentials      | Không, nhưng phải tạo lại container |
| Dữ liệu PostgreSQL thay đổi   | Không                               |
| Chỉ sửa frontend              | Không                               |

`docker restart` không đọc lại `.env`. Khi environment thay đổi, phải xóa và tạo
container mới.

# Theo dõi trong lúc test

Xem log:

```powershell
docker logs -f --tail 100 be-chatbot-deploy
```

Xem RAM:

```powershell
docker stats be-chatbot-deploy --no-stream
```

Kiểm tra trạng thái:

```powershell
docker inspect be-chatbot-deploy `
  --format 'Status={{.State.Status}} OOMKilled={{.State.OOMKilled}}'
```

# Kết thúc phiên làm việc

## Dừng FE

Trong terminal chạy Vite:

```text
Ctrl+C
```

## Lựa chọn 1 — Giữ container để lần sau start nhanh

```powershell
docker stop be-chatbot-deploy
```

Lần sau:

```powershell
docker start be-chatbot-deploy
```

## Lựa chọn 2 — Xóa container, giữ image

```powershell
docker rm -f be-chatbot-deploy
```

Database PostgreSQL không bị mất. Lần sau chỉ cần tạo lại container.

Lần sau tạo lại container bằng:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_docker_be.ps1
```

`run_docker_be.ps1` chỉ dùng Firebase JSON và `DATABASE_URL` tạm thời trong lúc
tạo container, sau đó tự khôi phục hoặc xóa các biến tạm khỏi PowerShell.

Workflow ngắn gọn nhất:

```text
Không đổi BE:
Docker Desktop → PostgreSQL → docker start → npm.cmd run dev

Có đổi BE:
run_docker_be.ps1 -Build → kiểm tra health → npm.cmd run dev

Kết thúc:
Ctrl+C FE → docker stop hoặc docker rm
```
