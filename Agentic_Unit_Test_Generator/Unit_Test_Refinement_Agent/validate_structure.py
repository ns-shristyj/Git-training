#!/usr/bin/env python3
"""Quick validation that agent structure is correct (no imports, just checks)."""
import sys
import ast

def validate_file(path, expected_functions=None):
    """Parse file and check for expected functions."""
    try:
        with open(path) as f:
            tree = ast.parse(f.read())
    except SyntaxError as e:
        print(f"✗ {path}: syntax error — {e}")
        return False

    funcs = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    if expected_functions:
        missing = expected_functions - funcs
        if missing:
            print(f"✗ {path}: missing functions {missing}")
            return False

    print(f"✓ {path}: valid")
    return True

def main():
    checks = [
        ("agent.py", {"invoke"}),
        ("generator.py", {"refine_tests"}),
        ("prompts.py", {"build_system_prompt", "build_user_message", "build_retry_message"}),
        ("github_input.py", {"fetch_source_from_github", "fetch_multiple_from_github"}),
        ("validators.py", {"check_python_test_quality", "check_generic_test_quality"}),
        ("language_framework.py", {"detect_language_framework"}),
        ("local_test.py", {"main"}),
    ]

    all_pass = True
    for filename, expected_funcs in checks:
        if not validate_file(filename, expected_funcs):
            all_pass = False

    if all_pass:
        print("\n✓ All files structurally valid")
        sys.exit(0)
    else:
        print("\n✗ Some files have issues")
        sys.exit(1)

if __name__ == "__main__":
    main()
