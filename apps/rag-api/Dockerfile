# syntax=docker/dockerfile:1.7
# The API imports the shared E5 provider, so it needs the embedding extra and
# the ingestion package even though the HTTP application lives under rag-api.
ARG UV_VERSION=0.11.15
ARG PYTHON_DEV_IMAGE=cgr.dev/chainguard/python:latest-dev
ARG PYTHON_RUNTIME_IMAGE=cgr.dev/chainguard/python:latest
ARG PYTHON_VERSION=3.13

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM ${PYTHON_DEV_IMAGE} AS builder
ARG PYTHON_VERSION
USER root
COPY --from=uv /uv /uvx /usr/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_HTTP_TIMEOUT=120 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_PYTHON_INSTALL_DIR=/python \
    PATH="/app/.venv/bin:/usr/bin:$PATH"
WORKDIR /app

RUN uv python install "${PYTHON_VERSION}"
COPY pyproject.toml uv.lock README.md ./
COPY apps/rag-api/src ./apps/rag-api/src
COPY apps/ingestion/src ./apps/ingestion/src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable --extra embedding --python "${PYTHON_VERSION}"

FROM ${PYTHON_RUNTIME_IMAGE} AS runtime
USER root
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=builder --chown=65532:65532 /python /python
COPY --from=builder --chown=65532:65532 /app/.venv /app/.venv
COPY --from=builder --chown=65532:65532 /app/apps/rag-api /app/apps/rag-api
COPY --from=builder --chown=65532:65532 /app/apps/ingestion /app/apps/ingestion

USER 65532
EXPOSE 8000
# Chainguard Python has a Python ENTRYPOINT. Clear it so Kubernetes commands
# and the local smoke target can invoke the venv executable explicitly.
ENTRYPOINT []
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
