# Neptune MCP Server Dockerfile
# Build a containerized MCP server that can be run with Docker

FROM python:3.13-slim

# Install git (required for neptune-common dependency from GitHub)
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy all source files
COPY pyproject.toml uv.lock* README.md ./
COPY src/ ./src/

# Install dependencies and package
RUN uv sync --frozen --no-dev

# Create config directory for Neptune
RUN mkdir -p /root/.config/neptune

# Environment variables (can be overridden at runtime)
ENV NEPTUNE_API_BASE_URL=https://beta.neptune.dev/v1

# Default to stdio transport for MCP
# Override with --transport=http --host=0.0.0.0 --port=8001 for HTTP
ENTRYPOINT ["uv", "run", "neptune", "mcp"]

# Default arguments (stdio transport)
CMD []
