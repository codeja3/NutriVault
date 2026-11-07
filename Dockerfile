# NutriVault Turnkey Local Container
FROM python:3.12-slim

# Install uv from official distroless image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set environment
ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    NUTRIVAULT_HOST=0.0.0.0 \
    NUTRIVAULT_PORT=8080 \
    NUTRIVAULT_DB=/app/data/nutrivault.db

WORKDIR /app

# Create non-root user and persistent storage directory
RUN useradd -m -u 1000 nutrivault && \
    mkdir -p /app/data && \
    chown -R nutrivault:nutrivault /app

# Copy dependency specifications first for caching
COPY --chown=nutrivault:nutrivault pyproject.toml uv.lock ./

# Switch to non-root user
USER nutrivault

# Synchronize runtime dependencies
RUN uv sync --frozen --no-dev

# Copy application source code and documents
COPY --chown=nutrivault:nutrivault src/ ./src/
COPY --chown=nutrivault:nutrivault PRD.md SPEC.md MANUAL.md README.md ./

VOLUME ["/app/data"]
EXPOSE 8080

CMD ["uv", "run", "python", "-m", "src.api", "0.0.0.0", "8080", "/app/data/nutrivault.db"]
