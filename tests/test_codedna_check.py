"""test_codedna_check.py — Tests for the CodeDNA L1 header drift checker.

exports: class CodednaCheckTestCase | class ToolDirectoryTestCase | class LanguageHeaderTestCase | class FindingLineNumbersTestCase | class CommentContentTestCase | class ShellHeredocTestCase | class HeaderShapeTestCase
used_by: none
rules:   Load the checker by file path — the skill directory name is not a Python package.
agent:   grok-build-plan | 9router | 2026-10-08 | 01a11c14-e6f9-7581-9248-a9b2f058a3e8 | added checker tests
agent:   grok-4.6 | xai | 2026-10-09 | 01a1165a-8f16-7702-b7e8-488efac69c7e | added per-language, line-number, content, and shape test classes
agent:   claude-fable-5 | anthropic | 2026-10-09 | ddf225f-review | added HTML dedupe, skip-content main(), and CSS url-string masking tests
agent:   claude-fable-5 | anthropic | 2026-10-09 | ddf225f-lowfix | added agent-shape, SPDX-exempt, and over-cap-summary regression tests
agent:   grok-build | xai | 2026-10-09 | 01a120bc-e75a-79c3-8ab4-e055948b9a83 | added tool-directory, exclude-flag, Python comment, absolute-line, and heredoc tests
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import re
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

    def test_binary_content_does_not_crash_the_scan(self) -> None:
        path = self.root / "src" / "binary.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(bytes(range(256)))
        self.assertEqual(["missing L1 header"], self.checker.check_file(path, self.root))
        self.assertEqual([], self.checker.check_comment_content(path))

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

    def test_main_reports_two_when_a_scanned_path_does_not_exist(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = self.checker.main([str(self.root / "gone")])
        self.assertEqual(2, exit_code, stdout.getvalue())
        self.assertIn("path not found", stdout.getvalue(), stdout.getvalue())


GO_CLEAN = textwrap.dedent(
    """\
    // sample.go — Example Go module used by the checker tests.
    //
    // exports: helper
    // used_by: none
    // rules:   none
    // agent:   test-agent | 9router | 2026-10-08 | s_test | added sample

    package sample

    func helper() int { return 1 }
    """
)

TS_CLEAN = textwrap.dedent(
    """\
    // sample.ts — Example TypeScript module used by the checker tests.
    //
    // exports: helper
    // used_by: none
    // rules:   none
    // agent:   test-agent | 9router | 2026-10-08 | s_test | added sample

    export function helper(): number { return 1; }
    """
)

RS_CLEAN = textwrap.dedent(
    """\
    // sample.rs — Example Rust module used by the checker tests.
    //
    // exports: helper
    // used_by: none
    // rules:   none
    // agent:   test-agent | 9router | 2026-10-08 | s_test | added sample

    pub fn helper() -> i32 { 1 }
    """
)

SH_CLEAN = textwrap.dedent(
    """\
    #!/usr/bin/env bash
    # sample.sh — Example shell script used by the checker tests.
    #
    # exports: none
    # used_by: none
    # rules:   none
    # agent:   test-agent | 9router | 2026-10-08 | s_test | added sample

    set -euo pipefail
    helper() { echo ok; }
    """
)

HTML_CLEAN = textwrap.dedent(
    """\
    <!-- sample.html — Example markup file used by the checker tests.
         exports: none
         used_by: none
         rules:   none
         agent:   test-agent | 9router | 2026-10-08 | s_test | added sample
    -->
    <!DOCTYPE html>
    <html><head><title>sample</title></head><body></body></html>
    """
)

CSS_CLEAN = textwrap.dedent(
    """\
    /* sample.css — Example stylesheet used by the checker tests.

       exports: none
       used_by: none
       rules:   none
       agent:   test-agent | 9router | 2026-10-08 | s_test | added sample
    */
    body { margin: 0; }
    """
)

PY_CLEAN = textwrap.dedent(
    '''\
    """sample.py — Example Python module used by the checker tests.

    exports: helper
    used_by: none
    rules:   none
    agent:   test-agent | 9router | 2026-10-08 | s_test | added sample
    """

    def helper() -> int:
        return 1
    '''
)

JS_CLEAN = textwrap.dedent(
    """\
    // sample.js — Example JavaScript module used by the checker tests.
    //
    // exports: helper
    // used_by: none
    // rules:   none
    // agent:   test-agent | 9router | 2026-10-08 | s_test | added sample

    function helper() { return 1; }
    module.exports = { helper };
    """
)


class ToolDirectoryTestCase(CodednaCheckTestCase):
    """Tool-owned directories are skipped — agents and editors do not own project source."""

    def test_collect_source_files_skips_tool_directories(self) -> None:
        self.write("src/sample.py", CLEAN_MODULE)
        for name in (".claude", ".codex", ".commandcode", ".cursor", ".gemini", ".grok"):
            self.write(f"{name}/cache/tool.py", "import os\n")
        found = {path.name for path in self.checker.collect_source_files([self.root])}
        self.assertEqual({"sample.py"}, found)

    def test_main_is_clean_when_only_tool_directories_hold_source(self) -> None:
        self.write(".claude/plugins/hooks/hook.py", "import os\n\n# warms the cache\n")
        self.write(".codex/sessions/loader.js", "// session loader for the runtime\n")
        self.assertEqual(0, self.run_main())

    def test_exclude_flag_skips_an_extra_directory_name(self) -> None:
        self.write("src/sample.py", CLEAN_MODULE)
        self.write("third_party_agent/tool.py", "import os\n")
        without_exclude = self.run_main()
        with contextlib.redirect_stdout(io.StringIO()):
            with_exclude = self.checker.main(
                ["--exclude", "third_party_agent", "--root", str(self.root), str(self.root)]
            )
        self.assertEqual((1, 0), (without_exclude, with_exclude))

    def test_directory_whose_name_merely_starts_like_a_skip_name_is_scanned(self) -> None:
        self.write("src/sample.py", CLEAN_MODULE)
        self.write(".claudex/tool.py", "import os\n")
        found = {str(path.relative_to(self.root)) for path in self.checker.collect_source_files([self.root])}
        self.assertEqual({"src/sample.py", ".claudex/tool.py"}, found)

    def test_skip_names_match_relative_to_the_scanned_root(self) -> None:
        nested = self.root / ".cursor" / "proj"
        nested.mkdir(parents=True)
        self.write(".cursor/proj/src/sample.py", CLEAN_MODULE)
        found = {path.name for path in self.checker.collect_source_files([nested])}
        self.assertEqual({"sample.py"}, found)

    def test_explicit_file_argument_inside_a_tool_directory_is_scanned(self) -> None:
        path = self.write(".grok/cache/tool.py", "import os\n")
        self.assertEqual(["missing L1 header"], self.checker.check_file(path, self.root))

    def test_tool_directory_names_are_declared(self) -> None:
        declared = self.checker.TOOL_OWNED_DIRS
        self.assertTrue({".claude", ".codex", ".commandcode"} <= declared, declared)
        self.assertTrue(declared <= self.checker.DEFAULT_IGNORED_DIRS, declared)


class ShellHeredocTestCase(CodednaCheckTestCase):
    """Heredoc bodies are data — skip them without silencing the comments around them."""

    def findings_after(self, inserted: str) -> list[str]:
        """Return content findings for a script with `inserted` placed after the prologue."""
        body = SH_CLEAN.replace("set -euo pipefail", "set -euo pipefail\n" + inserted)
        path = self.write("deploy/sample.sh", body)
        return self.checker.check_comment_content(path)

    def test_quoted_and_plain_heredoc_bodies_are_skipped(self) -> None:
        findings = self.findings_after(
            "cat <<'EOF' > generated.conf\n# managed by the installer\nkey = value\nEOF\n"
            "cat <<-END > other.conf\n\t# indented body line\n\tEND\n"
        )
        self.assertEqual([], findings)

    def test_escaped_delimiter_body_is_skipped(self) -> None:
        findings = self.findings_after(
            "cat <<\\EOF > generated.conf\n# managed by the installer\nEOF\n"
        )
        self.assertEqual([], findings)

    def test_two_heredocs_on_one_line_are_skipped_in_order(self) -> None:
        findings = self.findings_after(
            "cat <<A <<B > out.conf\n# body of A\nA\n# body of B\nB\n"
        )
        self.assertEqual([], findings)

    def test_comment_after_the_terminator_is_still_reported(self) -> None:
        findings = self.findings_after(
            "cat <<EOF > generated.conf\n# managed by the installer\nEOF\n# helper keeps the ledger warm\n"
        )
        self.assertEqual(1, len(findings), findings)
        self.assertIn("outside the permitted content", findings[0])

    def test_space_indented_line_does_not_close_a_plain_heredoc(self) -> None:
        findings = self.findings_after(
            "cat <<EOF > generated.conf\nkey = value\n  EOF\n# still inside the body\nEOF\n"
        )
        self.assertEqual([], findings)

    def test_trailing_blank_does_not_close_a_plain_heredoc(self) -> None:
        findings = self.findings_after(
            "cat <<EOF > generated.conf\nkey = value\nEOF \n# still inside the body\nEOF\n"
        )
        self.assertEqual([], findings)

    def test_trailing_blank_does_not_close_a_tab_stripped_heredoc(self) -> None:
        findings = self.findings_after(
            "cat <<-END > generated.conf\n\t# indented body line\n\tEND \n# still inside the body\n\tEND\n"
        )
        self.assertEqual([], findings)

    def test_unterminated_heredoc_silences_nothing(self) -> None:
        findings = self.findings_after("cat <<EOF > generated.conf\n# helper keeps the ledger warm\n")
        self.assertEqual(1, len(findings), findings)

    def test_arithmetic_shift_is_not_a_heredoc(self) -> None:
        findings = self.findings_after("mask=$((1 << bits))\n# helper keeps the ledger warm\n")
        self.assertEqual(1, len(findings), findings)

    def test_herestring_is_not_a_heredoc(self) -> None:
        findings = self.findings_after("cat <<< hello > /dev/null\n# helper keeps the ledger warm\n")
        self.assertEqual(1, len(findings), findings)

    def test_heredoc_marker_inside_a_quoted_string_is_not_a_heredoc(self) -> None:
        findings = self.findings_after(
            'echo "pass <<EOF when done"\n# helper keeps the ledger warm\nEOF\n'
        )
        self.assertEqual(1, len(findings), findings)


class LanguageHeaderTestCase(CodednaCheckTestCase):
    """Per-language header checks — every scanned suffix must score clean."""

    def check_clean(self, relative: str, text: str) -> list[str]:
        path = self.write(relative, text)
        return self.checker.check_file(path, self.root)

    def test_go_header_is_clean(self) -> None:
        self.assertEqual([], self.check_clean("src/sample.go", GO_CLEAN))

    def test_python_header_is_clean(self) -> None:
        self.assertEqual([], self.check_clean("src/sample.py", PY_CLEAN))

    def test_typescript_header_is_clean(self) -> None:
        self.assertEqual([], self.check_clean("src/sample.ts", TS_CLEAN))

    def test_rust_header_is_clean(self) -> None:
        self.assertEqual([], self.check_clean("src/sample.rs", RS_CLEAN))

    def test_shell_header_with_shebang_is_clean(self) -> None:
        self.assertEqual([], self.check_clean("deploy/sample.sh", SH_CLEAN))

    def test_bash_suffix_header_is_clean(self) -> None:
        self.assertEqual([], self.check_clean("deploy/sample.bash", SH_CLEAN.replace("sample.sh", "sample.bash")))

    def test_zsh_header_is_clean(self) -> None:
        self.assertEqual([], self.check_clean("deploy/sample.zsh", SH_CLEAN.replace("sample.sh", "sample.zsh").replace("env bash", "env zsh")))

    def test_html_header_is_clean(self) -> None:
        self.assertEqual([], self.check_clean("web/sample.html", HTML_CLEAN))

    def test_css_header_is_clean(self) -> None:
        self.assertEqual([], self.check_clean("web/sample.css", CSS_CLEAN))

    def test_javascript_header_is_clean(self) -> None:
        self.assertEqual([], self.check_clean("web/sample.js", JS_CLEAN))

    def test_shebang_line_is_not_the_header_title_line(self) -> None:
        findings = self.check_clean("deploy/sample.sh", SH_CLEAN)
        self.assertFalse(any("description form" in finding for finding in findings), findings)

    def test_html_header_first_line_must_carry_the_em_dash(self) -> None:
        broken = HTML_CLEAN.replace("sample.html — Example", "sample.html Example")
        findings = self.check_clean("web/sample.html", broken)
        self.assertTrue(any("description form" in finding for finding in findings), findings)

    def test_css_header_first_line_must_carry_the_em_dash(self) -> None:
        broken = CSS_CLEAN.replace("sample.css — Example", "sample.css Example")
        findings = self.check_clean("web/sample.css", broken)
        self.assertTrue(any("description form" in finding for finding in findings), findings)

    def test_missing_header_is_reported_for_every_language(self) -> None:
        bodies = {
            "src/sample.go": "package sample\n\nfunc helper() int { return 1 }\n",
            "web/sample.js": "function helper() { return 1; }\n",
            "web/sample.ts": "export function helper(): number { return 1; }\n",
            "src/sample.rs": "pub fn helper() -> i32 { 1 }\n",
            "web/sample.html": "<!DOCTYPE html><html><body></body></html>\n",
            "web/sample.css": "body { margin: 0; }\n",
        }
        for relative, body in bodies.items():
            findings = self.check_clean(relative, body)
            self.assertEqual(["missing L1 header"], findings, relative)

    def test_shebang_only_file_reports_the_missing_header(self) -> None:
        path = self.write("deploy/legacy.sh", "#!/usr/bin/env bash\necho hi\n")
        self.assertEqual(["missing L1 header"], self.checker.check_file(path, self.root))


class FindingLineNumbersTestCase(CodednaCheckTestCase):
    """Every finding carries the header line number the fix belongs to."""

    def test_missing_field_finding_carries_a_line_number(self) -> None:
        path = self.write("src/sample.go", GO_CLEAN.replace("// rules:   none\n", ""))
        findings = self.checker.check_file(path, self.root)
        numbered = [finding for finding in findings if re.match(r"^\d+:", finding)]
        self.assertEqual(findings, numbered)
        self.assertTrue(all(finding.split(":", 1)[0].isdigit() for finding in findings), findings)

    def test_absent_export_finding_carries_the_field_label_line(self) -> None:
        path = self.write("src/sample.go", GO_CLEAN.replace("exports: helper", "exports: vanished"))
        findings = self.checker.check_file(path, self.root)
        self.assertTrue(any("vanished" in finding for finding in findings), findings)
        labeled = [finding for finding in findings if "vanished" in finding][0]
        self.assertRegex(labeled, r"^\d+: ")

    def test_stale_used_by_finding_carries_the_field_label_line(self) -> None:
        body = GO_CLEAN.replace("// used_by: none", "// used_by: src/gone.go → helper")
        path = self.write("src/sample.go", body)
        self.write("src/helper_present.go", "")
        findings = self.checker.check_file(path, self.root)
        labeled = [finding for finding in findings if "src/gone.go" in finding][0]
        self.assertRegex(labeled, r"^\d+: ")

    def test_first_line_finding_carries_line_one(self) -> None:
        body = GO_CLEAN.replace("sample.go — Example Go module", "sample.go Example Go module")
        path = self.write("src/sample.go", body)
        findings = self.checker.check_file(path, self.root)
        self.assertTrue(any(finding.startswith("1: ") for finding in findings), findings)

    def test_python_field_finding_lines_are_absolute_below_a_shebang(self) -> None:
        body = "#!/usr/bin/env python3\n" + PY_CLEAN.replace("exports: helper", "exports: vanished")
        path = self.write("src/sample.py", body)
        findings = self.checker.check_file(path, self.root)
        matching = [finding for finding in findings if "vanished" in finding]
        self.assertEqual(1, len(matching), findings)
        self.assertTrue(matching[0].startswith("4: "), matching)


class CommentContentTestCase(CodednaCheckTestCase):
    """Comments outside permitted content are reported, per language dialect."""

    def test_go_body_prose_is_reported(self) -> None:
        body = GO_CLEAN.replace(
            "func helper() int { return 1 }",
            "func helper() int {\n\t// warms the ledger cache first.\n\treturn 1\n}",
        )
        path = self.write("src/sample.go", body)
        findings = self.checker.check_comment_content(path)
        self.assertEqual(1, len(findings), findings)
        self.assertIn("outside the permitted content", findings[0])

    def test_go_directives_are_exempt(self) -> None:
        body = GO_CLEAN.replace(
            "package sample",
            "package sample\n\n//go:generate stringer -type Kind\n//nolint:gocyclo\n",
        )
        path = self.write("src/sample.go", body)
        self.assertEqual([], self.checker.check_comment_content(path))

    def test_go_commented_out_code_is_reported(self) -> None:
        body = GO_CLEAN.replace("func helper() int { return 1 }", "func helper() int {\n\t// return 2\n\treturn 1\n}")
        path = self.write("src/sample.go", body)
        findings = self.checker.check_comment_content(path)
        self.assertTrue(any("commented-out code" in finding for finding in findings), findings)

    def test_go_rule_lines_and_continuations_are_permitted(self) -> None:
        body = GO_CLEAN.replace(
            "package sample",
            "package sample\n\n// helper returns one row.\n//\n// Rules:   ids come back sorted.\n//           order matters for the ledger.\nfunc helper() int { return 1 }\n",
        )
        path = self.write("src/sample.go", body)
        self.assertEqual([], self.checker.check_comment_content(path))

    def test_go_verbatim_summary_line_is_permitted(self) -> None:
        body = GO_CLEAN.replace("package sample", "package sample\n\nfunc helper() int { return 1 }\n")
        path = self.write("src/sample.go", body)
        self.assertEqual([], self.checker.check_comment_content(path))

    def test_python_inline_rules_comment_is_permitted(self) -> None:
        body = PY_CLEAN.replace(
            "def helper",
            "# Rules: ids come back sorted.\ndef helper",
        )
        path = self.write("src/sample.py", body)
        self.assertEqual([], self.checker.check_comment_content(path))

    def test_python_body_prose_is_reported(self) -> None:
        body = PY_CLEAN.replace(
            "def helper() -> int:",
            "def helper() -> int:\n    \"\"\"helper returns one row.\n\n    This restates the code without a rule.\n    \"\"\"",
        )
        path = self.write("src/sample.py", body)
        findings = self.checker.check_comment_content(path)
        self.assertTrue(any("outside the permitted content" in finding for finding in findings), findings)

    def test_python_body_comment_is_reported(self) -> None:
        body = PY_CLEAN.replace("    return 1", "    # warms the ledger cache\n    return 1")
        path = self.write("src/sample.py", body)
        findings = self.checker.check_comment_content(path)
        self.assertTrue(any("outside the permitted content" in finding for finding in findings), findings)

    def test_python_commented_out_code_is_reported(self) -> None:
        body = PY_CLEAN.replace("    return 1", "    # return 2\n    return 1")
        path = self.write("src/sample.py", body)
        findings = self.checker.check_comment_content(path)
        self.assertTrue(any("commented-out code" in finding for finding in findings), findings)

    def test_python_comments_are_scanned_when_the_file_does_not_parse(self) -> None:
        body = PY_CLEAN.replace(
            "def helper() -> int:\n    return 1",
            "if True print(1)\n\n\n# warms the ledger cache",
        )
        path = self.write("src/sample.py", body)
        findings = self.checker.check_comment_content(path)
        self.assertTrue(any("outside the permitted content" in finding for finding in findings), findings)

    def test_python_hash_inside_a_string_is_not_a_comment(self) -> None:
        body = PY_CLEAN.replace(
            "def helper() -> int:\n    return 1",
            'def helper() -> int:\n    return 1\n\n\nTEMPLATE = """\n# not a comment\n"""',
        )
        path = self.write("src/sample.py", body)
        self.assertEqual([], self.checker.check_comment_content(path))

    def test_python_hash_inside_an_f_string_is_not_a_comment(self) -> None:
        body = PY_CLEAN.replace(
            "def helper() -> int:\n    return 1",
            'def helper() -> int:\n    return 1\n\n\nMESSAGE = f"""\n# not a comment {1}\n"""',
        )
        path = self.write("src/sample.py", body)
        self.assertEqual([], self.checker.check_comment_content(path))

    def test_python_tool_directives_are_exempt(self) -> None:
        body = "# -*- coding: utf-8 -*-\n" + PY_CLEAN.replace(
            "def helper", "# type: ignore[import]\n# noqa: E501\ndef helper"
        )
        path = self.write("src/sample.py", body)
        self.assertEqual([], self.checker.check_comment_content(path))
        self.assertEqual([], self.checker.check_file(path, self.root))

    def test_shell_prose_is_reported_and_shellcheck_exempt(self) -> None:
        body = SH_CLEAN.replace(
            "set -euo pipefail",
            "set -euo pipefail\n# shellcheck disable=SC2086\n# helper prepares the ledger.\n",
        )
        path = self.write("deploy/sample.sh", body)
        findings = self.checker.check_comment_content(path)
        self.assertEqual(1, len(findings), findings)
        self.assertIn("outside the permitted content", findings[0])

    def test_javascript_prose_is_reported(self) -> None:
        body = JS_CLEAN.replace(
            "function helper() { return 1; }",
            "function helper() {\n\t// warms the ledger cache first.\n\treturn 1;\n}",
        )
        path = self.write("web/sample.js", body)
        findings = self.checker.check_comment_content(path)
        self.assertTrue(any("outside the permitted content" in finding for finding in findings), findings)

    def test_javascript_urls_and_regex_are_not_comments(self) -> None:
        body = JS_CLEAN.replace(
            "function helper() { return 1; }",
            'function helper() {\n\tconst re = /a/b/c/g; const url = "http://x.test/a//b"; if (url) { return 1; } return re.test(url) ? 1 : 0;\n}',
        )
        path = self.write("web/sample.js", body)
        self.assertEqual([], self.checker.check_comment_content(path))

    def test_html_markup_comment_is_reported_and_codes_dna_meta_kept(self) -> None:
        body = HTML_CLEAN.replace(
            "<body></body>",
            "<body><!-- drafts only; do not ship --></body>",
        )
        path = self.write("web/sample.html", body)
        findings = self.checker.check_comment_content(path)
        matching = [finding for finding in findings if "outside the permitted content" in finding]
        self.assertEqual(1, len(matching), findings)
        self.assertTrue(re.match(r"\d+:", matching[0]), findings)

    def test_html_inline_comment_on_marked_up_line_reports_once(self) -> None:
        body = HTML_CLEAN.replace(
            "<body></body>",
            "<body> <!-- note prose --> </body>",
        )
        path = self.write("web/sample.html", body)
        findings = self.checker.check_comment_content(path)
        matching = [finding for finding in findings if "outside the permitted content" in finding]
        self.assertEqual(1, len(matching), findings)

    def test_skip_content_limits_run_to_header_checks(self) -> None:
        body = HTML_CLEAN.replace(
            "<body></body>",
            "<body><!-- drafts only; do not ship --></body>",
        )
        path = self.write("web/sample.html", body)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = self.checker.main([str(path), "--skip-content", "--root", str(self.root)])
        self.assertEqual(0, exit_code, stdout.getvalue())
        self.assertIn("0 finding(s)", stdout.getvalue(), stdout.getvalue())
        self.assertNotIn("outside the permitted content", stdout.getvalue(), stdout.getvalue())

    def test_css_url_string_interior_never_reads_as_comment(self) -> None:
        body = CSS_CLEAN.replace(
            "body { margin: 0; }",
            'body { background: url("https://cdn.example/a.png"); }',
        )
        path = self.write("web/sample.css", body)
        self.assertEqual([], self.checker.check_comment_content(path))

    def test_css_prose_is_reported(self) -> None:
        body = CSS_CLEAN.replace(
            "body { margin: 0; }",
            "/* legacy spacing kept for now */\nbody { margin: 0; }",
        )
        path = self.write("web/sample.css", body)
        findings = self.checker.check_comment_content(path)
        self.assertTrue(any("outside the permitted content" in finding for finding in findings), findings)

    def test_rust_prose_is_reported(self) -> None:
        body = RS_CLEAN.replace(
            "pub fn helper() -> i32 { 1 }",
            "pub fn helper() -> i32 {\n\t// warms the ledger cache.\n\t1\n}",
        )
        path = self.write("src/sample.rs", body)
        findings = self.checker.check_comment_content(path)
        self.assertTrue(any("outside the permitted content" in finding for finding in findings), findings)

    def test_rust_doc_summary_and_rules_are_permitted(self) -> None:
        body = RS_CLEAN.replace(
            "pub fn helper() -> i32 { 1 }",
            "/// helper returns one row.\n///\n/// Rules:   ids come back sorted.\npub fn helper() -> i32 { 1 }\n",
        )
        path = self.write("src/sample.rs", body)
        self.assertEqual([], self.checker.check_comment_content(path))

    def test_todo_marker_is_reported_in_go(self) -> None:
        body = GO_CLEAN.replace("func helper() int { return 1 }", "func helper() int {\n\t// TODO: drop after the ledger migration\n\treturn 1\n}")
        path = self.write("src/sample.go", body)
        findings = self.checker.check_comment_content(path)
        self.assertTrue(any("mid-stream field" not in finding for finding in findings), findings)
        self.assertTrue(any("TODO" in finding for finding in findings), findings)


