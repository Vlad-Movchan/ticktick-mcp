FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

# Install dependencies (cached layer)
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

# Copy source
COPY productivity_mcp/ ./productivity_mcp/

ENV PATH="/app/.venv/bin:$PATH"
ENV TICKTICK_TOKEN_PATH=/data/tokens.json

EXPOSE 8000

CMD ["productivity-mcp"]
