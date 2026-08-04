# KubeRAG Project Status

Last updated: 2026-08-04

This page is the quickest starting point for a contributor, reviewer, or
operator joining the project. It separates what is running now from what is
only prepared in Git, so a reader does not mistake a manifest for a deployed
service.

> **Current handoff:** application and observability workloads are placed on
> their workers. PostgreSQL still has its primary on the server with a streaming
> replica on the observability worker. Read
> [`runbooks/gcp-three-node-handoff.md`](runbooks/gcp-three-node-handoff.md)
> before any PostgreSQL switchover or `postgresql-final` apply.

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

The Week 4 observability stack is deployed on the GCP checkpoint with runtime
evidence under `docs/evidence/OBS-*`. Grafana, Prometheus, Loki, Tempo,
Pyroscope, and an OpenTelemetry Collector run only as internal `ClusterIP`
services in `observability`. A FastAPI request produced Prometheus metrics, a
structured Loki log (queryable by `request_id` / `trace_id` metadata), a Tempo
trace with `embed_query`, `pgvector_search`, `build_prompt`, and `llm_generate`
spans, and a Pyroscope CPU profile. A Prefect ingest run
(`flow_run_id=0161776d-6e44-41c5-a9ac-64088949778c`) produced Loki logs under
`service_name=kuberag-ingestion`, Tempo spans `ingestion.fetch` /
`ingestion.upsert`, and Prometheus metrics `kuberag_ingestion_*` after a
short-lived-process OTLP flush fix. Grafana data sources and the
`KubeRAG Overview` dashboard are provisioned from Git and verified via the
in-Pod Grafana API. Alertmanager/Slack has been verified through a test-only
Firing→Resolved lifecycle; k6 runtime evidence is captured under `PERF-*`, and
the supply-chain CI path built, scanned, SBOM-generated, keylessly signed and
verified the three release digests. Those digests were deployed by reviewed
release manifest on 2026-08-03. Envoy is a Prometheus scrape target
(OBS-001 closed).

The final intended topology is now mostly deployed on GCP: one k3s server and
two private workers are `Ready`. Application Pods run on the application
worker; observability Pods run on the observability worker. PostgreSQL primary
remains on the server until a controlled switchover/failover is approved.

## What Exists Today

| Area | Local machine | GCP VM | Meaning |
|---|---|---|---|
| k3s cluster | One single-node dev cluster | One server + two private workers | Local and GCP are separate clusters. GCP server is the sole control plane. |
| Node state | `Ready` | All 3 nodes `Ready` | `kuberag-server`, `kuberag-worker-application`, and `kuberag-worker-observability` are schedulable. |
| Persistent storage | Local host storage | Server 150 GiB data disk; each worker has a 50 GiB data disk | `local-path` PVs are node-local and cannot be moved by changing only a node selector. |
| Traefik | Disabled for KubeRAG | Disabled | Envoy Gateway is the application entry point. |
| Envoy Gateway controller | Installed and verified | Installed and verified | Chart `v1.8.3` in `gateway-system`. |
| Smoke route | Verified end-to-end | Verified end-to-end via public `:8080` | `curl` returns the smoke Pod hostname. |
| PSS restricted | Verified | Verified | Unsafe privileged/root Pods are rejected. |
| PostgreSQL/pgvector | Not deployed | Verified primary + replica | `kuberag-pg-1` is primary on server; `kuberag-pg-2` streams asynchronously on the observability worker. |
| Source adapters | Offline fixtures/unit tests | Live VnExpress scheduled | Demo source is VnExpress RSS only. |
| Prefect flow | Offline skeleton tested | Deployed and verified | Daily `0 3 * * *` UTC is registered (10:00 Vietnam); Prefect metadata uses PostgreSQL database `prefect`, separate from RAG data. |
| llama.cpp | Not deployed | Verified on application worker | Internal `ClusterIP` Service loads Qwen2.5-1.5B GGUF from the warmed application-worker PVC; it is not public. |
| RAG API | Skeleton only | Verified through Envoy on application worker | Restricted FastAPI Deployment has E5 cache PVC on the application worker, CNPG Secret, llama.cpp Service dependency, and a 45 s application timeout. The GCP demo route is public without bearer auth, but Envoy applies a shared 10 requests/minute limit. |
| Frontend | Local Vite development available | Deployed through Envoy `/` on application worker | Non-root Nginx serves the built React/Vite SPA; it calls `/api/v1` and shows source title, URL, and optional RSS thumbnail. |
| Observability | Manifests prepared only | Deployed on observability worker | Prometheus, Grafana, Loki, Tempo, Pyroscope, and OTel Collector are private `ClusterIP` workloads on `kuberag-worker-observability`; Grafana via IAP port-forward / in-Pod API. |

