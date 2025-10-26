# =============================================================
#  V14_CollaborationMatrix.py — Adaptive Trading Intelligence
#  Version: V14_Pre-Alpha (2025-10-19)
#  Module: CommanderFlex ↔ AI_Coordinator Fusion Layer
#  Mode: Paper-only Simulation — Human + AI Collaboration
# =============================================================

import json
import time
from datetime import datetime, timezone
import hashlib

# -------------------------------------------------------------
#  CONFIGURATION
# -------------------------------------------------------------
DEFAULT_HUMAN_WEIGHT = 0.6   # Human decision bias
DEFAULT_AI_WEIGHT = 0.4      # AI bias (adaptive)
OVERRIDE_TOLERANCE = 0.15    # Max divergence between signals

# -------------------------------------------------------------
#  COLLABORATION MATRIX CLASS
# -------------------------------------------------------------
class V14CollaborationMatrix:
    def __init__(self, logger=None):
        self.logger = logger or self._default_logger
        self.override_threshold = OVERRIDE_TOLERANCE
        self.human_weight = DEFAULT_HUMAN_WEIGHT
        self.ai_weight = DEFAULT_AI_WEIGHT

    # ---------------------------------------------------------
    #  LOGGER (fallback)
    # ---------------------------------------------------------
    def _default_logger(self, message: str):
        ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        print(f"[{ts}] [CollaborationMatrix] {message}")

    # ---------------------------------------------------------
    #  HASH CHECKSUM
    # ---------------------------------------------------------
    def _checksum(self, data: dict) -> str:
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()

    # ---------------------------------------------------------
    #  WEIGHTED FUSION CALCULATION
    # ---------------------------------------------------------
    def _weighted_fusion(self, human_signal: float, ai_signal: float) -> float:
        return (human_signal * self.human_weight) + (ai_signal * self.ai_weight)

    # ---------------------------------------------------------
    #  DIVERGENCE DETECTION
    # ---------------------------------------------------------
    def _check_divergence(self, human_signal: float, ai_signal: float) -> bool:
        if ai_signal == 0:
            return False
        diff = abs(human_signal - ai_signal) / abs(ai_signal)
        if diff > self.override_threshold:
            self.logger(f"⚠️ Divergence detected: {diff:.2%} > {self.override_threshold:.2%}")
            return True
        return False

    # ---------------------------------------------------------
    #  COLLABORATION FUSION PROCESS
    # ---------------------------------------------------------
    def fuse(self, human_input: dict, ai_input: dict, risk_status: str) -> dict:
        """Combine human + AI directives under risk supervision."""

        # Extract signals
        h_signal = float(human_input.get("signal_strength", 0.0))
        a_signal = float(ai_input.get("signal_strength", 0.0))

        h_conf = float(human_input.get("confidence", 1.0))
        a_conf = float(ai_input.get("confidence", 1.0))

        # Adjust weights dynamically based on confidence
        total_conf = h_conf + a_conf
        self.human_weight = h_conf / total_conf if total_conf else DEFAULT_HUMAN_WEIGHT
        self.ai_weight = a_conf / total_conf if total_conf else DEFAULT_AI_WEIGHT

        # Check divergence
        divergent = self._check_divergence(h_signal, a_signal)

        # Weighted fusion
        fused_value = self._weighted_fusion(h_signal, a_signal)

        # Apply risk moderation
        if risk_status == "LOCK":
            fused_value *= 0.0
            self.logger("🚫 RiskSentinel lock active — override fusion output.")

        elif risk_status == "LIMITED":
            fused_value *= 0.5
            self.logger("⚠️ RiskSentinel LIMITED mode — reducing fusion power by 50%.")

        # Build fusion result
        result = {
            "timestamp": time.time(),
            "fused_signal": round(fused_value, 5),
            "human_weight": round(self.human_weight, 3),
            "ai_weight": round(self.ai_weight, 3),
            "risk_status": risk_status,
            "divergent": divergent,
            "checksum": self._checksum({
                "h_signal": h_signal,
                "a_signal": a_signal,
                "risk": risk_status,
                "weights": (self.human_weight, self.ai_weight),
            }),
        }

        self.logger(
            f"✅ Fusion complete → Fused={result['fused_signal']:.4f} (H:{self.human_weight:.2f} / AI:{self.ai_weight:.2f}) Risk={risk_status}"
        )

        return result

# -------------------------------------------------------------
#  TEST ROUTINE (simulation)
# -------------------------------------------------------------
if __name__ == "__main__":
    cmatrix = V14CollaborationMatrix()

    # Example simulated inputs
    human_input = {"signal_strength": 0.72, "confidence": 0.8}
    ai_input = {"signal_strength": 0.68, "confidence": 0.9}
    risk_status = "SAFE"

    fusion_result = cmatrix.fuse(human_input, ai_input, risk_status)

    print("\nFinal Fusion Output:")
    print(json.dumps(fusion_result, indent=2))