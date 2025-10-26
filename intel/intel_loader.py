import json
from pathlib import Path

INTEL_PATH = Path(__file__).parent / "intel_index.json"

def load_intel_index():
    if not INTEL_PATH.exists():
        return {}
    with open(INTEL_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_influenced_soldiers(intel_key: str):
    idx = load_intel_index()
    try:
        return idx["sources"][intel_key]["influences"]
    except KeyError:
        return []

if __name__ == "__main__":
    data = load_intel_index()
    print(json.dumps(data, indent=2))
