# unk_files - Archived V13 Files

This directory contains files that have been moved from the main V13 trading system directory for organizational purposes. All files are preserved and can be restored if needed.

## Directory Structure

### build_artifacts/
Contains build-related files and artifacts:
- `build/` - Build output directory
- `dist/` - Distribution files
- `V13_VisualMonitor.spec` - PyInstaller spec file

### node_installations/
Contains Node.js installation files:
- `node-global/` - Global Node.js installation
- `node-v20.18.1-win-x64/` - Node.js v20.18.1 installation
- `node-v22.21.0-win-x64/` - Node.js v22.21.0 installation

### old_versions/
Contains previous versions of V13 modules:
- `V13_VisualMonitor.py.bak` - Backup of original Visual Monitor
- `V13_VisualMonitor_UIv2.py` - UI version 2
- `V13_VisualMonitor_UIv2_fixed.py` - Fixed version of UI v2
- `V13_VisualMonitor_UIv2_new.py` - New version of UI v2

**Active Version:** `core/V13_VisualMonitor_UIv2_enhanced.py` (in main directory)

### reference_docs/
Contains reference documentation:
- `binance-spot-api-docs/` - Complete Binance Spot API documentation

### temp_files/
Contains temporary and miscellaneous files:
- `New Text Document.txt` - Empty text file
- `query` - Query file
- `binance_test.py` - Binance testing script
- `check_audit.py` - Audit checking script
- `__init__.py` - Empty init file
- `Videos/` - Videos directory
- `V13.code-workspace/` - VSCode workspace configuration

### test_files/
Contains test and development files:
- `v_14_collaboration_matrix_test_harness.py` - V14 collaboration matrix test harness
- `V_13_signal_validator_handshake_test.py` - Signal validator handshake test

### vscode_config/
Contains VSCode and Python environment files:
- `.venv/` - Python virtual environment
- `__pycache__/` - Python bytecode cache (root level)
- `__pycache__/` - Python bytecode cache (core level)
- `.vscode/` - VSCode configuration

## Restoration Instructions

To restore any file or directory:

```powershell
# Restore a single file
Move-Item -Path "unk_files/[subfolder]/[filename]" -Destination "./" -Force

# Restore a directory
Move-Item -Path "unk_files/[subfolder]/[dirname]" -Destination "./" -Force
```

## Notes

- All files are preserved exactly as they were
- No files have been deleted, only moved
- The main V13 directory now contains only active, essential files
- This organization supports long-term AI-assisted development by maintaining a clean working directory
- Reference MASTER_BLUEPRINT_V13.md in the root directory for complete V13 system documentation
