# KubeRAG repository guidance

## Purpose

This repository implements **KubeRAG**, a secure and observable cloud-native RAG platform on Kubernetes. The current implementation milestone targets a temporary single-node k3s cluster for local development and constrained demo work. The final target remains a three-node k3s cluster. The required demonstration uses PostgreSQL/pgvector, Prefect, FastAPI, React/Vite and a self-hosted llama.cpp model. It does not use an external LLM API in the primary demo path.

Read these files before planning or editing:

1. `docs/PROJECT_SCOPE.md`
2. `docs/ARCHITECTURE.md`
3. `docs/TECH_STACK.md`
4. The relevant milestone in `docs/ROADMAP.md`
5. The relevant IDs in `docs/ACCEPTANCE_CRITERIA.md`
6. `docs/DEFINITION_OF_DONE.md`

If code and documentation conflict, report the conflict. Do not silently change architecture or scope.

## Planned repository layout

```text
apps/
  rag-api/          FastAPI retrieval and generation API
  ingestion/        Prefect flows, source adapters and embedding/upsert
  frontend/         React/Vite single-page UI
infra/
  terraform/        GCP network, VM, disk, firewall and outputs
  ansible/          OS and k3s configuration
deploy/
  helm/             Project-owned Helm configuration/templates when justified
  kustomize/        Base and environment overlays for custom workloads
observability/
  collector/        OpenTelemetry Collector configuration
  dashboards/       Provisioned Grafana dashboards
  alerts/           Provisioned alert rules/contact-point templates
tests/
  k6/               Load and rate-limit scenarios
docs/
  evidence/         Runtime evidence grouped by acceptance criterion
  runbooks/         Operational procedures
```

During migration, preserve a working main branch. Move and refactor in reviewable phases; do not combine repository relocation with major behavior changes unless the approved plan explicitly requires it.

## Architecture boundaries

- HTTP routes perform transport and validation only. Keep retrieval/generation logic in services.
- Keep database, embedding and LLM calls behind typed interfaces so unit tests do not need network access.
- The required RAG flow is deterministic: embed query → retrieve chunks → build bounded prompt → generate answer.
- The current infrastructure target is temporary single-node k3s; keep topology-specific code and manifests easy to restore to the final 1 server + 2 worker topology.
- Do not add LangGraph, tool-calling agents or multi-agent orchestration to required scope.
- PostgreSQL/pgvector is the system of record and vector store.
- Prefect owns ingestion orchestration; do not run the daily ingestion scheduler inside FastAPI.
- llama.cpp owns self-hosted generation; no external LLM API is allowed in the primary demo path.
- Envoy Gateway owns application routing and rate limiting. Never add an in-process rate limiter to FastAPI.
- OpenTelemetry Collector is the OTLP gateway for logs and traces.
- Prometheus scrapes metrics.
- Pyroscope SDK sends profiles directly to Pyroscope.
- Do not add Grafana Alloy unless an approved architecture change identifies a concrete missing capability.

## Newbie-guided collaboration

The primary operator is learning the platform while implementing it. Agents
working under `docs/` must preserve the teaching workflow defined in the root
`AGENTS.md` and apply these rules to plans, runbooks, and command examples:

- Use Vietnamese when the user writes Vietnamese and teach every unfamiliar
  concept or technology before relying on it. This requirement covers the full
  stack in `docs/TECH_STACK.md`: GCP/network/storage, IaC and deployment tools,
  Kubernetes resources and security, Envoy routing, application/RAG flow,
  PostgreSQL/pgvector, Prefect ingestion, embedding/llama.cpp, observability,
  testing, CI, and software supply-chain controls.
- For each new concept, explain the problem it solves, why KubeRAG needs it,
  where it sits, inputs/outputs, dependencies, repository configuration,
  verification method, common failures, and cost/security implications.
- Compare easily confused concepts explicitly and explain end-to-end KubeRAG
  request, data, deployment, and telemetry flows before isolated details.
- Explain the goal, reason, state change, security/cost impact, command,
  expected output, and stopping point for each unfamiliar infrastructure step.
- Guide one mutating checkpoint at a time and wait for actual output before
  continuing. An explanation request is not permission to edit or execute, but
  an unambiguous affirmative response to a clearly proposed non-destructive
  action is sufficient; never require an exact authorization phrase.
- Ask for clarification when consent could apply to more than one action.
  Billable, privileged, firewall-broadening, data-destructive, and destroy
  operations still need immediate confirmation naming the action.
