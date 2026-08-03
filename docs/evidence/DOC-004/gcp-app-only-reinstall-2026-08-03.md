# DOC-004 — GCP app-only reinstall (partial clean-install evidence)

## Scope and result

On 2026-08-03 the operator deliberately recreated only the stateless KubeRAG
application resources on the existing single-node GCP k3s cluster:

- namespace `rag`: Deployments `kuberag-rag-api`, `kuberag-web`; Services
  `kuberag-rag-api`, `kuberag-web`;
- namespace `prefect`: Deployments `prefect-server`, `prefect-worker`; Service
  `prefect-server`.

The command did **not** delete a PVC/PV, Secret, CloudNativePG resource,
llama.cpp, Envoy Gateway, or observability resource. It then ran
`make gcp-release-apply`, which applied only the reviewed immutable-digest
release overlays and waited for the four long-lived Deployments.

All four rollouts succeeded. The post-rollout snapshot reported all ten PVCs
as `Bound`, API/web/Prefect Server/Prefect worker as `1/1 Available`, and the
Envoy request `GET /api/v1/status` as `{"status":"ready"}`. Prometheus showed
both `kuberag-rag-api` and `kuberag-envoy-metrics` with `up=1`.

The worker initially starts after the Prefect Server because the release
manifest now has a restricted init container that polls
`/api/health`. Its evidence was:

```text
prefect-worker-77b579dd84-459hp   Running   true   Completed   0

Prefect server is healthy
Worker 'ProcessWorker 64903760-a85f-402a-adcb-d878810d3616' started!
```

`Completed` is the init-container state and `0` is the worker container restart
count after a further 55-second observation period. This closes the startup
race found in the previous app-only reinstall.

## Boundary of this evidence

This is **partial** evidence for `DOC-004`, not a passing full clean install:
the existing cluster, its persistent data, and platform components were kept
intact by design. A later isolated environment or a deliberately cleaned
cluster must still follow the complete install runbook and smoke suite before
`DOC-004` can be marked `Pass`.

At the time of the final read, Alertmanager still listed
`KubeRagWorkloadRestarted` for the *previous* worker Pod from the failed first
attempt. That rule has a 15-minute lookback, so it is expected to resolve
without indicating a restart of the new worker.
