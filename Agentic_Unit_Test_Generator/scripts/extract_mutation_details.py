#!/usr/bin/env python3
"""
Extract mutation details from mutmut cache and save as JSON for parsing.
Reads from .mutmut-cache to extract survived mutation details.
"""
import json
import sys
import os
from pathlib import Path


def extract_mutations_from_cache(output_file="mutation_details.json"):
    """Parse .mutmut-cache for survived mutations with full details."""
    cache_file = ".mutmut-cache"
    if not os.path.exists(cache_file):
        print(f"[MUTATION DETAILS] Cache file not found: {cache_file}", file=sys.stderr)
        return None

    try:
        with open(cache_file, "r") as f:
            cache_data = json.load(f)

        survived = []

        # mutmut cache format: dict with "mutations" key
        if "mutations" in cache_data:
            for mut_id, mut_data in cache_data["mutations"].items():
                if mut_data.get("status") == "survived":
                    # mut_data has keys: status, line, mutator, original, mutated, operator
                    survived.append({
                        "id": f"Mutant #{mut_id}" if isinstance(mut_id, int) else mut_id,
                        "line": mut_data.get("line", "?"),
                        "operator": mut_data.get("mutator", mut_data.get("operator", "unknown")),
                        "original": str(mut_data.get("original", ""))[:100],
                        "mutated": str(mut_data.get("mutated", ""))[:100],
                    })

        output = {
            "survived_count": len(survived),
            "mutations": survived[:20]
        }

        with open(output_file, "w") as f:
            json.dump(output, f, indent=2)

        print(f"[MUTATION DETAILS] Extracted {len(survived)} survived mutations to {output_file}")
        return output_file

    except json.JSONDecodeError as e:
        print(f"[MUTATION DETAILS] Failed parsing cache JSON: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[MUTATION DETAILS] Error extracting: {e}", file=sys.stderr)
        return None


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "mutation_details.json"
    extract_mutations_from_cache(output)
