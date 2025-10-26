import os
from pathlib import Path

core_dir = Path("core")
core_files = ['V13_LaunchSequence.py', 'V13_TelemetryFusion.py', 'V13_SessionAudit.py']

print("Verifying base files in /core:")
for f in core_files:
    file_path = core_dir / f
    status = "Exists" if file_path.exists() else "Missing"
    print(f"{f}: {status}")

print("Core integrity check complete.")
