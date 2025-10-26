"""
run_night_session.py

Launch a Spot-only V13 night session (6 hours by default) and then
generate a concise battlefield report. Uses existing runtime/session
config and commander loop. Keep it simple to avoid runtime overhead.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.V13_SessionAudit import pre_launch_audit
from commander_v13_manual import CommanderV13Manual


def main() -> None:
    try:
        pre_launch_audit()
    except Exception:
        pass

    commander = CommanderV13Manual()
    try:
        commander.run()
    finally:
        # Post-process report after commander ends
        try:
            from scripts.generate_battlefield_report import main as gen_report
            gen_report()
        except Exception:
            pass


if __name__ == "__main__":
    main()

