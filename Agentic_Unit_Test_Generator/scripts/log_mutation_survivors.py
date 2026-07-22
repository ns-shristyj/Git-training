#!/usr/bin/env python3
"""
Parse mutation report XMLs and log survived mutant details to workflow console.
Useful for debugging why certain mutants escaped the test suite.
"""
import xml.etree.ElementTree as ET
import sys
import os


def log_survivors(mutation_reports_dir):
    """Parse all mutation XMLs in directory and log survived mutants."""
    if not os.path.isdir(mutation_reports_dir):
        print(f"[MUTATION LOG] Directory not found: {mutation_reports_dir}")
        return

    xml_files = [f for f in os.listdir(mutation_reports_dir) if f.endswith('.xml')]
    if not xml_files:
        print("[MUTATION LOG] No mutation reports found.")
        return

    total_survived = 0
    for xml_file in sorted(xml_files):
        xml_path = os.path.join(mutation_reports_dir, xml_file)
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            testsuites = [root] if root.tag == 'testsuite' else root.findall('testsuite')

            module_name = xml_file.replace('.xml', '')
            survived_in_file = []

            for suite in testsuites:
                for testcase in suite.findall('testcase'):
                    failure = testcase.find('failure')
                    if failure is not None:
                        mutant_id = testcase.get('name', 'unknown')
                        survived_in_file.append(mutant_id)

            total_survived += len(survived_in_file)

            if survived_in_file:
                print(f"🔴 {module_name}: {len(survived_in_file)} mutant(s) survived")
                for m in survived_in_file[:5]:
                    print(f"   └─ {m}")
                if len(survived_in_file) > 5:
                    print(f"   └─ ... and {len(survived_in_file) - 5} more")
            else:
                print(f"✅ {module_name}: All mutants killed!")

        except Exception as e:
            print(f"[ERROR] Failed parsing {xml_file}: {e}", file=sys.stderr)

    print(f"\n📊 Total survived mutants across all modules: {total_survived}")


if __name__ == "__main__":
    mutation_dir = sys.argv[1] if len(sys.argv) > 1 else "./mutation_reports"
    log_survivors(mutation_dir)
