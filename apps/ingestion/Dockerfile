# syntax=docker/dockerfile:1.7
# kuberag-ingestion: Prefect-oriented ingestion image on Chainguard Python.
#
# Build from the repository root:
#   docker build -f apps/ingestion/Dockerfile -t kuberag-ingestion:local .
#
# Free Chainguard tags float on :latest / :latest-dev (currently CPython 3.14).
# Versioned 3.12/3.13 tags need Chainguard enterprise, so the builder installs
# managed CPython 3.13 via uv into /python and the runtime copies that
# interpreter with the venv. Release overlays must pin by immutable digest
# before production deploy (SEC-001).

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

# Monorepo hatch packaging currently includes both Python packages.
COPY pyproject.toml uv.lock README.md ./
COPY apps/rag-api/src ./apps/rag-api/src
COPY apps/ingestion/src ./apps/ingestion/src
COPY apps/ingestion/alembic.ini ./apps/ingestion/alembic.ini
COPY apps/ingestion/migrations ./apps/ingestion/migrations

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable --extra embedding --python "${PYTHON_VERSION}"

FROM ${PYTHON_RUNTIME_IMAGE} AS runtime
USER root

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ALEMBIC_CONFIG=/app/apps/ingestion/alembic.ini

WORKDIR /app

# Chainguard Python runs as non-root uid 65532 by default.
# Copy managed CPython (matches requires-python) plus the virtualenv.
COPY --from=builder --chown=65532:65532 /python /python
COPY --from=builder --chown=65532:65532 /app/.venv /app/.venv
COPY --from=builder --chown=65532:65532 /app/apps/ingestion /app/apps/ingestion

USER 65532

# Distroless runtime: no shell. Do not add shell-based HEALTHCHECK here.
# Default command only proves the image imports; workers override CMD later, e.g.
#   prefect worker start --pool kuberag-ingestion
ENTRYPOINT []
CMD [ \
    "/app/.venv/bin/python", \
    "-c", \
    "from ingestion.flows.ingest import DAILY_INGEST_FLOW_NAME, deployment_schedule; print(DAILY_INGEST_FLOW_NAME); print(deployment_schedule())" \
]
