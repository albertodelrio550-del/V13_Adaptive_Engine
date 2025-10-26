#!/bin/bash
# ============================================================
#  V13 Manual Trading Framework — Config Injector
#  Build: 2025-10-18
#  Purpose: Safely update runtime configuration or doctrine
#  without restarting the Commander session.
# ============================================================

ROOT_DIR="$(dirname "$0")"
CONFIG_DIR="$ROOT_DIR/config"
RUNTIME_CFG="$CONFIG_DIR/runtime_config.json"
DOCTRINE_CFG="$CONFIG_DIR/doctrine_overrides.json"
LOG_DIR="$ROOT_DIR/logs"

echo "=============================================="
echo " ⚙️  V13 Config Injector — Runtime Update Tool"
echo " Build: 2025-10-18"
echo "=============================================="
echo ""

# 1. Verify config directory presence
if [ ! -d "$CONFIG_DIR" ]; then
  echo "❌ Config directory not found: $CONFIG_DIR"
  exit 1
fi

# 2. Display current runtime configuration
echo "🔍 Current runtime_config.json:"
cat "$RUNTIME_CFG" 2>/dev/null || echo "⚠️  Missing runtime_config.json"
echo ""
echo "🔍 Current doctrine_overrides.json:"
cat "$DOCTRINE_CFG" 2>/dev/null || echo "⚠️  Missing doctrine_overrides.json"
echo ""

# 3. Ask user for target mode update
read -p "Enter new runtime mode (Safe / Balanced / Aggressive): " NEW_MODE

if [[ "$NEW_MODE" != "Safe" && "$NEW_MODE" != "Balanced" && "$NEW_MODE" != "Aggressive" ]]; then
  echo "❌ Invalid mode selection. Must be one of: Safe, Balanced, Aggressive."
  exit 1
fi

# 4. Inject new runtime configuration
cat > "$RUNTIME_CFG" <<EOF
{
  "mode": "$NEW_MODE",
  "thresholds": {
    "superupdate": 0.8,
    "crashguard": 0.1
  }
}
EOF

# 5. Confirm update
echo ""
echo "✅ Updated runtime_config.json successfully:"
cat "$RUNTIME_CFG"
echo ""

# 6. Optional Doctrine Bias Update
read -p "Do you want to apply a doctrine bias update? (y/n): " DOC_UPDATE
if [[ "$DOC_UPDATE" == "y" || "$DOC_UPDATE" == "Y" ]]; then
  read -p "Enter bias_multiplier (e.g., 1.0 = neutral, 0.9 = dampen): " BIAS
  cat > "$DOCTRINE_CFG" <<EOF
{
  "bias_multiplier": $BIAS,
  "force_mode": null,
  "min_confidence": 0.2
}
EOF
  echo "✅ Doctrine override updated:"
  cat "$DOCTRINE_CFG"
else
  echo "⏭️  Doctrine override unchanged."
fi

# 7. Log injection event
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "{\"timestamp\": \"$TIMESTAMP\", \"event\": \"ConfigInjector update\", \"mode\": \"$NEW_MODE\"}" >> "$LOG_DIR/event_history.log"

echo ""
echo "✅ Configuration injection complete."
echo "🧾 Logged in: $LOG_DIR/event_history.log"
echo "Commander will read updated parameters on the next tactical cycle."
echo "=============================================="
