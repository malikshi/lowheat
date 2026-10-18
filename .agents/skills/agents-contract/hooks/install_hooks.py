"""install_hooks.py — Wire the contract hook into Claude Code, Grok, and Command Code.

exports: BACKUP_SUFFIX | COMMANDCODE_MATCHER | HARNESSES | HARNESS_CLAUDE | HARNESS_COMMANDCODE | HARNESS_GROK | HOOK_MATCHER | HOOK_SCRIPT_NAME | HOOK_TIMEOUT_SECONDS | MARKER | Change | InstallError | claude_settings_path | commandcode_settings_path | grok_hooks_path | handler_command | install | main | uninstall
used_by: tests/test_install_hooks.py → Change, HARNESS_*, HOOK_MATCHER, HOOK_SCRIPT_NAME, HOOK_TIMEOUT_SECONDS, MARKER, BACKUP_SUFFIX, InstallError, claude_settings_path, commandcode_settings_path, grok_hooks_path, handler_command, install, uninstall [cascade]
used_by: README.md → the hook wiring section
related: contract_hook.py is the script every entry runs; hook_harness.py names the three harnesses.
rules:   Merge, never overwrite: keep every existing key and every foreign handler, replace only handlers whose command carries MARKER, and copy the pristine file to BACKUP_SUFFIX once before the first write. A malformed target or a hooks key that is not an object raises InstallError with the file byte-identical — never write a half-parsed config. Every harness gets the same command string, because Grok loads the Claude settings file too and deduplicates handlers that run the same thing. The Grok hook file is one the installer creates, so its uninstall deletes that file only when stripping our handlers left nothing else in it.
agent:   grok-build | xai | 2026-10-17 | 01a14a7c-788f-7061-83bb-6dded52bc3b5 | first cut: per-harness settings paths, marker-based merge and uninstall, one-shot backup, dry-run
agent:   grok-build | xai | 2026-10-18 | 01a14ad3-ab3e-74b1-81d5-fc6f08b61af7 | Grok now merges like the others and keeps foreign handlers: uninstall restores the pristine copy, writes the stripped file when it gained foreign content, and deletes only an empty file ours alone filled; on review: shlex.quote both paths in the handler command (a space installed a dead hook, a metacharacter injected a second command), the strip removes only MARKER handlers so a foreign handler inside our group survives, and the settings write stages beside the target and moves with os.replace; second pass: expand `~` before quoting, which quoting had frozen, and resolve a symlinked settings file so a dotfiles link survives while its target is replaced; third pass: the CLI refuses a missing interpreter or script before writing, while an unwire still runs when the checkout is gone
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from hook_harness import HARNESS_CLAUDE, HARNESS_COMMANDCODE, HARNESS_GROK

HARNESSES = (HARNESS_CLAUDE, HARNESS_GROK, HARNESS_COMMANDCODE)
HOOK_SCRIPT_NAME = "contract_hook.py"
MARKER = HOOK_SCRIPT_NAME
HOOK_TIMEOUT_SECONDS = 10
HOOK_MATCHER = "Bash|Grep|Glob"
COMMANDCODE_MATCHER = "SHELL"
BACKUP_SUFFIX = ".lowheat-bak"


class InstallError(RuntimeError):
    """Raised when a target settings file cannot be merged safely.

    Rules:   Raise before any write — the caller must be able to trust that a failed install left every file byte-identical.
    """


@dataclass(frozen=True)
class Change:
    """One settings file the installer wrote, removed, or left alone."""

    harness: str
    path: Path
    action: str
    detail: str = ""


def claude_settings_path(home: Path | str) -> Path:
    """Return the Claude Code user settings file under home."""
    return Path(home) / ".claude" / "settings.json"


def grok_hooks_path(home: Path | str) -> Path:
    """Return the Grok user hook file under home."""
    return Path(home) / ".grok" / "hooks" / "contract.json"


def commandcode_settings_path(home: Path | str) -> Path:
    """Return the Command Code user settings file under home."""
    return Path(home) / ".commandcode" / "settings.json"


def handler_command(python: str, script: str) -> str:
    """Return the shell command a harness runs for the contract hook.

    Rules:   Both paths are absolute — a hook runs with the workspace as its working directory, so a relative path would resolve elsewhere or fail a folder-trust check. Expand `~` first: quoting the path stops the shell from expanding it, and a hook that cannot start is a silent failure. Quote each one for the shell: a space in a path would otherwise split the command into a program that does not exist, and a metacharacter would inject a second command the harness runs on every matching tool call.
    """
    return f"{shlex.quote(os.path.expanduser(python))} {shlex.quote(os.path.expanduser(script))}"


def _handler(python: str, script: str) -> dict[str, Any]:
    return {
        "type": "command",
        "command": handler_command(python, script),
        "timeout": HOOK_TIMEOUT_SECONDS,
    }


def _group(matcher: str | None, python: str, script: str) -> dict[str, Any]:
    """Return one matcher group, omitting the matcher where the event takes none.

    Rules:   Grok and Command Code ignore a matcher on SessionStart, and Command Code refuses to fire the hook at all when one is present, so a context-only group must carry no matcher key.
    """
    if matcher:
        return {"matcher": matcher, "hooks": [_handler(python, script)]}
    return {"hooks": [_handler(python, script)]}


def _read_text(path: Path) -> str:
    """Return the file text.

    Rules:   An unreadable file raises InstallError naming the path — the installer never guesses at content it could not read.
    """
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise InstallError(f"{path}: {error}") from error


def _parse_settings(text: str, path: Path) -> dict[str, Any]:
    """Return the parsed settings object.

    Rules:   Unparseable JSON or a root that is not an object raises InstallError — a config the installer cannot read must stay byte-identical.
    """
    try:
        data = json.loads(text)
    except ValueError as error:
        raise InstallError(f"{path}: {error}") from error
    if not isinstance(data, dict):
        raise InstallError(f"{path}: settings root is not a JSON object")
    return data


def _read_settings(path: Path) -> dict[str, Any]:
    """Return the parsed settings object, or an empty one when the file is absent."""
    if not path.exists():
        return {}
    return _parse_settings(_read_text(path), path)


def _hooks_object(data: dict[str, Any], path: Path) -> dict[str, Any]:
    """Return the settings hooks object, creating an empty one when absent.

    Rules:   A hooks key that is not an object raises InstallError — merging into it would drop whatever the file actually holds.
    """
    hooks = data.get("hooks")
    if hooks is None:
        hooks = {}
        data["hooks"] = hooks
    if not isinstance(hooks, dict):
        raise InstallError(f"{path}: hooks is not a JSON object")
    return hooks


def _carries_marker(handler: Any) -> bool:
    """Report whether a handler is one this installer wrote."""
    return isinstance(handler, dict) and MARKER in str(handler.get("command", ""))


def _strip_ours(groups: Any, path: Path) -> list[Any]:
    """Return the groups with every handler this installer wrote removed.

    Rules:   A group that is not a list raises InstallError; anything else is preserved in order so a foreign hook keeps its place and its timeout. Remove only handlers carrying MARKER — a foreign handler a user added to one of our groups must survive, and the group is dropped only when no handler remains. Never mutate a group in place: a group that loses a handler is rebuilt.
    """
    if not isinstance(groups, list):
        raise InstallError(f"{path}: hooks entry is not a JSON array")
    kept: list[Any] = []
    for group in groups:
        handlers = group.get("hooks") if isinstance(group, dict) else None
        if not isinstance(handlers, list):
            kept.append(group)
            continue
        remaining = [handler for handler in handlers if not _carries_marker(handler)]
        if not remaining:
            continue
        kept.append(group if len(remaining) == len(handlers) else {**group, "hooks": remaining})
    return kept


def _write_text(
    path: Path, text: str, harness: str, action: str, dry_run: bool
) -> Change:
    """Write text to the settings file after one backup of the pristine copy.

    Rules:   The backup is taken only when it does not exist yet, so a second run never overwrites the original, and it sits beside the link so an uninstall finds it there. The write stages beside the resolved target and moves into place with os.replace: a truncate-then-write that hits ENOSPC, EIO, or a kill would leave the harness a corrupt settings file, and replacing the link itself would silently detach a dotfiles-managed settings file from its target. A dry run returns the change without touching the disk.
    """
    if dry_run:
        return Change(harness, path, action, "dry run")
    backup = path.with_name(path.name + BACKUP_SUFFIX)
    target = Path(os.path.realpath(path)) if path.is_symlink() else path
    staged = target.with_name(target.name + ".tmp")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not backup.exists():
            shutil.copy2(path, backup)
        staged.write_text(text, encoding="utf-8")
        os.replace(staged, target)
    except OSError as error:
        raise InstallError(f"{path}: {error}") from error
    return Change(harness, path, action)


def _write(
    path: Path, data: Mapping[str, Any], harness: str, action: str, dry_run: bool
) -> Change:
    """Write the merged settings object, indented two spaces like the harnesses write it."""
    return _write_text(path, json.dumps(data, indent=2) + "\n", harness, action, dry_run)


def _upsert(
    path: Path,
    groups_by_event: Mapping[str, list[dict[str, Any]]],
    harness: str,
    dry_run: bool,
) -> Change:
    """Merge our groups into a settings file, one event at a time.

    Rules:   Ours are appended last so a foreign guard keeps running first, and any earlier copy of ours is removed first so a re-run or a moved checkout replaces it instead of duplicating it.
    """
    data = _read_settings(path)
    hooks = _hooks_object(data, path)
    for event, groups in groups_by_event.items():
        existing = _strip_ours(hooks.get(event, []), path)
        hooks[event] = existing + groups
    return _write(path, data, harness, "write", dry_run)


def install(
    harness: str,
    home: Path | str,
    python: str | None = None,
    script: str | None = None,
    dry_run: bool = False,
) -> list[Change]:
    """Wire the contract hook into one harness under home.

    Rules:   Every harness merges — ours are appended last so a foreign guard keeps running first, and an earlier copy of ours is replaced so a re-run or a moved checkout never duplicates it. Grok gets no SessionStart group because it ignores one there. The interpreter and script resolve to absolute paths at install time, so the harness never depends on PATH or on the working directory.
    """
    interpreter = str(python or sys.executable)
    target = str(
        Path(os.path.expanduser(script or Path(__file__).with_name(HOOK_SCRIPT_NAME))).resolve()
    )
    if harness == HARNESS_GROK:
        groups = {"PreToolUse": [_group(HOOK_MATCHER, interpreter, target)]}
        return [_upsert(grok_hooks_path(home), groups, HARNESS_GROK, dry_run)]
    if harness == HARNESS_CLAUDE:
        groups = {
            "PreToolUse": [_group(HOOK_MATCHER, interpreter, target)],
            "SessionStart": [_group(None, interpreter, target)],
        }
        return [_upsert(claude_settings_path(home), groups, HARNESS_CLAUDE, dry_run)]
    if harness == HARNESS_COMMANDCODE:
        groups = {
            "PreToolUse": [_group(COMMANDCODE_MATCHER, interpreter, target)],
            "SessionStart": [_group(None, interpreter, target)],
        }
        return [_upsert(commandcode_settings_path(home), groups, HARNESS_COMMANDCODE, dry_run)]
    raise InstallError(f"unknown harness: {harness}")


def _settings_path(harness: str, home: Path | str) -> Path:
    """Return the settings file one harness keeps under home.

    Rules:   An unknown harness raises InstallError here, so every caller sees the same validation.
    """
    if harness == HARNESS_GROK:
        return grok_hooks_path(home)
    if harness == HARNESS_CLAUDE:
        return claude_settings_path(home)
    if harness == HARNESS_COMMANDCODE:
        return commandcode_settings_path(home)
    raise InstallError(f"unknown harness: {harness}")


def _remove_file(path: Path, harness: str, dry_run: bool) -> Change:
    """Delete a hook file the installer created and now owns.

    Rules:   Only the Grok hook file reaches here, and only when stripping our handlers left it empty with no backup claiming it — a file the installer did not create is never deleted. A dry run reports the removal without touching the disk.
    """
    if dry_run:
        return Change(harness, path, "remove", "dry run")
    try:
        path.unlink()
    except OSError as error:
        raise InstallError(f"{path}: {error}") from error
    return Change(harness, path, "remove")


def uninstall(harness: str, home: Path | str, dry_run: bool = False) -> list[Change]:
    """Remove the contract hook from one harness under home.

    Rules:   Remove only handlers carrying MARKER; leave every other hook in place and drop an event key that ends up empty. When the stripped result matches the pristine backup, write that backup back verbatim so the file returns byte for byte; when the file gained foreign content since the install, write the stripped object instead. Delete the Grok hook file only when nothing else remains in it and no backup claims it. A file that never held our handlers is left alone.
    """
    path = _settings_path(harness, home)
    if not path.exists():
        return [Change(harness, path, "unchanged")]
    text = _read_text(path)
    data = _parse_settings(text, path)
    hooks = _hooks_object(data, path)
    for event in list(hooks):
        remaining = _strip_ours(hooks.get(event), path)
        if remaining:
            hooks[event] = remaining
        else:
            del hooks[event]
    if not hooks:
        del data["hooks"]
    backup = path.with_name(path.name + BACKUP_SUFFIX)
    if backup.exists():
        pristine = _read_text(backup)
        if _parse_settings(pristine, backup) == data:
            return [_write_text(path, pristine, harness, "restore", dry_run)]
    if not data and harness == HARNESS_GROK:
        return [_remove_file(path, harness, dry_run)]
    if _parse_settings(text, path) == data:
        return [Change(harness, path, "unchanged")]
    return [_write(path, data, harness, "write", dry_run)]


def _run(targets: Iterable[str], args: argparse.Namespace) -> list[Change]:
    home = Path(args.home).expanduser() if args.home else Path.home()
    changes: list[Change] = []
    for harness in targets:
        if args.uninstall:
            changes.extend(uninstall(harness, home, dry_run=args.dry_run))
        else:
            changes.extend(
                install(
                    harness,
                    home,
                    python=args.python,
                    script=args.script,
                    dry_run=args.dry_run,
                )
            )
    return changes


def _missing_paths(python: str, script: str | None) -> list[str]:
    """Return the interpreter and hook script paths that do not exist.

    Rules:   A harness runs the hook file by absolute path, so a path that does not exist installs a hook that never starts while the installer still reports success. Validate exactly what the command will run: the interpreter, and the script the installer would resolve.
    """
    candidates = [os.path.expanduser(python)]
    candidates.append(
        os.path.expanduser(script)
        if script
        else str(Path(__file__).with_name(HOOK_SCRIPT_NAME))
    )
    return [path for path in candidates if not Path(path).exists()]


def main(argv=None) -> int:
    """Wire or unwire the contract hook for the harnesses named on the command line.

    Rules:   Default to all three harnesses under the real home; report every file touched so the caller can see exactly what changed and revert with --uninstall. Refuse a wiring run whose interpreter or script does not exist, before anything is written — an unwire still runs, because the checkout may already be gone.
    """
    parser = argparse.ArgumentParser(
        description="Wire the agents-contract hook into Claude Code, Grok, and Command Code."
    )
    parser.add_argument("--harness", choices=[*HARNESSES, "all"], default="all")
    parser.add_argument("--uninstall", action="store_true", help="remove the hook wiring")
    parser.add_argument("--dry-run", action="store_true", help="report changes without writing")
    parser.add_argument("--home", default=None, help="home directory to wire (default: $HOME)")
    parser.add_argument("--python", default=sys.executable, help="interpreter that runs the hook")
    parser.add_argument("--script", default=None, help="path to contract_hook.py")
    args = parser.parse_args(argv)
    targets = HARNESSES if args.harness == "all" else (args.harness,)
    if not args.uninstall:
        missing = _missing_paths(args.python, args.script)
        if missing:
            for path in missing:
                print(f"install_hooks: {path}: not found", file=sys.stderr)
            return 1
    try:
        changes = _run(targets, args)
    except InstallError as error:
        print(f"install_hooks: {error}", file=sys.stderr)
        return 1
    for change in changes:
        detail = f" ({change.detail})" if change.detail else ""
        print(f"{change.harness}: {change.action} {change.path}{detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
