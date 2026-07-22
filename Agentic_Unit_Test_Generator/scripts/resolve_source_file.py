#!/usr/bin/env python3
"""
resolve_source_file.py

Given a generated test file path (e.g. Agentic_Unit_Test_Generator/tests/test_calculator.py),
extract import statements to find the source module it targets, then resolve to file path.

Example:
  Test file contains: from NIC_SecEng_Task.Calculator.string_func import ...
  Resolves to: NIC_SecEng_Task/Calculator/string_func.py

Usage:
    python3 resolve_source_file.py <test_file_path>
"""

import os
import re
import sys

SEARCH_ROOT = "NIC_SecEng_Task"


def extract_source_module_from_imports(test_file_path: str):
    """Parse test file imports and extract non-test module paths."""
    try:
        with open(test_file_path, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"[resolve] Error reading test file: {e}", file=sys.stderr)
        return None

    # Look for import statements
    patterns = [
        r'from\s+([\w.]+)\s+import',
        r'import\s+([\w.]+)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            # Skip test modules
            if 'test' in match.lower():
                continue
            # Return first non-test import
            return match

    return None


def module_path_to_file_path(module_path: str) -> str:
    """Convert module path (e.g., NIC_SecEng_Task.Calculator.string_func) to file path."""
    return module_path.replace('.', '/') + '.py'


def find_source_file(module_path: str):
    """Find source file by converting module path to file path."""
    file_path = module_path_to_file_path(module_path)

    if os.path.exists(file_path):
        return file_path

    print(f"[resolve] WARNING: module path '{module_path}' -> '{file_path}' not found", file=sys.stderr)
    return None


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 resolve_source_file.py <test_file_path>", file=sys.stderr)
        sys.exit(1)

    test_file_path = sys.argv[1]

    # Extract source module from test file imports
    source_module = extract_source_module_from_imports(test_file_path)

    if source_module is None:
        print(f"[resolve] No source module found in imports of {test_file_path}", file=sys.stderr)
        return

    # Convert module path to file path and verify it exists
    source_file = find_source_file(source_module)

    if source_file is None:
        return

    print(source_file)


if __name__ == "__main__":
    main()
