"""
V13 Intel Scanner
-----------------
Detects new PDF intel files in /intel/,
extracts keywords, and maps them to soldier modules
for potential logic review or update.
"""

import os
import re
import json
from pathlib import Path
from PyPDF2 import PdfReader

INTEL_DIR = Path(__file__).parent
INDEX_PATH = INTEL_DIR / "intel_index.json"

# Basic keyword → soldier mapping
KEYWORD_MAP = {
    "volatility": ["Ball1", "Ball5", "Ball6"],
    "momentum": ["Ball2", "Ball6", "Ball8"],
    "balance": ["Ball3", "Ball4"],
    "vwap": ["Ball3"],
    "mean reversion": ["Ball4"],
    "risk": ["Ball5", "Ball9"],
    "drawdown": ["Ball9", "Ball10"],
    "recovery": ["Ball10"],
    "aggression": ["Ball1", "Ball6"],
}

def extract_keywords(text: str):
    found = set()
    for key in KEYWORD_MAP.keys():
        if re.search(rf"\b{key}\b", text, flags=re.IGNORECASE):
            found.add(key)
    return list(found)

def scan_pdf(path: Path):
    try:
        reader = PdfReader(str(path))
        text = ""
        for page in reader.pages[:3]:  # sample first 3 pages
            text += page.extract_text() or ""
        return extract_keywords(text)
    except Exception as e:
        print(f"[Intel] Failed to read {path.name}: {e}")
        return []

def update_index():
    index = {}
    if INDEX_PATH.exists():
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            index = json.load(f)

    sources = index.get("sources", {})
    for file in INTEL_DIR.glob("*.pdf"):
        key = file.stem.lower()
        if key in sources:
            continue  # already indexed
        keywords = scan_pdf(file)
        influences = sorted({mod for k in keywords for mod in KEYWORD_MAP[k]})
        sources[key] = {
            "file": str(file),
            "tags": keywords,
            "status": "new",
            "influences": influences
        }

    index["sources"] = sources
    index["last_update"] = str(os.path.getmtime(INTEL_DIR))
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
    print(f"[Intel] Index updated: {len(sources)} sources recorded.")

if __name__ == "__main__":
    update_index()
