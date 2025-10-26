#!/bin/bash
# ============================================================
# 🔹 V13 Manual Trading Engine - Startup Orchestrator
# Build: 2025-10-18
# Verified Architecture | Paper-Only Framework
# ============================================================
# Layers: Commander | Aggregator | Bridge | Telemetry | Doctrine
# Purpose: Initialize verified modules for manual trading simulation
# ------------------------------------------------------------

# === CONFIGURATION ==========================================
ENGINE_ROOT="$HOME/Videos/bohrn_2025/trade/V13"
PYTHON_ENV="$ENGINE_ROOT/env/bin/python3"
LOG_DIR="$ENGINE_ROOT/telemetry"
BOOT_LOG="$LOG_DIR/boot_report.log"
MODE="balanced"   # default mode: safe | balanced | aggressive
VERSION="13.0.0"

# === SAFETY PRE-CHECKS ======================================
echo "------------------------------------------------------------"
echo "🧭 V13 Manual Trading Engine — Startup Sequence"
echo "Build: $VERSION | Mode: PAPER | Default: $MODE"
echo "------------------------------------------------------------"

# Ensure directory exists
if [ ! -d "$ENGINE_ROOT" ]; then
  echo "❌ Engine root not found at: $ENGINE_ROOT"
  exit 1
fi

# Ensure virtual environment Python exists
if [ ! -f "$PYTHON_ENV" ]; then
  echo "⚠️ Python environment not found. Attempting setup..."
  python3 -m venv "$ENGINE_ROOT/env"
  source "$ENGINE_ROOT/env/bin/activate"
  pip install -r "$ENGINE_ROOT/requirements.txt"
fi

# Create telemetry folder if missing
mkdir -p "$LOG_DIR"

# Start log
echo "🚀 Launching V13 Engine at $(date)" > "$BOOT_LOG"
echo "Version: $VERSION | Mode: $MODE" >> "$BOOT_LOG"
echo "------------------------------------------------------------" >> "$BOOT_LOG"

# === MODULE BOOT SEQUENCE ===================================

# 1️⃣ Commander Boot
echo "[1/5] Commander initializing..."
$PYTHON_ENV "$ENGINE_ROOT/core/commander.py" --verify --log "$LOG_DIR/commander.log"
if [ $? -ne 0 ]; then
  echo "❌ Commander failed to start. Check commander.log"
  exit 1
fi
echo "✅ Commander online." | tee -a "$BOOT_LOG"

# 2️⃣ Aggregator Activation
echo "[2/5] Aggregator activating ($MODE mode)..."
$PYTHON_ENV "$ENGINE_ROOT/core/aggregator.py" --session init --mode "$MODE" --feed sim
if [ $? -ne 0 ]; then
  echo "❌ Aggregator error. Check aggregator.log"
  exit 1
fi
echo "✅ Aggregator operational." | tee -a "$BOOT_LOG"

# 3️⃣ Bridge Synchronization
echo "[3/5] Bridge establishing connections..."
$PYTHON_ENV "$ENGINE_ROOT/core/bridge.py" --connect telemetry --doctrine sync
if [ $? -ne 0 ]; then
  echo "❌ Bridge connection failed. Check bridge.log"
  exit 1
fi
echo "✅ Bridge link verified." | tee -a "$BOOT_LOG"

# 4️⃣ Telemetry Diagnostics
echo "[4/5] Running telemetry diagnostics..."
$PYTHON_ENV "$ENGINE_ROOT/tools/telemetry_diag.py" --verify --report "$LOG_DIR/startup_health.json"
if [ $? -ne 0 ]; then
  echo "⚠️ Telemetry reported minor issues. Review startup_health.json."
else
  echo "✅ Telemetry stable." | tee -a "$BOOT_LOG"
fi

# 5️⃣ Doctrine Integrity Check
echo "[5/5] Doctrine layer integrity verification..."
$PYTHON_ENV "$ENGINE_ROOT/core/doctrine.py" --verify --strict
if [ $? -ne 0 ]; then
  echo "⚠️ Doctrine check returned warnings. Inspect doctrine.log."
else
  echo "✅ Doctrine verified." | tee -a "$BOOT_LOG"
fi

# === FINAL STATUS ===========================================
echo "------------------------------------------------------------" | tee -a "$BOOT_LOG"
echo "✅ V13 Manual Trading Engine started successfully." | tee -a "$BOOT_LOG"
echo "Modules: Commander | Aggregator | Bridge | Telemetry | Doctrine" | tee -a "$BOOT_LOG"
echo "Mode: $MODE  | Version: $VERSION" | tee -a "$BOOT_LOG"
echo "Logs available in: $LOG_DIR" | tee -a "$BOOT_LOG"
echo "------------------------------------------------------------" | tee -a "$BOOT_LOG"
echo "🟢 Startup complete — system ready for manual operations."
echo

# === OPTIONAL PARAMETERS ====================================
# Usage:
#   ./V13_startup.sh --mode safe
#   ./V13_startup.sh --mode balanced
#   ./V13_startup.sh --mode aggressive
#
# All operations are PAPER ONLY. No live trade execution.

# === PARAMETER PARSER =======================================
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --mode) MODE="$2"; shift ;;
        --check) echo "Performing dry-run check only."; exit 0 ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done
