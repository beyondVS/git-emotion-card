FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Set the project environment path to outside the workdir
ENV UV_PROJECT_ENVIRONMENT="/opt/venv"

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Add the virtual environment to the PATH so that the installed tools are found
ENV PATH="/opt/venv/bin:$PATH"

# Copy the project into the image
COPY . /app

RUN chmod +x /app/entrypoint.sh

# Install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Set the entrypoint to our script
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]

# Run the Django development server by default
CMD ["uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--reload"]

