from pathlib import Path

from . import utils


def main() -> None:
    log_path = Path("logs/V13_Latency.log")
    entries = utils.load_json_lines(log_path)
    summary = utils.summarise_latency(entries)

    if not summary.get("sample_count"):
        utils.exit_with_status(
            "WARN",
            f"No latency samples found in {log_path}",
            "test_latency",
            {"log_path": str(log_path)},
        )

    avg_latency = summary.get("avg_latency_ms", 0.0)
    max_latency = summary.get("max_latency_ms", 0.0)
    status = "PASS"
    message = "Latency within tolerance"
    if avg_latency > 500 or max_latency > 1000:
        status = "FAIL"
        message = f"Latency breach detected (avg={avg_latency:.1f} ms, max={max_latency:.1f} ms)"

    summary.update({"threshold_avg_ms": 500, "threshold_max_ms": 1000})
    utils.exit_with_status(
        status,
        message,
        "test_latency",
        summary,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover
        utils.exit_with_status("FAIL", f"Unhandled exception: {exc}", "test_latency", {})
