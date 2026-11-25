"""test_comment_bootstrap.py — Tests for first-run comment-audit bootstrap.

exports: class CommentBootstrapTestCase
used_by: none
rules:   Load the script by file path — the skill directory name is not a Python package. Every case writes to a temporary project so no installed or checked-in docs are touched.
agent:   unknown | nexrouter | 2026-11-21 | unknown | added bootstrap regressions: first run, idempotence, no overwrite, and no ratchet bypass
"""

from __future__ import annotations

import importlib.util
import io
import os
import contextlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

BUDGET_PATH = (
    Path(__file__).resolve().parents[1]
    / ".agents"
    / "skills"
    / "agents-contract"
    / "scripts"
    / "comment_budget.py"
)
TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "docs"

SAMPLE = '"""m.py — probe.\n\nexports: none\nused_by: none\nrules:   none\nagent:   a | b | 2026-11-21 | s | note\n"""\nx = 1\n'


def load_budget():
    """Load the budget script from its file path.

    Rules:   The `agents-contract` directory name holds a dash, so the module needs importlib.
    """
    spec = importlib.util.spec_from_file_location("comment_budget", BUDGET_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["comment_budget"] = module
    spec.loader.exec_module(module)
    return module


class CommentBootstrapTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.budget = load_budget()
        self.root = Path(tempfile.mkdtemp(prefix="comment-bootstrap-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        (self.root / "src").mkdir()
        (self.root / "src" / "m.py").write_text(SAMPLE, encoding="utf-8")

    def run_budget(self, *args: str) -> tuple[int, str]:
        """Run the CLI and return both exit code and output."""
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = self.budget.main([*args, str(self.root)])
        return code, stdout.getvalue()

    def test_bootstrap_creates_baseline_template_and_ledger(self) -> None:
        code, output = self.run_budget(
            "--bootstrap",
            "--template-dir",
            str(TEMPLATE_DIR),
            "--baseline",
            str(self.root / "docs" / "comment-budget.json"),
        )

        self.assertEqual(0, code, output)
        self.assertEqual(
            {"version": 1, "comments": 5, "open_notes": 0},
            json.loads((self.root / "docs" / "comment-budget.json").read_text()),
        )
        self.assertTrue((self.root / "docs" / "adr" / "0000-template.md").is_file())
        self.assertTrue((self.root / "docs" / "adr" / "README.md").is_file())
        self.assertTrue((self.root / "docs" / "comment-debt.md").is_file())

    def test_bootstrap_does_not_overwrite_existing_files(self) -> None:
        docs = self.root / "docs"
        docs.mkdir()
        baseline = docs / "comment-budget.json"
        baseline.write_text('{"version": 1, "comments": 999, "open_notes": 9}', encoding="utf-8")
        debt = docs / "comment-debt.md"
        debt.write_text("my own ledger\n", encoding="utf-8")

        code, output = self.run_budget(
            "--bootstrap",
            "--template-dir",
            str(TEMPLATE_DIR),
            "--baseline",
            str(baseline),
        )

        self.assertEqual(0, code, output)
        self.assertEqual(999, json.loads(baseline.read_text())["comments"])
        self.assertEqual("my own ledger\n", debt.read_text())

    def test_bootstrap_is_idempotent(self) -> None:
        args = (
            "--bootstrap",
            "--template-dir",
            str(TEMPLATE_DIR),
            "--baseline",
            str(self.root / "docs" / "comment-budget.json"),
        )
        self.run_budget(*args)

        code, output = self.run_budget(*args)

        self.assertEqual(0, code, output)
        self.assertIn("already", output)

    def test_bootstrap_is_not_implied_by_update(self) -> None:
        code, output = self.run_budget(
            "--update", "--baseline", str(self.root / "docs" / "comment-budget.json")
        )

        self.assertEqual(1, code)
        self.assertIn("refusing to create or reset one", output)
        self.assertIn("create one with --bootstrap", output)
        self.assertFalse((self.root / "docs" / "comment-budget.json").exists())

    def test_update_with_force_does_not_reset_a_missing_or_corrupt_baseline(self) -> None:
        baseline = self.root / "docs" / "comment-budget.json"
        baseline.parent.mkdir(parents=True)

        missing_code, _ = self.run_budget(
            "--update", "--force", "--baseline", str(baseline)
        )
        self.assertEqual(1, missing_code)
        self.assertFalse(baseline.exists())

        baseline.write_text("{not json", encoding="utf-8")
        before = baseline.read_bytes()
        corrupt_code, _ = self.run_budget(
            "--update", "--force", "--baseline", str(baseline)
        )
        self.assertEqual(1, corrupt_code)
        self.assertEqual(before, baseline.read_bytes())

    def test_bootstrap_passes_immediately_after_creating_baseline(self) -> None:
        baseline = self.root / "docs" / "comment-budget.json"
        self.run_budget(
            "--bootstrap", "--template-dir", str(TEMPLATE_DIR), "--baseline", str(baseline)
        )

        code, output = self.run_budget("--baseline", str(baseline))

        self.assertEqual(0, code, output)

    def test_a_bare_baseline_path_writes_beside_the_resolved_baseline(self) -> None:
        baseline = self.root / "docs" / "comment-budget.json"
        baseline.parent.mkdir(parents=True)
        stdout = io.StringIO()
        previous = Path.cwd()
        try:
            os.chdir(self.root)
            with contextlib.redirect_stdout(stdout):
                code = self.budget.main(
                    [
                        "--bootstrap",
                        "--template-dir",
                        str(TEMPLATE_DIR),
                        "--baseline",
                        "docs/comment-budget.json",
                        str(self.root),
                    ]
                )
        finally:
            os.chdir(previous)

        self.assertEqual(0, code, stdout.getvalue())
        self.assertTrue((self.root / "docs" / "adr" / "0000-template.md").is_file())

    def test_bootstrap_refuses_a_missing_template_dir(self) -> None:
        code, output = self.run_budget(
            "--bootstrap",
            "--template-dir",
            str(self.root / "absent"),
            "--baseline",
            str(self.root / "docs" / "comment-budget.json"),
        )

        self.assertEqual(2, code)
        self.assertIn("template", output.lower())

    def test_bootstrap_refuses_a_corrupt_baseline_instead_of_resetting_it(self) -> None:
        baseline = self.root / "docs" / "comment-budget.json"
        baseline.parent.mkdir(parents=True)
        baseline.write_text("{not json", encoding="utf-8")
        before = baseline.read_bytes()

        code, output = self.run_budget(
            "--bootstrap", "--template-dir", str(TEMPLATE_DIR), "--baseline", str(baseline)
        )

        self.assertEqual(2, code)
        self.assertEqual(before, baseline.read_bytes())


if __name__ == "__main__":
    unittest.main()
