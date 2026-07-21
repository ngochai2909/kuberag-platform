# Agent Source Base

A production-minded starting point for a FastAPI service backed by a LangChain agent running
on LangGraph. It provides a real tool-calling loop, thread-scoped memory, bounded execution,
safe API errors, structured logs, API-key protection, deterministic tests, Docker, and CI.

The base deliberately includes one read-only calculator tool and no database, vector store,
write tool, or raw-prompt telemetry. Add those only when a project has a concrete requirement.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- An OpenAI API key for live chat requests

## Quick start

```bash
cp .env.example .env
make setup
make run
```

Open `http://localhost:8000/docs` in development. Without `OPENAI_API_KEY`, the application
starts for local inspection, `/health/live` remains healthy, `/health/ready` returns 503, and
the chat endpoint is unavailable.

Configure at least:

```dotenv
OPENAI_API_KEY=replace-with-a-real-secret
```

Then call the API:

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"What is (27 * 14) + 5?"}'
```

Reuse the returned `thread_id` in later requests to continue the same in-memory conversation.

## Production configuration

Production mode fails fast unless authentication and the model provider are configured:

```dotenv
APP_ENV=production
API_AUTH_ENABLED=true
APP_API_KEY=generate-a-long-random-secret
OPENAI_API_KEY=replace-with-a-real-secret
DOCS_ENABLED=false
```

Authenticated calls use a bearer token:

```bash
curl -X POST https://example.com/api/v1/chat \
  -H "Authorization: Bearer $APP_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"message":"Hello"}'
```

The built-in authentication is appropriate for a single service client. Replace it with the
project's OIDC/JWT identity adapter before building a multi-user system. Enforce distributed
rate limiting at the API gateway or add a shared-store limiter; an in-process limiter is not
included because it is misleading under multiple workers.

The default `InMemorySaver` supports local thread memory only. It is lost on restart and is not
shared by workers. Use an async Postgres/Redis checkpointer and bind thread ownership to the
authenticated principal before multi-instance or multi-tenant deployment.

## Commands

```bash
make setup         # install from the lockfile
make run           # development server
make test          # tests and coverage gate
make lint          # Ruff
make format        # apply formatting
make typecheck     # mypy
make check         # all non-mutating verification
make lock          # intentionally refresh uv.lock
```

## Project layout

```text
src/app/
├── agents/        # prompt, safe tools, registry, graph construction
├── api/           # versioned HTTP routes and dependencies
├── core/          # settings, errors, logging, request middleware
├── models/        # public API schemas
├── services/      # application interfaces and agent use case
└── main.py        # app factory and ASGI entrypoint
tests/
├── unit/
└── integration/
evals/             # behavioral regression dataset and guidance
```

## Adding a tool

1. Define a small Pydantic input schema and bound input size/value ranges.
2. Keep credentials and authorization context out of model-controlled arguments.
3. Register the tool with its risk level in `app.agents.tools.registry`.
4. Read-only tools may run directly. Write or destructive tools must be rejected until an
   approval/authorization middleware is installed.
5. Add unit tests, failure tests, and at least one behavioral eval case.

## Observability and privacy

Application logs never include request bodies. LangSmith tracing is disabled by default because
agent traces can contain prompts, responses, and tool results. Enable it only after defining
retention, access, sampling, and PII redaction rules.

## Using this as a template

Rename the package/project metadata, set an appropriate license, replace the authentication and
persistence adapters required by your product, and delete features you do not need. Do not carry
placeholder integrations into a new project.
