from pathlib import Path

from . import utils


def _validate_allocation_map(entry: dict, breaches: list[str]) -> None:
    allocation = entry.get("allocation") or {}
    total = 0.0
    for key, value in allocation.items():
        try:
            value = float(value)
        except (TypeError, ValueError):
            breaches.append(f"{key} allocation not numeric")
            continue
        if value < 0 or value > 1:
            breaches.append(f"{key} allocation out of bounds: {value}")
        total += value
    if allocation and abs(total - 1.0) > 0.05:
        breaches.append(f"Allocation does not sum to ~1 (total={total:.3f})")


def main() -> None:
    alloc_path = Path("data/adaptive_allocation.json")
    payload = utils.load_json(alloc_path)
    history = (payload or {}).get("history", [])
    if not history:
        utils.exit_with_status(
            "WARN",
            "No adaptive allocation history recorded",
            "test_adaptive_weights",
            {"allocation_path": str(alloc_path)},
        )

    breaches: list[str] = []
    for entry in history[-25:]:
        _validate_allocation_map(entry, breaches)

    if len(history) >= 2:
        latest = history[-1]["allocation"]
        prior = history[-2]["allocation"]
        for key in {"Assassins", "Avengers"}:
            try:
                delta = abs(float(latest.get(key, 0)) - float(prior.get(key, 0)))
            except (TypeError, ValueError):
                continue
            if delta > 0.2:
                breaches.append(f"{key} allocation jump {delta:.3f} exceeds 20%")

    status = "PASS"
    message = "Adaptive allocation history consistent"
    if breaches:
        status = "FAIL"
        message = "; ".join(breaches)

    details = {
        "entries_checked": min(25, len(history)),
        "latest_entry": history[-1],
        "breaches": breaches,
    }
    utils.exit_with_status(status, message, "test_adaptive_weights", details)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover
        utils.exit_with_status("FAIL", f"Unhandled exception: {exc}", "test_adaptive_weights", {})
