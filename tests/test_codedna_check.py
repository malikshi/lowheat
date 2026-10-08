"""test_codedna_check.py — Tests for the CodeDNA L1 header drift checker.

exports: class CodednaCheckTestCase
used_by: none
rules:   Load the checker by file path — the skill directory name is not a Python package.
agent:   grok-build-plan | 9router | 2026-10-08 | 01a11c14-e6f9-7581-9248-a9b2f058a3e8 | added checker tests
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import shutil
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

CHECKER_PATH = (
    Path(__file__).resolve().parents[1]
    / ".agents"
    / "skills"
    / "agents-contract"
    / "scripts"
    / "codedna_check.py"
)

CLEAN_MODULE = textwrap.dedent(
    '''\
    """sample.py — Example module used by the checker tests.

    exports: helper
    used_by: none
    rules:   none
    agent:   test-agent | 9router | 2026-10-08 | s_test | added sample
    """


    def helper() -> int:
        return 1
    '''
)


def load_checker():
    """Load the checker module from its file path.

    Rules:   The `agents-contract` directory name holds a dash, so the module needs importlib.
    """
    spec = importlib.util.spec_from_file_location("codedna_check", CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["codedna_check"] = module
    spec.loader.exec_module(module)
    return module


class CodednaCheckTestCase(unittest.TestCase):
    """Exercise the checker against temporary source trees."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.checker = load_checker()

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="codedna-check-"))
        self.addCleanup(shutil.rmtree, self.root)

    def write(self, relative: str, text: str) -> Path:
        """Write one source file under the temporary root."""
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def findings_for(self, text: str) -> list[str]:
        """Return the checker findings for a single sample module."""
        path = self.write("src/sample.py", text)
        return self.checker.check_file(path, self.root)

    def run_main(self) -> int:
        """Run the checker over the temporary root with output captured."""
        with contextlib.redirect_stdout(io.StringIO()):
            return self.checker.main(["--root", str(self.root), str(self.root)])

    def test_clean_module_reports_no_findings(self) -> None:
        self.assertEqual([], self.findings_for(CLEAN_MODULE))

    def test_missing_l1_field_is_reported(self) -> None:
        findings = self.findings_for(CLEAN_MODULE.replace("rules:   none\n", ""))
        self.assertTrue(any("rules" in finding for finding in findings), findings)

    def test_stale_used_by_target_is_reported(self) -> None:
        text = CLEAN_MODULE.replace("used_by: none", "used_by: src/gone.py → helper")
        findings = self.findings_for(text)
        self.assertTrue(any("src/gone.py" in finding for finding in findings), findings)

    def test_export_absent_from_the_body_is_reported(self) -> None:
        text = CLEAN_MODULE.replace("exports: helper", "exports: helper | vanished")
        findings = self.findings_for(text)
        self.assertTrue(any("vanished" in finding for finding in findings), findings)

    def test_agent_history_over_five_entries_is_reported(self) -> None:
        entries = "\n".join(
            f"agent:   test-agent | 9router | 2026-10-0{index} | s{index} | change {index}"
            for index in range(1, 7)
        )
        current = "agent:   test-agent | 9router | 2026-10-08 | s_test | added sample"
        findings = self.findings_for(CLEAN_MODULE.replace(current, entries))
        self.assertTrue(any("agent" in finding for finding in findings), findings)

    def test_collect_source_files_skips_ignored_directories(self) -> None:
        self.write("src/sample.py", CLEAN_MODULE)
        self.write("node_modules/pkg/index.js", "// placeholder\n")
        found = {path.name for path in self.checker.collect_source_files([self.root])}
        self.assertEqual({"sample.py"}, found)

    def test_comment_header_language_is_checked(self) -> None:
        module = textwrap.dedent(
            """\
            // sample.go — Example module used by the checker tests.
            //
            // exports: helper
            // used_by: none
            // rules:   none
            // agent:   test-agent | 9router | 2026-10-08 | s_test | added sample

            package sample

            func helper() int { return 1 }
            """
        )
        path = self.write("src/sample.go", module)
        self.assertEqual([], self.checker.check_file(path, self.root))

    def test_missing_header_is_reported(self) -> None:
        path = self.write("src/sample.go", "package sample\n\nfunc helper() int { return 1 }\n")
        self.assertEqual(["missing L1 header"], self.checker.check_file(path, self.root))

    def test_first_line_without_a_description_is_reported(self) -> None:
        text = CLEAN_MODULE.replace(
            "sample.py — Example module used by the checker tests.", "sample.py"
        )
        findings = self.findings_for(text)
        self.assertTrue(any("description" in finding for finding in findings), findings)

    def test_contract_examples_break_no_rule(self) -> None:
        contract = Path(__file__).resolve().parents[1] / "AGENTS.md"
        text = contract.read_text(encoding="utf-8")
        self.assertEqual([], self.checker.check_examples(text, "AGENTS.md"))

    def test_comment_outside_the_permitted_content_is_reported(self) -> None:
        findings = self.checker.check_examples("```python\n# just a note\nvalue = 1\n```\n", "AGENTS.md")
        self.assertTrue(any("comment is outside" in finding for finding in findings), findings)

    def test_field_not_permitted_at_this_scope_is_reported(self) -> None:
        block = 'def charge() -> None:\n    """Charge a card.\n\n    exports: helper\n    """\n'
        findings = self.checker.check_examples(f"```python\n{block}```\n", "AGENTS.md")
        self.assertEqual(1, len(findings))
        self.assertIn("is not permitted here", findings[0])

    def test_prose_after_the_rules_block_is_reported(self) -> None:
        block = (
            'def charge() -> None:\n'
            '    """Charge a card.\n\n'
            "    Rules:   amounts arrive in cents.\n\n"
            "    Extra prose that restates the code.\n"
            '    """\n'
        )
        findings = self.checker.check_examples(f"```python\n{block}```\n", "AGENTS.md")
        self.assertEqual(1, len(findings))
        self.assertIn("Extra prose", findings[0])

    def test_summary_line_over_the_word_cap_is_reported(self) -> None:
        long_summary = " ".join(f"word{index}" for index in range(16))
        block = f'def charge() -> None:\n    """{long_summary}.\n\n    Rules:   amounts arrive in cents.\n    """\n'
        findings = self.checker.check_examples(f"```python\n{block}```\n", "AGENTS.md")
        self.assertEqual(1, len(findings))
        self.assertIn("cap is 15", findings[0])

    def test_main_fails_on_a_contract_example_that_breaks_the_rules(self) -> None:
        self.write("AGENTS.md", "```python\n# not permitted\n```\n")
        with_violation = self.run_main()
        self.write("AGENTS.md", "```python\n# Rules: keep the exit code honest\n```\n")
        without_violation = self.run_main()
        self.assertEqual((1, 0), (with_violation, without_violation))

    def test_main_returns_one_when_findings_exist_and_zero_when_clean(self) -> None:
        self.write("src/sample.py", CLEAN_MODULE.replace("rules:   none\n", ""))
        with_findings = self.run_main()
        self.write("src/sample.py", CLEAN_MODULE)
        without_findings = self.run_main()
        self.assertEqual((1, 0), (with_findings, without_findings))


if __name__ == "__main__":
    unittest.main()
