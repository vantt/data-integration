"""Expression language of `derived` metrics.

An expression is arithmetic over metric ids, numbers and calendar quantities:

    gross_revenue / (gmv_target * day_of_month / days_in_month)
    greatest(gmv_target - gross_revenue, 0) / days_left_in_month

Allowed: `+ - * /`, unary minus, numeric constants, metric ids, the calendar names below, and
`greatest(<expr>, <number>)` as a lower clamp. The compiler limit is linearity: two metrics never
multiply each other, and a metric may appear in a denominator only when that division is the root
of the expression (a ratio of two linear forms).
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Callable

CALENDAR_NAMES = ("day_of_month", "days_in_month", "days_left_in_month")


class FormulaError(ValueError):
    """The expression is not valid or exceeds the compiler limits."""


@dataclass(frozen=True)
class Formula:
    text: str
    tree: ast.expr
    metrics: tuple[str, ...]  # metric ids referenced, sorted


def parse(text: str) -> Formula:
    try:
        tree = ast.parse(text, mode="eval").body
    except SyntaxError as exc:
        raise FormulaError(f"cannot parse expression '{text}': {exc.msg}") from exc
    names: set[str] = set()
    _check_nodes(tree, names)
    degree = _degree(tree, at_root=True)
    if degree > 1:
        raise FormulaError(f"'{text}' is not linear in metrics")
    metrics = tuple(sorted(n for n in names if n not in CALENDAR_NAMES))
    if not metrics:
        raise FormulaError(f"'{text}' references no metric")
    return Formula(text=text, tree=tree, metrics=metrics)


def _check_nodes(node: ast.AST, names: set[str]) -> None:
    if isinstance(node, ast.BinOp):
        if not isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            raise FormulaError(f"operator {type(node.op).__name__} is not allowed")
        _check_nodes(node.left, names)
        _check_nodes(node.right, names)
    elif isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, ast.USub):
            raise FormulaError(f"unary operator {type(node.op).__name__} is not allowed")
        _check_nodes(node.operand, names)
    elif isinstance(node, ast.Name):
        names.add(node.id)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise FormulaError(f"constant {node.value!r} is not a number")
    elif isinstance(node, ast.Call):
        if not (isinstance(node.func, ast.Name) and node.func.id == "greatest"):
            raise FormulaError("the only function allowed is greatest(<expr>, <number>)")
        if node.keywords or len(node.args) != 2 or not _is_number(node.args[1]):
            raise FormulaError("greatest takes exactly (<expr>, <number>)")
        _check_nodes(node.args[0], names)
    else:
        raise FormulaError(f"{type(node).__name__} is not allowed in an expression")


def _is_number(node: ast.AST) -> bool:
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        node = node.operand
    return isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool)


def _degree(node: ast.AST, at_root: bool = False) -> int:
    """0 = no metric, 1 = linear in metrics. Raises FormulaError beyond the limit."""
    if isinstance(node, ast.Name):
        return 0 if node.id in CALENDAR_NAMES else 1
    if isinstance(node, ast.Constant):
        return 0
    if isinstance(node, ast.UnaryOp):
        return _degree(node.operand)
    if isinstance(node, ast.Call):  # greatest(x, c)
        return _degree(node.args[0])
    assert isinstance(node, ast.BinOp)
    left, right = _degree(node.left), _degree(node.right)
    if isinstance(node.op, (ast.Add, ast.Sub)):
        return max(left, right)
    if isinstance(node.op, ast.Mult):
        if left + right > 1:
            raise FormulaError("two metrics multiply each other")
        return left + right
    # division
    if right == 0:
        return left
    if not at_root:
        raise FormulaError("a metric in a denominator is only allowed when the division is the root of the expression")
    return 1


def to_sql(formula: Formula, metric_sql: Callable[[str], str], calendar_sql: Callable[[str], str]) -> str:
    """Render the expression; every division guards its denominator with NULLIF(..., 0)."""

    def render(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return calendar_sql(node.id) if node.id in CALENDAR_NAMES else metric_sql(node.id)
        if isinstance(node, ast.Constant):
            return repr(node.value)
        if isinstance(node, ast.UnaryOp):
            return f"(-{render(node.operand)})"
        if isinstance(node, ast.Call):
            inner, floor = render(node.args[0]), render(node.args[1])
            # CASE, not GREATEST: DuckDB's GREATEST ignores NULL, the clamp must propagate it
            return f"(CASE WHEN {inner} < {floor} THEN {floor} ELSE {inner} END)"
        assert isinstance(node, ast.BinOp)
        left, right = render(node.left), render(node.right)
        if isinstance(node.op, ast.Div):
            return f"({left} / NULLIF({right}, 0))"
        op = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*"}[type(node.op)]
        return f"({left} {op} {right})"

    return render(formula.tree)
