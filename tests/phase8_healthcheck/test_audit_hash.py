import hashlib
from pathlib import Path

from . import utils


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    seal_path = Path("logs/GLOBAL_SEAL.txt")
    if not seal_path.exists():
        utils.exit_with_status(
            "WARN",
            f"Global seal file missing at {seal_path}",
            "test_audit_hash",
            {"seal_path": str(seal_path)},
        )

    lines = [line.strip() for line in seal_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        utils.exit_with_status(
            "FAIL",
            "Global seal file is empty",
            "test_audit_hash",
            {"seal_path": str(seal_path)},
        )

    entries = []
    composite_line = None
    for line in lines:
        if line.startswith("COMPOSITE "):
            composite_line = line
            continue
        parts = line.rsplit(" ", 1)
        if len(parts) != 2:
            continue
        entries.append((Path(parts[0]), parts[1]))

    mismatches = []
    composite_digest = hashlib.sha256()
    for path, expected_hash in entries:
        if not path.exists():
            mismatches.append({"path": str(path), "reason": "missing"})
            continue
        actual_hash = _file_sha256(path)
        if actual_hash != expected_hash:
            mismatches.append(
                {
                    "path": str(path),
                    "reason": "hash_mismatch",
                    "expected": expected_hash,
                    "actual": actual_hash,
                }
            )
        composite_digest.update(path.read_bytes())

    composite_ok = False
    if composite_line:
        _, expected = composite_line.split(" ", 1)
        composite_ok = composite_digest.hexdigest() == expected.strip()
        if not composite_ok:
            mismatches.append(
                {
                    "path": "COMPOSITE",
                    "reason": "hash_mismatch",
                    "expected": expected.strip(),
                    "actual": composite_digest.hexdigest(),
                }
            )

    status = "PASS"
    message = "Audit seal verified"
    if mismatches:
        status = "FAIL"
        message = "Audit seal mismatch detected"

    details = {
        "entries_checked": len(entries),
        "composite_present": composite_line is not None,
        "mismatches": mismatches,
    }
    utils.exit_with_status(status, message, "test_audit_hash", details)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover
        utils.exit_with_status("FAIL", f"Unhandled exception: {exc}", "test_audit_hash", {})
