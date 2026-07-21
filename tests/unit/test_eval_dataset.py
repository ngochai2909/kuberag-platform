from __future__ import annotations

import json
from pathlib import Path

DATASET_PATH = Path(__file__).parents[2] / "evals" / "cases.jsonl"


def test_eval_dataset_has_required_schema_and_safety_coverage() -> None:
    cases = [
        json.loads(line)
        for line in DATASET_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert len(cases) >= 4
    assert len({case["id"] for case in cases}) == len(cases)
    assert {
        "tool_choice",
        "prompt_injection",
        "authorization",
        "indirect_prompt_injection",
    } <= {case["category"] for case in cases}

    for case in cases:
        assert isinstance(case["input"], str)
        assert case["input"]
        assert isinstance(case["expectations"], list)
        assert case["expectations"]
