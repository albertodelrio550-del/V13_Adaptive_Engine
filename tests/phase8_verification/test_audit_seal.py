import hashlib
import unittest
from pathlib import Path

from V13_CommandMatrix import GLOBAL_SEAL_PATH
from tests.phase8_verification import utils


class AuditSealTest(unittest.TestCase):
    def setUp(self) -> None:
        self.matrix = utils.create_matrix(utils.AllowAllRiskGate())
        for block_id in self.matrix.blocks:
            utils.write_block_log(
                self.matrix,
                block_id,
                f"{block_id} audit line\nanother event\n",
            )

    def test_global_seal_hashes_match_files(self) -> None:
        self.matrix._write_global_audit_seal()
        self.assertTrue(GLOBAL_SEAL_PATH.exists())

        lines = [
            line.strip()
            for line in GLOBAL_SEAL_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertTrue(lines)

        composite_expected = None
        composite = hashlib.sha256()
        for line in lines:
            if line.startswith("COMPOSITE "):
                composite_expected = line.split(" ", 1)[1]
                continue
            path_str, digest = line.rsplit(" ", 1)
            path = Path(path_str)
            self.assertTrue(path.exists(), f"Audit path missing: {path}")
            data = path.read_bytes()
            actual = hashlib.sha256(data).hexdigest()
            self.assertEqual(
                actual,
                digest,
                f"Hash mismatch for {path}",
            )
            composite.update(data)

        self.assertIsNotNone(composite_expected)
        self.assertEqual(composite.hexdigest(), composite_expected)


if __name__ == "__main__":
    unittest.main()
