"""
============================================================
Doctrine_Loader.py — V13 Dynamic Doctrine System Loader
Build: 2025-10-20 | Component of V13_Stable_Release
============================================================

Purpose:
    Dynamically load, validate, and register doctrine JSONs 
    (Trade A → Assassins, Trade B → Avengers) into runtime memory.

Dependencies:
    - os, json, hashlib
    - Used by: V13_DoctrineFeedbackLoop.py, V13_CommanderMonitor.py
    - Source Folder: /docs/Doctrine_V13/
"""

import os
import json
import hashlib
from datetime import datetime

# ---------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------
DOCTRINE_PATH = os.path.join(
    os.getcwd(), "docs", "Doctrine_V13"
)
HASH_FILE = os.path.join(DOCTRINE_PATH, "Integrity_HashList.md5")

# ---------------------------------------------------------------------
# UTILITY FUNCTIONS
# ---------------------------------------------------------------------
def calculate_md5(file_path):
    """Calculate MD5 hash for given doctrine file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def load_json(file_path):
    """Load and return a JSON doctrine."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def log_hash(name, hash_value):
    """Append or update hash record for doctrine integrity."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    record = f"{timestamp} | {name} | {hash_value}\n"
    with open(HASH_FILE, "a", encoding="utf-8") as f:
        f.write(record)

# ---------------------------------------------------------------------
# CORE LOADER FUNCTION
# ---------------------------------------------------------------------
def load_doctrines():
    """Scan /docs/Doctrine_V13/ and load available doctrine JSONs."""
    doctrines = {}
    if not os.path.exists(DOCTRINE_PATH):
        raise FileNotFoundError(f"[ERROR] Doctrine folder missing: {DOCTRINE_PATH}")

    for file in os.listdir(DOCTRINE_PATH):
        if file.endswith(".json"):
            file_path = os.path.join(DOCTRINE_PATH, file)
            try:
                data = load_json(file_path)
                hash_value = calculate_md5(file_path)
                doctrines[data["Doctrine_ID"]] = {
                    "data": data,
                    "hash": hash_value,
                    "status": "validated"
                }
                log_hash(data["Doctrine_ID"], hash_value)
                print(f"[✓] Loaded Doctrine: {data['Doctrine_Name']} ({file})")
            except Exception as e:
                print(f"[✗] Failed to load {file}: {e}")

    if not doctrines:
        print("[!] No doctrine JSONs found.")
    else:
        print(f"[✓] Total Doctrines Loaded: {len(doctrines)}")

    return doctrines
"""
============================================================
Doctrine_Loader.py — V13 Dynamic Doctrine System Loader
Build: 2025-10-20 | Updated with Activity Logging
============================================================
"""

import os
import json
import hashlib
from datetime import datetime

# ---------------------------------------------------------------------
# CONFIGURATION PATHS
# ---------------------------------------------------------------------
DOCTRINE_PATH = os.path.join(
    os.getcwd(), "docs", "Doctrine_V13"
)
PLAYBOOK_PATH = os.path.join(os.getcwd(), "docs")
HASH_FILE = os.path.join(DOCTRINE_PATH, "Integrity_HashList.md5")
LOG_PATH = os.path.join(os.getcwd(), "logs", "Doctrine_Activity_Log.csv")

os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

# ---------------------------------------------------------------------
# LOGGING FUNCTION
# ---------------------------------------------------------------------
def log_activity(event, doctrine_name, doctrine_id, status):
    """Append a record of any doctrine-related action."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = "Timestamp,Event,Doctrine_Name,Doctrine_ID,Status\n"

    # Create file with header if new
    if not os.path.exists(LOG_PATH):
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            f.write(header)

    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"{timestamp},{event},{doctrine_name},{doctrine_id},{status}\n")

