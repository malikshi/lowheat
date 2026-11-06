"""test_codedna_check.py — Tests for the CodeDNA L1 header drift checker.

exports: class CodednaCheckTestCase | class ToolDirectoryTestCase | class LanguageHeaderTestCase | class FindingLineNumbersTestCase | class CommentContentTestCase | class ShellHeredocTestCase | class HeaderShapeTestCase | class MaskCodeEdgeTestCase | class EverySuffixTestCase | class DialectContentTestCase | class CliEntryPointTestCase | language_header | language_fixture | prose_body
used_by: none
rules:   Load the checker by file path — the skill directory name is not a Python package.
agent:   fx | unknown | 2026-10-31 | unknown | added regression tests for multiline block comments, trailing comments, incomplete agent entries, raw docstrings, unquoted CSS URLs, and example directives
agent:   grok-4.6 | xai | 2026-10-31 | unknown | added HTML regressions for `/*` in markup and a header closing line with an agent entry, plus shebang coverage across Python, the JS family, and shell
agent:   grok-4.6 | xai | 2026-10-31 | unknown | added the every-suffix matrix, per-family directive exemption, lookalike corpus, and a subprocess CLI determinism test
agent:   fx | unknown | 2026-11-05 | unknown | added the documented-CLI contract scan regression
agent:   fx | unknown | 2026-11-06 | unknown | added regressions for upstream exports/used_by forms: a return type is not a symbol, every `|`-joined consumer is checked, an ASCII `->` is accepted
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import re
import shutil
import subprocess
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

    def test_upstream_exports_form_names_symbols_not_return_types(self) -> None:
        text = CLEAN_MODULE.replace(
            "exports: helper", "exports: helper(flag) → int | other(flag) -> bool"
        )
        self.assertEqual([], self.findings_for(text + "\n\ndef other(flag) -> bool:\n    return True\n"))

    def test_export_arguments_are_not_read_as_symbols(self) -> None:
        text = CLEAN_MODULE.replace(
            "exports: helper", "exports: helper(left, right) → int | vanish(left, right) → int"
        )
        findings = self.findings_for(text)
        self.assertTrue(any("vanish" in finding for finding in findings), findings)
        self.assertFalse(any("left" in finding or "right" in finding for finding in findings), findings)

    def test_every_used_by_consumer_on_one_line_is_checked(self) -> None:
        self.write("src/kept.py", CLEAN_MODULE)
        text = CLEAN_MODULE.replace(
            "used_by: none", "used_by: src/kept.py → helper | src/gone.py → helper"
        )
        findings = self.findings_for(text)
        self.assertTrue(any("src/gone.py" in finding for finding in findings), findings)

    def test_ascii_arrow_in_used_by_is_accepted(self) -> None:
        self.write("src/kept.py", CLEAN_MODULE)
        text = CLEAN_MODULE.replace("used_by: none", "used_by: src/kept.py -> helper")
        self.assertEqual([], self.findings_for(text))

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
        contract = Path(__file__).resolve().parents[1] / "contract" / "AGENTS.md"
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

    def test_backslash_before_the_marker_keeps_the_heredoc_opener(self) -> None:
        findings = self.findings_after("echo a\\ <<EOF > out.conf\n# body line\nEOF\n")
        self.assertEqual([], findings)

    def test_closed_quote_before_the_marker_keeps_the_heredoc_opener(self) -> None:
        findings = self.findings_after('echo "pass" <<EOF > out.conf\n# body line\nEOF\n')
        self.assertEqual([], findings)

    def test_escaped_quote_before_the_marker_keeps_the_heredoc_opener(self) -> None:
        findings = self.findings_after('echo \\" <<EOF > out.conf\n# body line\nEOF\n')
        self.assertEqual([], findings)


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

    def test_shebang_is_skipped_for_every_executable_dialect(self) -> None:
        cases = {
            "src/sample.py": PY_CLEAN,
            "web/sample.js": JS_CLEAN,
            "web/sample.mjs": JS_CLEAN,
            "web/sample.cjs": JS_CLEAN,
            "web/sample.jsx": JS_CLEAN,
            "web/sample.ts": TS_CLEAN,
            "web/sample.tsx": TS_CLEAN,
            "deploy/sample.sh": SH_CLEAN,
            "deploy/sample.bash": SH_CLEAN,
            "deploy/sample.zsh": SH_CLEAN,
        }
        for relative, fixture in cases.items():
            name = Path(relative).name
            body = fixture.replace("sample." + Path(relative).suffix[1:], name)
            if not body.startswith("#!"):
                body = "#!/usr/bin/env test-runner\n" + body
            with self.subTest(relative=relative):
                path = self.write(relative, body)
                self.assertEqual([], self.checker.check_file(path, self.root))
                self.assertEqual([], self.checker.check_comment_content(path))

    def test_shebang_only_javascript_file_reports_the_missing_header(self) -> None:
        path = self.write("web/tool.js", "#!/usr/bin/env node\n")
        self.assertEqual(["missing L1 header"], self.checker.check_file(path, self.root))

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

    def test_python_prose_above_docstring_is_reported(self) -> None:
        # Rules: `#` lines above the module docstring sit outside the header zone — they must not ride the L1 exemption.
        module = PY_CLEAN.split("def helper() -> int:")[0].rstrip() + "\nx = 1\n"
        body = "# TODO: wire the module header fields before shipping this module\n" + module
        path = self.write("src/sample.py", body)
        findings = self.checker.check_comment_content(path)
        self.assertTrue(any("TODO" in finding for finding in findings), findings)

        prose = "# gap.py — docstring lives below this stray leading line.\n" + module
        path = self.write("src/prose.py", prose)
        findings = self.checker.check_comment_content(path)
        self.assertTrue(any("outside the permitted content" in finding for finding in findings), findings)

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

    def test_python_shebang_is_exempt(self) -> None:
        body = "#!/usr/bin/env python3\n" + PY_CLEAN
        path = self.write("scripts/sample.py", body)
        self.assertEqual([], self.checker.check_comment_content(path))

    def test_python_shebang_below_line_one_is_reported(self) -> None:
        body = "#!/usr/bin/env python3\n" + PY_CLEAN.replace(
            "    return 1", "    return 1\n    #!/usr/bin/env python3"
        )
        path = self.write("scripts/sample.py", body)
        findings = self.checker.check_comment_content(path)
        self.assertEqual(1, len(findings), findings)
        self.assertIn("outside the permitted content", findings[0])

    def test_javascript_shebang_is_never_prose(self) -> None:
        path = self.write("web/sample.js", "#!/usr/bin/env node\n" + JS_CLEAN)
        self.assertEqual([], self.checker.check_comment_content(path))

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

    def test_html_markup_slash_star_is_not_a_block_comment(self) -> None:
        body = HTML_CLEAN.replace(
            "<body></body>",
            '<body><span>type a wildcard (<b>provider/*</b>)</span>\n<!-- drafts only; do not ship -->\n</body>',
        )
        path = self.write("web/sample.html", body)
        findings = self.checker.check_comment_content(path)
        matching = [finding for finding in findings if "outside the permitted content" in finding]
        self.assertEqual(1, len(matching), findings)
        self.assertTrue(matching[0].startswith("9:"), findings)

    def test_html_header_closing_line_stays_in_the_header_zone(self) -> None:
        body = HTML_CLEAN.replace(
            "         agent:   test-agent | 9router | 2026-10-08 | s_test | added sample\n    -->\n",
            "         agent:   test-agent | 9router | 2026-10-08 | s_test | added sample -->\n",
        )
        path = self.write("web/sample.html", body)
        self.assertEqual([], self.checker.check_comment_content(path))
        self.assertEqual([], self.checker.check_file(path, self.root))

    def test_css_header_closing_line_stays_in_the_header_zone(self) -> None:
        body = CSS_CLEAN.replace(
            "       agent:   test-agent | 9router | 2026-10-08 | s_test | added sample\n*/\n",
            "       agent:   test-agent | 9router | 2026-10-08 | s_test | added sample */\n",
        )
        path = self.write("web/sample.css", body)
        self.assertEqual([], self.checker.check_file(path, self.root))
        self.assertEqual([], self.checker.check_comment_content(path))

    def test_html_inline_rules_comment_is_permitted(self) -> None:
        body = HTML_CLEAN.replace(
            "<body></body>",
            "<body> <!-- Rules: keep the shell fixed --> </body>",
        )
        path = self.write("web/sample.html", body)
        self.assertEqual([], self.checker.check_comment_content(path))

    def test_css_starred_block_prose_is_reported_once(self) -> None:
        body = CSS_CLEAN.replace(
            "body { margin: 0; }",
            "/*\n * prose that must be reported\n */\nbody { margin: 0; }",
        )
        path = self.write("web/sample.css", body)
        findings = self.checker.check_comment_content(path)
        self.assertEqual(1, len(findings), findings)
        self.assertIn("outside the permitted content", findings[0])

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

    def test_multiline_block_comment_prose_is_reported(self) -> None:
        cases = {
            "src/sample.go": GO_CLEAN.replace(
                "func helper() int { return 1 }",
                "func helper() int {\n\t/*\n\t prose that must be reported\n\t*/\n\treturn 1\n}",
            ),
            "web/sample.js": JS_CLEAN.replace(
                "function helper() { return 1; }",
                "function helper() {\n  /*\n   prose that must be reported\n  */\n  return 1;\n}",
            ),
            "web/sample.css": CSS_CLEAN.replace(
                "body { margin: 0; }",
                "/*\n prose that must be reported\n*/\nbody { margin: 0; }",
            ),
            "web/sample.html": HTML_CLEAN.replace(
                "<body></body>",
                "<body>\n<!--\n prose that must be reported\n-->\n</body>",
            ),
        }
        for relative, body in cases.items():
            path = self.write(relative, body)
            findings = self.checker.check_comment_content(path)
            self.assertTrue(
                any("outside the permitted content" in finding for finding in findings),
                (relative, findings),
            )

    def test_trailing_comment_prose_is_reported(self) -> None:
        cases = {
            "src/sample.py": PY_CLEAN.replace(
                "    return 1", "    return 1  # prose that must be reported"
            ),
            "src/sample.go": GO_CLEAN.replace(
                "func helper() int { return 1 }",
                "func helper() int { return 1 } // prose that must be reported",
            ),
            "web/sample.js": JS_CLEAN.replace(
                "function helper() { return 1; }",
                "function helper() { return 1; } // prose that must be reported",
            ),
        }
        for relative, body in cases.items():
            path = self.write(relative, body)
            findings = self.checker.check_comment_content(path)
            self.assertTrue(
                any("outside the permitted content" in finding for finding in findings),
                (relative, findings),
            )

    def test_css_unquoted_url_does_not_hide_a_trailing_comment(self) -> None:
        body = CSS_CLEAN.replace(
            "body { margin: 0; }",
            "body { background: url(https://cdn.example/a.png); } /* prose that must be reported */",
        )
        path = self.write("web/sample.css", body)
        findings = self.checker.check_comment_content(path)
        self.assertTrue(any("outside the permitted content" in finding for finding in findings), findings)

    def test_shell_parameter_expansion_is_not_a_comment(self) -> None:
        body = SH_CLEAN.replace(
            "helper() { echo ok; }",
            "value=${name#prefix}\nhelper() { echo ok; }",
        )
        path = self.write("deploy/sample.sh", body)
        self.assertEqual([], self.checker.check_comment_content(path))

    def test_example_tool_directive_is_exempt(self) -> None:
        block = "# type: ignore[attr-defined]\nvalue = 1\n"
        self.assertEqual([], self.checker.check_examples(f"```python\n{block}```\n", "AGENTS.md"))

    def test_example_block_that_does_not_parse_is_reported(self) -> None:
        findings = self.checker.check_examples("```python\ndef broken(:\n```\n", "AGENTS.md")
        self.assertTrue(any("does not parse" in finding for finding in findings), findings)


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

    def test_agent_entry_missing_session_or_note_is_reported(self) -> None:
        for entry in (
            "// agent:   test-agent | 9router | 2026-10-08",
            "// agent:   test-agent | 9router | 2026-10-08 | s_test",
        ):
            body = GO_CLEAN.replace(
                "// agent:   test-agent | 9router | 2026-10-08 | s_test | added sample",
                entry,
            )
            path = self.write("src/sample.go", body)
            findings = self.checker.check_file(path, self.root)
            self.assertTrue(
                any("agent history entry" in finding for finding in findings),
                (entry, findings),
            )

    def test_raw_and_unicode_module_docstrings_are_clean(self) -> None:
        for prefix in ("r", "u"):
            body = PY_CLEAN.replace('"""sample.py', f'{prefix}"""sample.py', 1)
            path = self.write(f"src/{prefix}_sample.py", body)
            self.assertEqual([], self.checker.check_file(path, self.root), prefix)

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


class MaskCodeEdgeTestCase(CodednaCheckTestCase):
    """Masking edge branches: unterminated literals, escapes, and template expressions."""

    def test_js_template_expression_is_masked_whole(self) -> None:
        body = JS_CLEAN.replace(
            "function helper() { return 1; }",
            'const t = `a\\`b${ {"k": "// not"} }c`;\n// helper keeps the ledger warm\n',
        )
        path = self.write("web/sample.js", body)
        findings = self.checker.check_comment_content(path)
        self.assertEqual(1, len(findings), findings)

    def test_unterminated_template_expression_does_not_crash(self) -> None:
        body = JS_CLEAN.replace("function helper() { return 1; }", "const t = `a${unclosed")
        path = self.write("web/sample.js", body)
        self.assertEqual([], self.checker.check_comment_content(path))

    def test_shell_backticks_mask_without_hiding_the_next_comment(self) -> None:
        body = SH_CLEAN.replace(
            "set -euo pipefail", "set -euo pipefail\nvalue=`echo hi`\n# helper prepares the ledger.\n"
        )
        path = self.write("deploy/sample.sh", body)
        findings = self.checker.check_comment_content(path)
        self.assertEqual(1, len(findings), findings)

    def test_escaped_quote_inside_a_string_keeps_it_closed(self) -> None:
        body = JS_CLEAN.replace(
            "function helper() { return 1; }",
            'const s = "a\\"b";\n// helper keeps the ledger warm\n',
        )
        path = self.write("web/sample.js", body)
        findings = self.checker.check_comment_content(path)
        self.assertEqual(1, len(findings), findings)

    def masked(self, text: str, suffix: str) -> str:
        import codedna_masking
        import codedna_spec

        profile = codedna_spec.profile_for(Path("sample" + suffix))
        return codedna_masking.mask_code(profile, text)

    def test_mask_code_blanks_an_escaped_quote_string_whole(self) -> None:
        self.assertEqual(
            "const s = " + " " * 6 + ";\n", self.masked('const s = "a\\"b";\n', ".js")
        )

    def test_mask_code_blanks_a_template_through_its_closing_backtick(self) -> None:
        self.assertEqual(
            "const t = " + " " * 8 + ";\nvalue = 1;\n",
            self.masked("const t = `a${x}b`;\nvalue = 1;\n", ".js"),
        )

    def test_mask_code_restarts_a_template_at_a_backtick_inside_an_expression(self) -> None:
        # Rules: pin the documented brace scan — a backtick inside `${...}` restarts the literal there.
        self.assertEqual(
            "const t = " + " " * 6 + "b  \n", self.masked('const t = `a${\\`b`;\n', ".js")
        )

    def test_mask_code_leaves_html_slash_star_as_markup(self) -> None:
        self.assertEqual('a/*b\n', self.masked('a/*b\n', ".html"))

    def test_mask_code_still_blanks_css_and_javascript_block_comments(self) -> None:
        self.assertEqual("     \n", self.masked("/*x*/\n", ".css"))
        self.assertEqual("     \n", self.masked("/*x*/\n", ".js"))

    def test_python_file_that_does_not_tokenize_checks_docstrings_only(self) -> None:
        body = PY_CLEAN.replace(
            "rules:   none", "rules:   none\nmessage: probe note\nextra prose line"
        ).replace(
            "    return 1", "    return 1\n\nx = (1\n\n# helper keeps the ledger warm"
        )
        path = self.write("src/sample.py", body)
        findings = self.checker.check_comment_content(path)
        self.assertEqual(1, len(findings), findings)
        self.assertIn("outside the permitted content", findings[0])


# Rules: one row per supported suffix — marker, code line, optional file prologue. The Python row is
# separate because its L1 header lives in a docstring; every other dialect proves its comment grammar.
LANGUAGE_CASES = {
    ".py": ("#", "x = 1"),
    ".go": ("//", "package sample"),
    ".js": ("//", "const x = 1;"),
    ".jsx": ("//", "const x = 1;"),
    ".mjs": ("//", "const x = 1;"),
    ".cjs": ("//", "const x = 1;"),
    ".ts": ("//", "const x: number = 1;"),
    ".tsx": ("//", "const x: number = 1;"),
    ".rs": ("//", "fn main() {}"),
    ".sh": ("#", "echo ok"),
    ".bash": ("#", "echo ok"),
    ".zsh": ("#", "echo ok"),
    ".css": ("/*", "body { margin: 0; }"),
    ".html": ("<!--", "<p>hi</p>"),
    ".htm": ("<!--", "<p>hi</p>"),
    ".c": ("//", "int main(void) { return 0; }"),
    ".h": ("//", "int helper(void);"),
    ".cc": ("//", "int main() { return 0; }"),
    ".cpp": ("//", "int main() { return 0; }"),
    ".cxx": ("//", "int main() { return 0; }"),
    ".hpp": ("//", "int helper();"),
    ".hh": ("//", "int helper();"),
    ".hxx": ("//", "int helper();"),
    ".m": ("//", "int main(void) { return 0; }"),
    ".mm": ("//", "int main() { return 0; }"),
    ".cs": ("//", "class Sample { }"),
    ".java": ("//", "class Sample { }"),
    ".kt": ("//", "fun main() { }"),
    ".kts": ("//", "val x = 1"),
    ".scala": ("//", "object Sample { }"),
    ".sc": ("//", "object Sample { }"),
    ".groovy": ("//", "class Sample { }"),
    ".gradle": ("//", "plugins { }"),
    ".swift": ("//", "func main() { }"),
    ".rb": ("#", "def sample; 1; end"),
    ".rake": ("#", "task :sample do end"),
    ".gemspec": ("#", "Gem::Specification.new"),
    ".ru": ("#", "run lambda { |env| [200, {}, []] }"),
    ".php": ("//", "function sample() { return 1; }"),
    ".phtml": ("//", "<p>hi</p>"),
    ".pl": ("#", "my $x = 1;"),
    ".pm": ("#", "package Sample;"),
    ".lua": ("--", "local x = 1"),
    ".hs": ("--", "main = pure ()"),
    ".lhs": ("--", "main = pure ()"),
    ".ex": ("#", "defmodule Sample do end"),
    ".exs": ("#", "defmodule Sample do end"),
    ".erl": ("%", "-module(sample)."),
    ".hrl": ("%", "-define(X, 1)."),
    ".clj": (";", "(defn sample [] 1)"),
    ".cljs": (";", "(defn sample [] 1)"),
    ".cljc": (";", "(defn sample [] 1)"),
    ".dart": ("//", "void main() {}"),
    ".sql": ("--", "SELECT 1;"),
    ".ps1": ("#", 'Write-Output "ok"'),
    ".psm1": ("#", 'Write-Output "ok"'),
    ".psd1": ("#", "@{ }"),
    ".bat": ("REM", "echo ok"),
    ".cmd": ("REM", "echo ok"),
    ".vb": ("'", "Module Sample"),
    ".vbs": ("'", 'WScript.Echo "ok"'),
    ".frm": ("'", "Option Explicit"),
    ".fs": ("//", "let sample = 1"),
    ".fsi": ("//", "val sample : int"),
    ".fsx": ("//", "let sample = 1"),
    ".ml": ("(*", "let sample = 1"),
    ".mli": ("(*", "val sample : int"),
    ".r": ("#", "sample <- 1"),
    ".jl": ("#", "sample = 1"),
    ".zig": ("//", "pub fn main() void {}"),
    ".nim": ("#", "let sample = 1"),
    ".cr": ("#", "sample = 1"),
    ".d": ("//", "void main() {}"),
    ".sol": ("//", "contract Sample {}"),
    ".tf": ("#", 'variable "sample" {}'),
    ".tfvars": ("#", "sample = 1"),
    ".hcl": ("#", 'variable "sample" {}'),
    ".f": ("!", "      program sample"),
    ".for": ("!", "      program sample"),
    ".f90": ("!", "program sample"),
    ".f95": ("!", "program sample"),
    ".f03": ("!", "program sample"),
    ".f08": ("!", "program sample"),
    ".elm": ("--", "sample = 1"),
    ".vue": ("<!--", "<template><div></div></template>"),
    ".svelte": ("<!--", "<div></div>"),
    ".astro": ("<!--", "<div></div>"),
}
PHP_PROLOGUE = "<?php\n"
PROSE_BODY = "helper keeps the ledger warm."


def language_header(suffix: str, marker: str) -> str:
    """Return a well-formed L1 header in one dialect.

    Rules:   Field order follows the contract; every fixture name matches its suffix so the header title is realistic.
    """
    name = "sample" + suffix
    fields = (
        "exports: none",
        "used_by: none",
        "rules:   none",
        "agent:   test-agent | 9router | 2026-10-08 | s_test | added sample",
    )
    if marker == "(*":
        return f"(* {name} — Example module used by the checker tests.\n" + "\n".join(fields) + "\n*)\n"
    if marker == "/*":
        return f"/* {name} — Example module used by the checker tests.\n" + "\n".join(fields) + "\n*/\n"
    if marker == "<!--":
        indented = "\n".join("     " + field for field in fields)
        return f"<!-- {name} — Example module used by the checker tests.\n{indented}\n-->\n"
    lines = [f"{marker} {name} — Example module used by the checker tests.", marker]
    return "\n".join(lines + [f"{marker} {field}" for field in fields]) + "\n\n"


def language_fixture(suffix: str, marker: str, code: str, extra: str = "") -> str:
    """Return a complete fixture: optional prologue, header, code, and extra lines.

    Rules:   A `.php`/`.phtml` file must open with its `<?php` prologue for the parser to see the header.
    """
    prologue = PHP_PROLOGUE if suffix in (".php", ".phtml") else ""
    return prologue + language_header(suffix, marker) + code + "\n" + extra


def prose_body(marker: str) -> str:
    """Return one genuine prose comment in the marker's dialect.

    Rules:   Block-only dialects keep the prose inside their own block markers.
    """
    closers = {"(*": "*)", "<!--": "-->", "/*": "*/"}
    if marker in closers:
        return f"{marker} {PROSE_BODY} {closers[marker]}\n"
    return f"{marker} {PROSE_BODY}\n"


class EverySuffixTestCase(CodednaCheckTestCase):
    """Every supported suffix resolves to an explicit profile and scores clean when well formed."""

    def test_every_source_suffix_has_a_matrix_row(self) -> None:
        declared = set(self.checker.SOURCE_SUFFIXES)
        self.assertEqual(declared, set(LANGUAGE_CASES), "update LANGUAGE_CASES with SOURCE_SUFFIXES")

    def test_every_source_suffix_has_an_explicit_profile(self) -> None:
        declared = set(self.checker.SOURCE_SUFFIXES)
        self.assertEqual(declared, set(self.checker.EXPLICIT_SUFFIXES))

    def test_clean_fixture_is_clean_for_every_suffix(self) -> None:
        cases = dict(LANGUAGE_CASES)
        for suffix, (marker, code) in cases.items():
            with self.subTest(suffix=suffix):
                text = PY_CLEAN if suffix == ".py" else language_fixture(suffix, marker, code)
                path = self.write("src/sample" + suffix, text)
                self.assertEqual([], self.checker.check_file(path, self.root), suffix)
                self.assertEqual([], self.checker.check_comment_content(path), suffix)

    def test_headerless_file_is_reported_for_every_suffix(self) -> None:
        cases = dict(LANGUAGE_CASES)
        for suffix, (marker, code) in cases.items():
            with self.subTest(suffix=suffix):
                path = self.write("src/bare" + suffix, code + "\n")
                self.assertEqual(["missing L1 header"], self.checker.check_file(path, self.root), suffix)

    def test_prose_comment_is_reported_for_every_suffix(self) -> None:
        cases = dict(LANGUAGE_CASES)
        for suffix, (marker, code) in cases.items():
            with self.subTest(suffix=suffix):
                if suffix == ".py":
                    text = PY_CLEAN.replace("    return 1", f"    return 1\n\n# {PROSE_BODY}")
                else:
                    text = language_fixture(suffix, marker, code, prose_body(marker))
                path = self.write("src/prose" + suffix, text)
                findings = self.checker.check_comment_content(path)
                self.assertEqual(1, len(findings), (suffix, findings))
                self.assertIn("outside the permitted content", findings[0], suffix)
                expected_line = len(text.splitlines())
                self.assertTrue(findings[0].startswith(f"{expected_line}:"), (suffix, findings))

    def test_block_form_header_is_clean(self) -> None:
        fields = (
            "exports: none\nused_by: none\nrules:   none\n"
            "agent:   test-agent | 9router | 2026-10-08 | s_test | added sample\n"
        )
        cases = {
            ".c": "/* sample.c — Example module.\n *\n * "
            + fields.replace("\n", "\n * ").rstrip()
            + "\n */\nint main(void) { return 0; }\n",
            ".java": "/**\n * sample.java — Example module.\n *\n * "
            + fields.replace("\n", "\n * ").rstrip()
            + "\n */\nclass Sample { }\n",
            ".hs": "{- sample.hs — Example module.\n" + fields + "-}\nmain = pure ()\n",
            ".lua": "--[[ sample.lua — Example module.\n" + fields + "]]\nlocal x = 1\n",
        }
        for suffix, text in cases.items():
            with self.subTest(suffix=suffix):
                path = self.write("src/block" + suffix, text)
                self.assertEqual([], self.checker.check_file(path, self.root), suffix)
                self.assertEqual([], self.checker.check_comment_content(path), suffix)

    def test_doubled_comment_marker_header_is_clean(self) -> None:
        fields = (
            "exports: none\nused_by: none\nrules:   none\n"
            "agent:   test-agent | 9router | 2026-10-08 | s_test | added sample"
        )
        cases = {
            ".erl": "%% sample.erl — Example module.\n%%\n%% "
            + fields.replace("\n", "\n%% ")
            + "\n\n-module(sample).\n",
            ".clj": ";; sample.clj — Example module.\n;;\n;; "
            + fields.replace("\n", "\n;; ")
            + "\n\n(defn sample [] 1)\n",
        }
        for suffix, text in cases.items():
            with self.subTest(suffix=suffix):
                path = self.write("src/doubled" + suffix, text)
                self.assertEqual([], self.checker.check_file(path, self.root), suffix)
                self.assertEqual([], self.checker.check_comment_content(path), suffix)

    def test_at_prefixed_rem_header_is_clean(self) -> None:
        text = language_header(".bat", "REM").replace("REM", "@REM") + "echo ok\n"
        path = self.write("src/quiet.bat", text)
        self.assertEqual([], self.checker.check_file(path, self.root))
        self.assertEqual([], self.checker.check_comment_content(path))

    def test_uppercase_suffix_resolves_to_the_same_profile(self) -> None:
        text = language_fixture(".r", "#", "sample <- 1")
        upper = self.write("src/UPPER.R", text)
        lower = self.write("src/lower.r", text)
        self.assertEqual([], self.checker.check_file(upper, self.root))
        self.assertEqual([], self.checker.check_comment_content(upper))
        found = {path.name for path in self.checker.collect_source_files([self.root])}
        self.assertIn("UPPER.R", found)
        self.assertEqual(self.checker.check_file(lower, self.root), self.checker.check_file(upper, self.root))


FAMILY_DIRECTIVE_LINES = {
    ".c": "/* SPDX-License-Identifier: MIT */\n// clang-format off\n// NOLINT\n// Rules: keep the guard.\n",
    ".cpp": "#include <vector>\n// NOLINT\n// Rules: keep the guard.\n",
    ".m": "// NOLINT\n/* Rules: keep the guard. */\n",
    ".cs": "/// <summary>documented</summary>\n//#region helpers\n// Rules: keep the guard.\n",
    ".java": "//noinspection unchecked\n// Rules: keep the guard.\n",
    ".kt": "//noinspection unchecked\n// Rules: keep the guard.\n",
    ".scala": "// NOLINT\n// Rules: keep the guard.\n",
    ".groovy": "// NOLINT\n// Rules: keep the guard.\n",
    ".swift": "/// documented\n// Rules: keep the guard.\n",
    ".dart": "/// documented\n// Rules: keep the guard.\n",
    ".go": "//go:build linux\n//nolint\n// Rules: keep the guard.\n",
    ".rs": "/// documented\n//! module note\n#![allow(dead_code)]\n// Rules: keep the guard.\n",
    ".js": "/* eslint-disable */\n/*! bundle banner */\n// Rules: keep the guard.\n",
    ".ts": "// @ts-ignore\n/// <reference path=\"x.d.ts\" />\n// Rules: keep the guard.\n",
    ".py": "# type: ignore\n# noqa\n# SPDX-License-Identifier: MIT\n# Rules: keep the guard.\n",
    ".sh": "# shellcheck disable=SC2034\n# Rules: keep the guard.\n",
    ".css": "/* SPDX-License-Identifier: MIT */\n/* Rules: keep the guard. */\n",
    ".html": "<!-- SPDX-License-Identifier: MIT -->\n<!-- Rules: keep the guard. -->\n",
    ".vue": "<!-- Rules: keep the guard. -->\n",
    ".svelte": "<!-- Rules: keep the guard. -->\n",
    ".astro": "<!-- Rules: keep the guard. -->\n",
    ".rb": "# frozen_string_literal: true\n# rubocop:disable Style\n# Rules: keep the guard.\n",
    ".pl": "# no critic\n# Rules: keep the guard.\n",
    ".php": "# Rules: keep the guard.\n// Rules: keep the guard.\n",
    ".lua": "--[[ Rules: keep the guard. ]]\n-- Rules: keep the guard.\n",
    ".hs": "{-# LANGUAGE OverloadedStrings #-}\n{- Rules: keep the guard. -}\n-- Rules: keep the guard.\n",
    ".elm": "{- Rules: keep the guard. -}\n-- Rules: keep the guard.\n",
    ".ex": "# Rules: keep the guard.\n",
    ".erl": "%% Rules: keep the guard.\n",
    ".clj": "; Rules: keep the guard.\n",
    ".sql": "/* Rules: keep the guard. */\n-- Rules: keep the guard.\n",
    ".ps1": "<# Rules: keep the guard. #>\n# Rules: keep the guard.\n",
    ".bat": "REM Rules: keep the guard.\n:: Rules: keep the guard.\n",
    ".vb": "' Rules: keep the guard.\nREM Rules: keep the guard.\n",
    ".fs": "(* Rules: keep the guard. *)\n// Rules: keep the guard.\n",
    ".ml": "(* Rules: keep the guard. *)\n",
    ".r": "# Rules: keep the guard.\n",
    ".jl": "#= Rules: keep the guard. =#\n# Rules: keep the guard.\n",
    ".zig": "/// documented\n// Rules: keep the guard.\n",
    ".nim": "#[ Rules: keep the guard. ]#\n# Rules: keep the guard.\n",
    ".cr": "# Rules: keep the guard.\n",
    ".d": "/+ Rules: keep the guard. +/\n// Rules: keep the guard.\n",
    ".sol": "/// documented\n// Rules: keep the guard.\n",
    ".tf": "/* Rules: keep the guard. */\n// Rules: keep the guard.\n# Rules: keep the guard.\n",
    ".f90": "! Rules: keep the guard.\n",
}

FALSE_POSITIVE_CORPUS = [
    (".c", '#include <stdio.h>\n#define LIMIT 1\nconst char *url = "https://example.com/a//b";\n'),
    (".c", '#define URL "http://x"\nint x = 1; /* Rules: inline block stays permitted */\n'),
    (".cpp", 'std::string u = "http://example.com";\nint n = 4 / 2;\n'),
    (".js", '#!/usr/bin/env node\nconst url = "https://example.com/a//b";\nconst re = /[//]/;\nconst t = `https://x/${url}//y`;\n'),
    (".js", "const re = /https?:\\/\\//;\nconst n = a / b / c;\n// Rules: keep the ratio.\n"),
    (".ts", 'const u: string = "http://x//y";\nconst re = /[//]/;\n'),
    (".rb", '#!/usr/bin/env ruby\nputs "a # b"\nre = /^#/\nS = "x"\n'),
    (".rb", "=begin\nRules: keep the boundary handling\n=end\nx = 1\n"),
    (".pl", '#!/usr/bin/env perl\nmy $s = "a # b";\nmy $n = 1;\n'),
    (".php", '#!/usr/bin/env php\n$u = "https://x//y";\n# Rules: keep it.\n$n = 1;\n'),
    (".lua", "local s = [[ a -- b ]]\nlocal t = { a = 1 }\n--[[ Rules: long comment body stays permitted ]]\n"),
    (".lua", "local n = #t\nlocal x = 1 -- Rules: trailing line comment stays permitted\n"),
    (".hs", 'x = a --> b\ns = "-- not a comment"\n{- Rules: block body stays permitted -}\n'),
    (".ps1", '$u = "http://x//y"\n<# Rules: block body stays permitted #>\nWrite-Output "# not a comment"\n'),
    (".cs", '/// <summary>documented</summary>\nvar u = "http://x//y";\nvar v = @"a // b";\n'),
    (".vb", 'Dim s = "it\'s fine"\n\' Rules: keep it.\nREM Rules: keep it too.\n'),
    (".bat", '@echo off\nREM Rules: keep it.\n:: Rules: keep it too.\necho http://x//y\necho ::1\n'),
    (".sql", "SELECT '-- not a comment';\nSELECT 1; -- Rules: keep it.\n"),
    (".kt", "val x = 1\n/* Rules: outer /* inner */ stays permitted */\n"),
    (".nim", "let x = 1\n#[ Rules: nested #[ inner ]# ok ]#\n"),
    (".jl", "x = 1\n#= Rules: nested #= inner =# ok =#\n"),
    (".fs", "let x = 1\n(* Rules: nested (* stays *) permitted *)\n"),
    (".ml", "let x = 1\n(* Rules: nested (* inner *) ok *)\n"),
    (".html", '<a href="https://x//y">link</a>\n<!-- Rules: markup comment stays permitted -->\n'),
    (".vue", "<template><a :href=\"https://x//y\">x</a></template>\n<!-- Rules: markup comment stays permitted -->\n"),
    (".cpp", 'const char *raw = R"(a // b /* c */ )";\n'),
    (".cpp", 'auto t = R"tag(first // line\nsecond /* line */\ntag)";\n'),
    (".ps1", '$t = @"\n// not a comment\n# nor this\n"@\nWrite-Output "ok"\n'),
    (".groovy", "def t = '''\n// not a comment\n# nor this\n'''\n"),
    (".pl", "my $last = $#array;\nmy $n = 1;\n"),
    (".java", 'String u = "http://x//y";\nchar q = \'"\';\n'),
    (".kt", 'val u = "https://x//y"\nval q = \'"\'\n'),
    (".rb", 'puts "#{x} # y"\nname = "a # b"\n'),
    (".r", 'x <- "# not a comment"\n'),
    (".sql", 'SELECT "a -- b";\nSELECT 2; -- Rules: keep it.\n'),
    (".erl", 'S = "a % b".\n'),
    (".clj", '(def s "a ; b")\n'),
    (".bat", 'echo ":: not a label"\necho "REM not a comment"\n'),
    (".d", 'string s = "/* not a comment */";\n'),
    (".nim", 'let s = "# not a comment"\n'),
    (".jl", 's = "# not a comment"\n'),
    (".ps1", '$x = 1 # Rules: keep it.\nWrite-Host "# not a comment"\n'),
    (".php", "?>\n# markup heading is output text\n<p># also output</p>\n<?php\necho 1;\n"),
    (".ex", 'x = 1\n"""\n# not a comment\n"""\n'),
    (".jl", 'x = 1\n"""\n# not a comment\n"""\n'),
    (".clj", "(def c \\;)\n(def d \\#)\n"),
]


