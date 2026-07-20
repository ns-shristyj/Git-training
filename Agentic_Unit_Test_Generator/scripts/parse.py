#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import json
import os
import re
import sys
import ast

def _clean_group_heading(group_name):
    """
    Extracts the file name and the test class name from a dotted path 
    and turns 'Agentic_Unit_Test_Generator.tests.test_complex_service.TestProcessUserData'
    into 'Complex service - Process user data'.
    """
    parts = group_name.split('.')
    
    # If it's a full path, isolate just the last two components (file name and class/function)
    if len(parts) >= 2:
        target_parts = parts[-2:]
    else:
        target_parts = parts

    cleaned_components = []
    for part in target_parts:
        # Skip generic grouping folders if they accidentally leak into the last two parts
        if part.lower() in ["tests", "test"]:
            continue
            
        # Remove "test_" or "Test_" prefixes safely
        p = re.sub(r'^[Tt]est_?', '', part)
        # Add spaces before capital letters (handles CamelCase class names)
        p = re.sub(r'(?<!^)(?=[A-Z])', ' ', p)
        # Convert underscores and hyphens to spaces
        p = p.replace("_", " ").replace("-", " ")
        # Clean up double spaces
        p = " ".join(p.split())
        
        if p:
            cleaned_components.append(p)
            
    # Join the file name and class name with a clean dash space
    final_heading = " - ".join(cleaned_components)
    
    # Capitalize only the very first letter of the combined heading string
    return final_heading.capitalize()

def _extract_test_docstrings(group_name):
    """Parses a test file using AST to map test function names to their docstrings."""
    # Convert package path back to a real file path
    # e.g., 'Agentic_Unit_Test_Generator.tests.test_complex_service' -> 'Agentic_Unit_Test_Generator/tests/test_complex_service.py'
    file_path = group_name.replace('.', '/') + '.py'
    
    docstrings = {}
    if not os.path.exists(file_path):
        return docstrings

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            node = ast.parse(f.read(), filename=file_path)
        
        # Walk through the file and look for function/method definitions
        for item in ast.walk(node):
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if item.name.startswith("test_"):
                    doc = ast.get_docstring(item)
                    if doc:
                        # Clean up formatting whitespace/newlines from docstrings
                        docstrings[item.name] = " ".join(doc.split())
    except Exception as e:
        print(f"[PARSER] Warning: Could not parse docstrings from {file_path}: {e}", file=sys.stderr)
        
    return docstrings

def strip_ansi_codes(text):
    """Removes ANSI escape codes (terminal styling/colors) from strings."""
    if not text:
        return text
    ansi_regex = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_regex.sub('', text)

def _shorten_group_name(group_name):
    """Drops the package-path prefix, keeping only the module (and class, if
    any) — e.g. 'Agentic_Unit_Test_Generator.tests.test_api_client.TestFoo'
    becomes 'test_api_client.TestFoo'; a plain module with no class becomes
    just 'test_string_func'."""
    parts = group_name.split(".")
    if len(parts) < 2:
        return group_name
    last = parts[-1]
    if last[:1].isupper():
        return f"{parts[-2]}.{last}"
    return last


def _render_test_table(tests, docstrings):
    rows = "| Test Case | Description | Status | Error Details |\n| :--- | :--- | :---: | :--- |\n"
    for test in tests:
        if test["status"] == "passed":
            status_tag = "🟢 **PASSED**"
            error_detail = "*-*"
        else:
            status_tag = "🔴 **FAILED**"
            # Format error details cleanly into a collapsible block to prevent clutter
            clean_error = test["error_message"].replace('\n', '<br>') if test["error_message"] else "Unknown Error"
            error_detail = f"<details><summary>View Error Trace</summary><code style='white-space: pre-wrap;'>{clean_error}</code></details>"

        clean_name = test['short_name'].replace("test_", "").replace("_", " ").capitalize()
        description = docstrings.get(test['short_name'])
        if not description:
            description = clean_name
        rows += f"| `{clean_name}` | {description} | {status_tag} | {error_detail} |\n"
    return rows

