"""
V13 Doctrine Sync
-----------------
Reads intel_index.json and prints a soldier-to-intel influence report.
Used by Commander to confirm which doctrines are active at runtime.
"""

import json
from pathlib import Path

INDEX_PATH = Path(__file__).parent / "intel_index.json"

def load_intel_index():
    if not INDEX_PATH.exists():
        print("[Doctrine] No intel index found.")
        return {}
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def map_influences():
    index = load_intel_index()
    sources = index.get("sources", {})
    soldier_map = {}

    for key, data in sources.items():
        influences = data.get("influences", [])
        for soldier in influences:
            soldier_map.setdefault(soldier, []).append(key)

    return soldier_map

def print_doctrine_report():
    soldier_map = map_influences()
    if not soldier_map:
        print("[Doctrine] No influence map available.")
        return

    print("\n📘 V13 Doctrine Influence Report")
    print("──────────────────────────────────────────────")
    for soldier, doctrines in sorted(soldier_map.items()):
        print(f"{soldier:<8} ← {', '.join(doctrines)}")
    print("──────────────────────────────────────────────\n")

if __name__ == "__main__":
    print_doctrine_report()
