# ============================================================
# V13_DOCTRINE_REGISTRY_INIT.PY (PAPER MODE BLUEPRINT)
# Build: V13.2025.10.21.01
# Phase: 6 — Live Readiness Design
# Mode: PAPER (Simulation Safe)
# ============================================================

"""
Purpose:
    Doctrine Registry Initializer for V13.
    Scans docs/ for all v_13_playbook_*doctrine.txt files, extracts metadata,
    and registers each doctrine into data/doctrine_registry.json.

    PAPER MODE — No live dependencies or execution triggers.
"""

import os
import json
from datetime import datetime

# ------------------------------------------------------------
# PATH CONFIGURATION
# ------------------------------------------------------------

docs_dir = "docs/"
data_path = "data/doctrine_registry.json"
log_path = "logs/doctrine_registry.log"

# ------------------------------------------------------------
# PARSING LOGIC
# ------------------------------------------------------------

def parse_doctrine_metadata(file_path):
    """Read a doctrine file and extract identifying metadata."""
    metadata = {
        "name": None,
        "version": None,
        "mode": None,
        "status": None,
        "category": None,
        "registered": datetime.now().isoformat()
    }

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for line in lines[:40]:  # Scan top 40 lines only
            if "Build:" in line:
                metadata["version"] = line.split("Build:")[-1].strip()
            if "Mode:" in line:
                metadata["mode"] = line.split("Mode:")[-1].strip()
            if "Doctrine Status:" in line:
                metadata["status"] = line.split(":")[-1].strip()
            if "PLAYBOOK —" in line:
                metadata["name"] = line.split("—")[-1].strip()
            if "Category" in line:
                metadata["category"] = line.split(":")[-1].strip()
    except Exception as e:
        metadata["error"] = str(e)

    return metadata

# ------------------------------------------------------------
# REGISTRY BUILD PROCESS
# ------------------------------------------------------------

def build_registry():
    print("\n[V13] Scanning doctrine directory for active playbooks...")
    doctrine_files = [f for f in os.listdir(docs_dir) if f.startswith("v_13_playbook_") and f.endswith("doctrine.txt")]

    registry = {}
    for file_name in doctrine_files:
        path = os.path.join(docs_dir, file_name)
        meta = parse_doctrine_metadata(path)
        doctrine_key = meta.get("name", file_name.replace(".txt", ""))
        registry[doctrine_key] = meta
        print(f" → Registered: {doctrine_key} | Mode: {meta.get('mode')} | Status: {meta.get('status')}")

    return registry

# ------------------------------------------------------------
# SAVE REGISTRY
# ------------------------------------------------------------

def save_registry(data):
    os.makedirs(os.path.dirname(data_path), exist_ok=True)
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print(f"\n[V13] Registry saved to {data_path}")

# ------------------------------------------------------------
# LOGGING UTILITIES
# ------------------------------------------------------------

def log_registry(data):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"\n[Registry Update — {datetime.now().isoformat()}]\n")
        for k, v in data.items():
            f.write(f"{k}: {v.get('status')} | Mode: {v.get('mode')} | Version: {v.get('version')}\n")
    print(f"[V13] Registry log updated: {log_path}")

# ------------------------------------------------------------
# MAIN SIMULATION EXECUTION
# ------------------------------------------------------------

def simulate_registry_initialization():
    print("\n=== V13 Doctrine Registry Initialization — PAPER MODE ===")
    registry = build_registry()
    save_registry(registry)
    log_registry(registry)
    print("\n[V13] Registry initialization complete.")

# ------------------------------------------------------------
# ENTRY POINT (SIMULATION)
# ------------------------------------------------------------

if __name__ == "__main__":
    simulate_registry_initialization()

# ============================================================
# END OF V13_DoctrineRegistry_Init.py (Simulation Blueprint)
# ============================================================
