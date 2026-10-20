"""Compare two Python test files by their syntax tree, with every docstring removed.

Comments, docstrings, blank lines, line wrapping and trailing commas do not count; every
statement, name, string and number does. Prints 16 hex characters for each side and EQUAL
or NOT EQUAL. Usage: python -I core.py <expected> <actual>
"""
import ast, hashlib, sys

def tree(path):
    node = ast.parse(open(path).read())
    for n in ast.walk(node):
        body = getattr(n, "body", None)
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and body \
                and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            n.body = body[1:] or [ast.Pass()]
    return ast.dump(node, include_attributes=False)

a, b = (tree(p) for p in sys.argv[1:3])
ha, hb = (hashlib.sha256(x.encode()).hexdigest()[:16] for x in (a, b))
print(f"expected {ha}  actual {hb}  {'EQUAL' if a == b else 'NOT EQUAL'}")
sys.exit(0 if a == b else 1)
