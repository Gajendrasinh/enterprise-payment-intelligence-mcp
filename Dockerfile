# Multi-stage build for a lightweight, secure production image
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir --user .

# Final runtime image
FROM python:3.11-slim AS runtime

WORKDIR /app

# Create a non-root group and user
RUN groupadd -g 10001 mcpuser && \
    useradd -u 10001 -g mcpuser -m -s /bin/bash mcpuser

# Copy installed packages from builder to runtime
COPY --from=builder /root/.local /home/mcpuser/.local
COPY --from=builder /app/src /app/src
COPY pyproject.toml README.md ./

# Update PATH for the non-root user
ENV PATH=/home/mcpuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

# Set ownership to non-root user
RUN chown -R mcpuser:mcpuser /app /home/mcpuser

USER mcpuser

# Default to stdio transport for MCP agent communication
ENV MCP_TRANSPORT=stdio \
    LOG_LEVEL=INFO \
    ENVIRONMENT=production

ENTRYPOINT ["python", "-m", "payment_mcp.server"]
