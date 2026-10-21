FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend backend
COPY docker/start.sh docker/seed.py docker/
RUN chmod +x docker/start.sh
ENV PATH="/app/.venv/bin:$PATH" PYTHONPATH=/app PYTHONUNBUFFERED=1
# One image, five roles. Pick one with the argument:
#   docker/start.sh api | brand-node | paypal-node | worker | seed
# docker-compose.yml and render.yaml pass it as the command.
CMD ["/app/docker/start.sh", "api"]
