ING-005 Prefect daily schedule

Evidence layers:

1. Offline config helper (Git):
   `uv run pytest apps/ingestion/tests/unit/test_prefect_flow.py::test_deployment_schedule_is_daily_cron -q --no-cov`
2. GCP cluster registration:
   `docs/evidence/ING-005/gcp-prefect-schedule.txt`

What passed on GCP:

- Prefect server + process worker Deployments Available in namespace `prefect`
- Work pool `kuberag-ingestion`
- Deployment `kuberag-daily-ingest/daily` with cron `0 2 * * *` timezone `UTC` active

Still deferred:

- Live flow run against PostgreSQL + real multilingual-e5-small (`ING-006` cluster / `ING-010` cluster)
