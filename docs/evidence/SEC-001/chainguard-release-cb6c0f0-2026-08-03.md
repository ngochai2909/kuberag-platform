# SEC-001 — Chainguard non-root release images

Release commit: `cb6c0f07c9e0280f5fd2ac4a5ccaf356d59f0598`.

- `apps/rag-api/Dockerfile` and `apps/ingestion/Dockerfile` pin both
  `cgr.dev/chainguard/python` builder/runtime by digest and finish with
  `USER 65532`.
- `apps/frontend/Dockerfile` pins `cgr.dev/chainguard/node` and
  `cgr.dev/chainguard/nginx` by digest and finishes with `USER 65532`.
- CI run #31 built all three immutable artifacts successfully. Runtime
  verification in `SEC-007` shows Kubernetes pulled their resulting digests.

No Dockerfile uses `:latest` for a custom runtime base.

