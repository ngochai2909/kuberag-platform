ING-005 Prefect daily schedule

Evidence layers:

1. Offline config helper (Git):
   `uv run pytest apps/ingestion/tests/unit/test_prefect_flow.py::test_deployment_schedule_is_daily_cron -q --no-cov`
2. Historical GCP registration at 09:00 Vietnam:
   `docs/evidence/ING-005/gcp-prefect-schedule.txt`
3. Current GCP registration at 10:00 Vietnam:
   `docs/evidence/ING-005/gcp-prefect-schedule-1000-vietnam.txt`

What passed on GCP:

- Prefect server + process worker Deployments Available in namespace `prefect`
- Work pool `kuberag-ingestion`
- Deployment `kuberag-daily-ingest/daily` with cron `0 3 * * *` timezone `UTC`
  active, equivalent to 10:00 Asia/Ho_Chi_Minh

Still deferred:

- k6/load and observability work are outside this schedule evidence.
