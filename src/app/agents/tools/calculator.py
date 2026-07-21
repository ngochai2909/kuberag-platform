from __future__ import annotations

import ast
import math
import operator
from collections.abc import Callable

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field

_MAX_EXPRESSION_LENGTH = 200
_MAX_AST_NODES = 64
_MAX_AST_DEPTH = 12
_MAX_INPUT_ABS = 1e12
_MAX_RESULT_ABS = 1e100
_MAX_EXPONENT_ABS = 100

_BINARY_OPERATORS: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}
_UNARY_OPERATORS: dict[type[ast.unaryop], Callable[[float], float]] = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


class CalculatorInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    expression: str = Field(
        min_length=1,
        max_length=_MAX_EXPRESSION_LENGTH,
        description="Arithmetic expression using numbers, parentheses, +, -, *, /, //, %, or **.",
    )


@tool(args_schema=CalculatorInput)
def calculate(expression: str) -> str:
    """Evaluate a bounded arithmetic expression without executing arbitrary code."""

    try:
        result = evaluate_expression(expression)
    except (ArithmeticError, RecursionError, SyntaxError, TypeError, ValueError) as exc:
        return f"Invalid expression: {exc}"

    if isinstance(result, int):
        return str(result)
    return format(result, ".15g")


def evaluate_expression(expression: str) -> int | float:
    if len(expression) > _MAX_EXPRESSION_LENGTH:
        raise ValueError("expression is too long")

    tree = ast.parse(expression, mode="eval")
    nodes = list(ast.walk(tree))
    if len(nodes) > _MAX_AST_NODES:
        raise ValueError("expression is too complex")
    if _ast_depth(tree) > _MAX_AST_DEPTH:
        raise ValueError("expression is nested too deeply")

    return _evaluate_node(tree.body)


def _ast_depth(node: ast.AST) -> int:
    children = list(ast.iter_child_nodes(node))
    if not children:
        return 1
    return 1 + max(_ast_depth(child) for child in children)


def _evaluate_node(node: ast.AST) -> int | float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("only real numbers are supported")
        return _validate_number(node.value, maximum=_MAX_INPUT_ABS)

    if isinstance(node, ast.UnaryOp):
        unary_operation = _UNARY_OPERATORS.get(type(node.op))
        if unary_operation is None:
            raise ValueError(f"unsupported operator: {type(node.op).__name__}")
        return _validate_number(unary_operation(_evaluate_node(node.operand)))

    if isinstance(node, ast.BinOp):
        left = _evaluate_node(node.left)
        right = _evaluate_node(node.right)

        if isinstance(node.op, ast.Pow):
            if not isinstance(right, int) or abs(right) > _MAX_EXPONENT_ABS:
                raise ValueError("exponent must be an integer between -100 and 100")
            if abs(left) > _MAX_INPUT_ABS:
                raise ValueError("power base is too large")
            return _validate_number(operator.pow(left, right))

        binary_operation = _BINARY_OPERATORS.get(type(node.op))
        if binary_operation is None:
            raise ValueError(f"unsupported operator: {type(node.op).__name__}")
        return _validate_number(binary_operation(left, right))

    raise ValueError(f"unsupported expression element: {type(node).__name__}")


def _validate_number(
    value: int | float,
    *,
    maximum: float = _MAX_RESULT_ABS,
) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("result is not a real number")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("result is not finite")
    if abs(value) > maximum:
        raise ValueError("number is outside the allowed range")
    return value
