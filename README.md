# KubeRAG Platform

KubeRAG is a cloud-native RAG platform monorepo. The target platform uses FastAPI, PostgreSQL/pgvector, Prefect, React/Vite, Envoy Gateway, OpenTelemetry, Prometheus/Grafana, and a self-hosted llama.cpp model on Kubernetes.

The current infrastructure target is a **temporary single-node k3s environment** for local development and constrained demo work. The final target remains the original cluster shape: **1 k3s server/control-plane node and 2 k3s worker nodes** on GCP Compute Engine.

Current application state: **week 2 data and ingestion complete; week 3 RAG
runtime in progress**. The GCP checkpoint has CloudNativePG/pgvector, a live
Prefect VnExpress flow using `multilingual-e5-small`, a running internal
llama.cpp Pod serving `Qwen2.5-1.5B-Instruct` GGUF `Q4_K_M`, and a running
FastAPI RAG API. A real authenticated request has completed the deterministic
E5 -> pgvector -> prompt -> llama.cpp flow on GCP. The FastAPI Service remains
internal; Envoy now exposes the protected `/api/` route with a local rate
limit. The React frontend is not deployed yet.

For an accurate deployed-versus-prepared summary, start with
[`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md). It records the verified
single-node local/GCP foundation, including Envoy smoke routing, and the next
safe checkpoint.

## Requirements

- Python 3.12 or 3.13
- [uv](https://docs.astral.sh/uv/)
- Docker, only if building or running the local backend container
- Linux host with sudo access for local k3s
- Terraform for infrastructure validation
- Ansible for local k3s host configuration
- kubectl after k3s install; Helm before installing platform charts

Validated local platform versions:

- k3s `v1.35.5+k3s1`
- Helm `v4.2.2`
- Envoy Gateway Helm chart `v1.8.3`
- CloudNativePG chart `0.29.0` / operator `1.30.0`
- PostgreSQL `18.4` / pgvector `0.8.5`

## Quick Start

```bash
cp .env.example .env
make setup
make run
```

Open `http://localhost:8000/docs` in development.

During local development, `/health/live` is healthy when the process is
running. `/health/ready` returns `503` unless `RAG_RUNTIME_ENABLED=true` with a
database URI and the cluster-only E5/llama.cpp dependencies available. This is
intentional: laptop tests inject a fake service and never download models.

The public API contract is:

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is KubeRAG?","top_k":5}'
```

Without a configured `RagService`, this endpoint returns a safe `503` response. Unit and integration tests inject a fake service to verify request/response behavior without network access.

## Commands

```bash
make setup         # install from the lockfile
make run           # run the FastAPI backend from apps/rag-api
make test          # run backend tests and coverage gate
make lint          # Ruff linting for backend source/tests
make format        # format backend source/tests
make format-check  # verify formatting without modifying files
make typecheck     # mypy for backend source/tests
make check         # lint, format-check, typecheck, and test
make lock          # intentionally refresh uv.lock
```

## Local k3s Foundation

The current infrastructure phase is local single-node k3s. It does not create GCP resources. Envoy Gateway is installed with Helm; project-owned Gateway API resources and the restricted smoke backend are managed with Kustomize.

```bash
make infra-check
make k3s-install
export KUBECONFIG="$HOME/.kube/kuberag-k3s.yaml"

helm upgrade --install envoy-gateway \
  oci://docker.io/envoyproxy/gateway-helm \
  --version v1.8.3 \
  --namespace gateway-system \
  --create-namespace
kubectl wait --timeout=5m --namespace gateway-system \
  deployment/envoy-gateway --for=condition=Available

make k3s-foundation-apply
make k3s-foundation-status
make k3s-foundation-smoke
make k3s-unsafe-check
```

The local Gateway listens on `<node-ip>:8080` so Apache can continue using host port `80`. The local smoke route sends `/hostname` through Envoy to `kuberag-pss-smoke`; later application manifests replace it with `/` for React and `/api/` for FastAPI.

See `docs/runbooks/local-k3s-foundation.md` for evidence capture and rollback notes.

## GCP Single-Node Foundation

Terraform has created the temporary GCP single-node foundation in
`asia-southeast1-b`: one `e2-custom-8-16384` VM, a 30 GiB boot disk, a 150 GiB
data disk, a custom VPC, restricted firewall rules, and a static external IP.
SSH administration uses an IAP tunnel and the local `kuberag-gcp` SSH alias.

```bash
ssh kuberag-gcp
make gcp-k3s-syntax
make gcp-k3s-install
make gcp-k3s-tunnel  # keep running in a separate terminal
make gcp-k3s-status  # run from another terminal
```

The GCP VM now runs the pinned single-node k3s server. Its dedicated 150 GiB
disk is mounted at `/var/lib/kuberag`, and local `kubectl` access uses an IAP
tunnel instead of exposing another public administration port. See
`docs/runbooks/gcp-k3s-foundation.md` for the operating sequence and
`docs/runbooks/gcp-cost-control.md` for stop/start/destroy operations.

After the tunnel is open, common GCP status and ingestion commands are:

```bash
make gcp-envoy-install
make gcp-foundation-apply
make gcp-foundation-status
make gcp-foundation-smoke
make gcp-unsafe-check
make gcp-prefect-status
make gcp-ingest-run
make gcp-llama-status
make gcp-rag-routing-status
```

Prefect Server stores its deployment/schedule/run metadata in the separate
`prefect` database on the existing CloudNativePG cluster. This is separate from
the `kuberag` database that stores crawled documents and vectors. The setup and
recovery steps are documented in `docs/runbooks/prefect-postgresql.md`.

`make gcp-ingest-run` triggers the registered
`kuberag-daily-ingest/daily` deployment and waits for its terminal state. It
fetches live VnExpress data, embeds with the model cached on the cluster
PVC, and upserts into CloudNativePG. It changes persistent database state.

For day-to-day terminal operation, K9s navigation, RAG/llama.cpp checks, logs,
resource metrics, and a clear read-only versus mutating command split, see
[`docs/runbooks/README.md`](docs/runbooks/README.md).

`make gcp-llama-status` is read-only and shows the internal llama.cpp
Deployment, Service, model PVC, and Pod. The Service is `ClusterIP`: only
in-cluster workloads such as the future FastAPI Pod can call it. It is not an
internet-facing model API.

The deployed API uses a 2 GiB E5 cache PVC and two in-cluster Secrets: one
contains the CNPG database URI and one is a random API bearer token. Neither
value is printed or committed. Its current status is read-only:

```bash
make gcp-rag-api-status
```

The API routing overlay is deliberately separate from the foundation. Once it
has been rendered and reviewed, `make gcp-rag-routing-apply` exposes only
`/api/` through the existing Envoy listener on port `8080`; the FastAPI
Service, PostgreSQL, and llama.cpp remain internal ClusterIP services. The
route preserves bearer-token authentication and applies Envoy local rate
limiting at 10 requests per minute. See `docs/runbooks/README.md` for the
status and smoke commands.

## Monorepo Layout

```text
apps/
  rag-api/          FastAPI contract, retrieval, llama.cpp client, composition
  ingestion/        Adapters, Prefect flows, e5 embedding, Alembic, upsert
  frontend/         Placeholder for React/Vite UI
infra/
  terraform/        GCP network, firewall, VM, disk, IP, and outputs
  ansible/          Local and GCP single-node k3s host configuration
deploy/
  helm/             Project-owned Helm values/assets
  kustomize/        Kubernetes workload bases and environment overlays
observability/
  collector/        Placeholder for OpenTelemetry Collector config
  dashboards/       Placeholder for Grafana dashboards
  alerts/           Placeholder for alerting config
tests/
  k6/               Placeholder for load and rate-limit tests
docs/
  evidence/         Runtime evidence grouped by acceptance criterion
  runbooks/         Operational procedures
```

## Phase Boundaries

The current boundary has verified the single-node foundation,
PostgreSQL/pgvector persistence, ingestion through real E5, and a deployed
internal FastAPI-to-llama.cpp RAG request. The frontend and final Envoy
application routes follow. Observability and supply-chain work follow in later
phases.

The single-node target is temporary. The 3-node GCP topology and PostgreSQL primary/replica placement must be restored before final acceptance.

## Security Notes

- Do not commit real `.env` files, credentials, kubeconfig, Terraform state, tokens, or private keys.
- Rate limiting belongs at Envoy Gateway, not inside FastAPI.
- Future custom container images must use approved Chainguard bases and run as non-root.
- Unit tests must remain deterministic and must not call live external services.
- RAG prompts treat retrieved documents as untrusted data, not instructions.
