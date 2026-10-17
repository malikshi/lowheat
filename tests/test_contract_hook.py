"""test_contract_hook.py — Tests for the agents-contract hook policy, encoding, and entry point.

exports: class HarnessDetectionTestCase | class EventAndToolTestCase | class ShellPolicyTestCase | class DiscoveryPolicyTestCase | class SessionContextTestCase | class EncodingTestCase | class BudgetTestCase | class EntrypointTestCase
used_by: none
rules:   Load the hook modules by file path — the skill directory name is not a Python package. Never call the real rtk, semble, or harness binaries: inject runners, `which` lookups, and a temporary cache root.
agent:   grok-4.6 | xai | 2026-10-17 | 01a14a7c-788f-7061-83bb-6dded52bc3b5 | added policy, encoding, budget, and entry-point tests for the three-harness contract hook
agent:   grok-build | xai | 2026-10-18 | 01a14ad3-ab3e-74b1-81d5-fc6f08b61af7 | regression tests for the empty-query nudge: pattern aliases, the directory the call carries, and the placeholder fallback
agent:   grok-build | xai | 2026-10-18 | 01a14ad3-ab3e-74b1-81d5-fc6f08b61af7 | asserted both the rewrite reason and the refusal name `rtk bypass`, the route the engine never rewrites; on review: a rewrite carries no permissionDecision, shlex quoting defuses a substitution in the suggestion, a glob keeps `**/` out of the find hint, and a closed stdout still exits 0; second pass: a glob with a slash gets the grep rung, while `**/**/*.py` still collapses to a find form
"""

from __future__ import annotations

import contextlib
import importlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import unittest.mock
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

hook_harness = importlib.import_module("hook_harness")
hook_policy = importlib.import_module("hook_policy")
contract_hook = importlib.import_module("contract_hook")
install_hooks = importlib.import_module("install_hooks")

Decision = hook_harness.Decision

CLAUDE_ENV = {"CLAUDE_PROJECT_DIR": "/tmp/project"}
GROK_ENV = {"GROK_HOOK_EVENT": "PreToolUse", "GROK_SESSION_ID": "grok-session"}
COMMANDCODE_ENV = {"COMMANDCODE_HOOK_EVENT": "PreToolUse", "COMMANDCODE_SESSION_ID": "cc-session"}

REWRITABLE = "git status"
REWRITTEN = "rtk git status"


def claude_payload(command: str = REWRITABLE, session: str = "s-claude") -> dict:
    return {
        "session_id": session,
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command, "timeout": 120000},
    }


def grok_payload(command: str = REWRITABLE, session: str = "s-grok") -> dict:
    return {
        "hookEventName": "pre_tool_use",
        "hook_event_name": "PreToolUse",
        "sessionId": session,
        "toolName": "run_terminal_command",
        "toolInput": {"command": command},
    }


def commandcode_payload(command: str = REWRITABLE, session: str = "s-cc") -> dict:
    return {
        "session_id": session,
        "hook_event_name": "PreToolUse",
        "tool_name": "shell_command",
        "tool_display_name": "SHELL",
        "tool_input": {"command": command},
    }


def which_lookup(semble_path, rtk_path="/usr/bin/rtk"):
    def lookup(name: str):
        if name == hook_policy.SEMBLE_BIN:
            return semble_path
        if name == hook_policy.RTK_BIN:
            return rtk_path
        return None

    return lookup


def rtk_runner(rewritten=REWRITTEN, returncode=0, stdout=None):
    def run(args, input=None, capture_output=None, text=None, timeout=None):
        if stdout is not None:
            body = stdout
        else:
            body = json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "updatedInput": {"command": rewritten},
                    }
                }
            )
        return subprocess.CompletedProcess(args, returncode, body, "")

    return run


def exploding_runner(args, input=None, capture_output=None, text=None, timeout=None):
    raise FileNotFoundError("rtk is not installed")


class HookTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cache_root = Path(self._tmp.name)

    def make_semble_shim(self, shebang: str = "#!/bin/sh", name: str = "semble") -> Path:
        path = Path(self._tmp.name) / "bin" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{shebang}\n", encoding="utf-8")
        path.chmod(0o755)
        return path

    def which(self, rtk="/usr/bin/rtk", shebang="#!/bin/sh", semble_absent=False):
        shim = (
            None
            if semble_absent
            else str(self.make_semble_shim(shebang, name="semble-default"))
        )
        return which_lookup(shim, rtk)

    def decide(self, payload, env, **kwargs):
        options = {"cache_root": self.cache_root}
        if "run" not in kwargs:
            options["run"] = rtk_runner()
        if "which" not in kwargs:
            options["which"] = self.which()
        options.update(kwargs)
        return hook_policy.decide(payload, env, **options)


class HarnessDetectionTestCase(HookTestCase):
    def test_detects_each_harness_from_its_environment(self):
        cases = (
            (claude_payload(), CLAUDE_ENV, hook_harness.HARNESS_CLAUDE),
            (grok_payload(), GROK_ENV, hook_harness.HARNESS_GROK),
            (commandcode_payload(), COMMANDCODE_ENV, hook_harness.HARNESS_COMMANDCODE),
        )
        for payload, env, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(hook_harness.detect_harness(payload, env), expected)

    def test_detects_each_harness_from_the_payload_shape_alone(self):
        cases = (
            (claude_payload(), hook_harness.HARNESS_CLAUDE),
            (grok_payload(), hook_harness.HARNESS_GROK),
            (commandcode_payload(), hook_harness.HARNESS_COMMANDCODE),
        )
        for payload, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(hook_harness.detect_harness(payload, {}), expected)


class EventAndToolTestCase(HookTestCase):
    def test_normalizes_event_names_across_harnesses(self):
        cases = (
            (claude_payload(), CLAUDE_ENV, hook_harness.HARNESS_CLAUDE),
            (grok_payload(), GROK_ENV, hook_harness.HARNESS_GROK),
            (commandcode_payload(), COMMANDCODE_ENV, hook_harness.HARNESS_COMMANDCODE),
        )
        for payload, env, harness in cases:
            with self.subTest(harness=harness):
                self.assertEqual(hook_harness.event_name(payload, env, harness), "PreToolUse")

    def test_reads_session_start_from_a_claude_payload(self):
        payload = {"session_id": "s", "hook_event_name": "SessionStart", "source": "startup"}
        self.assertEqual(
            hook_harness.event_name(payload, CLAUDE_ENV, hook_harness.HARNESS_CLAUDE),
            "SessionStart",
        )

    def test_reads_the_tool_name_from_each_harness(self):
        cases = (
            (claude_payload(), hook_harness.HARNESS_CLAUDE, "Bash"),
            (grok_payload(), hook_harness.HARNESS_GROK, "run_terminal_command"),
            (commandcode_payload(), hook_harness.HARNESS_COMMANDCODE, "shell_command"),
        )
        for payload, harness, expected in cases:
            with self.subTest(harness=harness):
                self.assertEqual(hook_harness.tool_name(payload, harness), expected)

    def test_classifies_grep_aliases_as_discovery_tools(self):
        for name in ("Grep", "grep", "Glob", "glob", "list_dir"):
            with self.subTest(tool=name):
                self.assertIn(name.lower(), hook_harness.DISCOVERY_TOOLS)

    def test_classifies_every_shell_alias_as_a_shell_tool(self):
        for name in ("Bash", "run_terminal_command", "shell_command"):
            with self.subTest(tool=name):
                self.assertIn(name.lower(), hook_harness.SHELL_TOOLS)


