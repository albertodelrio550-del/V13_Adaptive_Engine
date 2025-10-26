# =============================================================
#  V13_SignalValidator.py — Adaptive Manual Trading Engine
#  Version: V13_Stable_Release (2025-10-19)
#  Module: TelemetryFusion ↔ DoctrineBridge Validator
#  Mode: Paper-only, Simulation
# =============================================================

import json
import time
import hashlib
from datetime import datetime, timezone

# -------------------------------------------------------------
#  CONFIGURATION
# -------------------------------------------------------------
TIMESTAMP_TOLERANCE_MS = 250
DELTA_TOLERANCE_PERCENT = 0.1
MAX_CONSECUTIVE_MISMATCHES = 3

# -------------------------------------------------------------
#  SIGNAL VALIDATOR CLASS
# -------------------------------------------------------------
class V13SignalValidator:
    def __init__(self, logger=None):
        self.logger = logger or self._default_logger
        self.mismatch_counter = 0

    # ---------------------------------------------------------
    #  INTERNAL LOGGER (fallback)
    # ---------------------------------------------------------
    def _default_logger(self, message: str):
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        print(f"[{timestamp}] [SignalValidator] {message}")

    # ---------------------------------------------------------
    #  TIMESTAMP VALIDATION
    # ---------------------------------------------------------
    def _validate_timestamp(self, cmd_ts: float, market_ts: float) -> bool:
        delta_ms = abs(cmd_ts - market_ts) * 1000
        if delta_ms > TIMESTAMP_TOLERANCE_MS:
            self.logger(f"❌ Timestamp desync: {delta_ms:.2f} ms > {TIMESTAMP_TOLERANCE_MS} ms")
            return False
        return True

    # ---------------------------------------------------------
    #  DELTA AGREEMENT VALIDATION
    # ---------------------------------------------------------
    def _validate_delta(self, commander_delta: float, fusion_delta: float) -> bool:
        if fusion_delta == 0:
            return True
        deviation = abs(commander_delta - fusion_delta) / abs(fusion_delta) * 100
        if deviation > DELTA_TOLERANCE_PERCENT:
            self.logger(f"⚠️ Delta mismatch: {deviation:.3f}% > {DELTA_TOLERANCE_PERCENT}%")
            return False
        return True

    # ---------------------------------------------------------
    #  VOLATILITY & RISK VALIDATION
    # ---------------------------------------------------------
    def _validate_risk_and_volatility(self, volatility: float, risk_status: str) -> bool:
        if risk_status not in ["SAFE", "LIMITED"]:
            self.logger(f"🚫 RiskSentinel lock active: {risk_status}")
            return False
        if volatility > 0.05:
            self.logger(f"⚠️ Volatility spike detected: {volatility*100:.2f}% > 5.00% threshold")
        return True

    # ---------------------------------------------------------
    #  SIGNAL HASH (CHECKSUM)
    # ---------------------------------------------------------
    def _generate_checksum(self, data: dict) -> str:
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()

    # ---------------------------------------------------------
    #  MAIN VALIDATION PIPELINE
    # ---------------------------------------------------------
    def validate(self, command_packet: dict, market_snapshot: dict, risk_status: str, sync_flag: bool) -> dict:
        """Validate cross-module trading signal integrity."""

        # Safety precheck
        if not sync_flag:
            self.logger("🛑 BridgeGuardian: Sync flag = False. Halting validation.")
            return {"status": "ERROR", "reason": "Bridge desync"}

        cmd_ts = command_packet.get("timestamp", 0)
        market_ts = market_snapshot.get("timestamp", 0)
        commander_delta = command_packet.get("price_delta", 0.0)
        fusion_delta = market_snapshot.get("price_delta", 0.0)
        volatility = market_snapshot.get("volatility", 0.0)

        # Step 1: Timestamp validation
        if not self._validate_timestamp(cmd_ts, market_ts):
            self._increment_mismatch()
            return {"status": "INVALID", "reason": "Timestamp desync"}

        # Step 2: Delta agreement
        if not self._validate_delta(commander_delta, fusion_delta):
            self._increment_mismatch()
            return {"status": "INVALID", "reason": "Delta mismatch"}

        # Step 3: Volatility and risk control
        if not self._validate_risk_and_volatility(volatility, risk_status):
            self._increment_mismatch()
            return {"status": "LOCK", "reason": "Risk or volatility breach"}

        # Step 4: Generate checksum
        checksum_payload = {
            "cmd_ts": cmd_ts,
            "market_ts": market_ts,
            "commander_delta": commander_delta,
            "fusion_delta": fusion_delta,
            "volatility": volatility,
        }
        checksum = self._generate_checksum(checksum_payload)

        # Reset mismatch counter on success
        self.mismatch_counter = 0

        # Step 5: Return validated output
        validated = {
            "status": "VALID",
            "timestamp": time.time(),
            "checksum": checksum,
            "risk_status": risk_status,
            "volatility": volatility,
            "validated_by": "V13_SignalValidator",
        }

        self.logger(f"✅ Signal validated successfully. Checksum={checksum[:8]}... Vol={volatility*100:.2f}%")
        return validated

    # ---------------------------------------------------------
    #  INTERNAL COUNTER MANAGEMENT
    # ---------------------------------------------------------
    def _increment_mismatch(self):
        self.mismatch_counter += 1
        if self.mismatch_counter >= MAX_CONSECUTIVE_MISMATCHES:
            self.logger("🚨 Persistent mismatch threshold reached. Triggering RiskSentinel lock.")
            self.mismatch_counter = 0

# -------------------------------------------------------------
#  TEST ROUTINE (simulation)
# -------------------------------------------------------------
if __name__ == "__main__":
    validator = V13SignalValidator()

    command_packet = {
        "timestamp": time.time(),
        "price_delta": 0.0025,
    }

    market_snapshot = {
        "timestamp": time.time(),
        "price_delta": 0.0024,
        "volatility": 0.038,
    }

    result = validator.validate(command_packet, market_snapshot, risk_status="SAFE", sync_flag=True)
    print(json.dumps(result, indent=2))
