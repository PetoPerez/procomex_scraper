FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY README.md ./
COPY requirements.txt ./
COPY vendor /app/vendor

ENV PIP_DEFAULT_TIMEOUT=120
ENV PIP_NO_CACHE_DIR=off
RUN python -m pip install --upgrade pip setuptools wheel && \
    python -m pip install --no-index --find-links /app/vendor --no-cache-dir -r requirements.txt
# Playwright is optional (used only for JS-rendered pages). To enable,
# add it to `requirements.txt` and uncomment the line below.
# RUN playwright install --with-deps
COPY . /app

ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "main.py"]
