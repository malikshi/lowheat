"""hook_harness.py — Harness detection and reply shapes for the agents-contract hook.

exports: HARNESS_CLAUDE | HARNESS_GROK | HARNESS_COMMANDCODE | KIND_CONTEXT | KIND_DENY | KIND_NOOP | KIND_REWRITE | SHELL_TOOLS | DISCOVERY_TOOLS | Decision | detect_harness | event_name | tool_name | tool_input | session_id | encode
used_by: .agents/skills/agents-contract/hooks/hook_policy.py → Decision, DISCOVERY_TOOLS, SHELL_TOOLS, detect_harness, event_name, session_id, tool_input, tool_name [cascade]
used_by: .agents/skills/agents-contract/hooks/contract_hook.py → detect_harness, encode [cascade]
used_by: tests/test_contract_hook.py → Decision, HARNESS_CLAUDE, HARNESS_GROK, HARNESS_COMMANDCODE, SHELL_TOOLS, DISCOVERY_TOOLS, detect_harness, event_name, tool_name, encode [cascade]
rules:   Emit only a shape the target harness documents: Claude Code and Command Code read hookSpecificOutput, Grok reads hookSpecificOutput.updatedInput and its own top-level decision, and a Grok SessionStart is observe-only, so a context decision encodes to None. A rewrite never grants approval — no permissionDecision on the rewrite path, so the harness's own permission rules still see the rewritten command. An unknown payload shape reads as Claude Code — the three wired harnesses are the only callers.
agent:   grok-build | xai | 2026-10-17 | 01a14a7c-788f-7061-83bb-6dded52bc3b5 | first cut: env-then-payload detection, alias tables for shell and discovery tools, four decision kinds, per-harness encoders
agent:   grok-build | xai | 2026-10-18 | 01a14ad3-ab3e-74b1-81d5-fc6f08b61af7 | dropped permissionDecision allow from the Claude Code rewrite reply: it skipped the permission prompt, so a wrapped `git push` ran without the approval the contract requires
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

HARNESS_CLAUDE = "claude"
HARNESS_GROK = "grok"
HARNESS_COMMANDCODE = "commandcode"

KIND_NOOP = "noop"
KIND_DENY = "deny"
KIND_REWRITE = "rewrite"
KIND_CONTEXT = "context"

SHELL_TOOLS = frozenset(
    {"bash", "shell", "powershell", "run_terminal_command", "shell_command"}
)
DISCOVERY_TOOLS = frozenset({"grep", "glob", "list_dir"})

_EVENT_ALIASES = {
    "pretooluse": "PreToolUse",
    "sessionstart": "SessionStart",
}
_EVENT_ENV = {
    HARNESS_GROK: "GROK_HOOK_EVENT",
    HARNESS_COMMANDCODE: "COMMANDCODE_HOOK_EVENT",
}
_SESSION_ENV = {
    HARNESS_GROK: "GROK_SESSION_ID",
    HARNESS_COMMANDCODE: "COMMANDCODE_SESSION_ID",
}


@dataclass(frozen=True)
class Decision:
    """One hook outcome in harness-neutral terms.

    Rules:   Build every outcome through noop, deny, rewrite, or inject — the kind string is what encode switches on, and an unknown kind encodes to nothing rather than to a guess.
    """

    kind: str = KIND_NOOP
    reason: str = ""
    updated_input: Mapping[str, Any] | None = None
    text: str = ""

    @classmethod
    def noop(cls) -> "Decision":
        """Return the outcome that leaves the tool call untouched.

        Rules:   An unwired event, an unknown tool, and a missing binary all resolve here — the hook never blocks on a state it cannot read.
        """
        return cls(kind=KIND_NOOP)

    @classmethod
    def deny(cls, reason: str) -> "Decision":
        """Return the outcome that refuses the tool call with a reason the model reads.

        Rules:   The reason is shown to the model, so it carries the replacement command — never a bare refusal.
        """
        return cls(kind=KIND_DENY, reason=reason)

    @classmethod
    def rewrite(cls, updated_input: Mapping[str, Any], reason: str) -> "Decision":
        """Return the outcome that replaces the tool input before it runs.

        Rules:   updated_input replaces the whole input object, so callers pass every unchanged field alongside the rewritten one.
        """
        return cls(kind=KIND_REWRITE, reason=reason, updated_input=updated_input)

    @classmethod
    def inject(cls, text: str) -> "Decision":
        """Return the outcome that appends session context for the model.

        Rules:   Only Claude Code and Command Code read this on SessionStart; Grok discards hook output there, and encode returns None for it.
        """
        return cls(kind=KIND_CONTEXT, text=text)


def detect_harness(payload: Mapping[str, Any], env: Mapping[str, str]) -> str:
    """Return the harness that fired the hook.

    Rules:   The environment decides first — Grok and Command Code always set their event variable — then the payload shape; anything else reads as Claude Code.
    """
    if env.get(_EVENT_ENV[HARNESS_GROK]) or "toolName" in payload:
        return HARNESS_GROK
    if env.get(_EVENT_ENV[HARNESS_COMMANDCODE]) or "tool_display_name" in payload:
        return HARNESS_COMMANDCODE
    return HARNESS_CLAUDE


def event_name(payload: Mapping[str, Any], env: Mapping[str, str], harness: str) -> str:
    """Return the event as SessionStart, PreToolUse, or other.

    Rules:   The payload event decides, with the harness event variable as the fallback; Grok sends hookEventName in snake case and its variable in Pascal case, so normalize every spelling through one alias table and read an unrecognized event as other.
    """
    raw = str(payload.get("hookEventName") or payload.get("hook_event_name") or "")
    if not raw:
        raw = str(env.get(_EVENT_ENV.get(harness, "")) or "")
    key = raw.replace("_", "").replace("-", "").strip().lower()
    return _EVENT_ALIASES.get(key, "other")


def tool_name(payload: Mapping[str, Any], harness: str) -> str:
    """Return the tool name the event carries.

    Rules:   Grok sends toolName, Claude Code and Command Code send tool_name; an absent name returns an empty string so the policy reads the call as an unknown tool.
    """
    key = "toolName" if harness == HARNESS_GROK else "tool_name"
    return str(payload.get(key) or "")


def tool_input(payload: Mapping[str, Any], harness: str) -> Mapping[str, Any]:
    """Return the tool arguments the event carries.

    Rules:   Grok sends toolInput, Claude Code and Command Code send tool_input; a missing or non-object value returns an empty mapping so callers read fields without a type check.
    """
    key = "toolInput" if harness == HARNESS_GROK else "tool_input"
    value = payload.get(key)
    return value if isinstance(value, Mapping) else {}


def session_id(payload: Mapping[str, Any], harness: str, env: Mapping[str, str]) -> str:
    """Return the session key the deny budgets are spent against.

    Rules:   Prefer the payload id, then the harness environment variable; fall back to one shared bucket so an unknown session still cannot be denied twice.
    """
    for key in ("session_id", "sessionId"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return str(env.get(_SESSION_ENV.get(harness, "")) or "shared")


def encode(harness: str, decision: Decision) -> dict[str, Any] | None:
    """Render a Decision into the reply the harness reads.

    Rules:   None means print nothing. A deny carries permissionDecision for Claude Code and Command Code and a top-level decision for Grok. A rewrite carries updatedInput and no permission decision, because a `permissionDecision` of `allow` skips the harness's own permission prompt — that would auto-approve commands the workspace contract says need explicit user approval, and would let whatever the external rewrite produced run unseen. Without it, the harness evaluates its own rules against the rewritten command. No harness shows a reason on a rewrite, so none is emitted. Context is read only by Claude Code and Command Code.
    """
    if decision.kind == KIND_DENY:
        if harness == HARNESS_GROK:
            return {"decision": "deny", "reason": decision.reason}
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": decision.reason,
            }
        }
    if decision.kind == KIND_REWRITE:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "updatedInput": dict(decision.updated_input or {}),
            }
        }
    if decision.kind == KIND_CONTEXT and harness in (HARNESS_CLAUDE, HARNESS_COMMANDCODE):
        return {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": decision.text,
            }
        }
    return None