## GCP Three-Node Transition: Verified State

The following was observed from the running GCP cluster on 2026-08-04, not
inferred from manifests:

| Component | Runtime state | Location / detail |
|---|---|---|
| k3s nodes | Pass | Server, application worker, and observability worker all reported `Ready`; consult Terraform output/IAP-only inventory for private addresses. |
| Worker networking | Pass | Workers have no public IP. Cloud NAT `kuberag-nat` provides egress only for subnet `kuberag-subnet`; HTTPS outbound from the application worker passed. |
| Artifact Registry pull auth | Pass | Both workers run a kubelet credential provider that exchanges GCE metadata-service identity for short-lived Artifact Registry credentials. No service-account key or registry token is stored in Git/Kubernetes. |
| PostgreSQL replica | Pass | `kuberag-pg-1` is primary on the server and `kuberag-pg-2` is `Running` on the observability worker. `pg_stat_replication` returned `kuberag-pg-2|streaming|async`. |
| Application cache preparation | Pass | The LLM model, RAG embedding, and Prefect embedding warm Jobs all completed on the application worker. Their new node-local PVCs remain Bound. |
| Application placement | Pass | Frontend, RAG API, llama.cpp, Prefect server/worker run on `kuberag-worker-application` with warmed `-application` PVCs. Three-node overlays lower CPU requests to fit the 2 vCPU worker. Evidence: `docs/evidence/K8S-002/three-node-app-placement-2026-08-04.md`. |
| Observability placement | Pass | Fresh redeploy onto `kuberag-worker-observability` (telemetry PVC history reset once). Evidence: `docs/evidence/OBS-014/three-node-observability-placement-2026-08-04.md`. |
| PostgreSQL final placement/failover | Pending | Primary still on server; replica streaming on observability worker. Do not apply `postgresql-final` before controlled switchover/failover and explicit confirmation. |

