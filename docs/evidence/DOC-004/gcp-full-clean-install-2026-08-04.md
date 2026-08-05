# DOC-004 — GCP full clean install log (2026-08-04)

Required acceptance: clean install from a wiped compute/network environment
succeeds by following project docs/scripts, with an install log and smoke
results.

## Scope chosen

Full GCP destroy/recreate of **compute + network only** (15 Terraform
resources). Artifact Registry, Workload Identity Federation, and service
accounts were **retained** so immutable release digests remained pullable.

Destroy plan summary:
`docs/evidence/DOC-004/terraform-destroy-plan-summary-2026-08-04.md`.

Demo script (`DOC-006`) was explicitly left **pending** and is out of scope
for this log.

## Timeline (UTC, 2026-08-04)

| Step | Action | Result |
|---|---|---|
| 0 | Preflight inventory; recommend push of prior local commits | Noted |
| 1 | `terraform plan -destroy` (targeted compute/network) | 15 to destroy; summary saved |
| 2 | Targeted `terraform apply` destroy | 0 VMs remaining |
| 3–4 | `terraform plan` + `apply` recreate | 15 added; new external IP assigned |
| 5 | Clear stale SSH host keys for recreated VMs | `known_hosts` updated |
| 6 | `make gcp-k3s-install` + `make gcp-three-node-join` | 3 nodes `Ready` |
| 7 | Envoy + foundation smoke | `/hostname` 200 |
| 8 | CNPG + migrate + postgresql expand | 2 PG instances |
| 9 | Secrets (Grafana/RAG/Prefect); Slack webhook | Placeholder Slack secret created without live `SLACK_WEBHOOK_URL` — Alertmanager starts; Slack delivery **not** verified this install |
| 10 | Observability Helm with three-node nodeSelectors | Obs stack on observability worker |
| 11 | Cache warm + release digests + three-node apps + routing | Apps on application worker |
| 12 | Prefect bootstrap + e5 download/smoke | Worker Ready; e5 Jobs Completed |
| 13 | PG promote + `postgresql-final` + replica recreate | Primary `kuberag-pg-2` on observability worker; replica `kuberag-pg-1` on application worker |
| 14 | `make gcp-ingest-run` | Completed `flow_run_id=39890d19-ded8-4542-ab3b-90052468604f` |
| 15 | Gateway + RAG smoke | See smoke section below |

## Public entry after recreate

| Item | Value |
|---|---|
| External IP (new) | `136.85.35.106` |
| Previous external IP | `136.85.70.219` (destroyed with address resource) |
| Gateway URL | `http://136.85.35.106:8080` |
| Admin path | IAP SSH (`Host kuberag-gcp`) + optional local tunnel `make gcp-k3s-tunnel` → `127.0.0.1:16443` |

Firewall `:8080` still depends on operator egress CIDRs in ignored
`terraform.tfvars`.

## Final verified topology

```text
Internet -> 136.85.35.106:8080 -> Envoy (server)
  -> application worker: web, RAG API, llama.cpp, Prefect, PG replica (pg-1)
  -> observability worker: Prometheus/Grafana/Loki/Tempo/Pyroscope/OTel/Alertmanager,
                           PG primary (pg-2)
```

Nodes (remote `k3s kubectl`, ages from this install):

```text
NAME                           STATUS   ROLES           INTERNAL-IP
kuberag-server                 Ready    control-plane   10.42.0.2
kuberag-worker-application     Ready    <none>          10.42.0.4
kuberag-worker-observability   Ready    <none>          10.42.0.3
```

PostgreSQL:

```text
kuberag-pg-1   Running   kuberag-worker-application     (async replica)
kuberag-pg-2   Running   kuberag-worker-observability   (primary)
Cluster currentPrimary=kuberag-pg-2 readyInstances=2
```

## Smoke (minimum)

Gateway (public IP, no kube tunnel required):

```text
curl http://136.85.35.106:8080/hostname  -> HTTP 200
curl http://136.85.35.106:8080/          -> HTTP 200 (SPA)
curl http://136.85.35.106:8080/api/v1/status -> {"status":"ready"}
```

Ingest Job:

```text
kuberag-ingest-run   Complete   1/1
flow_run_id=39890d19-ded8-4542-ab3b-90052468604f state=Completed
```

RAG query through Envoy (after rate-limit cooldown; shorter `top_k=1` to stay
under the FastAPI 45s bound on cold/slow CPU generation):

```text
POST /api/v1/query  -> HTTP 200 (~18s)
request_id=676cfb0d-3a0c-448e-8428-3a039da59b27
sources=1
answer_len=37
```

Summary JSON (no full prompt/document body):
`docs/evidence/DOC-004/smoke-query-summary-2026-08-04.json`.

Notes from this smoke:

- Rapid consecutive queries hit Envoy shared limit **10 req/min** → HTTP 429.
- One longer question returned HTTP 504 (`rag_timeout`) while llama.cpp was
  still evaluating; retry with a shorter prompt succeeded.
- Local `kubectl` via `127.0.0.1:16443` can fail with TLS handshake timeout
  when the IAP SSH tunnel dies; restart with `make gcp-k3s-tunnel` or use
  `ssh kuberag-gcp 'sudo k3s kubectl ...'`.

## Intentionally not claimed

- `DOC-006` demo script / 12–15 minute rehearsal — still pending.
- Live Slack alert delivery on this clean install (webhook placeholder only).
- `SEC-009` branch protection required-status-checks screenshot — still pending
  by prior operator choice.

## Verdict

**DOC-004 Pass** for the chosen scope: targeted compute/network wipe,
recreate, three-node platform rebuild, ingest Completed, and gateway/RAG smoke
through the new external IP.
