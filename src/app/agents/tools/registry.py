from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from langchain_core.tools import BaseTool

from app.agents.tools.calculator import calculate


class ToolRisk(StrEnum):
    READ_ONLY = "read_only"
    WRITE = "write"
    DESTRUCTIVE = "destructive"


@dataclass(frozen=True, slots=True)
class ToolRegistration:
    tool: BaseTool
    risk: ToolRisk
    requires_approval: bool = False


DEFAULT_TOOL_REGISTRY: Final[tuple[ToolRegistration, ...]] = (
    ToolRegistration(tool=calculate, risk=ToolRisk.READ_ONLY),
)


def executable_tools(
    registrations: tuple[ToolRegistration, ...] = DEFAULT_TOOL_REGISTRY,
) -> list[BaseTool]:
    """Return tools that are safe to execute without an approval middleware."""

    unsafe = [
        item.tool.name
        for item in registrations
        if item.risk is not ToolRisk.READ_ONLY or item.requires_approval
    ]
    if unsafe:
        names = ", ".join(sorted(unsafe))
        raise ValueError(f"tools require an authorization/approval middleware: {names}")
    return [item.tool for item in registrations]