class DialectContentTestCase(CodednaCheckTestCase):
    """Directive, license, and Rules lines stay exempt in every family; lookalikes stay code."""

    def test_directive_license_and_rules_lines_are_exempt_per_family(self) -> None:
        for suffix, extra in FAMILY_DIRECTIVE_LINES.items():
            with self.subTest(suffix=suffix):
                marker, code = LANGUAGE_CASES[suffix]
                text = (
                    PY_CLEAN + extra
                    if suffix == ".py"
                    else language_fixture(suffix, marker, code, extra)
                )
                path = self.write("src/family" + suffix, text)
                self.assertEqual([], self.checker.check_comment_content(path), suffix)

    def test_lookalike_corpus_produces_no_findings(self) -> None:
        for suffix, body in FALSE_POSITIVE_CORPUS:
            with self.subTest(suffix=suffix, body=body.splitlines()[0]):
                marker, code = LANGUAGE_CASES[suffix]
                prefix = ""
                if body.startswith("#!"):
                    prefix, body = body.split("\n", 1)
                    prefix += "\n"
                    body += "\n"
                text = prefix + language_fixture(suffix, marker, code, body)
                path = self.write("src/lookalike" + suffix, text)
                self.assertEqual([], self.checker.check_comment_content(path), suffix)
                self.assertEqual([], self.checker.check_file(path, self.root), suffix)

    def test_directive_above_the_header_is_not_the_title(self) -> None:
        cases = (
            (".go", "//go:build linux\n\n"),
            (".c", "/* SPDX-License-Identifier: MIT */\n\n"),
            (".c", "/*\n * SPDX-License-Identifier: MIT\n */\n\n"),
            (".sh", "# shellcheck disable=SC2034\n"),
        )
        for index, (suffix, prefix) in enumerate(cases):
            marker, code = LANGUAGE_CASES[suffix]
            with self.subTest(suffix=suffix, case=index):
                text = prefix + language_fixture(suffix, marker, code)
                path = self.write(f"src/directive{index}" + suffix, text)
                self.assertEqual([], self.checker.check_file(path, self.root), suffix)
                self.assertEqual([], self.checker.check_comment_content(path), suffix)
        bare = self.write("src/bare.go", "//go:build linux\n\npackage sample\n")
        self.assertEqual(["missing L1 header"], self.checker.check_file(bare, self.root))

    def test_rust_doc_marker_header_is_clean(self) -> None:
        lines = (
            "/// sample.rs — Example module.",
            "///",
            "/// exports: none",
            "/// used_by: none",
            "/// rules:   none",
            "/// agent:   test-agent | 9router | 2026-10-08 | s_test | added sample",
        )
        for marker in ("///", "//!"):
            with self.subTest(marker=marker):
                text = "\n".join(line if marker == "///" else line.replace("///", "//!") for line in lines)
                path = self.write("src/doc.rs", text + "\n\npub fn f() {}\n")
                self.assertEqual([], self.checker.check_file(path, self.root))
                self.assertEqual([], self.checker.check_comment_content(path))

    def test_directive_banner_between_header_fields_is_skipped(self) -> None:
        lines = [
            "// sample.go — Example module.",
            "//",
            "// exports: none",
            "// Code generated by tool — do not edit.",
            "// used_by: none",
            "// rules:   none",
            "// agent:   test-agent | 9router | 2026-10-08 | s_test | added sample",
        ]
        path = self.write("src/banner.go", "\n".join(lines) + "\n\npackage sample\n")
        self.assertEqual([], self.checker.check_file(path, self.root))

    def test_percent_assignment_does_not_swallow_later_comments(self) -> None:
        body = "total %= 3\n# helper keeps the ledger warm\n"
        path = self.write("src/percent.rb", language_fixture(".rb", "#", body.rstrip("\n")))
        findings = self.checker.check_comment_content(path)
        self.assertEqual(1, len(findings), findings)
        self.assertIn("outside the permitted content", findings[0])

    def test_unterminated_percent_literal_fails_open(self) -> None:
        body = "x = %q[abc\n# helper keeps the ledger warm\n"
        path = self.write("src/open.rb", language_fixture(".rb", "#", body.rstrip("\n")))
        findings = self.checker.check_comment_content(path)
        self.assertEqual(1, len(findings), findings)

    def test_hash_bracket_comment_is_prose_outside_php(self) -> None:
        body = "#[note] helper keeps the ledger warm\n"
        path = self.write(
            "src/hash.rb", language_fixture(".rb", "#", "x = 1", body.rstrip("\n"))
        )
        findings = self.checker.check_comment_content(path)
        self.assertEqual(1, len(findings), findings)

    def test_shell_length_expansion_is_not_a_comment(self) -> None:
        body = "echo ${#arr[@]}\nif [ ${#x} -gt 0 ]; then echo ok; fi\n"
        path = self.write("src/length.sh", language_fixture(".sh", "#", body.rstrip("\n")))
        self.assertEqual([], self.checker.check_comment_content(path))

    def test_php_attribute_is_not_a_comment(self) -> None:
        body = "class D {\n    #[Pure]\n    public function f() { return 1; }\n}"
        path = self.write("src/attr.php", language_fixture(".php", "//", body))
        self.assertEqual([], self.checker.check_comment_content(path))

    def test_percent_and_sigil_literals_are_not_comments(self) -> None:
        ruby = "x = %w[#a #b]\ny = %q(#note)\nz = a % b\n"
        elixir = "x = ~w[#a #b]\n"
        for suffix, body in ((".rb", ruby), (".ex", elixir)):
            marker, code = LANGUAGE_CASES[suffix]
            with self.subTest(suffix=suffix):
                path = self.write("src/literal" + suffix, language_fixture(suffix, marker, body.rstrip("\n")))
                self.assertEqual([], self.checker.check_comment_content(path), suffix)

    def test_quote_characters_do_not_hide_trailing_comments(self) -> None:
        cases = {
            ".ml": ("(*", "let f (x: 'a) = x (* helper keeps the ledger warm *)\n"),
            ".hs": ("--", "foo' x = x -- helper keeps the ledger warm\n"),
            ".fs": ("//", "let f (x: 'a) = x // helper keeps the ledger warm\n"),
            ".clj": (";", "(def x 'y) ; helper keeps the ledger warm\n"),
        }
        for suffix, (marker, body) in cases.items():
            with self.subTest(suffix=suffix):
                path = self.write("src/quoted" + suffix, language_fixture(suffix, marker, body.rstrip("\n")))
                findings = self.checker.check_comment_content(path)
                self.assertEqual(1, len(findings), (suffix, findings))
                self.assertIn("outside the permitted content", findings[0])

    def test_prose_inside_a_nested_block_is_reported(self) -> None:
        marker, code = LANGUAGE_CASES[".kt"]
        body = "/* outer /* inner */ helper keeps the ledger warm. */\n"
        path = self.write("src/nested.kt", language_fixture(".kt", marker, code, body))
        findings = self.checker.check_comment_content(path)
        self.assertEqual(1, len(findings), findings)
        self.assertIn("outside the permitted content", findings[0])

    def test_shebang_is_not_prose_in_every_executable_dialect(self) -> None:
        hbodies = ("#!/usr/bin/env ruby\n", "#!/usr/bin/env perl\n", "#!/usr/bin/env node\n", "#!/usr/bin/env pwsh\n")
        suffixes = (".rb", ".pl", ".js", ".ps1")
        for suffix, shebang in zip(suffixes, hbodies):
            with self.subTest(suffix=suffix):
                marker, code = LANGUAGE_CASES[suffix]
                text = shebang + language_fixture(suffix, marker, code)
                path = self.write("src/exec" + suffix, text)
                self.assertEqual([], self.checker.check_comment_content(path), suffix)
                self.assertEqual([], self.checker.check_file(path, self.root), suffix)


