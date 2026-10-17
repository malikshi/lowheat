"""test_install_hooks.py — Tests for the contract hook installer across the three harnesses.

exports: class ClaudeInstallTestCase | class GrokInstallTestCase | class CommandCodeInstallTestCase | class InstallerSafetyTestCase
used_by: none
rules:   Load the installer by file path — the skill directory name is not a Python package. Every case runs against a temporary home directory; never touch the real harness configs.
agent:   grok-4.6 | xai | 2026-10-17 | 01a14a7c-788f-7061-83bb-6dded52bc3b5 | added merge, idempotence, backup, uninstall, and safety tests for the three-harness wiring
"""

from __future__ import annotations

import importlib
import io
import contextlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS_DIR = (
    Path(__file__).resolve().parents[1]
    / ".agents"
    / "skills"
    / "agents-contract"
    / "hooks"
)
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

install_hooks = importlib.import_module("install_hooks")

CLAUDE = install_hooks.HARNESS_CLAUDE
GROK = install_hooks.HARNESS_GROK
COMMANDCODE = install_hooks.HARNESS_COMMANDCODE

PYTHON = "/usr/local/bin/python3"
SCRIPT = "/opt/lowheat/.agents/skills/agents-contract/hooks/contract_hook.py"

EXISTING_CLAUDE_SETTINGS = {
    "permissions": {"allow": ["Bash(*)"]},
    "hooks": {
        "PreToolUse": [
            {
                "matcher": "Bash",
                "hooks": [
                    {"type": "command", "command": "bash '/root/.claude/hooks/check-bash-command.sh'"}
                ],
            }
        ],
        "SessionStart": [
            {
                "matcher": "^(startup|resume)$",
                "hooks": [{"type": "command", "command": "bash '/root/.claude/hooks/herdr.sh' session"}],
            }
        ],
    },
}

EXISTING_COMMANDCODE_SETTINGS = {
    "permissions": {"allow": ["Shell(semble:*)"]},
    "tasteLearning": False,
}


def handler_commands(groups) -> list[str]:
    return [
        handler.get("command", "")
        for group in groups
        for handler in group.get("hooks", [])
    ]


class InstallerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)

    def install(self, harness, **kwargs):
        options = {"home": self.home, "python": PYTHON, "script": SCRIPT}
        options.update(kwargs)
        return install_hooks.install(harness, **options)

    def uninstall(self, harness, **kwargs):
        options = {"home": self.home}
        options.update(kwargs)
        return install_hooks.uninstall(harness, **options)

    def read_json(self, path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    def write_claude_settings(self, data=EXISTING_CLAUDE_SETTINGS) -> Path:
        path = install_hooks.claude_settings_path(self.home)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path


class ClaudeInstallTestCase(InstallerTestCase):
    def test_install_merges_without_touching_existing_settings(self):
        path = self.write_claude_settings()

        self.install(CLAUDE)
        data = self.read_json(path)

        self.assertEqual(data["permissions"], {"allow": ["Bash(*)"]})
        commands = handler_commands(data["hooks"]["PreToolUse"])
        self.assertIn("bash '/root/.claude/hooks/check-bash-command.sh'", commands)
        self.assertTrue(any(install_hooks.MARKER in item for item in commands))

    def test_install_matches_shell_grep_and_glob_in_one_pre_tool_use_group(self):
        path = self.write_claude_settings()

        self.install(CLAUDE)
        data = self.read_json(path)

        matchers = [group.get("matcher") for group in data["hooks"]["PreToolUse"]]
        self.assertIn("Bash|Grep|Glob", matchers)

    def test_install_adds_a_session_start_group_without_a_matcher(self):
        path = self.write_claude_settings()

        self.install(CLAUDE)
        data = self.read_json(path)

        our_groups = [
            group
            for group in data["hooks"]["SessionStart"]
            if any(install_hooks.MARKER in item for item in handler_commands([group]))
        ]
        self.assertEqual(len(our_groups), 1)
        self.assertNotIn("matcher", our_groups[0])

    def test_install_is_idempotent(self):
        path = self.write_claude_settings()

        self.install(CLAUDE)
        self.install(CLAUDE)
        data = self.read_json(path)

        ours = [
            item
            for item in handler_commands(data["hooks"]["PreToolUse"])
            if install_hooks.MARKER in item
        ]
        self.assertEqual(len(ours), 1)

    def test_install_replaces_a_stale_handler_path(self):
        path = self.write_claude_settings()
        self.install(CLAUDE, script="/old/contract_hook.py")

        self.install(CLAUDE, script=SCRIPT)
        data = self.read_json(path)
        commands = handler_commands(data["hooks"]["PreToolUse"])

        self.assertNotIn("/old/contract_hook.py", " ".join(commands))
        self.assertIn(SCRIPT, " ".join(commands))

    def test_uninstall_removes_only_our_handlers(self):
        path = self.write_claude_settings()
        self.install(CLAUDE)

        self.uninstall(CLAUDE)
        data = self.read_json(path)

        commands = handler_commands(data["hooks"]["PreToolUse"])
        self.assertIn("bash '/root/.claude/hooks/check-bash-command.sh'", commands)
        self.assertFalse(any(install_hooks.MARKER in item for item in commands))
        self.assertEqual(len(data["hooks"]["SessionStart"]), 1)

    def test_uninstall_restores_the_pristine_bytes(self):
        path = self.write_claude_settings()
        original = path.read_text(encoding="utf-8")
        self.install(CLAUDE)

        self.uninstall(CLAUDE)

        self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_uninstall_restores_pristine_bytes_when_only_we_touched_the_file(self):
        path = install_hooks.claude_settings_path(self.home)
        path.parent.mkdir(parents=True, exist_ok=True)
        original = '{"permissions": {"allow": ["Bash(*)"]}}\n'
        path.write_text(original, encoding="utf-8")
        self.install(CLAUDE)

        self.uninstall(CLAUDE)

        self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_uninstall_reports_a_restore(self):
        self.write_claude_settings()
        self.install(CLAUDE)

        changes = self.uninstall(CLAUDE)

        self.assertEqual(changes[0].action, "restore")

    def test_uninstall_leaves_a_file_without_our_handlers_alone(self):
        path = self.write_claude_settings()
        original = path.read_text(encoding="utf-8")

        changes = self.uninstall(CLAUDE)

        self.assertEqual(changes[0].action, "unchanged")
        self.assertEqual(path.read_text(encoding="utf-8"), original)


class GrokInstallTestCase(InstallerTestCase):
    def test_install_writes_the_documented_hook_file(self):
        path = install_hooks.grok_hooks_path(self.home)

        self.install(GROK)
        data = self.read_json(path)

        group = data["hooks"]["PreToolUse"][0]
        self.assertEqual(group["matcher"], "Bash|Grep|Glob")
        self.assertEqual(group["hooks"][0]["type"], "command")
        self.assertIn(SCRIPT, group["hooks"][0]["command"])
        self.assertIn("timeout", group["hooks"][0])

    def test_grok_hook_file_carries_no_session_start_group(self):
        self.install(GROK)

        data = self.read_json(install_hooks.grok_hooks_path(self.home))
        self.assertNotIn("SessionStart", data["hooks"])

    def test_uninstall_deletes_the_hook_file(self):
        path = install_hooks.grok_hooks_path(self.home)
        self.install(GROK)

        self.uninstall(GROK)
        self.assertFalse(path.exists())

    def test_install_uses_the_same_command_string_as_the_other_harnesses(self):
        self.install(GROK)
        self.install(CLAUDE)

        grok_command = self.read_json(install_hooks.grok_hooks_path(self.home))["hooks"][
            "PreToolUse"
        ][0]["hooks"][0]["command"]
        claude_commands = handler_commands(
            self.read_json(install_hooks.claude_settings_path(self.home))["hooks"]["PreToolUse"]
        )

        self.assertIn(grok_command, claude_commands)


class CommandCodeInstallTestCase(InstallerTestCase):
    def test_install_creates_settings_when_missing(self):
        path = install_hooks.commandcode_settings_path(self.home)

        self.install(COMMANDCODE)
        data = self.read_json(path)

        group = data["hooks"]["PreToolUse"][0]
        self.assertEqual(group["matcher"], "SHELL")
        self.assertIn(SCRIPT, group["hooks"][0]["command"])

    def test_install_preserves_existing_keys(self):
        path = install_hooks.commandcode_settings_path(self.home)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(EXISTING_COMMANDCODE_SETTINGS), encoding="utf-8")

        self.install(COMMANDCODE)
        data = self.read_json(path)

        self.assertEqual(data["permissions"], {"allow": ["Shell(semble:*)"]})
        self.assertIs(data["tasteLearning"], False)

    def test_session_start_group_omits_the_matcher(self):
        self.install(COMMANDCODE)

        data = self.read_json(install_hooks.commandcode_settings_path(self.home))
        group = data["hooks"]["SessionStart"][0]
        self.assertNotIn("matcher", group)

    def test_uninstall_strips_the_hooks_key_when_nothing_is_left(self):
        path = install_hooks.commandcode_settings_path(self.home)
        self.install(COMMANDCODE)

        self.uninstall(COMMANDCODE)
        data = self.read_json(path)

        self.assertNotIn("hooks", data)

    def test_uninstall_restores_inline_array_formatting(self):
        path = install_hooks.commandcode_settings_path(self.home)
        path.parent.mkdir(parents=True, exist_ok=True)
        original = '{"permissions": {"allow": ["Shell(semble:*)", "Shell(rtk:*)"]}}\n'
        path.write_text(original, encoding="utf-8")
        self.install(COMMANDCODE)

        self.uninstall(COMMANDCODE)

        self.assertEqual(path.read_text(encoding="utf-8"), original)


