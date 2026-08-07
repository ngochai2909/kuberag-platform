# GCP Three-Node Handoff Runbook

Last verified: 2026-08-04 (post clean install `DOC-004`)

This runbook records the verified final three-node topology. It is not
permission to run mutating steps: confirm each cluster, persistence, or cloud
change immediately before running it.

## Target topology and current position

```text
Internet -> 136.85.35.106:8080 -> Envoy on server -> Services
  -> application worker: web, RAG API, llama.cpp, Prefect, PG replica (pg-1)
  -> observability worker: obs stack, PG primary (pg-2)

kuberag-server                 control plane + Envoy controller path
kuberag-worker-application     apps + model caches + PG async replica
kuberag-worker-observability   observability stack + PG primary
```

All three nodes are `Ready` after the 2026-08-04 full clean install. Workers
have no public addresses; private addresses remain in Terraform output and the
IAP-only inventory. Cloud NAT is egress-only and IAP remains the administration
path. Clean-install evidence:
`docs/evidence/DOC-004/gcp-full-clean-install-2026-08-04.md`.

## Completed and verified

- Terraform created both 8 GiB workers and their 50 GiB data disks. Cloud NAT
  `kuberag-nat` is attached to `kuberag-subnet`.
- Ansible joined both workers to k3s and applied labels
  `kuberag.io/role=application` and `kuberag.io/role=observability`.
- Kubelet pulls Artifact Registry images using a local credential-provider
  executable and short-lived tokens from the GCE metadata service. Do not
  replace this with a service-account key, static token, or Git-tracked Docker
  config.
- CloudNativePG reports `INSTANCES=2`, `READY=2`, and healthy status.
  After switchover/`postgresql-final`, `kuberag-pg-2` is primary on the
  observability worker and `kuberag-pg-1` is the streaming async replica on
  the application worker.
- The following Jobs completed on the application worker:
  `kuberag-llm-model-warm`, `kuberag-rag-api-embedding-warm`, and
  `kuberag-prefect-embedding-warm`.

## Important storage rule

`local-path` volumes are node-local. Existing PVCs on the server have a PV
node affinity for `kuberag-server`; adding a `nodeSelector` alone would leave
the replacement Pod `Pending`.

The three warmed PVCs have distinct `-application` names. The server cache
PVCs remain intact for rollback. PostgreSQL and observability data are not
cache: never delete, recreate, or move their PVCs as an application rollout
shortcut.

## Completed checkpoints (2026-08-04)

### Application placement

Verified after `make gcp-three-node-apps-apply`. Frontend, RAG API, llama.cpp,
Prefect server, and Prefect worker run on `kuberag-worker-application` using
the warmed `-application` PVCs. On 2026-08-06, the application worker was
resized to 4 vCPU / 16 GiB so llama.cpp can use its four configured generation
threads. The lower CPU *requests* in the three-node overlays remain from the
former 2 vCPU packing configuration; limits stay higher for burst. Evidence:
`docs/evidence/K8S-002/three-node-app-placement-2026-08-04.md`.

### Observability placement (fresh redeploy)

Verified after `scripts/gcp-three-node-observability-migrate.sh` /
`make gcp-three-node-observability-migrate`. Prometheus, Grafana, Loki, Tempo,
Pyroscope, Alertmanager, and the OTel Collector run on
`kuberag-worker-observability`. Short-retention observability PVCs were
recreated (telemetry history reset once). PostgreSQL was not modified during
that step. Evidence:
`docs/evidence/OBS-014/three-node-observability-placement-2026-08-04.md`.

### PostgreSQL switchover and final placement

Verified on 2026-08-04:

1. `kubectl cnpg promote kuberag-pg kuberag-pg-2 -n data` — primary moved to
   the observability worker; warm RAG remained HTTP 200.
2. `make gcp-three-node-postgresql-final` — affinity limited to
   `observability|application` (server excluded).
3. `kubectl cnpg destroy kuberag-pg 1 -n data` then operator recreate —
   async replica joined on the application worker with a new local-path PVC.
4. Cluster healthy with streaming replication; final RAG HTTP 200.

Evidence: `docs/evidence/DB-002/`, `docs/evidence/DB-008/`,
`docs/evidence/DB-009/`.

## Current topology

```text
Internet -> 136.85.35.106:8080 -> Envoy on server -> Services
  -> application worker (frontend, RAG API, llama.cpp, Prefect, PG replica)
  -> observability worker (observability stack, PG primary)
```

`DOC-004` clean install Pass; `DOC-006` demo script still pending.

## Do not run casually

- Further `cnpg destroy` / PostgreSQL PVC deletion without a named recovery plan.
- Terraform destroy, VM stop, firewall broadening, or public IP on workers.
- Treating the historical `kuberag-ingestion-failure-test-*` Error Pod as a
  new incident.

## Known non-incidents

- `kuberag-ingestion-failure-test-*` is an intentional historical failure-test
  Pod. Its `Error` status is evidence for alert lifecycle testing, not an active
  ingestion incident.
- A local kubeconfig connection-refused error normally means its IAP tunnel is
  not running, not that Kubernetes is down.

## Verification sources

- `docs/PROJECT_STATUS.md` — concise deployed-vs-pending state.
- `docs/PROGRESS.md` — detailed project log.
- `infra/ansible/playbooks/k3s-gcp-three-node.yml` — worker join and registry
  credential-provider configuration.
- `deploy/kustomize/overlays/gcp-three-node/` — app, cache, and PostgreSQL
  transition overlays.