class ShellPolicyTestCase(HookTestCase):
    def test_claude_rewrites_a_wrappable_command_and_keeps_other_fields(self):
        decision = self.decide(claude_payload(), CLAUDE_ENV)

        self.assertEqual(decision.kind, "rewrite")
        self.assertEqual(decision.updated_input["command"], REWRITTEN)
        self.assertEqual(decision.updated_input["timeout"], 120000)

    def test_grok_rewrites_a_wrappable_command(self):
        decision = self.decide(grok_payload(), GROK_ENV)

        self.assertEqual(decision.kind, "rewrite")
        self.assertEqual(decision.updated_input["command"], REWRITTEN)

    def test_commandcode_denies_the_first_raw_command_with_the_rtk_form(self):
        decision = self.decide(commandcode_payload(), COMMANDCODE_ENV)

        self.assertEqual(decision.kind, "deny")
        self.assertIn(REWRITTEN, decision.reason)
        self.assertIn("rtk", decision.reason)

    def test_commandcode_allows_the_same_raw_command_after_the_budget_is_spent(self):
        self.decide(commandcode_payload(), COMMANDCODE_ENV)
        second = self.decide(commandcode_payload(), COMMANDCODE_ENV)

        self.assertEqual(second.kind, "noop")

    def test_commandcode_budget_is_per_session(self):
        self.decide(commandcode_payload(session="s-one"), COMMANDCODE_ENV)
        other = self.decide(commandcode_payload(session="s-two"), COMMANDCODE_ENV)

        self.assertEqual(other.kind, "deny")

    def test_no_decision_when_rtk_is_not_installed(self):
        for payload, env in (
            (claude_payload(), CLAUDE_ENV),
            (grok_payload(), GROK_ENV),
            (commandcode_payload(), COMMANDCODE_ENV),
        ):
            with self.subTest(env=env):
                decision = self.decide(payload, env, which=self.which(semble_absent=True, rtk=None))
                self.assertEqual(decision.kind, "noop")

    def test_no_decision_when_rtk_offers_no_rewrite(self):
        for payload, env in (
            (claude_payload(), CLAUDE_ENV),
            (commandcode_payload(), COMMANDCODE_ENV),
        ):
            with self.subTest(env=env):
                decision = self.decide(payload, env, run=rtk_runner(stdout=""))
                self.assertEqual(decision.kind, "noop")

    def test_no_decision_when_rtk_returns_the_command_unchanged(self):
        decision = self.decide(claude_payload(), CLAUDE_ENV, run=rtk_runner(rewritten=REWRITABLE))

        self.assertEqual(decision.kind, "noop")

    def test_fails_open_when_the_rtk_process_cannot_start(self):
        decision = self.decide(claude_payload(), CLAUDE_ENV, run=exploding_runner)

        self.assertEqual(decision.kind, "noop")

    def test_fails_open_when_rtk_exits_nonzero(self):
        decision = self.decide(claude_payload(), CLAUDE_ENV, run=rtk_runner(returncode=1))

        self.assertEqual(decision.kind, "noop")

    def test_ignores_an_empty_command(self):
        payload = claude_payload(command="")
        payload["tool_input"]["command"] = "   "

        self.assertEqual(self.decide(payload, CLAUDE_ENV).kind, "noop")

    def test_rewrite_reason_names_the_route_to_untouched_output(self):
        decision = self.decide(claude_payload(), CLAUDE_ENV)

        self.assertIn("rtk bypass", decision.reason)

    def test_refusal_names_the_route_to_untouched_output(self):
        decision = self.decide(commandcode_payload(), COMMANDCODE_ENV)

        self.assertIn("rtk bypass", decision.reason)

    def test_ignores_a_non_shell_tool(self):
        payload = claude_payload()
        payload["tool_name"] = "Read"
        payload["tool_input"] = {"file_path": "/tmp/x.py"}

        self.assertEqual(self.decide(payload, CLAUDE_ENV).kind, "noop")


