"""test_comment_budget.py — Tests for the comment-budget ratchet.

exports: class CommentBudgetTestCase
used_by: none
rules:   Load the script by file path — the skill directory name is not a Python package. Every case runs against a temporary tree so the checked-in baseline is never measured or rewritten by a test.
agent:   unknown | nexrouter | 2026-11-21 | unknown | added ratchet coverage: exemptions, over-budget exit, update refusal, and bad paths
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
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

CLEAN_MODULE = '''"""sample.py — Example module used by the budget tests.

exports: helper
used_by: none
rules:   none
agent:   test-agent | 9router | 2026-11-21 | s_test | added sample
"""


def helper() -> int:
    """Return one row.

    Rules:   ids come back sorted.
    """
    return 1
'''


def load_budget():
    """Load the budget script from its file path.

    Rules:   The `agents-contract` directory name holds a dash, so the module needs importlib.
    """
    spec = importlib.util.spec_from_file_location("comment_budget", BUDGET_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["comment_budget"] = module
    spec.loader.exec_module(module)
    return module


class CommentBudgetTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.budget = load_budget()
        self.root = Path(tempfile.mkdtemp(prefix="comment-budget-"))
        self.addCleanup(shutil.rmtree, self.root, True)

    def write(self, relative: str, text: str) -> Path:
        """Write one source file under the temporary root."""
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def run_main(self, *args: str) -> int:
        """Run the budget CLI with output captured."""
        with contextlib.redirect_stdout(io.StringIO()):
            return self.budget.main([*args, str(self.root)])

    def baseline(self, comments: int, open_notes: int = 0) -> Path:
        """Write a baseline file and return its path."""
        path = self.root / "budget.json"
        path.write_text(
            json.dumps({"version": 1, "comments": comments, "open_notes": open_notes}),
            encoding="utf-8",
        )
        return path

    def test_clean_module_counts_annotations_and_skips_code(self) -> None:
        self.write("src/sample.py", CLEAN_MODULE)

        counts = self.budget.count_comments([self.root])

        self.assertEqual(
            {
                "comments": 7,
                "open_notes": 0,
            },
            counts,
        )

    def test_shebang_and_directive_bodies_are_not_debt(self) -> None:
        self.write(
            "deploy/sample.sh",
            "#!/usr/bin/env bash\n# shellcheck disable=SC2086\nset -euo pipefail\n",
        )

        self.assertEqual({"comments": 0, "open_notes": 0}, self.budget.count_comments([self.root]))

    def test_heredoc_body_lines_are_not_debt(self) -> None:
        self.write(
            "deploy/gen.sh",
            "#!/usr/bin/env bash\ncat <<EOF > out.conf\n# managed by the installer\nEOF\n",
        )

        self.assertEqual({"comments": 0, "open_notes": 0}, self.budget.count_comments([self.root]))

    def test_message_lines_are_counted_as_open_notes(self) -> None:
        self.write(
            "src/sample.py", CLEAN_MODULE.replace("agent:", "message: waiting on #412\nagent:")
        )

        counts = self.budget.count_comments([self.root])

        self.assertEqual(8, counts["comments"])
        self.assertEqual(1, counts["open_notes"])

    def test_quiet_run_passes_when_the_tree_matches_the_baseline(self) -> None:
        self.write("src/sample.py", CLEAN_MODULE)

        self.assertEqual(0, self.run_main("--baseline", str(self.baseline(7)), "--quiet"))

    def test_growth_over_the_baseline_exits_one(self) -> None:
        self.write("src/sample.py", CLEAN_MODULE)

        self.assertEqual(1, self.run_main("--baseline", str(self.baseline(6))))

    def test_update_lowers_the_baseline(self) -> None:
        self.write("src/sample.py", CLEAN_MODULE)
        path = self.baseline(99)

        self.assertEqual(0, self.run_main("--baseline", str(path), "--update"))
        self.assertEqual(7, json.loads(path.read_text(encoding="utf-8"))["comments"])

    def test_update_refuses_to_raise_a_number(self) -> None:
        self.write("src/sample.py", CLEAN_MODULE)
        path = self.baseline(1)

        self.assertEqual(1, self.run_main("--baseline", str(path), "--update"))

        self.assertEqual(1, json.loads(path.read_text(encoding="utf-8"))["comments"])

    def test_update_refuses_a_corrupt_baseline_instead_of_resetting_it(self) -> None:
        self.write("src/sample.py", CLEAN_MODULE)
        path = self.root / "corrupt.json"
        path.write_text('{"comments": "garbage", "open_notes": 999}', encoding="utf-8")
        before = path.read_bytes()

        self.assertEqual(1, self.run_main("--baseline", str(path), "--update"))

        self.assertEqual(before, path.read_bytes())

    def test_update_refuses_an_unparseable_baseline(self) -> None:
        self.write("src/sample.py", CLEAN_MODULE)
        path = self.root / "broken.json"
        path.write_text("{not json", encoding="utf-8")
        before = path.read_bytes()

        self.assertEqual(1, self.run_main("--baseline", str(path), "--update"))

        self.assertEqual(before, path.read_bytes())

    def test_update_refuses_a_missing_baseline_without_force(self) -> None:
        self.write("src/sample.py", CLEAN_MODULE)
        path = self.root / "absent.json"

        self.assertEqual(1, self.run_main("--baseline", str(path), "--update"))

        self.assertFalse(path.exists())

    def test_a_boolean_or_negative_count_is_malformed(self) -> None:
        for payload in ('{"comments": true, "open_notes": 0}', '{"comments": -1, "open_notes": 0}', '{"comments": 5}'):
            path = self.root / "odd.json"
            path.write_text(payload, encoding="utf-8")
            with self.subTest(payload=payload):
                self.assertIsNone(self.budget.load_baseline(path))

    def test_a_directory_baseline_fails_cleanly_without_a_traceback(self) -> None:
        self.write("src/sample.py", CLEAN_MODULE)

        code = self.run_main("--baseline", str(self.root), "--update")

        self.assertIn(code, (1, 2))

    def test_python_shebang_and_directive_are_not_debt(self) -> None:
        self.write(
            "src/sample.py",
            "#!/usr/bin/env python3\n# type: ignore\n# noqa: E501\n" + CLEAN_MODULE,
        )

        self.assertEqual({"comments": 7, "open_notes": 0}, self.budget.count_comments([self.root]))

    def test_against_refuses_a_baseline_that_grew(self) -> None:
        current = self.baseline(10, 1)
        previous = self.root / "previous.json"
        previous.write_text('{"comments": 5, "open_notes": 1}', encoding="utf-8")

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = self.budget.main(
                ["--baseline", str(current), "--against", str(previous)]
            )

        self.assertEqual(1, code, stdout.getvalue())
        self.assertIn("comments grew 5 -> 10", stdout.getvalue())

    def test_against_accepts_a_baseline_that_shrank_or_held(self) -> None:
        current = self.baseline(5, 1)
        previous = self.root / "previous.json"
        previous.write_text('{"comments": 10, "open_notes": 1}', encoding="utf-8")

        self.assertEqual(
            0, self.budget.main(["--baseline", str(current), "--against", str(previous)])
        )

    def test_against_needs_two_readable_baselines(self) -> None:
        current = self.baseline(5, 1)

        self.assertEqual(
            2,
            self.budget.main(
                ["--baseline", str(current), "--against", str(self.root / "gone.json")]
            ),
        )

    def test_force_allows_a_deliberate_raise(self) -> None:
        self.write("src/sample.py", CLEAN_MODULE)
        path = self.baseline(1)

        self.assertEqual(0, self.run_main("--baseline", str(path), "--update", "--force"))

        self.assertEqual(7, json.loads(path.read_text(encoding="utf-8"))["comments"])

    def test_a_missing_scanned_path_exits_two(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = self.budget.main([str(self.root / "gone")])

        self.assertEqual(2, code)
        self.assertIn("path not found", stdout.getvalue())

    def test_a_missing_baseline_exits_two(self) -> None:
        self.write("src/sample.py", CLEAN_MODULE)

        self.assertEqual(2, self.run_main("--baseline", str(self.root / "absent.json")))

    def test_a_malformed_baseline_exits_two(self) -> None:
        self.write("src/sample.py", CLEAN_MODULE)
        path = self.root / "broken.json"
        path.write_text("{not json", encoding="utf-8")

        self.assertEqual(2, self.run_main("--baseline", str(path)))

    def test_checked_in_baseline_is_readable_and_clean(self) -> None:
        repo = BUDGET_PATH.parents[4]

        counts = self.budget.count_comments([repo])
        baseline = self.budget.load_baseline(repo / "docs" / "comment-budget.json")

        self.assertIsNotNone(baseline)
        self.assertGreater(counts["comments"], 0)
        self.assertEqual([], self.budget.compare_budget(counts, baseline))

    def test_checked_in_baseline_passes_the_cli(self) -> None:
        repo = BUDGET_PATH.parents[4]
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = self.budget.main([str(repo), "--baseline", str(repo / "docs" / "comment-budget.json")])

        self.assertEqual(0, code, stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
