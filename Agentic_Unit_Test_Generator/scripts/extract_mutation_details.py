#!/usr/bin/env python3
"""
Extract mutation details from mutmut cache and save as JSON for parsing.
Run this AFTER mutmut to get full mutation descriptions beyond what junitxml provides.
"""
import json
import sys
import subprocess
from pathlib import Path


def extract_mutations_to_json(output_file="mutation_details.json"):
    """Run 'mutmut results' and parse into structured data."""
    try:
        result = subprocess.run(
            ["mutmut", "results", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            # Filter for survived mutations
            survived = []
            if isinstance(data, dict) and "mutation_id" in data:
                # Single format
                if data.get("status") == "survived":
                    survived.append(data)
            elif isinstance(data, list):
                # List format
                survived = [m for m in data if m.get("status") == "survived"]

            output = {
                "survived_count": len(survived),
                "mutations": [
                    {
                        "id": m.get("mutation_id", "unknown"),
                        "line": m.get("line", "?"),
                        "operator": m.get("mutation_type", "unknown"),
                        "file": m.get("filename", "unknown"),
                        "original": m.get("original", ""),
                        "mutated": m.get("mutated", ""),
                    }
                    for m in survived[:20]  # Limit to top 20
                ]
            }
            with open(output_file, "w") as f:
                json.dump(output, f, indent=2)
            print(f"[MUTATION DETAILS] Extracted {len(survived)} survived mutations to {output_file}")
            return output_file
        else:
            print(f"[MUTATION DETAILS] mutmut results returned no JSON output", file=sys.stderr)
            return None
    except subprocess.TimeoutExpired:
        print("[MUTATION DETAILS] mutmut results timed out", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"[MUTATION DETAILS] Failed to parse mutmut JSON: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[MUTATION DETAILS] Error extracting mutations: {e}", file=sys.stderr)
        return None


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "mutation_details.json"
    extract_mutations_to_json(output)