class DiscoveryPolicyTestCase(HookTestCase):
    def grep_payload(self, pattern="firewall install", session="s-claude"):
        return {
            "session_id": session,
            "hook_event_name": "PreToolUse",
            "tool_name": "Grep",
            "tool_input": {"pattern": pattern, "path": "src"},
        }

    def test_denies_the_first_native_grep_and_names_the_ladder(self):
        decision = self.decide(self.grep_payload(), CLAUDE_ENV)

        self.assertEqual(decision.kind, "deny")
        self.assertIn("semble search", decision.reason)
        self.assertIn("rtk grep", decision.reason)
        self.assertIn("firewall install", decision.reason)

    def test_allows_native_grep_after_the_first_denial(self):
        self.decide(self.grep_payload(), CLAUDE_ENV)
        second = self.decide(self.grep_payload(), CLAUDE_ENV)

        self.assertEqual(second.kind, "noop")

    def test_glob_carries_its_own_budget(self):
        glob_payload = {
            "session_id": "s-claude",
            "hook_event_name": "PreToolUse",
            "tool_name": "Glob",
            "tool_input": {"pattern": "**/*.py"},
        }
        self.decide(self.grep_payload(), CLAUDE_ENV)
        decision = self.decide(glob_payload, CLAUDE_ENV)

        self.assertEqual(decision.kind, "deny")
        self.assertIn("rtk find", decision.reason)

    def test_grok_grep_is_nudged_once(self):
        payload = {
            "hookEventName": "pre_tool_use",
            "sessionId": "s-grok",
            "toolName": "grep",
            "toolInput": {"pattern": "retry budget"},
        }
        self.assertEqual(self.decide(payload, GROK_ENV).kind, "deny")
        self.assertEqual(self.decide(payload, GROK_ENV).kind, "noop")

    def test_no_decision_when_neither_semble_nor_rtk_is_available(self):
        decision = self.decide(self.grep_payload(), CLAUDE_ENV, which=self.which(semble_absent=True, rtk=None))

        self.assertEqual(decision.kind, "noop")

    def test_nudge_still_fires_when_only_rtk_is_installed(self):
        decision = self.decide(self.grep_payload(), CLAUDE_ENV, which=self.which(semble_absent=True))

        self.assertEqual(decision.kind, "deny")
        self.assertNotIn('semble search "', decision.reason)
        self.assertIn("rtk grep", decision.reason)

    def test_nudge_names_the_semble_mcp_tool_for_claude(self):
        decision = self.decide(self.grep_payload(), CLAUDE_ENV)

        self.assertIn("mcp__semble__search", decision.reason)

    def test_nudge_names_the_semble_mcp_tool_for_grok(self):
        payload = {
            "hookEventName": "pre_tool_use",
            "sessionId": "s-grok-mcp",
            "toolName": "grep",
            "toolInput": {"pattern": "retry budget"},
        }
        decision = self.decide(payload, GROK_ENV)

        self.assertIn("semble__search", decision.reason)

    def test_nudge_skips_a_cli_that_is_installed_but_cannot_run(self):
        decision = self.decide(self.grep_payload(), CLAUDE_ENV, which=self.which(shebang="#!/nonexistent/python3"))

        self.assertEqual(decision.kind, "deny")
        self.assertNotIn('semble search "', decision.reason)
        self.assertIn("cannot run", decision.reason)
        self.assertIn("rtk grep", decision.reason)

    def test_nudge_says_nothing_about_the_cli_when_it_is_absent(self):
        decision = self.decide(self.grep_payload(), CLAUDE_ENV, which=self.which(semble_absent=True))

        self.assertNotIn("cannot run", decision.reason)

    def test_no_nudge_when_the_cli_is_broken_and_rtk_is_missing(self):
        decision = self.decide(
            self.grep_payload(),
            CLAUDE_ENV,
            which=self.which(rtk=None, shebang="#!/nonexistent/python3"),
        )

        self.assertEqual(decision.kind, "noop")

    def test_cli_probe_failure_alone_does_not_stop_the_rtk_rung(self):
        decision = self.decide(
            self.grep_payload(),
            CLAUDE_ENV,
            which=self.which(shebang="#!/nonexistent/python3"),
        )

        self.assertEqual(decision.kind, "deny")
        self.assertIn("rtk grep -rn", decision.reason)

    def test_nudge_advertises_a_shim_whose_interpreter_exists(self):
        decision = self.decide(self.grep_payload(), CLAUDE_ENV, which=self.which())

        self.assertIn("semble search 'firewall install'", decision.reason)
        self.assertNotIn("cannot run", decision.reason)

    def test_nudge_names_the_directory_the_grep_call_carries(self):
        decision = self.decide(self.grep_payload(), CLAUDE_ENV)

        self.assertIn("'firewall install' src", decision.reason)

    def test_nudge_quotes_a_directory_that_carries_a_space(self):
        payload = self.grep_payload(session="s-spaced")
        payload["tool_input"]["path"] = "/home/me/My Docs/src"

        decision = self.decide(payload, CLAUDE_ENV)

        self.assertIn("'/home/me/My Docs/src'", decision.reason)

    def test_nudge_quotes_a_pattern_that_holds_a_substitution(self):
        payload = self.grep_payload(pattern="cost$(id -u)")

        decision = self.decide(payload, CLAUDE_ENV)

        self.assertIn("'cost$(id -u)'", decision.reason)

    def test_glob_nudge_strips_the_recursive_prefix_from_the_find_form(self):
        payload = {
            "session_id": "s-glob-prefix",
            "hook_event_name": "PreToolUse",
            "tool_name": "Glob",
            "tool_input": {"pattern": "**/*.py"},
        }

        decision = self.decide(payload, CLAUDE_ENV)

        self.assertIn("rtk find '*.py'", decision.reason)
        self.assertIn("semble search '**/*.py'", decision.reason)
        self.assertNotIn("rtk find '**/*.py'", decision.reason)

    def test_glob_nudge_offers_grep_when_no_find_form_exists(self):
        for pattern in ("src/**/*.py", "**/src/*.py", "src/*.py"):
            with self.subTest(pattern=pattern):
                payload = {
                    "session_id": f"s-glob-{pattern}",
                    "hook_event_name": "PreToolUse",
                    "tool_name": "Glob",
                    "tool_input": {"pattern": pattern},
                }

                decision = self.decide(payload, CLAUDE_ENV)

                self.assertEqual(decision.kind, "deny")
                self.assertNotIn("rtk find", decision.reason)
                self.assertIn(f"rtk grep -rn '{pattern}' .", decision.reason)

    def test_glob_nudge_collapses_a_repeated_recursive_prefix(self):
        payload = {
            "session_id": "s-glob-double-prefix",
            "hook_event_name": "PreToolUse",
            "tool_name": "Glob",
            "tool_input": {"pattern": "**/**/*.py"},
        }

        decision = self.decide(payload, CLAUDE_ENV)

        self.assertIn("rtk find '*.py'", decision.reason)

    def test_nudge_quotes_a_placeholder_for_a_call_with_no_pattern(self):
        payload = {
            "hookEventName": "pre_tool_use",
            "sessionId": "s-grok-listdir",
            "toolName": "list_dir",
            "toolInput": {"target_directory": "/srv/app/src"},
        }

        decision = self.decide(payload, GROK_ENV)

        self.assertEqual(decision.kind, "deny")
        self.assertIn("'<pattern>'", decision.reason)
        self.assertIn("/srv/app/src", decision.reason)
        self.assertNotIn('""', decision.reason)

    def test_nudge_falls_back_to_the_working_directory(self):
        payload = {
            "session_id": "s-claude-glob",
            "hook_event_name": "PreToolUse",
            "tool_name": "Glob",
            "tool_input": {},
        }

        decision = self.decide(payload, CLAUDE_ENV)

        self.assertEqual(decision.kind, "deny")
        self.assertIn("'<pattern>' .", decision.reason)
        self.assertNotIn('""', decision.reason)

    def test_native_binary_without_a_shebang_counts_as_ready(self):
        shim = Path(self._tmp.name) / "bin" / "semble-binary"
        shim.parent.mkdir(parents=True, exist_ok=True)
        shim.write_bytes(b"\x7fELF\x02\x01\x01\x00binary")
        shim.chmod(0o755)

        self.assertTrue(hook_policy.semble_cli_ready(str(shim)))

    def test_env_shebang_resolves_the_interpreter(self):
        ready = self.make_semble_shim("#!/usr/bin/env sh", name="semble-ready")
        missing = self.make_semble_shim(
            "#!/usr/bin/env definitely-not-a-binary", name="semble-missing"
        )

        self.assertTrue(hook_policy.semble_cli_ready(str(ready)))
        self.assertFalse(hook_policy.semble_cli_ready(str(missing)))

    def test_an_absent_path_is_never_ready(self):
        self.assertFalse(hook_policy.semble_cli_ready(None))
        self.assertFalse(hook_policy.semble_cli_ready("/nonexistent/semble"))

    def test_commandcode_read_tool_is_never_nudged(self):
        payload = commandcode_payload()
        payload["tool_name"] = "read_file"
        payload["tool_display_name"] = "READ"
        payload["tool_input"] = {"absolute_path": "/tmp/x.py"}

        self.assertEqual(self.decide(payload, COMMANDCODE_ENV).kind, "noop")


