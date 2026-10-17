"""hook_policy.py — Command Style and discovery decisions the contract hook enforces.

exports: BUDGET_LIMIT | CACHE_DIR_NAME | RTK_BIN | RTK_TIMEOUT_SECONDS | SEMBLE_BIN | SESSION_CONTEXT | SHELL_BUDGET_KEY | STATE_MAX_AGE_DAYS | consume | decide | default_cache_root | discovery_budget_key | deny_text | discovery_text | rtk_rewrite | semble_cli_ready | semble_mcp_tool | session_state_path
used_by: .agents/skills/agents-contract/hooks/contract_hook.py → decide [cascade]
used_by: tests/test_contract_hook.py → consume, decide, session_state_path [cascade]
related: hook_harness.py holds detection and the reply shapes; AGENTS.md → Command Style and the tool ladder are the rules enforced here.
rules:   Never block on a state the hook cannot read: a missing binary, an unreadable cache, a failed rtk lookup, or an unknown tool all resolve to Decision.noop(). Each deny is bounded by BUDGET_LIMIT per session and key, so a harness that ignores the reason cannot loop. A refusal must name a command the model can run as written, so no suggested argument is ever empty.
agent:   grok-build | xai | 2026-10-17 | 01a14a7c-788f-7061-83bb-6dded52bc3b5 | first cut: rtk-owned rewrite lookup, bounded deny budgets on a per-session state file, discovery nudge with the exact ladder command
agent:   grok-build | xai | 2026-10-18 | 01a14ad3-ab3e-74b1-81d5-fc6f08b61af7 | fixed the empty-query nudge: Grok's list_dir sends target_directory, so a call with no pattern now quotes a placeholder and the directory it carries
agent:   grok-build | xai | 2026-10-18 | 01a14ad3-ab3e-74b1-81d5-fc6f08b61af7 | both reasons now name `rtk bypass`, the one form the engine leaves untouched — the rewrite path has no budget, so an agent that needs the full output has no other route
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping

try:
    import fcntl
except ImportError:
    fcntl = None

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import hook_harness
from hook_harness import Decision

RTK_BIN = "rtk"
SEMBLE_BIN = "semble"
RTK_TIMEOUT_SECONDS = 3
STATE_MAX_AGE_DAYS = 7
_SECONDS_PER_DAY = 86400
_SHEBANG_BYTES = 256
BUDGET_LIMIT = 1
SHELL_BUDGET_KEY = "shell"
CACHE_DIR_NAME = "lowheat-hooks"
_RAW_FORM = "rtk bypass"
REWRITE_REASON = (
    "agents-contract Command Style: rtk wraps this command and compresses its "
    f"output. Write `{_RAW_FORM} <command>` when you need the output untouched."
)
_BUDGET_SESSION_CHARS = 64
_SAFE_SESSION_RE = re.compile(r"[^A-Za-z0-9._-]")
_PATTERN_KEYS = ("pattern", "query", "regex")
_DIRECTORY_KEYS = ("path", "target_directory", "directory")
_PATTERN_PLACEHOLDER = "<pattern>"

SESSION_CONTEXT = (
    "agents-contract (lowheat) is active. Command Style: shell commands run through rtk, the "
    "proxy that compresses their output — this session's PreToolUse hook rewrites a command to "
    "its rtk form where the harness allows it, and refuses one raw command per session with the "
    "rtk form to re-issue. Code discovery ladder: semble search (MCP or CLI) → rtk grep → native "
    "Grep/Glob; the first native Grep and the first native Glob call each session are refused once "
    "with the cheapest rung that actually runs (the semble MCP tool, the semble CLI when it "
    "executes, or rtk grep). Native Read stays correct for reading a file once its location is "
    "known. Details: AGENTS.md → Command Style, RTK.md, semble.md."
)


def default_cache_root() -> Path:
    """Return the directory that holds the per-session deny budgets.

    Rules:   Resolve it on call, never at import, so a harness that sets XDG_CACHE_HOME after this module loads still gets its own directory.
    """
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / CACHE_DIR_NAME


def session_state_path(session_id: str, cache_root: Path | None = None) -> Path:
    """Return the state file that records one session's spent budgets.

    Rules:   The session id arrives from a harness, so keep only [A-Za-z0-9._-] and 64 characters of it — the resolved file must never sit outside the cache directory.
    """
    root = (cache_root if cache_root is not None else default_cache_root()).resolve()
    safe = _SAFE_SESSION_RE.sub("_", str(session_id or ""))[:_BUDGET_SESSION_CHARS]
    safe = safe.strip("._") or "shared"
    return root / f"{safe}.json"


def consume(
    session_id: str,
    key: str,
    limit: int = BUDGET_LIMIT,
    cache_root: Path | None = None,
) -> bool:
    """Spend one unit of a per-session budget and report whether it was available.

    Rules:   False means do not act. The read-modify-write runs under an exclusive lock, because a harness may run the same hook for several tool calls at once, and two of them must never spend the same unit. A corrupt state file counts as fresh, but any read or write failure returns False, so an unusable cache can never turn into a repeated deny.
    """
    path = session_state_path(session_id, cache_root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False
    fresh = not path.exists()
    lock_path = path.with_name(path.name + ".lock")
    try:
        with open(lock_path, "a+", encoding="utf-8") as handle:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                spent = _spend(path, key, limit)
            finally:
                if fcntl is not None:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError:
        return False
    # Rules: a new session file is the cheap moment to sweep the cache — pruning on every spend would list the directory on the hot path.
    if spent and fresh:
        _prune_stale(path.parent, time.time())
    return spent


def _spend(path: Path, key: str, limit: int) -> bool:
    """Record one spent unit in the state file and report whether it was available.

    Rules:   Caller holds the lock. Any state the parse yields that is not an object counts as empty rather than raising — a state file a harness or a user mangled must not break the hook.
    """
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    if not isinstance(state, dict):
        state = {}
    value = state.get(key, 0)
    used = value if isinstance(value, int) and value >= 0 else 0
    if used >= limit:
        return False
    staged = path.with_name(path.name + ".tmp")
    try:
        staged.write_text(json.dumps({**state, key: used + 1}), encoding="utf-8")
        os.replace(staged, path)
    except OSError:
        return False
    return True


def _prune_stale(root: Path, now: float) -> None:
    """Delete state files no session can still be using.

    Rules:   Best effort — an unreadable directory or an undeletable file is skipped, because a stale cache is harmless while a failed hook is not.
    """
    cutoff = now - STATE_MAX_AGE_DAYS * _SECONDS_PER_DAY
    try:
        entries = list(root.iterdir())
    except OSError:
        return
    for entry in entries:
        try:
            if entry.is_file() and entry.stat().st_mtime < cutoff:
                entry.unlink()
        except OSError:
            continue


def discovery_budget_key(tool: str) -> str:
    """Return the budget key one discovery tool spends.

    Rules:   One key per tool so a Grep nudge never spends the Glob budget; lower-case the tool name so every harness alias shares its key.
    """
    return f"discovery:{tool.strip().lower()}"


def rtk_rewrite(command: str, run: Callable[..., Any] | None = None) -> str | None:
    """Return the rtk form of a shell command, or None when there is none.

    Rules:   rtk owns the wrap-or-raw decision — never re-derive it here. Every failure (missing binary, timeout, non-zero exit, unparseable reply, unchanged command) returns None, and the command then runs as written.
    """
    runner = run if run is not None else subprocess.run
    request = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    try:
        result = runner(
            [RTK_BIN, "hook", "claude"],
            input=request,
            capture_output=True,
            text=True,
            timeout=RTK_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if getattr(result, "returncode", 1) != 0:
        return None
    try:
        reply = json.loads(getattr(result, "stdout", "") or "")
    except ValueError:
        return None
    if not isinstance(reply, dict):
        return None
    output = reply.get("hookSpecificOutput")
    updated = output.get("updatedInput") if isinstance(output, dict) else None
    rewritten = updated.get("command") if isinstance(updated, dict) else None
    if not isinstance(rewritten, str) or not rewritten.strip() or rewritten == command:
        return None
    return rewritten


def semble_cli_ready(path: str | None) -> bool:
    """Report whether a semble executable the caller resolved can actually launch.

    Rules:   Never run the binary — `semble -V` costs 3–5 s because it imports the embedding stack, far too slow for a hook that runs inside a tool call. Read the shebang instead and confirm its interpreter exists: a uv-tool or pipx shim whose venv python vanished is the failure mode that makes an "installed" binary exit 127.
    """
    if not path:
        return False
    target = Path(path)
    try:
        with target.open("rb") as handle:
            header = handle.read(_SHEBANG_BYTES)
    except OSError:
        return False
    if not header.startswith(b"#!"):
        return True
    line = header.split(b"\n", 1)[0][2:].decode("utf-8", "replace").strip()
    parts = line.split()
    if not parts:
        return False
    interpreter = parts[0]
    if Path(interpreter).name == "env" and len(parts) > 1:
        interpreter = parts[1]
    resolved = interpreter if os.path.isabs(interpreter) else shutil.which(interpreter)
    return bool(resolved) and Path(resolved).exists()


def semble_mcp_tool(harness: str) -> str:
    """Return the semble MCP tool name one harness exposes.

    Rules:   Claude Code qualifies MCP tools as mcp__<server>__<tool> and Grok names them <server>__<tool>; name the tool a harness can actually call.
    """
    prefix = "mcp__" if harness == hook_harness.HARNESS_CLAUDE else ""
    return f"{prefix}semble__search"


def deny_text(rewritten: str) -> str:
    """Return the reason that carries the rtk form of a refused command.

    Rules:   Name the exact replacement command and the one escape hatch — output the caller will parse or redirect stays raw through `rtk bypass`, which the rtk engine never rewrites; the model reads this text as the tool result, so it must be actionable on its own.
    """
    return (
        "agents-contract Command Style: this command has an rtk form. Re-issue it as: "
        f"`{rewritten}`. rtk runs the same command and compresses its output; write "
        f"`{_RAW_FORM} <command>` for output you will parse or redirect. This refusal "
        "fires once per session."
    )


def _first_text(arguments: Mapping[str, Any], keys: tuple[str, ...]) -> str:
    """Return the first non-blank string the call carries under keys.

    Rules:   Harnesses name the same field differently, so probe the aliases in order and return an empty string when none carries text — callers substitute a placeholder rather than quoting an empty argument.
    """
    for key in keys:
        value = arguments.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def discovery_text(
    tool: str,
    arguments: Mapping[str, Any],
    harness: str,
    has_semble_cli: bool,
    has_rtk: bool,
    cli_installed: bool,
) -> str:
    """Return the reason that points a refused native search at the ladder.

    Rules:   Quote the pattern with json.dumps so a pattern carrying quotes or backslashes cannot break the reason, and quote _PATTERN_PLACEHOLDER when the call carries none — Grok's list_dir sends target_directory where a search sends pattern, and a refusal must never suggest an empty argument. The directory the call carried is quoted the same way, because a path with a space or a shell metacharacter is unrunnable as written. Name only rungs the hook has verified it can run, and say so when the CLI is installed but cannot execute — a shim on PATH that fails at exec time must never be recommended.
    """
    query = _first_text(arguments, _PATTERN_KEYS) or _PATTERN_PLACEHOLDER
    directory = json.dumps(_first_text(arguments, _DIRECTORY_KEYS) or ".")
    options = [f"the semble MCP {semble_mcp_tool(harness)} tool"]
    if has_semble_cli:
        options.append(
            f"semble search {json.dumps(query)} {directory} --max-snippet-lines 10"
        )
    if has_rtk:
        if tool.strip().lower() in hook_harness.DISCOVERY_TOOLS - {"grep"}:
            options.append(f"rtk find {json.dumps(query)} {directory}")
        else:
            options.append(f"rtk grep -rn {json.dumps(query)} {directory}")
    note = ""
    if cli_installed and not has_semble_cli:
        note = (
            " The semble CLI is on PATH here but cannot run (its shebang interpreter "
            "is missing), so rung 2 is unavailable."
        )
    return (
        f"agents-contract discovery ladder: semble MCP → semble CLI → rtk grep → native {tool} "
        f"(rung 4). This call was refused once. Try: {', '.join(options)}.{note} "
        "Exact line:content, every literal occurrence, and lossless reads stay native — "
        "re-issue this call and it runs; the nudge fires once per session per tool."
    )


def decide(
    payload: Mapping[str, Any],
    env: Mapping[str, str] | None = None,
    run: Callable[..., Any] | None = None,
    which: Callable[[str], str | None] | None = None,
    cache_root: Path | None = None,
) -> Decision:
    """Turn one harness event into the decision the contract hook applies.

    Rules:   An unrecognized event, tool, or missing binary resolves to Decision.noop(); only a SessionStart injects context, only a rewritable shell command is rewritten, and only a first-time native search is refused. Grok gets no SessionStart context because it discards hook output there.
    """
    environment = env if env is not None else os.environ
    lookup = which if which is not None else shutil.which
    harness = hook_harness.detect_harness(payload, environment)
    event = hook_harness.event_name(payload, environment, harness)
    if event == "SessionStart":
        return _session_context(harness)
    if event != "PreToolUse":
        return Decision.noop()
    name = hook_harness.tool_name(payload, harness).lower()
    if name in hook_harness.SHELL_TOOLS:
        return _shell_decision(payload, environment, harness, run, lookup, cache_root)
    if name in hook_harness.DISCOVERY_TOOLS:
        return _discovery_decision(payload, environment, harness, lookup, cache_root)
    return Decision.noop()


def _session_context(harness: str) -> Decision:
    """Return the Command Style digest a session-start event injects.

    Rules:   Grok reads only a top-level systemMessage on SessionStart, so it gets no context decision — the contract reaches it through AGENTS.md instead.
    """
    if harness == hook_harness.HARNESS_GROK:
        return Decision.noop()
    return Decision.inject(SESSION_CONTEXT)


def _shell_decision(
    payload: Mapping[str, Any],
    env: Mapping[str, str],
    harness: str,
    run: Callable[..., Any] | None,
    lookup: Callable[[str], str | None],
    cache_root: Path | None,
) -> Decision:
    """Return the rewrite or single refusal a shell command earns.

    Rules:   A harness that can rewrite gets the rtk form silently; Command Code cannot rewrite, so it gets one refusal per session carrying the command to re-issue; a command rtk leaves alone is never touched.
    """
    if not lookup(RTK_BIN):
        return Decision.noop()
    arguments = hook_harness.tool_input(payload, harness)
    command = arguments.get("command")
    if not isinstance(command, str) or not command.strip():
        return Decision.noop()
    rewritten = rtk_rewrite(command, run)
    if rewritten is None:
        return Decision.noop()
    if harness in (hook_harness.HARNESS_CLAUDE, hook_harness.HARNESS_GROK):
        return Decision.rewrite({**arguments, "command": rewritten}, REWRITE_REASON)
    session = hook_harness.session_id(payload, harness, env)
    if consume(session, SHELL_BUDGET_KEY, cache_root=cache_root):
        return Decision.deny(deny_text(rewritten))
    return Decision.noop()


def _discovery_decision(
    payload: Mapping[str, Any],
    env: Mapping[str, str],
    harness: str,
    lookup: Callable[[str], str | None],
    cache_root: Path | None,
) -> Decision:
    """Return the one refusal a native search earns per session.

    Rules:   Check the launchable rungs before spending the budget — a nudge that names nothing the harness can run must not consume the call, and the budget is spent even when the model later retries the same tool.
    """
    semble_path = lookup(SEMBLE_BIN)
    has_rtk = bool(lookup(RTK_BIN))
    has_semble_cli = semble_cli_ready(semble_path)
    if not (has_rtk or has_semble_cli):
        return Decision.noop()
    name = hook_harness.tool_name(payload, harness)
    session = hook_harness.session_id(payload, harness, env)
    if not consume(session, discovery_budget_key(name), cache_root=cache_root):
        return Decision.noop()
    return Decision.deny(
        discovery_text(
            name,
            hook_harness.tool_input(payload, harness),
            harness,
            has_semble_cli,
            has_rtk,
            semble_path is not None,
        )
    )

