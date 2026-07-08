#!/usr/bin/env python3
"""
filter_source_files.py

Reads a list of changed file paths from stdin (one per line, from git diff),
filters out non-testable files, and writes GitHub Actions outputs:

  run_generation=true/false
  source_file=<path>
  test_file=<path>
  filename_raw=<basename>

Usage (in workflow):
    git diff --name-only origin/base HEAD | python filter_source_files.py >> "$GITHUB_OUTPUT"

Selection logic:
  - Only .py files (hardcoded for prototype, extend ALLOWED_EXTENSIONS for multi-language)
  - Skip files matching SKIP_PATTERNS (tests, migrations, boilerplate, UI, config, etc.)
  - Skip files smaller than MIN_LINES (stubs, __init__.py, etc.)
  - Pick the first eligible file found (prototype scope: one file per PR)
  - If no eligible file found, output run_generation=false
"""

import sys
import os

# ── Extension whitelist ───────────────────────────────────────────────────────
# Add more when multi-language support is added (see edge case 4.1).
ALLOWED_EXTENSIONS = {".py"}

# ── Path/name patterns to skip ────────────────────────────────────────────────
# Anything matching one of these substrings (case-insensitive) is skipped.
SKIP_PATTERNS = [
    # existing tests
    "test_",
    "_test.",
    "/tests/",
    "/test/",

    # migrations and generated code
    "migration",
    "alembic",
    "schema",
    "generated",
    "auto_generated",

    # config and tooling
    "setup.py",
    "setup.cfg",
    "pyproject.toml",
    "conftest.py",
    ".flake8",
    ".pylintrc",
    "requirements",

    # UI / frontend leftovers in Python repos
    "static/",
    "templates/",
    "assets/",
    "public/",

    # CI / infrastructure
    ".github/",
    "Dockerfile",
    "docker-compose",
    "makefile",
    ".sh",

    # boilerplate entry points with no real logic
    "manage.py",
    "wsgi.py",
    "asgi.py",
    "app.py",          # Flask/FastAPI root entry — no logic to test
    "main.py",         # if it's just an entrypoint; remove if your main.py has real logic

    # the agent's own scripts — don't generate tests for the test generator
    "Agentic_Unit_Test_Generator/",
    "agentic_unit_test_generator/",

    # common gitignore-worthy files that sometimes slip through
    ".env",
    "__pycache__",
    ".pyc",
]

# ── Minimum lines threshold ───────────────────────────────────────────────────
# Files shorter than this are likely stubs, __init__.py re-exports, or constants.
MIN_LINES = 10

# ── Test output path template ─────────────────────────────────────────────────
# Where the generated test file will be written relative to the repo root.
TEST_OUTPUT_DIR = "Agentic_Unit_Test_Generator/tests"


def is_skippable(path: str) -> bool:
    lower = path.lower()
    for pattern in SKIP_PATTERNS:
        if pattern.lower() in lower:
            return True
    return False


def count_lines(path: str) -> int:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except (OSError, IOError):
        return 0


def derive_test_path(source_path: str) -> str:
    basename = os.path.basename(source_path)
    stem = os.path.splitext(basename)[0]
    return os.path.join(TEST_OUTPUT_DIR, f"test_{stem}.py")


def main():
    changed_files = [line.strip() for line in sys.stdin if line.strip()]

    if not changed_files:
        print("run_generation=false")
        print("# No changed files found", file=sys.stderr)
        return

    eligible = []
    skipped = []

    for path in changed_files:
        ext = os.path.splitext(path)[1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            skipped.append((path, f"extension '{ext}' not in allowed list"))
            continue

        if is_skippable(path):
            skipped.append((path, "matches skip pattern"))
            continue

        if not os.path.exists(path):
            skipped.append((path, "file not found on disk (deleted in this PR?)"))
            continue

        lines = count_lines(path)
        if lines < MIN_LINES:
            skipped.append((path, f"only {lines} lines — below MIN_LINES={MIN_LINES}"))
            continue

        eligible.append(path)

    # log decisions to stderr (visible in Actions logs, not captured as output)
    print(f"\n[filter] Changed files evaluated: {len(changed_files)}", file=sys.stderr)
    for path, reason in skipped:
        print(f"[filter] SKIP  {path} — {reason}", file=sys.stderr)
    for path in eligible:
        print(f"[filter] ELIGIBLE  {path}", file=sys.stderr)

    if not eligible:
        print("run_generation=false")
        print("[filter] No eligible source files found — skipping generation.", file=sys.stderr)
        return

    # prototype: take the first eligible file
    # production: loop over all eligible and generate per file
    source_file = eligible[0]
    test_file = derive_test_path(source_file)
    filename_raw = os.path.basename(source_file)

    if len(eligible) > 1:
        print(
            f"[filter] WARNING: {len(eligible)} eligible files found. "
            f"Prototype only processes the first: {source_file}",
            file=sys.stderr,
        )

    # write GitHub Actions outputs
    print(f"run_generation=true")
    print(f"source_file={source_file}")
    print(f"test_file={test_file}")
    print(f"filename_raw={filename_raw}")


if __name__ == "__main__":
    main()