def parse_coverage_xml(coverage_file_path):
    """Parses standard Cobertura XML coverage reports."""
    if not coverage_file_path or not os.path.exists(coverage_file_path):
        return None
    try:
        tree = ET.parse(coverage_file_path)
        root = tree.getroot()
        line_rate = float(root.get("line-rate", 0)) * 100
        lines_valid = int(root.get("lines-valid", 0))
        lines_covered = int(root.get("lines-covered", 0))
        
        file_breakdown = []
        for package in root.findall(".//package"):
            for clazz in package.findall(".//class"):
                c_name = clazz.get("name", "Unknown Module")
                c_line_rate = float(clazz.get("line-rate", 0)) * 100
                if "agentic_unit_test_generator" in c_name.lower() or "test_" in c_name.lower() or "parse" in c_name.lower():
                    continue
                file_breakdown.append({"name": c_name, "rate": f"{c_line_rate:.1f}%"})
        return {"total_rate": f"{line_rate:.1f}%", "lines_valid": lines_valid, "lines_covered": lines_covered, "files": file_breakdown}
    except Exception as e:
        print(f"[COVERAGE] Warning: Failed parsing coverage XML metadata: {e}", file=sys.stderr)
        return None

def parse_mutation_xml(mutation_path):
    """Parses mutmut's `mutmut junitxml` output (JUnit-shaped: each mutant is
    a testcase; a <failure> means the mutant survived, no <failure> means it
    was killed). Returns {killed, survived, total, score} or None.

    `mutation_path` may be a single XML file, or a directory containing one
    XML file per source/test pair (one mutmut run per pair) — counts are
    summed across every file in the directory.
    """
    if not mutation_path or not os.path.exists(mutation_path):
        return None

    xml_files = []
    if os.path.isdir(mutation_path):
        xml_files = [os.path.join(mutation_path, f) for f in os.listdir(mutation_path) if f.endswith(".xml")]
    else:
        xml_files = [mutation_path]

    killed = survived = total = 0
    for xml_file in xml_files:
        try:
            report = parse_junit_xml(xml_file, "mutation")
            total += report["summary"]["total"]
            survived += report["summary"]["failed"]
            killed += report["summary"]["passed"]
        except Exception as e:
            print(f"[MUTATION] Warning: Failed parsing mutation XML '{xml_file}': {e}", file=sys.stderr)

    if total == 0:
        return None
    score = (killed / total) * 100
    return {"killed": killed, "survived": survived, "total": total, "score": f"{score:.1f}%"}


def generate_github_summary(report, coverage_data, mutation_data=None):
    """Generates a highly presentable Markdown UI summary and saves it to a file for PR comments.

    Renders one summary + detail table per source test file (grouped by JUnit
    classname), instead of merging every file's tests into a single table.
    """
    lang = report["language"].upper()
    total = report["summary"]["total"]
    passed = report["summary"]["passed"]
    failed = report["summary"]["failed"]

    # Select banner status emoji
    status_emoji = "✅" if failed == 0 else "❌"

    markdown = f"""### {status_emoji} Automated Test Execution Summary ({lang})

| Total Tests | Passed ✅ | Failed ❌ | Pass Rate |
| :--- | :--- | :--- | :--- |
| **{total}** | **{passed}** | **{failed}** | **{int((passed/total)*100) if total > 0 else 0}%** |
"""

