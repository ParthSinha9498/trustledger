FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
RUN uv pip install --no-cache \
    "astropods-adapter-core==0.9.1" \
    "opentelemetry-sdk" \
    "opentelemetry-exporter-otlp-proto-http" \
    "opentelemetry-instrumentation-openai"
COPY backend backend
ENV PATH="/app/.venv/bin:$PATH" PYTHONPATH=/app PYTHONUNBUFFERED=1
CMD ["python", "-m", "backend.worker.astro"]
