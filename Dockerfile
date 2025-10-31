# syntax=docker/dockerfile:1.6
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=on

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      libjpeg62-turbo-dev \
      zlib1g-dev \
      libwebp-dev \
      libtiff-dev \
      libopenjp2-7-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
COPY tests ./tests

RUN pip install --upgrade pip && \
    pip wheel --wheel-dir /app/wheels --no-deps .

FROM python:3.12-slim

ENV PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=on \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PERSIST_DIR=/data

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libjpeg62-turbo \
      zlib1g \
      libwebp7 \
      libtiff6 \
      libopenjp2-7 \
      tzdata && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/wheels /wheels
RUN pip install --upgrade pip && \
    pip install --no-cache-dir /wheels/*

COPY src ./src
COPY README.md ./
COPY AGENTS.md ./

VOLUME ["/data"]

CMD ["python", "-m", "bot.main"]
