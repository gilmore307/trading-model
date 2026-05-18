from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
UNSTABLE_MODEL_ID_PATTERNS = (
    re.compile(r'"model_id"\s*:\s*"model_\d{2}_[^"]+"'),
    re.compile(r"DEFAULT_MODEL_ID\s*=\s*\"model_\d{2}_[^\"]+\""),
)
CODE_ROOTS = (REPO_ROOT / "src", REPO_ROOT / "scripts")


class StableModelIdTests(unittest.TestCase):
    def test_active_code_does_not_use_physical_surface_names_as_model_ids(self) -> None:
        offenders: list[str] = []
        for root in CODE_ROOTS:
            for path in sorted(root.rglob("*.py")):
                if "__pycache__" in path.parts:
                    continue
                text = path.read_text(encoding="utf-8")
                for pattern in UNSTABLE_MODEL_ID_PATTERNS:
                    for match in pattern.finditer(text):
                        offenders.append(f"{path.relative_to(REPO_ROOT)}:{text[:match.start()].count(chr(10)) + 1}:{match.group(0)}")
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
