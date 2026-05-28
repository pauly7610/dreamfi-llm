FROM golang:1.24-bookworm AS go-builder

WORKDIR /src

COPY go.mod go.sum /src/
RUN go mod download

COPY cmd /src/cmd
COPY internal /src/internal
COPY web /src/web

RUN go build -o /out/dreamfi ./cmd/dreamfi

FROM python:3.11-slim

WORKDIR /app

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

COPY pyproject.toml alembic.ini /app/
COPY dreamfi /app/dreamfi
COPY evals /app/evals
COPY generators /app/generators
COPY scripts /app/scripts
COPY --from=go-builder /out/dreamfi /usr/local/bin/dreamfi

RUN pip install -U pip && pip install .

EXPOSE 8080

CMD ["sh", "-c", "alembic upgrade head && exec dreamfi"]
