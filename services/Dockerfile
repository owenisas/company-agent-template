# Phase 2 knowledge services image.
FROM python:3.12-slim-bookworm

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

COPY pyproject.toml README.md ./
COPY apps ./apps
COPY packages ./packages

RUN pip install --no-cache-dir .

EXPOSE 8081 8082 8083

CMD ["uvicorn", "apps.knowledge_api.main:app", "--host", "0.0.0.0", "--port", "8081"]
