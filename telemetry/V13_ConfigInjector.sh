#!/bin/bash
# ============================================================
# 🔹 V13 Manual Trading Engine - Config Injector
# Build: 2025-10-18
# Verified Architecture | Paper-Only Deployment
# ============================================================
# Purpose:
#   Injects mode-based configuration into runtime_config.json
#   prior to startup. Supports Safe / Balanced / Aggressive modes.
#   Compatible with V13_startup.sh orchestration.
# ------------------------------------------------------------

ENGINE_ROOT="$HOME/Videos/bohrn_2025/trade/V13"
CONFIG_FILE="$ENGINE_ROOT/config/runtime_config.json"
LOG_FILE="$ENGINE_ROOT/telemetry/config_inject.log"

echo "------------------------------------------------------------"
echo "🧩 V13 Config Injector — Automated Mode Setup"
echo "Build: 2025-10-18 | PAPER MODE"
echo "------------------------------------------------------------"

# === MODE SELECTION =========================================
MODE="$1"

if [ -z "$MODE" ]; then
  echo "Usage: ./V13_ConfigInjector.sh [safe|balanced|aggressive]"
  exit 1
fi

# === DEFINE PARAMETERS BY MODE ===============================
case "$MODE" in
  safe)
    MAX_DD="-20"
    PROFIT_TARGET="+20"
    DEFENSE_RATIO="0.6"
    ATTACK_RATIO="0.4"
    LADDER_LOCK="30"
    ;;
  balanced)
    MAX_DD="-50"
    PROFIT_TARGET="+40"
    DEFENSE_RATIO="0.5"
    ATTACK_RATIO="0.5"
    LADDER_LOCK="50"
    ;;
  aggressive)
    MAX_DD="-200"
    PROFIT_TARGET="+100"
    DEFENSE_RATIO="0.3"
    ATTACK_RATIO="0.7"
    LADDER_LOCK="100"
    ;;
  *)
    echo "❌ Invalid mode: $MODE. Choose safe | balanced | aggressive"
    exit 1
    ;;
esac

# === VERIFY ENGINE PATH =====================================
if [ ! -d "$ENGINE_ROOT" ]; then
  echo "❌ Engine path not found: $ENGINE_ROOT"
  exit 1
fi

mkdir -p "$(dirname "$CONFIG_FILE")"
mkdir -p "$(dirname "$LOG_FILE")"

# === GENERATE CONFIG ========================================
cat <<EOF > "$CONFIG_FILE"
{
  "version": "13.0.0",
  "mode": "$MODE",
  "paper_only": true,
  "parameters": {
    "max_drawdown": $MAX_DD,
    "profit_target": $PROFIT_TARGET,
    "defense_ratio": $DEFENSE_RATIO,
    "attack_ratio": $ATTACK_RATIO,
    "ladder_lock_trigger": $LADDER_LOCK
  },
  "timestamp": "$(date +%Y-%m-%dT%H:%M:%S)",
  "modules": {
    "commander": "enabled",
    "aggregator": "enabled",
    "bridge": "enabled",
    "telemetry": "enabled",
    "doctrine": "enabled"
  },
  "notes": "Auto-injected configuration for $MODE mode."
}
EOF

# === LOG CONFIGURATION ======================================
echo "------------------------------------------------------------" > "$LOG_FILE"
echo "🧩 V13 ConfigInjector — Mode: $MODE" >> "$LOG_FILE"
echo "Date: $(date)" >> "$LOG_FILE"
echo "------------------------------------------------------------" >> "$LOG_FILE"
echo "MaxDD           : $MAX_DD" >> "$LOG_FILE"
echo "Profit Target   : $PROFIT_TARGET" >> "$LOG_FILE"
echo "Defense Ratio   : $DEFENSE_RATIO" >> "$LOG_FILE"
echo "Attack Ratio    : $ATTACK_RATIO" >> "$LOG_FILE"
echo "Ladder Lock     : $LADDER_LOCK" >> "$LOG_FILE"
echo "------------------------------------------------------------" >> "$LOG_FILE"
echo "✅ Config successfully injected into runtime_config.json" | tee -a "$LOG_FILE"

# === SUMMARY OUTPUT =========================================
echo "------------------------------------------------------------"
echo "✅ Configuration Ready:"
echo "  Mode            : $MODE"
echo "  Max Drawdown    : $MAX_DD"
echo "  Profit Target   : $PROFIT_TARGET"
echo "  Defense Ratio   : $DEFENSE_RATIO"
echo "  Attack Ratio    : $ATTACK_RATIO"
echo "  Ladder Lock     : $LADDER_LOCK"
echo "------------------------------------------------------------"
echo "🪶 Saved to: $CONFIG_FILE"
echo "📜 Log: $LOG_FILE"
echo "------------------------------------------------------------"

# === CHAINED STARTUP OPTION =================================
read -p "🔄 Launch engine now with this configuration? (y/N): " confirm
if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
  echo "🚀 Executing V13 startup with injected config..."
  bash "$ENGINE_ROOT/V13_startup.sh" --mode "$MODE"
else
  echo "✅ Configuration injection complete. Manual startup required."
fi
