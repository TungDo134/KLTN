@echo off
cd /d "%~dp0"

echo Dang khoi dong FastAPI bang moi truong .venv-deploy-test...
echo Backend se chay tai http://127.0.0.1:8000

".venv-deploy\Scripts\python.exe" -m uvicorn src.main:app --host 127.0.0.1 --port 8000
