# GCP Three-Node Handoff Runbook

Last verified: 2026-08-04

This runbook is the continuation point for the active final-topology migration.
It records runtime facts only. It is not permission to run the mutating steps:
confirm each cluster, persistence, or cloud change immediately before running
it.

## Target topology and current position

```text
Internet -> static IP :8080 -> Envoy on server -> Services -> application worker
                                               -> PostgreSQL primary / replica

kuberag-server                 control plane, Envoy, current application Pods,
                               PostgreSQL primary
kuberag-worker-application     warmed model caches; destination for app Pods
kuberag-worker-observability   PostgreSQL streaming replica; future observability
                               destination after PVC-data migration
```

All three nodes are `Ready`. The workers have no public addresses; their
private addresses remain in Terraform output and the IAP-only inventory. Cloud
NAT is egress-only and IAP remains the administration path.

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
  `kuberag-pg-1` is primary on the server; `kuberag-pg-2` is a streaming async
  replica on the observability worker.
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
the warmed `-application` PVCs. The 2 vCPU worker required lower CPU
*requests* in the three-node overlays so LLM + RAG + Prefect can schedule;
limits stay higher for burst. Evidence:
`docs/evidence/K8S-002/three-node-app-placement-2026-08-04.md`.

### Observability placement (fresh redeploy)

Verified after `scripts/gcp-three-node-observability-migrate.sh` /
`make gcp-three-node-observability-migrate`. Prometheus, Grafana, Loki, Tempo,
Pyroscope, Alertmanager, and the OTel Collector run on
`kuberag-worker-observability`. Short-retention observability PVCs were
recreated (telemetry history reset once). PostgreSQL was not modified.
Evidence: `docs/evidence/OBS-014/three-node-observability-placement-2026-08-04.md`.

## Next checkpoint: PostgreSQL switchover / failover

Prerequisite: IAP kubeconfig tunnel on local port `16443`.

Do **not** apply `postgresql-final` first. Current primary `kuberag-pg-1`
still uses a server-local PVC; replica `kuberag-pg-2` streams on the
observability worker. Ordered plan:

1. Baseline replication (`pg_stat_replication`) and a warm RAG query.
2. Controlled CNPG switchover/promote of `kuberag-pg-2` (or documented
   failover) with explicit confirmation naming that action.
3. Verify new primary, RAG query, and replication health (DB-008/DB-009).
4. Only then evaluate `make gcp-three-node-postgresql-final` and any
   recreate of the former primary as a replica on the application worker.
   Recreating a PostgreSQL instance PVC is destructive to that instance's
   local files and needs a separate confirmation.

## Do not run yet

- `make gcp-three-node-postgresql-final` before switchover/failover Pass.
- Deletion of PostgreSQL PVCs or any Terraform destroy / firewall broaden /
  public IP on workers.
- `kubectl delete job` for completed cache-warm Jobs until their evidence is
  retained (TTL may clean them later).

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
