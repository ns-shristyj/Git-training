"""Deterministic quality gates for generated test code.

Prompt instructions alone don't guarantee the model won't emit a vacuous test
(assert True, empty body, no assertions at all). These checks run against the
model's actual output and produce concrete rejection reasons that get fed back
to the model for a retry.
"""
import ast
import re

RAISES_CONTEXT_NAMES = {"raises", "assertRaises", "assertRaisesRegex", "warns"}


def check_python_test_quality(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"syntax_error: {e}"]

    test_funcs = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test")
    ]

    if not test_funcs:
        return ["no_test_functions_found"]

    issues = []
    for fn in test_funcs:
        if _is_vacuous_python_test(fn):
            issues.append(f"vacuous_test:{fn.name}")
    return issues


def _is_vacuous_python_test(fn: ast.FunctionDef) -> bool:
    body = fn.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]  # drop docstring

    if not body:
        return True
    if all(isinstance(stmt, ast.Pass) for stmt in body):
        return True

    for node in ast.walk(fn):
        if isinstance(node, ast.Assert):
            if not _is_trivially_true(node.test):
                return False
        elif isinstance(node, ast.With):
            for item in node.items:
                call = item.context_expr
                if isinstance(call, ast.Call):
                    name = _call_name(call.func)
                    if name in RAISES_CONTEXT_NAMES:
                        return False
        elif isinstance(node, ast.Call):
            name = _call_name(node.func)
            if name and name.startswith("assert") and name != "assert":
                return False

    return True


def _call_name(func_node) -> str:
    if isinstance(func_node, ast.Attribute):
        return func_node.attr
    if isinstance(func_node, ast.Name):
        return func_node.id
    return ""


def _is_trivially_true(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and bool(node.value)


_GENERIC_ASSERTION_PATTERN = re.compile(
    r"\b(assert(?:Equals|True|False|NotNull|Null|Throws|That)?\(|expect\(|toBe\(|toEqual\(|toThrow\(|\.should\b)"
)


def check_generic_test_quality(code: str, language: str) -> list[str]:
    """Best-effort heuristic for non-Python languages (no AST available here)."""
    issues = []
    if not code.strip():
        issues.append("empty_output")
        return issues
    if not _GENERIC_ASSERTION_PATTERN.search(code):
        issues.append("no_assertion_keyword_found")
    return issues
