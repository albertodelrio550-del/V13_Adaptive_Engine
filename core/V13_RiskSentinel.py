class RiskMonitor:
    def __init__(self):
        self.max_dd = 5
        print("[RiskMonitor] initialized (stub)")

    def assess(self, telemetry):
        return {'max_dd': self.max_dd}
# ==============================================================
# V13_RiskSentinel.py — Adaptive Risk & Capital Kernel
# Build: 2025-10-20 | Version: V13_Stable_Release
# --------------------------------------------------------------
"""Simplified RiskSentinel — functional for PAPER testing without heavy deps."""

from datetime import datetime, timezone
import time


class RiskMonitor:
    def __init__(self):
        # max drawdown percentage (paper testing default)
        self.max_dd = 5
        self.current_dd = 0.0
        self.dd_active = False
        self.volatility_threshold = 2.0  # Volatility alert threshold
        self.dfi_prompts = []  # Doctrine Feedback Intelligence prompts
        print("[RiskMonitor] initialized (simplified)")

    def assess(self, feed: dict):
        """Assess a feed snapshot and update drawdown state.

        feed is expected to contain keys like 'delta' and 'pnl'.
        Returns a dict summarizing the risk profile.
        """
        pnl = feed.get('pnl', 0)
        volatility = feed.get('volatility', 0.0)
        if pnl < 0:
            self.current_dd = abs(pnl)
            if self.current_dd >= self.max_dd:
                self.dd_active = True
        else:
            self.dd_active = False

        # Adaptive caution system
        caution_level = self._calculate_caution_level(pnl, volatility)

        # Context-aware risk alerts (non-execution)
        alerts = self._generate_alerts(pnl, volatility, caution_level)

        return {
            'current_dd': self.current_dd,
            'max_dd': self.max_dd,
            'active': self.dd_active,
            'volatility': volatility,
            'caution_level': caution_level,
            'alerts': alerts,
        }

    def _calculate_caution_level(self, pnl, volatility):
        """Calculate adaptive caution level based on drawdown and volatility."""
        caution = 0
        if self.dd_active:
            caution += 2
        if volatility > self.volatility_threshold:
            caution += 1
        if pnl < -1.0:  # Additional caution for significant losses
            caution += 1
        return min(caution, 3)  # Max caution level 3

    def _generate_alerts(self, pnl, volatility, caution_level):
        """Generate context-aware risk alerts."""
        alerts = []
        if caution_level >= 3:
            alerts.append("HIGH RISK: Immediate caution advised. Consider DFI prompts.")
            self.dfi_prompts.append("High caution: Review doctrine for risk mitigation.")
        elif caution_level >= 2:
            alerts.append("MODERATE RISK: Monitor closely.")
        elif caution_level >= 1:
            alerts.append("LOW RISK ALERT: Minor volatility detected.")

        if volatility > self.volatility_threshold:
            alerts.append(f"VOLATILITY ALERT: {volatility:.2f}% exceeds threshold.")

        return alerts

    def report_status(self):
        return {
            'current_dd': self.current_dd,
            'max_dd': self.max_dd,
            'active': self.dd_active,
            'volatility_threshold': self.volatility_threshold,
            'dfi_prompts': self.dfi_prompts,
        }

    def monitor_telemetry(self, telemetry_update):
        """
        Subscribe to TELEMETRY_UPDATE events.
        Evaluate current state against adaptive thresholds.
        Emit RISK_ALERT events and integrate DFI.
        """
        pnl = telemetry_update.get('pnl', 0)
        volatility = telemetry_update.get('volatility', 0.0)

        # Update drawdown
        if pnl < 0:
            self.current_dd = abs(pnl)
            self.dd_active = self.current_dd >= self.max_dd
        else:
            self.dd_active = False

        # Determine adaptive mode
        mode = self._determine_mode(self.current_dd)

        # Generate alerts
        alerts = self._generate_adaptive_alerts(self.current_dd, volatility, mode)

        # Emit RISK_ALERT event
        risk_alert = {
            "origin": "RiskSentinel",
            "event": "DD_WARNING" if self.dd_active else "STATUS_UPDATE",
            "value": self.current_dd,
            "mode": mode,
            "alerts": alerts,
            "timestamp": datetime.now().isoformat()
        }
        try:
            from core.V13_SyncLoop import emit_event
            emit_event("RISK_ALERT", risk_alert)
        except ImportError:
            pass  # SyncLoop not available

        # Integrate DFI (Doctrine Feedback Intelligence)
        if alerts:
            self._trigger_dfi_response(alerts, mode)

        # Log to SessionAudit
        try:
            from core.V13_SessionAudit import SessionAudit
            audit = SessionAudit()
            audit.log_runtime_event("RISK_MONITOR", f"DD: {self.current_dd:.2f}, Mode: {mode}, Alerts: {len(alerts)}")
        except ImportError:
            pass  # SessionAudit not available

        return risk_alert

    def _determine_mode(self, current_dd):
        """Determine adaptive mode based on drawdown thresholds."""
        if current_dd <= 2:
            return "SAFE"
        elif current_dd <= 5:
            return "BALANCED"
        else:
            return "AGGRESSIVE"

    def _generate_adaptive_alerts(self, current_dd, volatility, mode):
        """Generate alerts based on thresholds and mode."""
        alerts = []
        if mode == "AGGRESSIVE":
            alerts.append(f"Warning — {current_dd:.1f}% of MaxDD reached. Defensive posture recommended.")
        elif mode == "BALANCED":
            if current_dd >= 4:  # 80% of 5
                alerts.append(f"Warning — 80% of MaxDD reached.")
        if volatility > self.volatility_threshold:
            alerts.append(f"Volatility alert: {volatility:.2f}% exceeds threshold.")
        return alerts

    def _trigger_dfi_response(self, alerts, mode):
        """Trigger Doctrine Feedback Intelligence response."""
        try:
            from core.V13_DoctrineFeedbackLoop import DoctrineFeedbackLoop
            dfi = DoctrineFeedbackLoop()
            for alert in alerts:
                if "Defensive" in alert:
                    dfi.analyze({"cmd_text": "defensive"})  # Simulate doctrine response
        except ImportError:
            pass  # DoctrineFeedbackLoop not available

    def receive_trade_payload(self, payload):
        """
        Receive standardized trade payload from CommandMatrix for audit replay.
        Logs the payload for full order cycle replay during audits.
        """
        from core.V13_LogFormatter import log_event
        log_event(f"Trade payload received for audit: {payload}")
        # Store in a list or file for replay
        if not hasattr(self, 'trade_payloads'):
            self.trade_payloads = []
        self.trade_payloads.append(payload)
        # Optionally, assess risk based on payload
        # e.g., if payload['qty'] > 0.1, alert high exposure

