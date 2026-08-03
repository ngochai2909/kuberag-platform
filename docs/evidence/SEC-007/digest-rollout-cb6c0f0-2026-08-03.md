# SEC-007 — immutable digest rollout

After PR #26 merged, `make gcp-release-render` rendered only immutable
`image@sha256` references and `imagePullPolicy: IfNotPresent`. The controlled
`make gcp-release-apply` rollout completed for all four long-running
Deployments; no Prefect Job or data migration was started.

Runtime Pod image IDs after rollout:

| Workload | Digest |
| --- | --- |
| RAG API, including init container | `kuberag-api@sha256:3effa480d690775d75f7eaa251f585918378018253d15ceabafb64559cb3aa29` |
| Frontend | `kuberag-web@sha256:05181867af46b95469ffefc6b0e4543a1e68650b8d897967128dfeea4e5dbd25` |
| Prefect server and worker | `kuberag-ingestion@sha256:a6217acf0598a01400fd44b1f4fe030931145ad5a04b5362e26d27bd53373037` |

All four Deployments were `1/1 Ready`; Envoy `/api/v1/status` returned
`{"status":"ready"}` and Prometheus targets `kuberag-rag-api` and
`kuberag-envoy-metrics` were `up=1`.

