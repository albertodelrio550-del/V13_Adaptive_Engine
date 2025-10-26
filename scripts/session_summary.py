import argparse
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class TradeStats:
    count: int = 0
    wins: int = 0
    losses: int = 0
    breakeven: int = 0
    realized_pnl: Optional[float] = None


@dataclass
class Reconciliation:
    capital_start: float
    capital_end: float
    capital_delta: float
    chosen_realized_pnl: Optional[float]
    chosen_source: str
    mismatch: Optional[float]


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _parse_iso(ts: str) -> datetime:
    # Accept both with and without timezone; fallback to basic parsing
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        # try space separated variant
        try:
            return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return datetime.utcnow()


def _find_latest_session(audit: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
    sessions: List[Dict[str, Any]] = audit.get("sessions", [])
    if not sessions:
        raise SystemExit("No sessions found in audit report")
    if session_id:
        for s in sessions:
            if s.get("session_id") == session_id:
                return s
        raise SystemExit(f"Session {session_id} not found in audit report")
    # Pick by ended_at if available, else last
    def keyfunc(s: Dict[str, Any]):
        return _parse_iso(s.get("ended_at", "1970-01-01T00:00:00+00:00"))
    return sorted(sessions, key=keyfunc)[-1]


def _parse_battlefield_pnl(md_text: str) -> Optional[float]:
    # Look for line like: "Estimated Realized PnL: -110.74 (quote asset)"
    m = re.search(r"Estimated\s+Realized\s+PnL:\s*([+-]?\d+(?:\.\d+)?)", md_text)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def _latest_battlefield_text(reports_dir: Path) -> Optional[str]:
    files = sorted(reports_dir.glob("battlefield_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    try:
        return files[0].read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None


def _extract_trade_pnl_and_wl(trade_report: Dict[str, Any]) -> TradeStats:
    trades = trade_report.get("trades")
    stats = TradeStats()
    if not isinstance(trades, list) or not trades:
        stats.count = int(trade_report.get("count", 0))
        stats.realized_pnl = None
        return stats

    pnl_sum = 0.0
    pnl_found = False
    for t in trades:
        if not isinstance(t, dict):
            continue
        # Try common keys for realized PnL
        pnl = None
        for k in ("pnl", "realized_pnl", "profit", "profit_loss", "pl"):
            v = t.get(k)
            if isinstance(v, (int, float)):
                pnl = float(v)
                pnl_found = True
                break
            # sometimes as string
            if isinstance(v, str):
                try:
                    pnl = float(v)
                    pnl_found = True
                    break
                except Exception:
                    pass
        if pnl is not None:
            pnl_sum += pnl
            if pnl > 0:
                stats.wins += 1
            elif pnl < 0:
                stats.losses += 1
            else:
                stats.breakeven += 1
        else:
            # Unknown pnl => cannot W/L classify
            pass

    stats.count = len(trades)
    stats.realized_pnl = pnl_sum if pnl_found else None
    return stats


def _choose_pnl_source(
    audit_session: Dict[str, Any],
    trade_stats: TradeStats,
    alpaca_realized: Optional[float],
    battlefield_est: Optional[float],
) -> Tuple[Optional[float], str]:
    # Priority: executed trades > alpaca realized > audit realized_pnl > battlefield estimate
    if trade_stats.realized_pnl is not None:
        return trade_stats.realized_pnl, "executed_trades"
    if alpaca_realized is not None:
        return alpaca_realized, "alpaca"
    ap = audit_session.get("realized_pnl")
    if isinstance(ap, (int, float)):
        return float(ap), "audit_report"
    if battlefield_est is not None:
        return battlefield_est, "battlefield_estimate"
    return None, "unknown"


def _reconcile(audit_session: Dict[str, Any], chosen_pnl: Optional[float], chosen_src: str) -> Reconciliation:
    cs = float(audit_session.get("capital_start", 0.0))
    ce = float(audit_session.get("capital_end", 0.0))
    delta = ce - cs
    mismatch = None
    if chosen_pnl is not None:
        mismatch = delta - chosen_pnl
    return Reconciliation(
        capital_start=cs,
        capital_end=ce,
        capital_delta=delta,
        chosen_realized_pnl=chosen_pnl,
        chosen_source=chosen_src,
        mismatch=mismatch,
    )


def _fmt_currency(v: Optional[float]) -> str:
    if v is None:
        return "N/A"
    return f"{v:.2f}"


def generate_summary(
    audit_path: Path,
    trade_path: Optional[Path],
    reports_dir: Path,
    out_dir: Path,
    session_id: Optional[str],
) -> Tuple[Path, Path]:
    audit = _load_json(audit_path)
    s = _find_latest_session(audit, session_id)
    sid = s.get("session_id", "unknown_session")
    started_at = s.get("started_at")
    ended_at = s.get("ended_at")

    # Battlefield estimate
    btext = _latest_battlefield_text(reports_dir) or ""
    battlefield_est = _parse_battlefield_pnl(btext)

    # Trades
    trade_report = {}
    if trade_path and trade_path.exists():
        try:
            trade_report = _load_json(trade_path)
        except Exception:
            trade_report = {}
    trade_stats = _extract_trade_pnl_and_wl(trade_report)

    # Alpaca
    alpaca_block = s.get("alpaca_data", {}) if isinstance(s.get("alpaca_data"), dict) else {}
    alpaca_realized = alpaca_block.get("realized_pnl") if isinstance(alpaca_block.get("realized_pnl"), (int, float)) else None

    # Choose PnL source and reconcile
    chosen_pnl, chosen_src = _choose_pnl_source(s, trade_stats, alpaca_realized, battlefield_est)
    recon = _reconcile(s, chosen_pnl, chosen_src)

    # Win/Loss summary
    wins = trade_stats.wins
    losses = trade_stats.losses
    breakeven = trade_stats.breakeven
    total = trade_stats.count
    win_rate = (wins / total * 100.0) if total > 0 else 0.0

    # Build markdown
    md_lines = []
    md_lines.append(f"# V13 Session Summary — {sid}")
    md_lines.append("")
    md_lines.append("## Overview")
    md_lines.append(f"- Window: {started_at} → {ended_at}")
    md_lines.append(f"- Capital start: {_fmt_currency(recon.capital_start)}")
    md_lines.append(f"- Capital end:   {_fmt_currency(recon.capital_end)}")
    md_lines.append(f"- Capital delta: {_fmt_currency(recon.capital_delta)}")
    md_lines.append("")
    md_lines.append("## PnL Reconciliation")
    md_lines.append(f"- Chosen realized PnL: {_fmt_currency(recon.chosen_realized_pnl)} (source={recon.chosen_source})")
    md_lines.append(f"- Audit realized PnL:  {_fmt_currency(float(s.get('realized_pnl', 0.0)) if isinstance(s.get('realized_pnl'), (int, float)) else None)}")
    md_lines.append(f"- Battlefield estimate: {_fmt_currency(battlefield_est)}")
    if recon.mismatch is not None:
        flag = "OK" if abs(recon.mismatch) < 1e-6 else "MISMATCH"
        md_lines.append(f"- Capital vs PnL mismatch (chosen): {_fmt_currency(recon.mismatch)} [{flag}]")
    else:
        md_lines.append("- Capital vs PnL mismatch (chosen): N/A (no realized PnL source)")

    # Comparative mismatches for visibility across sources
    comp = []
    comp.append(("executed_trades", trade_stats.realized_pnl))
    comp.append(("alpaca", alpaca_realized))
    ap = float(s.get('realized_pnl')) if isinstance(s.get('realized_pnl'), (int, float)) else None
    comp.append(("audit_report", ap))
    comp.append(("battlefield_estimate", battlefield_est))
    for label, val in comp:
        if val is None:
            continue
        diff = recon.capital_delta - float(val)
        tag = "OK" if abs(diff) < 1e-6 else "MISMATCH"
        md_lines.append(f"- Mismatch vs {label}: {_fmt_currency(diff)} [{tag}]")
    md_lines.append("")
    md_lines.append("## Win/Loss")
    md_lines.append(f"- Trades: {total} | Wins: {wins} | Losses: {losses} | Breakeven: {breakeven}")
    md_lines.append(f"- Win rate: {win_rate:.1f}%")
    md_lines.append("")
    md_lines.append("## Notes")
    notes = s.get("learning_notes", [])
    for n in notes:
        md_lines.append(f"- {n}")
    if total == 0:
        md_lines.append("- No executed trades recorded; win/loss reflects zero activity.")
    if recon.mismatch is not None and abs(recon.mismatch) >= 0.01:
        md_lines.append("- Significant capital/PnL mismatch detected — verify data sources (executed vs model).")

    out_dir.mkdir(parents=True, exist_ok=True)
    out_md = out_dir / f"session_summary_{sid}.md"
    out_json = out_dir / f"session_summary_{sid}.json"
    out_md.write_text("\n".join(md_lines), encoding="utf-8")

    # JSON payload
    payload = {
        "session_id": sid,
        "window": {"started_at": started_at, "ended_at": ended_at},
        "reconciliation": asdict(recon),
        "sources": {
            "trade_report_present": bool(trade_report),
            "alpaca_realized": alpaca_realized,
            "battlefield_estimated": battlefield_est,
        },
        "winloss": asdict(trade_stats) | {"win_rate": win_rate},
    }
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_md, out_json


def main():
    parser = argparse.ArgumentParser(description="Generate per-session capital vs PnL reconciliation and win/loss summary.")
    parser.add_argument("--audit", type=Path, default=Path("logs/V13_session_audit_report.json"))
    parser.add_argument("--trades", type=Path, default=Path("logs/trade_report.json"))
    parser.add_argument("--reports", type=Path, default=Path("reports"))
    parser.add_argument("--out", type=Path, default=Path("reports"))
    parser.add_argument("--session", type=str, default=None, help="Session ID to summarize (defaults to latest)")
    args = parser.parse_args()

    out_md, out_json = generate_summary(args.audit, args.trades, args.reports, args.out, args.session)
    print(f"Wrote: {out_md}")
    print(f"Wrote: {out_json}")


if __name__ == "__main__":
    main()