class HeaderShapeTestCase(CodednaCheckTestCase):
    """Structural header drift: field order, agent-entry shape, window size."""

    def test_agent_entry_shape_is_checked(self) -> None:
        body = GO_CLEAN.replace(
            "// agent:   test-agent | 9router | 2026-10-08 | s_test | added sample",
            "// agent:   grok fixed the header",
        )
        path = self.write("src/sample.go", body)
        findings = self.checker.check_file(path, self.root)
        self.assertTrue(any("agent history entry" in finding for finding in findings), findings)

    def test_agent_loose_date_in_note_does_not_count_as_history(self) -> None:
        body = GO_CLEAN.replace(
            "// agent:   test-agent | 9router | 2026-10-08 | s_test | added sample",
            "// agent:   https://a|b and 2027-01-01 drifted",
        )
        path = self.write("src/sample.go", body)
        findings = self.checker.check_file(path, self.root)
        matching = [finding for finding in findings if "agent history entry" in finding]
        self.assertEqual(1, len(matching), findings)

    def test_agent_loose_date_reports_once_after_shaped_entries(self) -> None:
        body = GO_CLEAN.replace(
            "// agent:   test-agent | 9router | 2026-10-08 | s_test | added sample",
            "// agent:   probe | 9router | 2026-10-08 | s_probe | entry one\n// agent:   https://a|b and 2027-01-01 drifted",
        )
        path = self.write("src/sample.go", body)
        findings = self.checker.check_file(path, self.root)
        matching = [finding for finding in findings if "agent history entry" in finding]
        self.assertEqual(1, len(matching), findings)

    def test_spdx_license_line_is_exempt(self) -> None:
        body = GO_CLEAN.replace(
            "package sample",
            "// SPDX-License-Identifier: MIT\n\npackage sample",
        )
        path = self.write("src/sample.go", body)
        self.assertEqual([], self.checker.check_comment_content(path))

    def test_over_long_summary_reports_word_cap_not_commented_code(self) -> None:
        # Rules: drift probe for the summary category bug — 'for' in prose must not read as commented-out code.
        body = GO_CLEAN.replace(
            "func helper() int { return 1 }",
            "// helper returns one row for all of the merchants in the ledger house cache store today.\nfunc helper() int { return 1 }",
        )

        path = self.write("src/sample.go", body)
        findings = self.checker.check_comment_content(path)
        self.assertEqual(1, len(findings), findings)
        self.assertIn("summary line holds", findings[0], findings)

    def test_agent_entries_past_five_with_dates_are_reported(self) -> None:
        entries = "\n".join(
            f"// agent:   test-agent | 9router | 2026-10-0{index} | s{index} | change {index}"
            for index in range(1, 7)
        )
        body = GO_CLEAN.replace(
            "// agent:   test-agent | 9router | 2026-10-08 | s_test | added sample",
            entries,
        )
        path = self.write("src/sample.go", body)
        findings = self.checker.check_file(path, self.root)
        self.assertTrue(any("agent history" in finding for finding in findings), findings)

    def test_large_headers_are_fully_scanned(self) -> None:
        filler = "\n".join(
            f"// agent:   test-agent | 9router | 2026-10-{index:02d} | s{index} | change {index}"
            for index in range(1, 7)
        )
        body = GO_CLEAN.replace(
            "// agent:   test-agent | 9router | 2026-10-08 | s_test | added sample",
            filler,
        )
        path = self.write("src/sample.go", body)
        findings = self.checker.check_file(path, self.root)
        self.assertTrue(any("agent history holds 6 entries" in finding for finding in findings), findings)

    def test_field_order_drift_is_reported(self) -> None:
        body = GO_CLEAN.replace(
            "// used_by: none\n// rules:   none",
            "// rules:   none\n// used_by: none",
        )
        path = self.write("src/sample.go", body)
        findings = self.checker.check_file(path, self.root)
        self.assertTrue(any("field order" in finding for finding in findings), findings)

    def test_unindented_rules_value_line_is_still_a_field_continuation(self) -> None:
        body = GO_CLEAN.replace(
            "// rules:   none",
            "// rules:   ids come back sorted.\n// order matters for the ledger.",
        )
        path = self.write("src/sample.go", body)
        findings = self.checker.check_file(path, self.root)
        self.assertEqual([], findings, findings)


if __name__ == "__main__":
    unittest.main()
