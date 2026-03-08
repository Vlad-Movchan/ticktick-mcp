FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

# Install dependencies only (skip the project itself for better layer caching)
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy source and install the project as a proper wheel (not editable)
COPY productivity_mcp/ ./productivity_mcp/
RUN uv sync --frozen --no-dev --no-editable

ENV PATH="/app/.venv/bin:$PATH"
ENV TICKTICK_TOKEN_PATH=/data/tokens.json

EXPOSE 8000

CMD ["productivity-mcp"]
