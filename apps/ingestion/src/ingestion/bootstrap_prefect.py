"""One-shot Prefect bootstrap: process work pool + daily cron deployment.

Run inside the cluster against the Prefect API Service:

  python -m ingestion.bootstrap_prefect
"""

from __future__ import annotations

import asyncio
import sys

from prefect.client.orchestration import get_client
from prefect.client.schemas.actions import WorkPoolCreate
from prefect.exceptions import ObjectAlreadyExists
from prefect.schedules import Cron
from prefect.types.entrypoint import EntrypointType

from ingestion.flows.ingest import (
    DAILY_INGEST_CRON,
    DAILY_INGEST_FLOW_NAME,
    DAILY_INGEST_TIMEZONE,
    daily_ingest_flow,
    deployment_schedule,
)

WORK_POOL_NAME = "kuberag-ingestion"
DEPLOYMENT_NAME = "daily"
WORKER_TYPE = "process"


async def ensure_work_pool() -> None:
    async with get_client() as client:
        try:
            await client.create_work_pool(
                WorkPoolCreate(
                    name=WORK_POOL_NAME,
                    type=WORKER_TYPE,
                    description="KubeRAG process worker pool for daily ingestion",
                )
            )
            print(f"created work pool {WORK_POOL_NAME!r}")
        except ObjectAlreadyExists:
            print(f"work pool {WORK_POOL_NAME!r} already exists")


def main() -> int:
    asyncio.run(ensure_work_pool())
    schedule = Cron(DAILY_INGEST_CRON, timezone=DAILY_INGEST_TIMEZONE)
    deployment_id = daily_ingest_flow.deploy(
        name=DEPLOYMENT_NAME,
        work_pool_name=WORK_POOL_NAME,
        schedule=schedule,
        build=False,
        push=False,
        print_next_steps=False,
        ignore_warnings=True,
        entrypoint_type=EntrypointType.MODULE_PATH,
        tags=["kuberag", "ingestion"],
        description=(
            f"{DAILY_INGEST_FLOW_NAME} daily schedule "
            f"({DAILY_INGEST_CRON} {DAILY_INGEST_TIMEZONE})"
        ),
        parameters={"sources": ["vnexpress", "nvd"]},
    )
    print(f"registered deployment id={deployment_id}")
    print(f"flow={DAILY_INGEST_FLOW_NAME} deployment={DEPLOYMENT_NAME}")
    print(f"schedule={deployment_schedule()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