# ---------------------------------------------------------------------
# CORE FUNCTIONS
# ---------------------------------------------------------------------
def calculate_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_playbook(file_path):
    """Parse a playbook .txt file into doctrine dict."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split('\n')
    doctrine = {}

    # Extract from header comments
    for line in lines[:20]:  # Check first 20 lines for header
        line = line.strip()
        if line.startswith('# V13 PLAYBOOK —'):
            # Extract name from title
            title_part = line.replace('# V13 PLAYBOOK —', '').strip().upper()
            name = title_part.replace(' INTEGRATION FILE', '').replace(' ', '')
            doctrine['Name'] = name
        elif line.startswith('# Build:'):
            doctrine['Version'] = line.replace('# Build:', '').strip()
        elif line.startswith('# Mode:'):
            mode = line.replace('# Mode:', '').strip().split(' ')[0]
            doctrine['Mode'] = mode
        elif line.startswith('# Phase:'):
            # Optional, can add if needed
            pass

    # Fallback: if no header, try template sections
    sections = {}
    current_section = None
    for line in lines:
        line = line.strip()
        if line.startswith('[') and line.endswith(']'):
            current_section = line[1:-1]
            sections[current_section] = []
        elif current_section and line:
            sections[current_section].append(line)

    # Extract from DOCTRINE_INFO if present
    if 'DOCTRINE_INFO' in sections:
        for line in sections['DOCTRINE_INFO']:
            if '=' in line:
                key, value = line.split('=', 1)
                doctrine[key.strip()] = value.strip()

    # Add defaults if missing
    doctrine.setdefault('Doctrine_ID', doctrine.get('Name', 'Unknown'))
    doctrine.setdefault('Doctrine_Name', doctrine.get('Name', 'Unknown'))
    doctrine.setdefault('Core_Trade', 'Adaptive')  # Default
    doctrine.setdefault('Version', doctrine.get('Version', 'V13.2025.10.21.01'))
    doctrine.setdefault('Author', doctrine.get('Author', 'Unknown'))
    doctrine.setdefault('Category', doctrine.get('Category', 'Adaptive'))
    doctrine.setdefault('Mode', doctrine.get('Mode', 'PAPER'))
    doctrine.setdefault('Status', doctrine.get('Status', 'ACTIVE'))

    # Add full content for reference
    doctrine['Full_Content'] = content

    return doctrine

def log_hash(name, hash_value):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    record = f"{timestamp} | {name} | {hash_value}\n"
    with open(HASH_FILE, "a", encoding="utf-8") as f:
        f.write(record)

# ---------------------------------------------------------------------
# LOAD ALL DOCTRINES
# ---------------------------------------------------------------------
def load_doctrines():
    """Scan /docs/Doctrine_V13/ for JSONs and /docs/ for .txt playbooks."""
    doctrines = {}

    # Load JSON doctrines from Doctrine_V13
    if os.path.exists(DOCTRINE_PATH):
        for file in os.listdir(DOCTRINE_PATH):
            if file.endswith(".json") and file != "Doctrine_Index.json":  # Skip the index file
                file_path = os.path.join(DOCTRINE_PATH, file)
                try:
                    data = load_json(file_path)
                    hash_value = calculate_md5(file_path)
                    doctrines[data["Doctrine_ID"]] = {
                        "data": data,
                        "hash": hash_value,
                        "status": "validated"
                    }
                    log_hash(data["Doctrine_ID"], hash_value)
                    log_activity("LOAD", data["Doctrine_Name"], data["Doctrine_ID"], "Success")
                    print(f"[✓] Loaded Doctrine: {data['Doctrine_Name']} ({file})")
                except Exception as e:
                    log_activity("LOAD_FAIL", file, "Unknown", f"Error: {e}")
                    print(f"[✗] Failed to load {file}: {e}")

    # Load .txt playbooks from /docs/
    if os.path.exists(PLAYBOOK_PATH):
        for file in os.listdir(PLAYBOOK_PATH):
            if file.endswith(".txt") and "playbook" in file.lower():
                file_path = os.path.join(PLAYBOOK_PATH, file)
                try:
                    data = parse_playbook(file_path)
                    hash_value = calculate_md5(file_path)
                    doctrines[data["Doctrine_ID"]] = {
                        "data": data,
                        "hash": hash_value,
                        "status": "validated"
                    }
                    log_hash(data["Doctrine_ID"], hash_value)
                    log_activity("LOAD", data["Doctrine_Name"], data["Doctrine_ID"], "Success")
                    print(f"[✓] Loaded Playbook: {data['Doctrine_Name']} ({file})")
                except Exception as e:
                    log_activity("LOAD_FAIL", file, "Unknown", f"Error: {e}")
                    print(f"[✗] Failed to load {file}: {e}")

    if not doctrines:
        print("[!] No doctrines or playbooks found.")
        log_activity("EMPTY_LOAD", "None", "None", "No doctrines found")
    else:
        print(f"[✓] Total Doctrines Loaded: {len(doctrines)}")
        log_activity("SUMMARY", "All", "System", f"Count={len(doctrines)}")

    return doctrines

# ---------------------------------------------------------------------
# RUNTIME TEST (manual)
# ---------------------------------------------------------------------
if __name__ == "__main__":
    print("=== V13 Doctrine Loader Diagnostic ===")
    loaded = load_doctrines()
    for key, val in loaded.items():
        print(f"{key} → hash: {val['hash']}")