The completed cache-warm Jobs and the old `kuberag-ingestion-failure-test`
Pod are historical test resources. The latter intentionally has status `Error`
and must not be treated as a new production incident.

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
| `INF-006` Secret hygiene | Pass local review | `git ls-files` / ignore review under `docs/evidence/INF-006/`; CI Trivy secret path under `docs/evidence/SEC-003/`. |
| `SEC-001`–`SEC-008` | Pass CI + GCP runtime | Chainguard/non-root bases, Semgrep, Trivy filesystem/image scans, CycloneDX SBOM, Cosign, digest rollout and OIDC least privilege are captured under `docs/evidence/SEC-*`. |
| `SEC-009` | Pending settings evidence | Branch protection API needs repository-administration authentication; capture the Ruleset/branch-protection screen before marking Pass. |
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
| `ING-011`, `ALT-005`, `ALT-008` | Pass GCP runtime | Test-only Prefect failure stopped before fetch/upsert; its structured Loki log, Tempo error trace, Prometheus failure timestamp, Slack-routed alert, natural Firing→Resolved lifecycle, and zero Slack-delivery-failure counters are captured in `docs/evidence/ING-011/`, `docs/evidence/ALT-005/`, and `docs/evidence/ALT-008/`. |
| Prefect metadata persistence | Pass GCP | Separate CNPG role/database `prefect`; flow completed after migration with no SQLite lock log match. |
| `RAG-002` | Pass GCP integration | `PostgresRetriever` query vector retrieves the nearest fixture chunk through pgvector with its source fields; evidence: `docs/evidence/RAG-002/`. |
| `RAG-004` | Pass GCP runtime | llama.cpp reports healthy, exposes Qwen model alias, and completed a chat-completion request through a temporary local tunnel; evidence: `docs/evidence/RAG-004/`. |
| `RAG-005` | Pass GCP runtime | API composition calls only in-cluster E5/pgvector/llama.cpp; no external LLM API or OpenAI SDK is used. |
| `RAG-006` | Pass GCP runtime | API query through Envoy returned answer, VnExpress sources/URLs, optional thumbnail URLs, request ID, trace ID, and timings; evidence: `docs/evidence/RAG-006/`. |
| `NET-003`, `NET-005` | Pass GCP runtime | Envoy accepted `/api/` to FastAPI and the local `BackendTrafficPolicy` rate-limit policy. The temporary GCP demo is intentionally unauthenticated. |
| `WEB-001` | Pass GCP runtime | `kuberag-web` is Ready; its Service and accepted `/` HTTPRoute return the React SPA from the Envoy data plane. |
| `NET-006` | Pass GCP runtime | k6 status burst through Envoy returned 5 expected `429` and no `5xx`; Envoy Prometheus metric increased. Evidence: `docs/evidence/NET-006/k6-rate-limit-2026-08-03.md`. |
| `OBS-001` | Pass GCP runtime | Kubernetes, FastAPI/`kube-state-metrics`, and Envoy Gateway data-plane targets scrape. Post-k6 `up{job="kuberag-envoy-metrics"}=1`; evidence: `docs/evidence/OBS-001/` and `docs/evidence/PERF-003/`. |
| `OBS-002`–`OBS-004` | Pass GCP runtime | PromQL RPS/p50/p95/p99/status codes, Pod memory/restarts, RAG stage metrics, and ingestion `kuberag_ingestion_*` metrics captured under `docs/evidence/OBS-002`–`OBS-004/`. |
| `OBS-005`–`OBS-007` | Pass GCP runtime | FastAPI and Prefect OTLP logs in Loki; required fields present as structured metadata; sample review shows no raw prompt/document/secret (`docs/evidence/OBS-005`–`OBS-007/`). |
| `OBS-008`–`OBS-010` | Pass GCP runtime | Tempo RAG span tree, ingestion fetch/upsert spans, and response↔Loki↔Tempo `trace_id` correlation (`docs/evidence/OBS-008`–`OBS-010/`). |
| `OBS-011`–`OBS-014` | Pass GCP runtime | Pyroscope CPU profile, Git-provisioned Grafana datasources/dashboard (API evidence), no Alloy inventory, retention/PVC/limits match single-node budget (`docs/evidence/OBS-011`–`OBS-014/`). |

## Immediate Next Checkpoint

Application and observability placement are verified. The next mutation is
**controlled PostgreSQL switchover/failover**, then (only after Pass)
`postgresql-final` and any recreate of the former primary as a replica on the
application worker. Each of those steps needs immediate confirmation by name.

Do **not** skip straight to `postgresql-final`: it would make the old
server-local primary PVC unschedulable. Follow
[`runbooks/gcp-three-node-handoff.md`](runbooks/gcp-three-node-handoff.md).

## Major Work Still Ahead

- Controlled PostgreSQL switchover/failover with DB-002/DB-008/DB-009 evidence.
- Apply `postgresql-final` only after the primary no longer depends on the
  server-local PVC.
- SEC-009 branch-protection screenshot (needs GitHub admin access).
- Week 6 clean-install / release notes / DoD closeout.

## Useful References

- `docs/PROGRESS.md`: detailed phase log and ownership notes.
- `docs/ARCHITECTURE.md`: target architecture and component boundaries.
- `docs/data-model.md`: logical data model and the VnExpress ingestion decision.
- `docs/ROADMAP.md`: planned six-week sequence.
- `docs/ACCEPTANCE_CRITERIA.md`: required evidence and verification rules.
- `docs/runbooks/gcp-k3s-foundation.md`: operate the current GCP checkpoint.
- `docs/runbooks/gcp-three-node-handoff.md`: continue the active three-node
  transition safely.
