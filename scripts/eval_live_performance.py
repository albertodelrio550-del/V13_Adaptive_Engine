import os
import sys
sys.path.append(os.getcwd())
import json
from pathlib import Path
from statistics import mean
import requests

from alpaca_feed_core import load_keys, _get_headers

INTENT_LOG = Path("logs/CommandMatrix.log")
ORDERS_DIR = Path("data/orders")
LATENCY_LOG = Path("logs/V13_Latency.log")
OUTPUT = Path("logs/live_eval_summary.json")


def load_live_orders():
    keys = load_keys()
    url = keys.get("TRADE_ENDPOINT", "https://paper-api.alpaca.markets/v2") + "/orders"
    resp = requests.get(url, headers=_get_headers(keys), params={"status": "all", "limit": 100}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def load_signal_price(order_id: str):
    if not ORDERS_DIR.exists():
        return None
    files = sorted(ORDERS_DIR.glob("*.jsonl"), reverse=True)
    for path in files:
        for line in reversed(path.read_text(encoding="utf-8").splitlines()):
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if data.get("order_id") == order_id and data.get("signal_price") is not None:
                try:
                    return float(data["signal_price"])
                except (TypeError, ValueError):
                    return None
    return None


def load_latency(order_id: str):
    if not LATENCY_LOG.exists():
        return {}
    events = [json.loads(line) for line in LATENCY_LOG.read_text().splitlines() if line.strip()]
    acc = {event["event"]: event for event in events if event.get("order_id") == order_id}
    return {
        "exec_ms": acc.get("ACK_ACCEPTED", {}).get("since_intent_ms"),
        "fill_ms": acc.get("FILLED", {}).get("since_intent_ms"),
    }


def evaluate():
    orders = [o for o in load_live_orders() if o.get("client_order_id", "").startswith("LIVE")]
    results = []
    for order in orders:
        order_id = order.get("client_order_id")
        fill_price = float(order.get("filled_avg_price") or 0)
        signal_price = load_signal_price(order_id)
        latency = load_latency(order_id)
        drift = None
        if signal_price and signal_price > 0:
            drift = abs(fill_price - signal_price) / signal_price
        results.append({
            "order_id": order_id,
            "symbol": order.get("symbol"),
            "side": order.get("side"),
            "qty": order.get("filled_qty"),
            "fill_price": fill_price,
            "signal_price": signal_price,
            "drift": drift,
            "latency": latency,
        })

    summary = {
        "orders": results,
        "avg_drift": mean([r["drift"] for r in results if r["drift"] is not None]) if results else None,
        "alerts": []
    }
    for r in results:
        if r.get("drift") and r["drift"] > 0.003:
            summary["alerts"].append({"type": "drift", "order_id": r["order_id"], "value": r["drift"]})
        exec_ms = r.get("latency", {}).get("exec_ms")
        if exec_ms and exec_ms > 2000:
            summary["alerts"].append({"type": "latency", "order_id": r["order_id"], "value": exec_ms})

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Evaluation summary written to {OUTPUT}")


if __name__ == "__main__":
    evaluate()
