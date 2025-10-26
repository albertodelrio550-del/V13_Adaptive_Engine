from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core.V13_DoctrineFeedbackLoop import DoctrineFeedbackLoop

UPDATE_DIR = Path('docs/DoctrineUpdates')


def find_update(date_str: Optional[str] = None) -> Path:
    if not UPDATE_DIR.exists():
        raise FileNotFoundError('Doctrine update directory missing.')
    if date_str:
        candidate = UPDATE_DIR / f'doctrine_update_{date_str}.json'
        if not candidate.exists():
            raise FileNotFoundError(f'Doctrine update not found for {date_str}.')
        return candidate
    updates = sorted(UPDATE_DIR.glob('doctrine_update_*.json'))
    if not updates:
        raise FileNotFoundError('No doctrine updates available.')
    return updates[-1]


def load_update(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def show(update: dict, path: Path) -> None:
    print(f"Update File : {path}")
    print(f"Date        : {update.get('date')}")
    print(f"Generated   : {update.get('generated_at')}")
    print(f"Accepted    : {update.get('accepted')}")
    print(f"Reviewer    : {update.get('reviewer')}")
    print("Suggestions :")
    suggestions = update.get('suggestions') or {}
    reasoning = update.get('reasoning') or {}
    if not suggestions:
        reason = reasoning.get('Doctrine', 'Hold parameters') if reasoning else 'Hold parameters'
        print(f"  - HOLD :: {reason}")
    else:
        for key, value in suggestions.items():
            reason = reasoning.get(key, 'No reasoning provided')
            print(f"  - {key}: {value} :: {reason}")


def mark(path: Path, accept: bool, reviewer: Optional[str], notes: Optional[str]) -> None:
    update = load_update(path)
    update['accepted'] = accept
    update['reviewed_at'] = datetime.now(timezone.utc).isoformat()
    if reviewer:
        update['reviewer'] = reviewer
    if notes:
        update.setdefault('notes', []).append(notes)
    path.write_text(json.dumps(update, indent=2), encoding='utf-8')
    status = 'approved' if accept else 'rejected'
    print(f"Doctrine update {status}: {path}")
    if accept:
        DoctrineFeedbackLoop.record_accepted_update(update)


def main() -> None:
    parser = argparse.ArgumentParser(description='Review doctrine update proposals.')
    parser.add_argument('--date', help='Date of update (YYYY-MM-DD). Defaults to latest.')
    parser.add_argument('--approve', action='store_true', help='Approve the selected update.')
    parser.add_argument('--reject', action='store_true', help='Reject the selected update.')
    parser.add_argument('--reviewer', help='Reviewer name/initials.')
    parser.add_argument('--notes', help='Optional review notes.')
    parser.add_argument('--reset', action='store_true', help='Reset learning lockout.')
    parser.add_argument('--authorize', action='store_true', help='Authorize learning after reset.')
    parser.add_argument('--rollback', choices=['last_good'], help='Rollback to last good doctrine.')
    args = parser.parse_args()

    if args.approve and args.reject:
        raise SystemExit('Cannot approve and reject at the same time.')
    if args.reset and not args.authorize:
        raise SystemExit('Use --reset together with --authorize to re-enable learning.')
    if args.reset and args.authorize:
        loop = DoctrineFeedbackLoop(load_doctrines_flag=False)
        loop.reset_learning()
        print('Learning mode re-enabled.')
        return
    if args.rollback == 'last_good':
        path = DoctrineFeedbackLoop.rollback_last_good()
        print(f'Rollback update created: {path}')
        return
    path = find_update(args.date)
    if args.approve or args.reject:
        mark(path, args.approve, args.reviewer, args.notes)
    else:
        update = load_update(path)
        show(update, path)


if __name__ == '__main__':
    main()
