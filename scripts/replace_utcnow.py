from __future__ import annotations

import argparse
import re
from pathlib import Path

TARGET_SUFFIXES = {'.py'}
UTC_PATTERN = re.compile(r'datetime\.utcnow\s*\(\s*\)')


def ensure_timezone_import(text: str) -> str:
    pattern = re.compile(r'from datetime import ([^\n]+)')

    def repl(match: re.Match) -> str:
        items = [item.strip() for item in match.group(1).split(',') if item.strip()]
        if 'timezone' not in items:
            items.append('timezone')
        seen = set()
        ordered: list[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                ordered.append(item)
        return 'from datetime import ' + ', '.join(ordered)

    new_text, count = pattern.subn(repl, text)
    if count > 0:
        return new_text
    if 'from datetime import datetime' in text and 'timezone' not in text:
        return text.replace('from datetime import datetime', 'from datetime import datetime, timezone')
    if 'import datetime' in text and 'timezone' not in text:
        return text.replace('import datetime', 'import datetime\nfrom datetime import timezone', 1)
    return text


def transform(path: Path) -> None:
    original = path.read_text(encoding='utf-8')
    if 'datetime.utcnow' not in original:
        return
    replaced = UTC_PATTERN.sub('datetime.now(timezone.utc)', original)
    if replaced == original:
        return
    replaced = ensure_timezone_import(replaced)
    path.write_text(replaced, encoding='utf-8')


def main() -> None:
    parser = argparse.ArgumentParser(description='Replace datetime.utcnow with timezone-aware alternative.')
    parser.add_argument('--root', type=Path, default=Path('.'), help='Project root (default: current directory).')
    args = parser.parse_args()
    for file_path in args.root.rglob('*'):
        if file_path.is_file() and file_path.suffix in TARGET_SUFFIXES:
            transform(file_path)


if __name__ == '__main__':
    main()
