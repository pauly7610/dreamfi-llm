FROM python:3.11-slim

WORKDIR /app

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml alembic.ini /app/
COPY dreamfi /app/dreamfi
COPY evals /app/evals
COPY generators /app/generators
COPY scripts /app/scripts

RUN pip install -U pip && pip install .

EXPOSE 5001

CMD ["sh", "-c", "alembic upgrade head && uvicorn dreamfi.api.app:app --host 0.0.0.0 --port ${PORT:-5001}"]
