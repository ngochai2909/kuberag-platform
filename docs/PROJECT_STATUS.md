# KubeRAG Project Status

Last updated: 2026-07-28

This page is the quickest starting point for a contributor, reviewer, or
operator joining the project. It separates what is running now from what is
only prepared in Git, so a reader does not mistake a manifest for a deployed
service.

## Current Milestone

The temporary single-node infrastructure foundation is verified on both the
local machine and the GCP VM, including Envoy Gateway smoke routing on GCP.
The FastAPI RAG API is still a provider-independent skeleton; real
PostgreSQL/pgvector retrieval, ingestion, llama.cpp generation, and the React
frontend have not started.

The final intended topology remains one k3s server and two worker nodes. The
current one-node setup is a deliberately temporary, lower-cost checkpoint.

## What Exists Today

| Area | Local machine | GCP VM | Meaning |
|---|---|---|---|
| k3s cluster | Verified running | Verified running | One control-plane node per environment; this is not the final three-node cluster. |
| Node state | `Ready` | `Ready` | Kubernetes can schedule workload Pods. |
| Persistent storage | Local host storage | 150 GiB disk mounted at `/var/lib/kuberag` | k3s data and future PVC-backed data can use the dedicated GCP disk. |
| Traefik | Disabled for KubeRAG | Disabled | Envoy Gateway is the application entry point. |
| Envoy Gateway controller | Installed and verified | Installed and verified | Chart `v1.8.3` in `gateway-system`. |
| Smoke route | Verified end-to-end | Verified end-to-end via public `:8080` | `curl` returns the smoke Pod hostname. |
| PSS restricted | Verified | Verified | Unsafe privileged/root Pods are rejected. |
| Application workloads | Not deployed | Not deployed | No PostgreSQL, Prefect, frontend, real RAG API provider, or llama.cpp workload is running. |

## Verified GCP Foundation

The temporary GCP environment has one `e2-custom-8-16384` Compute Engine VM
(8 vCPU, 16 GiB RAM), a 30 GiB boot disk, and a separate 150 GiB persistent
data disk. Terraform created the VPC, subnet, restricted firewall rules, static
IP, VM, and disk. IAP is used for SSH and Kubernetes API administration.

```text
Terraform -> VPC, firewall, VM, disks, static IP
Ansible   -> mount persistent disk, install and configure k3s
Helm      -> Envoy Gateway controller
Kustomize -> namespaces, PSS, smoke Pod, Gateway, HTTPRoute
```

Verified request path:

```text
Laptop -> GCP firewall :8080 -> Envoy -> Service -> smoke Pod
```

Administrator egress CIDRs for `:8080` live only in the ignored local
`terraform.tfvars`. Company networks may present multiple public IPs; update
firewall CIDRs when the operator egress changes.

## Acceptance Snapshot

| Group | State | Notes |
|---|---|---|
| `INF-001` Terraform single-node foundation | Pass | Resource plan, apply, and VM inventory captured. |
| `INF-002` Terraform idempotency | Pass | Post-apply plan reported no changes; firewall CIDR update follow-up captured. |
| `INF-003` GCP Ansible single-node install | Pass | k3s installation recap and Ready node captured. |
| `INF-004` GCP Ansible idempotency | Pass | Second run reported `changed=0`, `failed=0`. |
| `INF-005` Cost control | Pass | Budget alert and stop/start/destroy runbook captured. |
| `INF-006` Secret hygiene | Pending | Requires the planned secret/config scan evidence. |
| `K8S-001` to `K8S-005` | Pass local + GCP | Node, PSS, safe smoke workload, and unsafe rejection verified on both clusters. |
| `NET-001` | Pass local + GCP | Envoy GatewayClass/Gateway/HTTPRoute accepted; smoke hostname returned. |
| `NET-004` | Pass local + GCP | Traefik absent from kube-system on both clusters. |

## Immediate Next Checkpoint

Start the data layer on the verified GCP single-node cluster:

1. Install CloudNativePG and create one temporary PostgreSQL instance with PVC.
2. Enable `vector`, add Alembic migrations, and verify basic vector query.
3. Keep Prefect ingestion and application routes pending until persistence and
   restart checks pass.

See `docs/ROADMAP.md` week 2 and `docs/runbooks/gcp-k3s-foundation.md`.

## Major Work Still Ahead

- PostgreSQL/pgvector through CloudNativePG, schema migrations, and persistence tests.
- Prefect ingestion for VnExpress RSS and NVD API, including fixtures and idempotency.
- Embeddings, llama.cpp generation, and the real deterministic RAG path.
- React/Vite frontend and Envoy routing for `/` and `/api/`.
- OpenTelemetry, Prometheus, Loki, Tempo, Pyroscope, Grafana, alerts, and dashboards.
- Gateway rate limiting, k6 load tests, Chainguard images, scanning, SBOMs, and signing.
- Restoration of the final 1 server + 2 worker topology and PostgreSQL replication/failover evidence.

## Useful References

- `docs/PROGRESS.md`: detailed phase log and ownership notes.
- `docs/ARCHITECTURE.md`: target architecture and component boundaries.
- `docs/data-model.md`: logical data model and the VnExpress ingestion decision.
- `docs/ROADMAP.md`: planned six-week sequence.
- `docs/ACCEPTANCE_CRITERIA.md`: required evidence and verification rules.
- `docs/runbooks/gcp-k3s-foundation.md`: operate the current GCP checkpoint.
