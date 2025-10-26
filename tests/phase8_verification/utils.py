from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from V13_CommandMatrix import (
    V13_CommandMatrix,
    BlockConfig,
    BlockState,
    OrderRecord,
)


@dataclass
class StubDecision:
    allowed: bool
    reason: str = "ok"
    details: Optional[Dict[str, Any]] = None


class AllowAllRiskGate:
    def approve(self, intent: Dict[str, Any]) -> StubDecision:
        return StubDecision(True, "ok", {"symbol": intent.get("symbol")})


class ExposureRiskGate:
    """Simple exposure tracker to simulate RiskSentinel aggregate control."""

    def __init__(self, cap: float = 500.0):
        self.cap = cap
        self.total = 0.0

    def approve(self, intent: Dict[str, Any]) -> StubDecision:
        qty = float(intent.get("qty", 0) or 0)
        price = float(intent.get("limit_price", intent.get("price", 100)) or 100)
        value = qty * price
        symbol = intent.get("symbol")
        details = {
            "symbol": symbol,
            "intent_value": round(value, 2),
            "gross_now": round(self.total, 2),
            "max_gross": self.cap,
        }
        if self.total + value > self.cap:
            return StubDecision(False, "exposure", details)
        self.total += value
        return StubDecision(True, "ok", details)


def create_matrix(risk_gate: Optional[Any] = None) -> V13_CommandMatrix:
    matrix = V13_CommandMatrix()
    if risk_gate is not None:
        matrix.risk_gate = risk_gate

    def _mock_post_to_alpaca(payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": f"ALP-{uuid.uuid4()}",
            "status": "filled",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    matrix._post_to_alpaca = _mock_post_to_alpaca  # type: ignore[attr-defined]
    return matrix


def ensure_block(matrix: V13_CommandMatrix, block_id: str, mode: str = "Balanced") -> None:
    block_id = block_id.upper()
    if block_id in matrix.blocks:
        return
    config = BlockConfig(
        block_id=block_id,
        mode=mode,
        capital=5000.0,
        strategy="AssassinAvenger",
        symbol="SPY",
        stagger=5.0,
        risk_ceiling=2.0,
    )
    matrix.blocks[block_id] = BlockState(config=config, status="READY")
    matrix.block_configs[block_id] = config


def write_block_log(matrix: V13_CommandMatrix, block_id: str, content: str) -> Path:
    path = matrix._block_audit_path(block_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
