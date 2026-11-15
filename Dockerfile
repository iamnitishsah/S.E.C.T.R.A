# API image: the FastAPI app over the research graph. No model runs in the container;
# it calls the LLM, embedding and rerank APIs, MySQL and Qdrant over the network.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first, against an empty package, so this layer is rebuilt only when pyproject.toml changes.
# The install is editable (-e) because the code finds configs/ relative to /app/src.
COPY pyproject.toml ./
RUN mkdir -p src/sectra && touch src/sectra/__init__.py && pip install -e .

COPY src ./src
COPY configs ./configs

# Run as an unprivileged user; data/logs is the only place the app writes.
RUN useradd --create-home --uid 1000 sectra && mkdir -p data/logs && chown -R sectra:sectra /app
USER sectra

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)" || exit 1

# One worker: the rate limiter and the caches live in process memory.
CMD ["uvicorn", "sectra.api.main:app", "--host", "0.0.0.0", "--port", "8000"]