from pathlib import Path

from . import utils


def main() -> None:
    status_path = Path("data/V13_Status.json")
    status_payload = utils.load_json(status_path)
    if not status_payload:
        utils.exit_with_status(
            "WARN",
            f"Status file {status_path} not found or empty",
            "test_risk_caps",
            {"status_path": str(status_path)},
        )

    block_cfg = utils.block_config_map()
    blocks = status_payload.get("blocks", {})
    global_metrics = status_payload.get("global", {})

    breaches = []
    for block_id, info in blocks.items():
        drawdown = float(info.get("drawdown", 0.0) or 0.0)
        ceiling = block_cfg.get(block_id.upper(), {}).get("risk_ceiling", 5.0)
        if drawdown > ceiling:
            breaches.append(
                {
                    "block_id": block_id,
                    "drawdown": round(drawdown, 4),
                    "ceiling": ceiling,
                }
            )

    global_dd = float(global_metrics.get("weighted_drawdown", 0.0) or 0.0)
    global_cap = float(global_metrics.get("max_cap", 5.0) or 5.0)
    global_breach = global_dd > global_cap

    status = "PASS"
    message = "Risk caps respected"
    if global_breach or breaches:
        status = "FAIL"
        message = "Risk cap breach detected"

    details = {
        "global": {
            "drawdown": round(global_dd, 4),
            "cap": global_cap,
            "breach": global_breach,
        },
        "local_breaches": breaches,
        "block_count": len(blocks),
    }
    utils.exit_with_status(status, message, "test_risk_caps", details)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover
        utils.exit_with_status("FAIL", f"Unhandled exception: {exc}", "test_risk_caps", {})
