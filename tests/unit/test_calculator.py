from __future__ import annotations

import pytest

from app.agents.tools.calculator import calculate, evaluate_expression
from app.agents.tools.registry import (
    ToolRegistration,
    ToolRisk,
    executable_tools,
)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("2 + 3 * 4", 14),
        ("(10 - 4) / 3", 2.0),
        ("17 // 5", 3),
        ("17 % 5", 2),
        ("-2 ** 4", -16),
        ("2 ** 10", 1024),
    ],
)
def test_evaluate_expression(expression: str, expected: int | float) -> None:
    assert evaluate_expression(expression) == expected


def test_calculator_tool_returns_text() -> None:
    assert calculate.invoke({"expression": "(27 * 14) + 5"}) == "383"


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('id')",
        "True + 1",
        "1 << 2",
        "2 ** 101",
        "2 ** 0.5",
        "1e309",
        "-" * 20 + "1",
        "1+" * 40 + "1",
    ],
)
def test_dangerous_or_unbounded_expressions_are_rejected(expression: str) -> None:
    result = calculate.invoke({"expression": expression})
    assert result.startswith("Invalid expression:")


def test_direct_evaluator_enforces_length_limit() -> None:
    with pytest.raises(ValueError, match="too long"):
        evaluate_expression("1" * 201)


def test_default_registry_contains_only_read_only_tools() -> None:
    tools = executable_tools()
    assert [tool.name for tool in tools] == ["calculate"]


def test_registry_rejects_side_effecting_tool_without_approval_layer() -> None:
    registrations = (ToolRegistration(tool=calculate, risk=ToolRisk.WRITE, requires_approval=True),)

    with pytest.raises(ValueError, match="authorization/approval"):
        executable_tools(registrations)
