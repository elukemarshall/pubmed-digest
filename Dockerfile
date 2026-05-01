FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
COPY tests ./tests
COPY evals ./evals

RUN uv sync --frozen --all-groups

CMD ["uv", "run", "python", "-c", "import pubmed_digest; print('pubmed-digest container ready')"]