class SessionContextTestCase(HookTestCase):
    def test_claude_session_start_injects_the_command_style_digest(self):
        payload = {"session_id": "s", "hook_event_name": "SessionStart", "source": "startup"}
        decision = self.decide(payload, CLAUDE_ENV)

        self.assertEqual(decision.kind, "context")
        self.assertIn("rtk", decision.text)
        self.assertIn("semble", decision.text)
        self.assertLess(len(decision.text), 10000)

    def test_commandcode_session_start_injects_the_digest(self):
        payload = {"session_id": "s", "hook_event_name": "SessionStart", "source": "startup"}
        decision = self.decide(payload, COMMANDCODE_ENV)

        self.assertEqual(decision.kind, "context")
        self.assertIn("rtk", decision.text)

    def test_grok_session_start_is_observe_only(self):
        payload = {"hookEventName": "session_start", "sessionId": "s"}
        decision = self.decide(payload, GROK_ENV)

        self.assertEqual(decision.kind, "noop")

    def test_unrelated_events_are_ignored(self):
        payload = {"session_id": "s", "hook_event_name": "PostToolUse", "tool_name": "Bash"}
        self.assertEqual(self.decide(payload, CLAUDE_ENV).kind, "noop")


class EncodingTestCase(HookTestCase):
    def test_claude_deny_uses_permission_decision(self):
        reply = hook_harness.encode(
            hook_harness.HARNESS_CLAUDE, Decision.deny("stop")
        )

        self.assertEqual(reply["hookSpecificOutput"]["hookEventName"], "PreToolUse")
        self.assertEqual(reply["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(reply["hookSpecificOutput"]["permissionDecisionReason"], "stop")

    def test_claude_rewrite_never_grants_approval(self):
        reply = hook_harness.encode(
            hook_harness.HARNESS_CLAUDE,
            Decision.rewrite({"command": REWRITTEN}, "wrapped"),
        )

        body = reply["hookSpecificOutput"]
        self.assertEqual(body["updatedInput"], {"command": REWRITTEN})
        self.assertNotIn("permissionDecision", body)
        self.assertNotIn("permissionDecisionReason", body)

    def test_grok_deny_uses_the_top_level_decision(self):
        reply = hook_harness.encode(hook_harness.HARNESS_GROK, Decision.deny("stop"))

        self.assertEqual(reply["decision"], "deny")
        self.assertEqual(reply["reason"], "stop")

    def test_grok_rewrite_carries_only_the_updated_input(self):
        reply = hook_harness.encode(
            hook_harness.HARNESS_GROK, Decision.rewrite({"command": REWRITTEN}, "wrapped")
        )

        body = reply["hookSpecificOutput"]
        self.assertEqual(body["updatedInput"], {"command": REWRITTEN})
        self.assertNotIn("permissionDecision", body)

    def test_a_rewrite_for_a_pushing_command_never_grants_approval(self):
        for harness in (hook_harness.HARNESS_CLAUDE, hook_harness.HARNESS_GROK):
            with self.subTest(harness=harness):
                reply = hook_harness.encode(
                    harness, Decision.rewrite({"command": "rtk git push"}, "wrapped")
                )
                body = reply["hookSpecificOutput"]

                self.assertNotIn("permissionDecision", body)
                self.assertNotIn("allow", json.dumps(reply))

    def test_commandcode_deny_uses_permission_decision(self):
        reply = hook_harness.encode(
            hook_harness.HARNESS_COMMANDCODE, Decision.deny("stop")
        )

        body = reply["hookSpecificOutput"]
        self.assertEqual(body["permissionDecision"], "deny")
        self.assertEqual(body["permissionDecisionReason"], "stop")

    def test_context_uses_additional_context_on_the_supported_harnesses(self):
        for harness in (hook_harness.HARNESS_CLAUDE, hook_harness.HARNESS_COMMANDCODE):
            with self.subTest(harness=harness):
                reply = hook_harness.encode(harness, Decision.inject("digest"))
                body = reply["hookSpecificOutput"]
                self.assertEqual(body["hookEventName"], "SessionStart")
                self.assertEqual(body["additionalContext"], "digest")

    def test_grok_session_context_has_no_reply_shape(self):
        self.assertIsNone(
            hook_harness.encode(hook_harness.HARNESS_GROK, Decision.inject("digest"))
        )

    def test_noop_and_unsupported_kinds_encode_to_nothing(self):
        self.assertIsNone(hook_harness.encode(hook_harness.HARNESS_CLAUDE, Decision.noop()))
        self.assertIsNone(hook_harness.encode(hook_harness.HARNESS_GROK, Decision.noop()))


class BudgetTestCase(HookTestCase):
    def test_first_consume_succeeds_and_the_second_fails(self):
        first = hook_policy.consume("s", "shell", cache_root=self.cache_root)
        second = hook_policy.consume("s", "shell", cache_root=self.cache_root)

        self.assertTrue(first)
        self.assertFalse(second)

    def test_keys_and_sessions_are_independent(self):
        self.assertTrue(hook_policy.consume("s1", "shell", cache_root=self.cache_root))
        self.assertTrue(hook_policy.consume("s1", "grep", cache_root=self.cache_root))
        self.assertTrue(hook_policy.consume("s2", "shell", cache_root=self.cache_root))

    def test_corrupt_state_file_reads_as_fresh(self):
        path = hook_policy.session_state_path("s", cache_root=self.cache_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json", encoding="utf-8")

        self.assertTrue(hook_policy.consume("s", "shell", cache_root=self.cache_root))

    def test_state_file_that_is_not_an_object_reads_as_fresh(self):
        path = hook_policy.session_state_path("s", cache_root=self.cache_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[1, 2, 3]", encoding="utf-8")

        self.assertTrue(hook_policy.consume("s", "shell", cache_root=self.cache_root))
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"shell": 1})

    def test_unwritable_state_never_blocks(self):
        cache_root = Path(self._tmp.name) / "file-not-a-dir"
        cache_root.write_text("", encoding="utf-8")

        self.assertFalse(hook_policy.consume("s", "shell", cache_root=cache_root))

    def test_state_write_failure_never_blocks(self):
        path = hook_policy.session_state_path("s", cache_root=self.cache_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.with_name(path.name + ".tmp").mkdir()

        self.assertFalse(hook_policy.consume("s", "shell", cache_root=self.cache_root))

    def test_prune_survives_a_root_that_is_not_a_directory(self):
        blocker = Path(self._tmp.name) / "not-a-directory"
        blocker.write_text("", encoding="utf-8")

        hook_policy._prune_stale(blocker, time.time())

        self.assertTrue(blocker.exists())

    def test_session_ids_cannot_escape_the_cache_directory(self):
        path = hook_policy.session_state_path("../../etc/passwd", cache_root=self.cache_root)

        self.assertEqual(path.parent, self.cache_root.resolve())
        self.assertNotIn("..", path.name)

    def test_parallel_consumers_spend_the_budget_once(self):
        results = []
        barrier = threading.Barrier(8)

        def spend():
            barrier.wait()
            results.append(hook_policy.consume("racy", "shell", cache_root=self.cache_root))

        threads = [threading.Thread(target=spend) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(results.count(True), 1)

    def test_stale_state_files_are_pruned(self):
        stale = hook_policy.session_state_path("old-session", cache_root=self.cache_root)
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text("{}", encoding="utf-8")
        old = time.time() - (hook_policy.STATE_MAX_AGE_DAYS + 1) * 24 * 3600
        os.utime(stale, (old, old))

        self.assertTrue(hook_policy.consume("fresh-session", "shell", cache_root=self.cache_root))

        self.assertFalse(stale.exists())
        self.assertTrue(hook_policy.session_state_path("fresh-session", cache_root=self.cache_root).exists())

    def test_recent_state_files_survive_a_prune(self):
        recent = hook_policy.session_state_path("recent-session", cache_root=self.cache_root)
        recent.parent.mkdir(parents=True, exist_ok=True)
        recent.write_text('{"shell": 1}', encoding="utf-8")

        hook_policy.consume("fresh-session", "shell", cache_root=self.cache_root)

        self.assertTrue(recent.exists())

    def test_probe_budgets_stay_inside_the_wired_hook_timeout(self):
        self.assertLess(
            hook_policy.RTK_TIMEOUT_SECONDS, install_hooks.HOOK_TIMEOUT_SECONDS
        )


class EntrypointTestCase(HookTestCase):
    def run_main(self, raw: str, env=None):
        stdout = io.StringIO()
        with unittest.mock.patch.dict("os.environ", env or CLAUDE_ENV):
            code = contract_hook.main(stdin=io.StringIO(raw), stdout=stdout)
        return code, stdout.getvalue()

    @unittest.skipUnless(shutil.which("rtk"), "rtk is not installed")
    def test_prints_the_encoded_reply_for_a_rewritable_command(self):
        payload = json.dumps(claude_payload())
        code, out = self.run_main(payload)

        self.assertEqual(code, 0)
        reply = json.loads(out)
        self.assertEqual(
            reply["hookSpecificOutput"]["updatedInput"]["command"], REWRITTEN
        )

    def test_prints_nothing_and_exits_zero_on_malformed_input(self):
        for raw in ("", "not json", "[]", "null"):
            with self.subTest(raw=raw):
                code, out = self.run_main(raw)
                self.assertEqual(code, 0)
                self.assertEqual(out, "")

    def test_fails_open_when_the_payload_has_no_known_shape(self):
        code, out = self.run_main(json.dumps({"unexpected": True}))

        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_a_closed_stdout_exits_zero_without_raising(self):
        class BrokenSink(io.StringIO):
            def write(self, text):
                raise BrokenPipeError("harness closed the pipe")

        decision = Decision.rewrite({"command": REWRITTEN}, "wrapped")
        with unittest.mock.patch.object(hook_policy, "decide", return_value=decision):
            code = contract_hook.main(
                stdin=io.StringIO(json.dumps(claude_payload())), stdout=BrokenSink()
            )

        self.assertEqual(code, 0)

    def test_internal_failure_writes_one_stderr_line_and_exits_zero(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with unittest.mock.patch.object(
            hook_policy, "decide", side_effect=RuntimeError("boom")
        ), contextlib.redirect_stderr(stderr):
            code = contract_hook.main(stdin=io.StringIO(json.dumps(claude_payload())), stdout=stdout)

        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("contract_hook: RuntimeError: boom", stderr.getvalue())


class ScriptInvocationTestCase(HookTestCase):
    def run_script(self, raw: str, env=None):
        environment = {**os.environ, **(env or CLAUDE_ENV), "XDG_CACHE_HOME": str(self.cache_root)}
        return subprocess.run(
            [sys.executable, str(HOOKS_DIR / "contract_hook.py")],
            input=raw,
            capture_output=True,
            text=True,
            timeout=30,
            env=environment,
        )

    @unittest.skipUnless(shutil.which("rtk"), "rtk is not installed")
    def test_runs_as_the_harness_runs_it(self):
        for payload, env in (
            (claude_payload(), CLAUDE_ENV),
            (grok_payload(), GROK_ENV),
            (commandcode_payload(), COMMANDCODE_ENV),
        ):
            with self.subTest(env=env):
                result = self.run_script(json.dumps(payload), env)
                self.assertEqual(result.returncode, 0)
                self.assertTrue(result.stdout.strip())
                json.loads(result.stdout)

    def test_exits_zero_with_no_output_on_garbage(self):
        result = self.run_script("not json at all")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_grok_session_start_prints_nothing(self):
        result = self.run_script(
            json.dumps({"hookEventName": "session_start", "sessionId": "s"}), GROK_ENV
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
