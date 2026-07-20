#!/usr/bin/env python3
"""
resolve_source_file.py

Inverse of filter_source_files.derive_test_path(): given a generated test
file path (e.g. Agentic_Unit_Test_Generator/tests/test_calculator.py),
find the application source file it targets (e.g.
NIC_SecEng_Task/Calculator/calculator.py) by basename match under
SEARCH_ROOT.

Used by the mutation-testing CI step to figure out which source file to
mutate for a given detected test file. Prints the resolved path to stdout,
or nothing (exit 0) if no match is found, so the caller can skip that pair.

Usage:
    python3 resolve_source_file.py <test_file_path>
"""

import os
import sys

SEARCH_ROOT = "NIC_SecEng_Task"
SKIP_DIR_SUBSTRINGS = ("__pycache__", "/tests/", "/test/")


def stem_from_test_path(test_path: str) -> str:
    basename = os.path.basename(test_path)
    stem = os.path.splitext(basename)[0]
    if stem.startswith("test_"):
        stem = stem[len("test_"):]
    return stem


def find_source_file(stem: str):
    target = f"{stem}.py"
    matches = []
    for dirpath, _dirnames, filenames in os.walk(SEARCH_ROOT):
        if any(skip in dirpath.replace(os.sep, "/") + "/" for skip in SKIP_DIR_SUBSTRINGS):
            continue
        if target in filenames:
            matches.append(os.path.join(dirpath, target))

    if not matches:
        return None
    if len(matches) > 1:
        print(
            f"[resolve] WARNING: multiple source files named '{target}' found "
            f"({matches}) — using first match.",
            file=sys.stderr,
        )
    return matches[0]


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 resolve_source_file.py <test_file_path>", file=sys.stderr)
        sys.exit(1)

    stem = stem_from_test_path(sys.argv[1])
    source_file = find_source_file(stem)

    if source_file is None:
        print(f"[resolve] No source file found for stem '{stem}'", file=sys.stderr)
        return

    print(source_file)


if __name__ == "__main__":
    main()