class InstallerSafetyTestCase(InstallerTestCase):
    def test_dry_run_changes_nothing_on_disk(self):
        path = self.write_claude_settings()
        before = path.read_text(encoding="utf-8")

        changes = self.install(CLAUDE, dry_run=True)

        self.assertTrue(changes)
        self.assertEqual(path.read_text(encoding="utf-8"), before)

    def test_malformed_settings_raise_and_leave_the_file_untouched(self):
        path = install_hooks.claude_settings_path(self.home)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json", encoding="utf-8")

        with self.assertRaises(install_hooks.InstallError):
            self.install(CLAUDE)
        self.assertEqual(path.read_text(encoding="utf-8"), "{not json")

    def test_settings_whose_hooks_key_is_not_an_object_raise(self):
        path = self.write_claude_settings({"hooks": []})

        with self.assertRaises(install_hooks.InstallError):
            self.install(CLAUDE)

    def test_backup_keeps_the_pristine_copy_across_runs(self):
        path = self.write_claude_settings()
        original = path.read_text(encoding="utf-8")

        self.install(CLAUDE)
        self.install(CLAUDE)

        backup = path.with_name(path.name + install_hooks.BACKUP_SUFFIX)
        self.assertEqual(backup.read_text(encoding="utf-8"), original)

    def test_report_names_the_harness_and_the_file(self):
        self.write_claude_settings()

        changes = self.install(CLAUDE)

        self.assertEqual(changes[0].harness, CLAUDE)
        self.assertEqual(changes[0].path, install_hooks.claude_settings_path(self.home))

    def test_handler_command_runs_the_script_with_the_interpreter(self):
        command = install_hooks.handler_command(PYTHON, SCRIPT)

        self.assertEqual(command, f"{PYTHON} {SCRIPT}")

    def test_hook_timeout_stays_within_the_recommended_budget(self):
        self.assertLessEqual(install_hooks.HOOK_TIMEOUT_SECONDS, 10)


class InstallerCliTestCase(InstallerTestCase):
    def run_main(self, argv):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = install_hooks.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_cli_wires_one_harness_under_the_given_home(self):
        code, out, _ = self.run_main(
            ["--harness", CLAUDE, "--home", str(self.home), "--python", PYTHON]
        )

        self.assertEqual(code, 0)
        self.assertIn("claude: write", out)
        self.assertTrue(install_hooks.claude_settings_path(self.home).exists())

    def test_cli_wires_all_three_harnesses_by_default(self):
        code, out, _ = self.run_main(["--home", str(self.home), "--python", PYTHON])

        self.assertEqual(code, 0)
        for harness in install_hooks.HARNESSES:
            with self.subTest(harness=harness):
                self.assertIn(f"{harness}: write", out)

    def test_cli_dry_run_reports_without_writing(self):
        code, out, _ = self.run_main(["--home", str(self.home), "--dry-run"])

        self.assertEqual(code, 0)
        self.assertIn("dry run", out)
        self.assertFalse(install_hooks.grok_hooks_path(self.home).exists())

    def test_cli_uninstall_removes_the_wiring_it_added(self):
        self.run_main(["--home", str(self.home), "--python", PYTHON])

        code, out, _ = self.run_main(["--home", str(self.home), "--uninstall"])

        self.assertEqual(code, 0)
        self.assertIn("grok: remove", out)
        self.assertFalse(install_hooks.grok_hooks_path(self.home).exists())

    def test_cli_reports_a_malformed_settings_file_and_exits_nonzero(self):
        path = install_hooks.claude_settings_path(self.home)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json", encoding="utf-8")

        code, _, err = self.run_main(["--harness", CLAUDE, "--home", str(self.home)])

        self.assertEqual(code, 1)
        self.assertIn("install_hooks:", err)
        self.assertEqual(path.read_text(encoding="utf-8"), "{not json")

    def test_cli_uninstall_leaves_an_absent_file_alone(self):
        code, out, _ = self.run_main(["--harness", CLAUDE, "--home", str(self.home), "--uninstall"])

        self.assertEqual(code, 0)
        self.assertIn("unchanged", out)

    def test_unknown_harness_raises(self):
        with self.assertRaises(install_hooks.InstallError):
            install_hooks.install("codex", self.home)
        with self.assertRaises(install_hooks.InstallError):
            install_hooks.uninstall("codex", self.home)

    def test_a_non_object_settings_root_raises(self):
        path = install_hooks.claude_settings_path(self.home)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[]", encoding="utf-8")

        with self.assertRaises(install_hooks.InstallError):
            self.install(CLAUDE)

    def test_an_event_that_is_not_an_array_raises(self):
        path = self.write_claude_settings({"hooks": {"PreToolUse": "not-a-list"}})

        with self.assertRaises(install_hooks.InstallError):
            self.install(CLAUDE)
        self.assertIn("not-a-list", path.read_text(encoding="utf-8"))

    def test_an_unwritable_settings_directory_raises(self):
        blocker = install_hooks.claude_settings_path(self.home).parent
        blocker.parent.mkdir(parents=True, exist_ok=True)
        blocker.write_text("", encoding="utf-8")

        with self.assertRaises(install_hooks.InstallError):
            self.install(CLAUDE)


if __name__ == "__main__":
    unittest.main()
