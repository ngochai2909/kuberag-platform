# KubeRAG Project Status

Last updated: 2026-07-30

This page is the quickest starting point for a contributor, reviewer, or
operator joining the project. It separates what is running now from what is
only prepared in Git, so a reader does not mistake a manifest for a deployed
service.

## Current Milestone

The temporary single-node infrastructure foundation is verified on both the
local machine and the GCP VM, including Envoy Gateway smoke routing on GCP.
The GCP cluster now runs one CloudNativePG-managed PostgreSQL 18.4 instance,
pgvector 0.8.5, the initial Alembic schema, and a separate PostgreSQL metadata
database for Prefect. The required demo source is VnExpress RSS only. The
FastAPI now has a provider-independent PostgreSQL retrieval adapter with local
unit/type/lint verification and a passing controlled GCP pgvector integration
test. The internal llama.cpp generation runtime is now deployed and verified.
FastAPI composition is deployed with a separate E5 cache PVC and has completed
a real RAG request through pgvector and llama.cpp. Envoy now routes `/api/` to
FastAPI and enforces a local rate limit. The React/Vite frontend is deployed at
`/`, calls the same-origin API, and renders VnExpress source cards with RSS
thumbnails when present. The GCP overlay explicitly enables a temporary public
demo mode; it is not production authentication.

The Week 4 observability stack is now deployed on the GCP checkpoint. Grafana,
Prometheus, Loki, Tempo, Pyroscope, and an OpenTelemetry Collector run only as
internal `ClusterIP` services in `observability`. A FastAPI request has produced
Prometheus metrics, a structured Loki log, a Tempo trace with `embed_query`,
`pgvector_search`, `build_prompt`, and `llm_generate` spans, and a Pyroscope CPU
profile. The new Prefect worker image carries the same OTLP configuration and
will emit its ingestion telemetry on the next scheduled or explicitly approved
flow run. Grafana has provisioned data sources and the `KubeRAG Overview`
dashboard from Git. Alerts, a Grafana walkthrough screenshot, and k6 evidence
are deliberately still pending.

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
| PostgreSQL/pgvector | Not deployed | Verified single instance | PVC 20 GiB is Bound; `vector` is enabled; Alembic schema and sample similarity query pass. |
| Source adapters | Offline fixtures/unit tests | Live VnExpress scheduled | Demo source is VnExpress RSS only. |
| Prefect flow | Offline skeleton tested | Deployed and verified | Daily `0 3 * * *` UTC is registered (10:00 Vietnam); Prefect metadata uses PostgreSQL database `prefect`, separate from RAG data. |
| llama.cpp | Not deployed | Verified running | Internal `ClusterIP` Service loads Qwen2.5-1.5B GGUF from a 5 GiB PVC; it is not public. |
| RAG API | Skeleton only | Verified through Envoy | Restricted FastAPI Deployment has E5 cache PVC, CNPG Secret, llama.cpp Service dependency, and a 45 s application timeout. The GCP demo route is public without bearer auth, but Envoy applies a shared 10 requests/minute limit. |
| Frontend | Local Vite development available | Deployed through Envoy `/` | Non-root Nginx serves the built React/Vite SPA; it calls `/api/v1` and shows source title, URL, and optional RSS thumbnail. |
| Observability | Manifests prepared only | Deployed and runtime-checked | Prometheus, Grafana, Loki, Tempo, Pyroscope, and OTel Collector are private `ClusterIP` workloads; Grafana is reached through IAP port-forward only. |

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
| `DB-001`, `DB-003`–`DB-007` | Pass GCP | CNPG, PVC, pgvector, migration/re-run, and vector query evidence captured. |
| `DB-010` | Pass GCP | Marker checksum/count survived controlled Pod recreate; PVC remained Bound. |
| `ING-001`, `ING-003`, `ING-004` | Pass offline | VnExpress fixtures, contract, timeout/retry/backoff unit evidence. |
| `ING-002` | Removed | NVD fully removed from code, fixtures, and demo corpus. |
| `ING-005` | Pass GCP | Daily `0 3 * * *` UTC (10:00 Vietnam) is registered on `kuberag-daily-ingest/daily`; evidence: `docs/evidence/ING-005/gcp-prefect-schedule-1000-vietnam.txt`. |
| `ING-006` | Pass GCP | Live VnExpress flow completed through real e5 into CloudNativePG. |
| `ING-007` | Pass GCP | Stable rerun skipped unchanged records; counts unchanged and SQL duplicate checks returned zero. |
| `ING-008` | Pass GCP | Completed run lifecycle, counters, and duration persisted in `ingestion_runs`. |
| `ING-009` | Pass offline | Sentence-aware chunk size/overlap boundary tests captured. |
| `ING-010` | Pass GCP smoke | `multilingual-e5-small` on PVC; batch smoke ~10s / ~1 GiB RSS; worker mode `e5`. |
| Prefect metadata persistence | Pass GCP | Separate CNPG role/database `prefect`; flow completed after migration with no SQLite lock log match. |
| `RAG-002` | Pass GCP integration | `PostgresRetriever` query vector retrieves the nearest fixture chunk through pgvector with its source fields; evidence: `docs/evidence/RAG-002/`. |
| `RAG-004` | Pass GCP runtime | llama.cpp reports healthy, exposes Qwen model alias, and completed a chat-completion request through a temporary local tunnel; evidence: `docs/evidence/RAG-004/`. |
| `RAG-005` | Pass GCP runtime | API composition calls only in-cluster E5/pgvector/llama.cpp; no external LLM API or OpenAI SDK is used. |
| `RAG-006` | Pass GCP runtime | API query through Envoy returned answer, VnExpress sources/URLs, optional thumbnail URLs, request ID, trace ID, and timings; evidence: `docs/evidence/RAG-006/`. |
| `NET-003`, `NET-005` | Pass GCP runtime | Envoy accepted `/api/` to FastAPI and the local `BackendTrafficPolicy` rate-limit policy. The temporary GCP demo is intentionally unauthenticated. |
| `WEB-001` | Pass GCP runtime | `kuberag-web` is Ready; its Service and accepted `/` HTTPRoute return the React SPA from the Envoy data plane. |
| `NET-006` | Partial | Controlled curl burst produced `429` after 10 requests; evidence: `docs/evidence/NET-006/gcp-rate-limit-429.txt`. Required k6 rate-limit evidence remains pending. |
| `OBS-001`–`OBS-014` | In progress | Stack, private storage/limits, provisioned data sources/dashboard, API metrics/log/trace/profile paths, and no-Alloy design are deployed. Runtime evidence capture, Grafana review, Prefect flow telemetry, and alert rules remain pending. |

