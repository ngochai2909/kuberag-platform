from __future__ import annotations

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[4]


def test_required_monorepo_directories_exist() -> None:
    expected_directories = [
        "apps/rag-api/src/app",
        "apps/rag-api/tests/unit",
        "apps/rag-api/tests/integration",
        "apps/ingestion",
        "apps/ingestion/migrations/versions",
        "apps/ingestion/tests/integration",
        "apps/frontend",
        "infra/terraform",
        "infra/ansible",
        "deploy/helm",
        "deploy/kustomize/base",
        "observability/collector",
        "observability/dashboards",
        "observability/alerts",
        "tests/k6",
        "docs/runbooks",
        "docs/evidence",
    ]

    missing = [path for path in expected_directories if not (REPOSITORY_ROOT / path).is_dir()]

    assert missing == []
