FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.deploy.txt .
RUN python -m pip install --no-cache-dir -r requirements.deploy.txt

COPY . .

CMD ["sh", "-c", "python -m uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
