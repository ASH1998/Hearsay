FROM python:3.12.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY apps/api/src apps/api/src
COPY packages/content packages/content

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["sh", "-ec", "alembic upgrade head && exec uvicorn hearsay_api.main:app --app-dir apps/api/src --host 0.0.0.0 --port 8000"]
