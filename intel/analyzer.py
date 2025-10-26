"""
Doctrine Analyzer
-----------------
Reads intel_index.json and concept_tags.json.
Builds parameter recommendations for each soldier based on doctrine keywords.
Saves results into config/doctrine_overrides.json.
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).parents[1]
INTEL_INDEX = BASE_DIR / "intel" / "intel_index.json"
CONCEPT_TAGS = BASE_DIR / "intel" / "concept_tags.json"
OVERRIDES = BASE_DIR / "config" / "doctrine_overrides.json"

def load_json(path):
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def analyze_doctrine():
    intel_index = load_json(INTEL_INDEX)
    concept_tags = load_json(CONCEPT_TAGS)
    sources = intel_index.get("sources", {})

    overrides = {}

    for name, src in sources.items():
        tags = src.get("tags", [])
        for tag in tags:
            if tag in concept_tags:
                param = concept_tags[tag]["param"]
                for soldier in src.get("influences", []):
                    overrides.setdefault(soldier, {}).setdefault(param, []).append(tag)

    # write results
    with open(OVERRIDES, "w", encoding="utf-8") as f:
        json.dump(overrides, f, indent=2)

    print(f"[Doctrine Analyzer] Updated overrides for {len(overrides)} soldiers.")
    return overrides

if __name__ == "__main__":
    analyze_doctrine()
