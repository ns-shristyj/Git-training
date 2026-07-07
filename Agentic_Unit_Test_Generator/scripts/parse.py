#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import json
import os
import re
import sys

def strip_ansi_codes(text):
    """Removes ANSI escape codes (terminal styling/colors) from strings."""
    if not text:
        return text
    ansi_regex = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_regex.sub('', text)

def generate_github_summary(report):
    """Generates a highly presentable Markdown UI summary for GitHub Actions."""
    summary_env = os.environ.get('GITHUB_STEP_SUMMARY')
    if not summary_env:
        # Fallback to console print if not running inside GitHub Actions
        print("\n[INFO] GITHUB_STEP_SUMMARY not detected. Skipping Markdown UI generation.")
        return

    lang = report["language"].upper()
    total = report["summary"]["total"]
    passed = report["summary"]["passed"]
    failed = report["summary"]["failed"]

    # Select banner status emoji
    status_emoji = "✅" if failed == 0 else "❌"
    
    markdown = f"""
# {status_emoji} Test Execution Summary ({lang})

| Total Tests | Passed ✅ | Failed ❌ | Pass Rate |
| :--- | :--- | :--- | :--- |
| **{total}** | <font color="green">**{passed}**</font> | <font color="red">**{failed}**</font> | **{int((passed/total)*100) if total > 0 else 0}%** |

---

## Detailed Test Breakdown
| Test Case Name | Status | Error Details |
| :--- | :---: | :--- |
"""

    for test in report["tests"]:
        if test["status"] == "passed":
            status_tag = "🟢 **PASSED**"
            error_detail = "*-*"
        else:
            status_tag = "🔴 **FAILED**"
            # Format error details cleanly into a collapsible block to prevent clutter
            clean_error = test["error_message"].replace('\n', '<br>') if test["error_message"] else "Unknown Error"
            error_detail = f"<details><summary>View Error Trace</summary><code style='white-space: pre-wrap;'>{clean_error}</code></details>"
        
        markdown += f"| {test['name']} | {status_tag} | {error_detail} |\n"

    # Write out directly to GitHub's UI rendering pipeline
    with open(summary_env, 'a') as f:
        f.write(markdown)
    print("[PARSER] Beautiful Markdown dashboard appended to GitHub Summary.")


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
        "tests": []
    }

    testsuites = [root] if root.tag == 'testsuite' else root.findall('testsuite')

    for suite in testsuites:
        unified_report["summary"]["total"] += int(suite.get('tests', 0))
        unified_report["summary"]["failed"] += int(suite.get('failures', 0)) + int(suite.get('errors', 0))
        
        for testcase in suite.findall('testcase'):
            test_name = testcase.get('name')
            classname = testcase.get('classname')
            full_name = f"{classname} -> {test_name}" if classname else test_name

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

            unified_report["tests"].append({
                "name": full_name,
                "status": status,
                "error_message": strip_ansi_codes(error_message) 
            })

    unified_report["summary"]["passed"] = (
        unified_report["summary"]["total"] - unified_report["summary"]["failed"]
    )
    return unified_report


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python parse.py <xml_file_path> <language>", file=sys.stderr)
        sys.exit(1)

    file_path = sys.argv[1]
    language = sys.argv[2]
    
    # Process
    report = parse_junit_xml(file_path, language)
        
    # Save raw JSON backup artifact
    with open('unified_results.json', 'w') as f:
        json.dump(report, f, indent=2)

    # Render interactive UI
    generate_github_summary(report)