## Immediate Next Checkpoint

Week 2 ingestion is complete on the GCP single-node checkpoint. The live
VnExpress Prefect flow uses real `intfloat/multilingual-e5-small`, writes
384-dimensional vectors to CloudNativePG, persists run counters, and skips
unchanged input on rerun.

Next checkpoint:

1. Capture Grafana screenshots and command evidence for the deployed four
   signals, including the next Prefect flow run.
2. Add a k6 rate-limit scenario and load-test evidence.
3. Provision alert rules/contact point and test an alert lifecycle.

See `docs/ROADMAP.md` week 2 and `docs/data-model.md`.

## Major Work Still Ahead

- Alert rules/contact point, Grafana evidence walkthrough, and k6 load/rate-limit tests.
- Chainguard image hardening, scanning, SBOMs, and signing.
- Restoration of the final 1 server + 2 worker topology and PostgreSQL replication/failover evidence.

## Useful References

- `docs/PROGRESS.md`: detailed phase log and ownership notes.
- `docs/ARCHITECTURE.md`: target architecture and component boundaries.
- `docs/data-model.md`: logical data model and the VnExpress ingestion decision.
- `docs/ROADMAP.md`: planned six-week sequence.
- `docs/ACCEPTANCE_CRITERIA.md`: required evidence and verification rules.
- `docs/runbooks/gcp-k3s-foundation.md`: operate the current GCP checkpoint.