class CliEntryPointTestCase(CodednaCheckTestCase):
    """The shipped command line drives the enlarged suffix set on a real tree."""

    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        """Run the checker script as a subprocess, exactly as a user would.

        Rules:   `cwd` is the temporary root so the repository's own AGENTS.md never enters the run.
        """
        return subprocess.run(
            [sys.executable, str(CHECKER_PATH), *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

    def build_tree(self) -> None:
        clean = {
            "clean/module.py": PY_CLEAN,
            "clean/module.go": GO_CLEAN,
            "clean/module.rb": language_fixture(".rb", "#", "x = 1"),
            "clean/module.hs": language_fixture(".hs", "--", "x = 1"),
            "clean/module.ml": language_fixture(".ml", "(*", "let x = 1"),
            "clean/module.bat": language_fixture(".bat", "REM", "echo ok"),
            "clean/module.vue": language_fixture(".vue", "<!--", "<template><div></div></template>"),
            "clean/module.sql": language_fixture(".sql", "--", "SELECT 1;"),
            "clean/module.ps1": language_fixture(".ps1", "#", "Write-Output ok"),
        }
        for relative, text in clean.items():
            self.write(relative, text)
        self.write("broken/prose.rb", language_fixture(".rb", "#", "x = 1", f"# {PROSE_BODY}\n"))

    def test_lowheat_contract_is_scanned_by_the_documented_cli(self) -> None:
        repo = CHECKER_PATH.parents[4]
        result = subprocess.run(
            [sys.executable, str(CHECKER_PATH), ".", "contract"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("1 contract(s)", result.stdout)

    def test_cli_is_deterministic_and_names_the_violating_line(self) -> None:
        self.build_tree()
        first = self.run_cli(str(self.root))
        second = self.run_cli(str(self.root))
        self.assertEqual(1, first.returncode, first.stdout + first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(first.stderr, second.stderr)
        self.assertIn("outside the permitted content", first.stdout)
        expected_line = len(language_fixture(".rb", "#", "x = 1", f"# {PROSE_BODY}\n").splitlines())
        self.assertIn(f"prose.rb: {expected_line}:", first.stdout)
        offending = [line for line in first.stdout.splitlines() if "outside the permitted content" in line]
        self.assertEqual(1, len(offending), first.stdout)
        self.assertIn("codedna_check: 1 finding(s)", first.stdout)

    def test_cli_is_clean_on_a_clean_tree(self) -> None:
        self.build_tree()
        (self.root / "broken" / "prose.rb").unlink()
        result = self.run_cli(str(self.root))
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("codedna_check: 0 finding(s)", result.stdout)

    def test_cli_reports_a_missing_path(self) -> None:
        result = self.run_cli(str(self.root / "gone"))
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertIn("path not found", result.stdout)


if __name__ == "__main__":
    unittest.main()
