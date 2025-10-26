"""
V13_DoctrineIntegrity.py — Doctrine Integrity Check
Build: 2025-10-20 | V13_Stable_Release

Purpose:
    Validates doctrinal reference files are unmodified before engine launch.
    Computes SHA256 for each file and compares with reference hashes in Integrity_HashList.md5.
    Aborts launch if mismatch detected.

Dependencies:
    - hashlib, os
    - docs/Doctrine_V13/Integrity_HashList.md5
"""

import hashlib
import os
from pathlib import Path

DOCTRINE_PATH = Path("docs/Doctrine_V13")
HASH_LIST = DOCTRINE_PATH / "Integrity_HashList.md5"
MONITORED_FILES = ["Assassins_Plan_V13.txt", "Avengers_Plan_V13.txt", "README.txt"]

def compute_sha256(file_path):
    """Compute SHA256 hash of a file."""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def load_reference_hashes():
    """Load reference hashes from Integrity_HashList.md5."""
    if not HASH_LIST.exists():
        raise FileNotFoundError(f"Reference hash list not found: {HASH_LIST}")

    hashes = {}
    with open(HASH_LIST, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                parts = line.split(" | ")
                if len(parts) == 3:
                    timestamp, doctrine_id, hash_value = parts
                    hashes[doctrine_id] = hash_value
    return hashes

def check_integrity():
    """Check integrity of monitored doctrine files."""
    print("[Security] Running doctrine integrity check...")

    try:
        reference_hashes = load_reference_hashes()
    except FileNotFoundError as e:
        print(f"[Security] ERROR: {e}")
        return False

    all_valid = True
    for file_name in MONITORED_FILES:
        file_path = DOCTRINE_PATH / file_name
        if not file_path.exists():
            print(f"[Security] ERROR: Monitored file missing: {file_name}")
            all_valid = False
            continue

        current_hash = compute_sha256(file_path)
        doctrine_id = file_name.replace(".txt", "").replace("_Plan_V13", "_V13").replace("README", "README")
        if "Assassins" in doctrine_id:
            doctrine_id = "TradeA_Assassins_V13"
        elif "Avengers" in doctrine_id:
            doctrine_id = "TradeB_Avengers_V13"
        elif "README" in doctrine_id:
            doctrine_id = "README"  # Assuming README is not in the hash list, skip or handle separately
        reference_hash = reference_hashes.get(doctrine_id)

        if reference_hash is None:
            print(f"[Security] WARN: No reference hash for {doctrine_id}")
            continue

        if current_hash != reference_hash:
            print(f"[Security] Doctrine integrity mismatch for {doctrine_id} — aborting initialization.")
            print(f"  Expected: {reference_hash}")
            print(f"  Actual:   {current_hash}")
            all_valid = False
        else:
            print(f"[Security] ✓ Integrity verified for {doctrine_id}")

    if all_valid:
        print("[Security] All doctrine files verified.")
    else:
        print("[Security] Doctrine integrity check FAILED. Launch aborted.")

    return all_valid

if __name__ == "__main__":
    success = check_integrity()
    exit(0 if success else 1)
