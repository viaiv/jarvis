import ast
from datetime import datetime
import operator
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from langchain_core.tools import tool

ALLOWED_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
ALLOWED_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _eval_ast(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body)

    if isinstance(node, ast.Constant):
        value = node.value
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Somente numeros sao permitidos.")
        return float(value)

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in ALLOWED_BIN_OPS:
            raise ValueError(f"Operador nao permitido: {op_type.__name__}.")
        left = _eval_ast(node.left)
        right = _eval_ast(node.right)
        return ALLOWED_BIN_OPS[op_type](left, right)

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in ALLOWED_UNARY_OPS:
            raise ValueError(f"Operador nao permitido: {op_type.__name__}.")
        value = _eval_ast(node.operand)
        return ALLOWED_UNARY_OPS[op_type](value)

    raise ValueError(f"Expressao nao suportada: {type(node).__name__}.")


def evaluate_expression(expression: str) -> float:
    parsed = ast.parse(expression, mode="eval")
    return _eval_ast(parsed)


@tool
def calculator(expression: str) -> str:
    """Calcula uma expressao aritmetica com +, -, *, /, %, ** e parenteses."""

    result = evaluate_expression(expression)
    if result.is_integer():
        return str(int(result))
    return str(result)


@tool
def current_time(timezone_name: str = "UTC") -> str:
    """Retorna data e hora atual em formato ISO para o fuso horario informado."""

    try:
        tz = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return (
            f"Fuso horario invalido: '{timezone_name}'. "
            "Use valores como 'UTC' ou 'America/Sao_Paulo'."
        )
    return datetime.now(tz).isoformat()


ALL_TOOLS = [calculator, current_time]