# ==============================================================
# Stage-3 Risk Gate (Pre-Trade Intent Validation)
# --------------------------------------------------------------
# A lightweight, synchronous validator used by the CommandMatrix
# to decide whether an order intent may proceed to routing.
#
# Notes:
# - Reads limits from config (V13_Config.ini)
# - Uses local data snapshots when available to avoid hard network deps
# - Maintains simple state for duplicate suppression and day pacing
# ==============================================================
import json
import os
import configparser
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    # Optional import for price snapshot (stocks)
    from alpaca_feed_core import get_snapshot_stocks
except Exception:
    get_snapshot_stocks = None  # Fallback when not available


class RiskDecision:
    def __init__(self, allowed: bool, reason: str = "ok", details: dict | None = None):
        self.allowed = allowed
        self.reason = reason
        self.details = details or {}

    def to_dict(self):
        return {"allowed": self.allowed, "reason": self.reason, **self.details}


class RiskGate:
    live_arm = False

    def __init__(self, cfg: configparser.ConfigParser | None = None):
        self.cfg = cfg or self._load_cfg()
        self.data_dir = Path("data")
        self.logs_dir = Path("logs")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._orders_today_file = self.data_dir / "orders_today.json"
        self._seen_tags_file = self.data_dir / "seen_order_tags.json"
        self._positions_file = self.data_dir / "positions.json"
        self._account_file = self.data_dir / "account.json"
        self._audit_file = self.logs_dir / "V13_SessionAudit.log"
        self._live_arm_path = Path("core/.live_armed")

    # --------- Public API ---------
    def approve(self, intent: dict) -> RiskDecision:
        # 1) Environment gate
        run_env = self.cfg.get('MODE', 'RUN_ENV', fallback='PAPER')
        channel = self.cfg.get('MODE', 'EXECUTION_CHANNEL', fallback='NONE')
        dry_run = self.cfg.getboolean('MODE', 'DRY_RUN_POST', fallback=False)
        tag = intent.get('client_order_tag') or intent.get('client_order_id') or ''
        env_meta = {"run_env": run_env, "channel": channel, "tag": tag}
        if run_env == 'PAPER':
            if channel != 'PAPER_POST':
                return self._deny('env', extra=env_meta)
        elif run_env == 'LIVE':
            if channel != 'LIVE_POST':
                return self._deny('live_channel', extra=env_meta)
            if not self._is_live_armed():
                return self._deny('live_locked', extra=env_meta)
            if dry_run:
                return self._deny('live_dry_run', extra=env_meta)
        else:
            return self._deny('env', extra=env_meta)

        # When DRY_RUN_POST is on, we still "approve" the intent so upper layers can log/visualize,
        # but the router must not POST. We encode this in details.
        dry_flag = {"dry_run": True} if dry_run else {}
        base_extra = {"tag": tag}

        # 2) Whitelist
        symbol = (intent.get('symbol') or '').strip().upper()
        wl = [s.strip().upper() for s in self.cfg.get('ROUTING', 'SYMBOL_WHITELIST', fallback='').split(',') if s.strip()]
        if symbol not in wl:
            return self._deny('symbol', extra={**base_extra, "symbol": symbol})

        # 3) Size vs per-position cap
        qty = float(intent.get('qty', 0) or 0)
        last_price = self._infer_price(intent, symbol)
        if last_price is None:
            return self._deny('price_unknown', extra={**base_extra, "symbol": symbol})
        value = qty * last_price

        max_pos = float(self.cfg.get('RISK_LIMITS', 'MAX_POS_USD', fallback='0') or 0)
        min_trade = float(self.cfg.get('RISK_LIMITS', 'MIN_TRADE_VALUE', fallback='0') or 0)
        if value < min_trade:
            return self._deny('min_trade', extra={**base_extra, "value": round(value, 2), "min_trade": min_trade})
        if value > max_pos:
            return self._deny('size', extra={**base_extra, "value": round(value, 2), "max_pos": max_pos})

        # 4) Aggregate exposure
        gross_now = self._current_exposure_usd()
        max_gross = float(self.cfg.get('RISK_LIMITS', 'MAX_GROSS_USD', fallback='0') or 0)
        if gross_now + value > max_gross:
            return self._deny('exposure', extra={**base_extra, "gross_now": round(gross_now, 2), "intent_value": round(value, 2), "max_gross": max_gross})

        # 5) Pace limit
        orders_today = self._orders_today()
        max_orders = int(self.cfg.get('RISK_LIMITS', 'MAX_ORDERS_DAY', fallback='0') or 0)
        if orders_today >= max_orders > 0:
            return self._deny('pace', extra={**base_extra, "orders_today": orders_today, "max_orders": max_orders})

        # 6) Loss lockouts (day/session)
        day_pnl, session_pnl = self._read_pnl_state()
        max_loss_day = float(self.cfg.get('RISK_LIMITS', 'MAX_LOSS_DAY', fallback='0') or 0)
        max_loss_ses = float(self.cfg.get('RISK_LIMITS', 'MAX_LOSS_SESSION', fallback='0') or 0)
        if day_pnl <= -max_loss_day and max_loss_day > 0:
            return self._deny('lockout_day', extra={**base_extra, "day_pnl": round(day_pnl, 2), "max_loss_day": max_loss_day})
        if session_pnl <= -max_loss_ses and max_loss_ses > 0:
            return self._deny('lockout_session', extra={**base_extra, "session_pnl": round(session_pnl, 2), "max_loss_session": max_loss_ses})

        # 7) Market state (stubbed for PAPER stocks; assume tradable/open)
        if not self._market_open_stub(symbol):
            return self._deny('market_closed', extra={**base_extra, "symbol": symbol})

        # 8) Duplicate idempotency (24h)
        if tag and self._seen_before(tag, within_hours=24):
            return self._deny('duplicate', extra={**base_extra, "tag": tag})

        # If we reached here: approved. Update counters/tag journal.
        self._increment_orders_today()
        if tag:
            self._remember_tag(tag)

        exposure_after = gross_now + value
        orders_after = orders_today + 1
        self._audit_line(
            "RISK_OK | "
            f"tag={tag} | {symbol} {intent.get('side')} {qty} @ {last_price:.2f} | "
            f"intent_value={value:.2f} | exposure_after={exposure_after:.2f} | "
            f"day_pnl={day_pnl:.2f} | session_pnl={session_pnl:.2f} | ordersToday={orders_after}"
        )

        return RiskDecision(True, 'ok', {"last_price": last_price, **dry_flag})

    # --------- Helpers ---------
    def _load_cfg(self):
        cfg = configparser.ConfigParser(inline_comment_prefixes=(';', '#'))
        cfg.optionxform = str
        cfg.read('config/V13_Config.ini')
        return cfg

    def _deny(self, reason: str, extra: dict | None = None) -> RiskDecision:
        parts = ["RISK_DENY", f"reason={reason}"]
        if extra:
            parts.extend(f"{k}={v}" for k, v in extra.items())
        self._audit_line(" | ".join(parts))
        return RiskDecision(False, reason, extra)

    def _is_live_armed(self) -> bool:
        armed_flag = getattr(RiskGate, 'live_arm', False)
        file_present = self._live_arm_path.exists()
        return armed_flag and file_present

    @classmethod
    def set_live_arm(cls, value: bool):
        cls.live_arm = bool(value)

    def _audit_line(self, msg: str):
        ts = datetime.now(timezone.utc).isoformat()
        self._audit_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._audit_file, 'a', encoding='utf-8') as f:
            f.write(f"{ts} | {msg}\n")

    def _infer_price(self, intent: dict, symbol: str) -> float | None:
        # Prefer explicit prices from intent when applicable
        for k in ('limit_price', 'stop_price'):
            v = intent.get(k)
            if v is not None:
                try:
                    return float(v)
                except Exception:
                    pass
        # Try live snapshot for stocks (optional)
        if get_snapshot_stocks:
            try:
                snap = get_snapshot_stocks(symbol)
                if snap and snap.get('last_price'):
                    return float(snap['last_price'])
            except Exception:
                pass
        # Try last cached market price in account/positions snapshots
        pos = self._read_json(self._positions_file)
        if isinstance(pos, list):
            # positions.json snapshot as list of positions
            for p in pos:
                if (p.get('symbol') or '').upper() == symbol and p.get('market_price'):
                    try:
                        return float(p['market_price'])
                    except Exception:
                        continue
        # No reliable price available
        return None

    def _current_exposure_usd(self) -> float:
        # Sum of absolute market values from positions snapshot if present
        pos = self._read_json(self._positions_file)
        total = 0.0
        try:
            if isinstance(pos, list):
                for p in pos:
                    mv = p.get('market_value')
                    if mv is not None:
                        total += abs(float(mv))
        except Exception:
            return 0.0
        return total

    def _orders_today(self) -> int:
        data = self._read_json(self._orders_today_file) or {}
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        if data.get('date') != today:
            return 0
        return int(data.get('count', 0))

    def _increment_orders_today(self):
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        count = self._orders_today() + 1
        payload = {"date": today, "count": count}
        self._write_json(self._orders_today_file, payload)

    def _seen_before(self, tag: str, within_hours: int = 24) -> bool:
        data = self._read_json(self._seen_tags_file) or {}
        now = datetime.now(timezone.utc)
        ts = data.get(tag)
        if ts:
            try:
                seen = datetime.fromisoformat(ts)
                if now - seen <= timedelta(hours=within_hours):
                    return True
            except Exception:
                pass
        return False

    def _remember_tag(self, tag: str):
        data = self._read_json(self._seen_tags_file) or {}
        data[tag] = datetime.now(timezone.utc).isoformat()
        self._write_json(self._seen_tags_file, data)

    def _read_pnl_state(self) -> tuple[float, float]:
        # Try a status file first
        status_path = Path('data') / 'V13_Status.json'
        try:
            if status_path.exists():
                st = json.loads(status_path.read_text(encoding='utf-8'))
                # If tracker writes cumulative PnL, treat as session PnL; day PnL unknown -> session used for both
                pnl = float(st.get('PnL', 0) or 0)
                return pnl, pnl
        except Exception:
            pass
        # Fallback: parse last Performance_Log.txt line if present
        try:
            plog = Path('logs') / 'Performance_Log.txt'
            if plog.exists():
                lines = plog.read_text(encoding='utf-8', errors='ignore').strip().splitlines()
                if lines:
                    last = lines[-1]
                    # expects ... Session=+12.34 ...
                    import re
                    m = re.search(r"Session=([+\-]?[0-9]+\.[0-9]+)", last)
                    if m:
                        ses = float(m.group(1))
                        return ses, ses
        except Exception:
            pass
        return 0.0, 0.0

    def _market_open_stub(self, symbol: str) -> bool:
        # For PAPER and initial wiring, assume tradable/open. Extend with real calendar checks later.
        return True

    @staticmethod
    def _read_json(path: Path):
        try:
            if path.exists():
                return json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            return None
        return None

    @staticmethod
    def _write_json(path: Path, payload):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
        except Exception:
            pass
