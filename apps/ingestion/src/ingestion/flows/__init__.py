"""Prefect ingestion flows for KubeRAG."""

from ingestion.flows.ingest import (
    DAILY_INGEST_CRON,
    DAILY_INGEST_FLOW_NAME,
    IngestionRuntime,
    daily_ingest_flow,
    deployment_schedule,
    ingestion_runtime,
)

__all__ = [
    "DAILY_INGEST_CRON",
    "DAILY_INGEST_FLOW_NAME",
    "IngestionRuntime",
    "daily_ingest_flow",
    "deployment_schedule",
    "ingestion_runtime",
]
