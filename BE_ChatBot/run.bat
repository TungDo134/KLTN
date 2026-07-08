c:: Dung cho case khong ctrl C de shutdown duoc

:: Kill Python process
@echo off
echo Killing all Python processes...
taskkill /IM python.exe /F >nul 2>&1

:: Start FastAPI
echo Starting FastAPI...
uvicorn src.main:app --reload