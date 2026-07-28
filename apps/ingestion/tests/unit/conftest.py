from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from prefect.testing.utilities import prefect_test_harness

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True, scope="session")
def prefect_test_fixture() -> Iterator[None]:
    """Run Prefect flows against an ephemeral test harness (no external server)."""

    with prefect_test_harness(server_startup_timeout=30):
        yield


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


def load_fixture(*parts: str) -> str:
    return FIXTURES_DIR.joinpath(*parts).read_text(encoding="utf-8")