# Append coverage details block if valid data exists
    if coverage_data:
        markdown += f"""
### 📊 Code Coverage Summary

| Overall Line Coverage | Covered Lines | Total Executable Lines |
| :---: | :---: | :---: |
| 🛡️ **{coverage_data['total_rate']}** | **{coverage_data['lines_covered']}** | **{coverage_data['lines_valid']}** |

<details>
<summary>📂 View Coverage Breakdown Per Module</summary>

| Module Path / Name | Coverage Rate |
| :--- | :---: |
"""
        for f in coverage_data["files"]:
            markdown += f"| `{f['name']}` | **{f['rate']}** |\n"
        markdown += "</details>\n"

    if mutation_data:
        markdown += f"""
### 🧬 Mutation Score

| Mutation Score | Killed | Survived | Total Mutants |
| :---: | :---: | :---: | :---: |
| 🎯 **{mutation_data['score']}** | **{mutation_data['killed']}** | **{mutation_data['survived']}** | **{mutation_data['total']}** |

*Mutation score = killed / total mutants. A surviving mutant means an injected bug slipped past every assertion in the generated test.*
"""

    for group_name, group in report["groups"].items():
        g_total = group["summary"]["total"]
        g_passed = group["summary"]["passed"]
        g_failed = group["summary"]["failed"]
        g_emoji = "✅" if g_failed == 0 else "❌"

        open_attr = " open" if g_failed > 0 else ""
        markdown += f"""
---

<details{open_attr}>
<summary>{g_emoji} <b>{_clean_group_heading(group_name)}</b> — {g_passed}/{g_total} passed</summary>

| Tests | Passed ✅ | Failed ❌ | Pass Rate |
| :--- | :--- | :--- | :--- |
| **{g_total}** | **{g_passed}** | **{g_failed}** | **{int((g_passed/g_total)*100) if g_total > 0 else 0}%** |

"""
        docstrings = _extract_test_docstrings(group_name)
        markdown += _render_test_table(group["tests"], docstrings)
        markdown += "\n</details>\n"

    # Save to a dedicated markdown file for the PR workflow to capture
    output_comment_file = 'pr_comment.md'
    with open(output_comment_file, 'w') as f:
        f.write(markdown)
    print(f"[PARSER] Markdown dashboard successfully saved to {output_comment_file} for PR delivery.")

def parse_junit_xml(xml_file_path, language_name):
    """Parses standard JUnit XML files."""
    if not os.path.exists(xml_file_path):
        print(f"CRITICAL ERROR: Target XML file '{xml_file_path}' not found.", file=sys.stderr)
        sys.exit(1)

    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to parse XML file: {e}", file=sys.stderr)
        sys.exit(1)

    unified_report = {
        "language": language_name,
        "summary": {"total": 0, "passed": 0, "failed": 0},
        "tests": [],
        "groups": {}
    }

    testsuites = [root] if root.tag == 'testsuite' else root.findall('testsuite')

    for suite in testsuites:
        unified_report["summary"]["total"] += int(suite.get('tests', 0))
        unified_report["summary"]["failed"] += int(suite.get('failures', 0)) + int(suite.get('errors', 0))

        for testcase in suite.findall('testcase'):
            test_name = testcase.get('name')
            classname = testcase.get('classname')
            full_name = f"{classname} -> {test_name}" if classname else test_name
            group_name = classname or suite.get('name') or "Tests"

            status = "passed"
            error_message = None

            failure = testcase.find('failure')
            error = testcase.find('error')

            if failure is not None:
                status = "failed"
                error_message = failure.text or failure.get('message')
            elif error is not None:
                status = "failed"
                error_message = error.text or error.get('message')

            test_entry = {
                "name": full_name,
                "short_name": test_name,
                "status": status,
                "error_message": strip_ansi_codes(error_message)
            }
            unified_report["tests"].append(test_entry)

            group = unified_report["groups"].setdefault(
                group_name,
                {"summary": {"total": 0, "passed": 0, "failed": 0}, "tests": []}
            )
            group["tests"].append(test_entry)
            group["summary"]["total"] += 1
            if status == "failed":
                group["summary"]["failed"] += 1

    unified_report["summary"]["passed"] = (
        unified_report["summary"]["total"] - unified_report["summary"]["failed"]
    )
    for group in unified_report["groups"].values():
        group["summary"]["passed"] = group["summary"]["total"] - group["summary"]["failed"]

    return unified_report


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python parse.py <xml_file_path> <language> [coverage_file_path] [mutation_file_path]", file=sys.stderr)
        sys.exit(1)

    file_path = sys.argv[1]
    language = sys.argv[2]
    coverage_path = sys.argv[3] if len(sys.argv) > 3 else None
    mutation_path = sys.argv[4] if len(sys.argv) > 4 else None

    # Process
    report = parse_junit_xml(file_path, language)
    coverage_data = parse_coverage_xml(coverage_path)
    mutation_data = parse_mutation_xml(mutation_path)

    if mutation_data:
        report["mutation"] = mutation_data

    # Save raw JSON backup artifact
    with open('unified_results.json', 'w') as f:
        json.dump(report, f, indent=2)

    # Render interactive UI
    generate_github_summary(report, coverage_data, mutation_data)