- Keep commands copy-paste safe, explain placeholders and indentation, and
  distinguish read-only checks from local, cluster, cloud-billable, privileged,
  and destructive operations.
- Require explicit confirmation immediately before cloud creation,
  `terraform apply`, firewall broadening, data deletion, or destroy operations.
- Never request or publish passwords, tokens, private keys, kubeconfig,
  Terraform state, ADC files, or full secret values.
- Document expected success and common failure output. Evidence and acceptance
  status must reflect commands that actually ran, never an assumed result.

## Scope and dependency rules

- Implement Required scope before Optional work.
- Do not add Redis, Kafka, MinIO, Elasticsearch/OpenSearch, a service mesh, Argo CD, Vault, Alloy, LangChain or LangGraph without explicit user approval and an updated architecture decision.
- Ask before changing a public API, database schema contract, data retention policy, cloud topology, security policy or required technology.
- Keep new production dependencies minimal and justify each one.
- Pin dependency/chart/image versions; do not use `latest`.
- Never weaken tests, scan policy or Pod Security merely to make a build pass.

## Security requirements

- Never commit or print credentials, tokens, private keys, kubeconfig, Terraform state or real `.env` values.
- Treat user questions, retrieved documents, model output and upstream source data as untrusted.
- Do not log raw prompts, complete retrieved documents, authorization headers or database URLs.
- All custom images must use an approved Chainguard base and run as non-root.
- All custom Kubernetes workloads must support Pod Security Standards `restricted`:
  - `runAsNonRoot: true`
  - seccomp `RuntimeDefault`
  - `allowPrivilegeEscalation: false`
  - drop Linux capabilities `ALL`
  - no privileged mode, hostPath or host namespaces
- Use least-privilege ServiceAccounts/RBAC and explicit Secret references.
- Final deploy manifests use immutable image digests.

## Data and migration rules

- Schema changes require versioned migrations and tests from an empty database plus upgrade tests when relevant.
- Preserve unique document identity and pipeline idempotency.
- Never delete or rewrite persisted data as a debugging shortcut.
- Destructive data operations require explicit user approval, exact target verification and a recovery plan.
- CloudNativePG applications connect through operator-managed Services, never Pod IPs.

## Observability rules

- Metrics must have stable names, units and bounded-cardinality labels.
- Never use request ID, trace ID, question, raw URL or document text as metric labels.
- Propagate request/trace context through relevant calls.
- Add telemetry for new critical paths and failures, but avoid payload-heavy spans/logs.
- Dashboards, data sources and alerts must be provisioned from version-controlled files rather than only created in the UI.

## Testing rules

- Unit tests must be deterministic and must not call live external services.
- Use fixtures for VnExpress/NVD and mocks/fakes for database, embedding and llama.cpp in unit tests.
- Add integration tests for real boundaries where required: PostgreSQL/pgvector, HTTP API, Envoy and telemetry.
- Every bug fix needs a regression test when practical.
- Run the narrowest relevant tests while iterating, then all relevant checks before handoff.
- Never claim a command passed unless it actually ran. Report exact failures or missing environment dependencies.

## Verification commands

The repository will converge on these stable entry points. If a command is not implemented yet, do not invent a passing result; add it only in the approved bootstrap task.

```text
make setup             Install development dependencies
make lint              Run linters
make format-check      Verify formatting
make typecheck         Run static type checks
make test              Run unit/integration tests appropriate for local use
make check             Run all non-mutating quality checks
make scan              Run Semgrep and Trivy source/config/secret scans
make render            Render Helm/Kustomize output
make smoke-test        Verify deployed services
make load-test         Run the standard k6 scenario
```

Before handing off an infrastructure change, also run the relevant Terraform, Ansible, Helm, Kustomize or kubectl validation described in `docs/DEFINITION_OF_DONE.md`.

## Change workflow

1. Resolve the issue, milestone and acceptance IDs.
2. Read relevant docs/code/tests.
3. For non-trivial work, provide a short plan before editing.
4. Implement the smallest coherent change.
5. Add/update tests and documentation.
6. Run narrow checks, then full relevant verification.
7. Review the diff for correctness, security, scope creep, resource cost and missing evidence.
8. Report changed files, decisions, commands/results and residual risks.

Use one branch/PR per coherent task or milestone. Do not mix unrelated formatting, dependency upgrades or optional features into a required-scope PR.

## Completion standard

A file existing is not proof that a requirement works. A task is complete only when it meets `docs/DEFINITION_OF_DONE.md` and its acceptance criteria have runtime/test evidence. The engineer must be able to explain the change before merging.
