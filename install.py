"""install.py — Put the contract in front of every harness that reads it.

exports: HARNESSES | HarnessPlan | find_conflicts | find_vendored_edits | main | plan_harnesses | plan_project | render_grok_rules | sync_contract_mirror | vendor_skill
used_by: README.md → the install section
related: contract/AGENTS.md is the source; contract/*.md are its companions; .agents/skills/agents-contract/hooks/install_hooks.py wires the hook.
rules:   Emit per harness; never hand-copy. Claude Code and Command Code expand `@path` imports in AGENTS.md, so they get one symlink to the contract. Grok does not expand imports — verified on grok 1.0.67, where a marker in an @-imported file was absent from the instruction context — so it gets the companions as separate files in a rules directory it scans. The contract text ends in `@`-imports for its four companions, so any harness receiving AGENTS.md must receive them beside it, in every scope and every harness subset; attaching them to one plan leaves the others loading a contract with dangling pointers. Both mechanisms load only files that exist: a broken symlink silently contributes nothing, so every emitted path is verified before the run reports success. Never overwrite a file the user owns: a vendored copy records its installed hashes in .vendored.json, so an in-place edit is refused while a stale upstream copy stays replaceable.
agent:   deepseek-v4.1-flash | nexrouter | 2026-10-23 | 81e2ea63-c0ca-489d-a506-5ec094106a17 | closed the last overwrite gap: provenance was unknowable from a path comparison alone, so a vendored file edited in place was replaced silently; vendor_skill now writes .vendored.json and find_vendored_edits diffs against it, which also keeps a stale upstream copy replaceable
agent:   deepseek-v4.1-flash | nexrouter | 2026-10-24 | 372685f1-d81d-4c7c-8fbb-7e8e636e8b48 | plan_project attached the companions to claude only, though all three plans share the root AGENTS.md whose tail imports them — a commandcode-only project install loaded the contract with four dangling @-pointers. Companions now attach to every plan; main's emitted-set dedup keeps a multi-harness run to one write each. Also dry_run now reports hook changes instead of silently skipping them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
CONTRACT_DIR = _HERE / "contract"
SKILL_DIR = _HERE / ".agents" / "skills" / "agents-contract"
COMPANIONS = ("RTK.md", "semble.md", "caveman.md", "ponytail.md")
HARNESSES = ("claude", "commandcode", "grok")
_VENDOR_IGNORE = ("__pycache__", "*.pyc")

HOME_DIR = {
    "claude": ".claude",
    "commandcode": ".commandcode",
    "grok": ".grok",
}


@dataclass(frozen=True)
class HarnessPlan:
    """One harness's install shape and the paths it needs.

    Rules:   `links` maps a path to create to the contract file it should resolve to; `rules_dir` names the directory Grok scans for companion files. A harness that expands imports gets `links` only, because its one AGENTS.md already reaches the companions. `copy` writes the file's contents instead of a symlink — required for project scope, where a link into the installer's checkout is dead on any other clone.
    """

    harness: str
    links: dict[Path, Path]
    rules_dir: Path | None
    copy: bool = False


def render_grok_rules(contract_dir: Path) -> dict[str, str]:
    """Return the companion files Grok needs as standalone rule documents.

    Rules:   Grok reads every `*.md` directly inside a rules directory as a user rule and does not expand `@`-imports, so each companion ships whole. Keep the filename stem: Grok loads the directory alphabetically, and a stable order keeps the prompt cache warm.
    """
    return {
        name: (contract_dir / name).read_text(encoding="utf-8")
        for name in COMPANIONS
    }


def sync_contract_mirror(contract_dir: Path, skill_dir: Path) -> Path:
    """Write the skill's copy of the contract from the single source.

    Rules:   The skill reads references/contract.md, and that copy must match contract/AGENTS.md byte for byte — a stale mirror is what made the skill and the contract disagree. Write through a temporary sibling and move it into place, so a concurrent read never sees a partial file.
    """
    source = contract_dir / "AGENTS.md"
    target = skill_dir / "references" / "contract.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = target.with_name(target.name + ".staged")
    shutil.copyfile(source, staged)
    os.replace(staged, target)
    return target


def plan_harnesses(home: Path) -> dict[str, HarnessPlan]:
    """Return the user-scope install shape for each harness under one home.

    Rules:   Resolve every target under the caller's home so a test can point at a temporary directory and never touch real configs. Claude Code reads CLAUDE.md and AGENTS.md, so it gets both; Command Code reads AGENTS.md only. Both land beside the harness's own config directory, which is where each looks for global memory.
    """
    plans: dict[str, HarnessPlan] = {}
    for harness in HARNESSES:
        base = home / HOME_DIR[harness]
        links: dict[Path, Path] = {base / "AGENTS.md": CONTRACT_DIR / "AGENTS.md"}
        if harness == "claude":
            links[base / "CLAUDE.md"] = CONTRACT_DIR / "AGENTS.md"
        rules_dir = base / "rules" if harness == "grok" else None
        plans[harness] = HarnessPlan(harness, links, rules_dir)
    return plans


def plan_project(root: Path) -> dict[str, HarnessPlan]:
    """Return the project-scope shape, rooted at one repository.

    Rules:   A project install lands real files, not links: the settings and contract are committed, and a symlink into the installing machine's checkout resolves to nothing on a teammate's clone — it loads no contract and, because the hook fails open, silently stops enforcing. Claude Code and Command Code read `<root>/AGENTS.md` and the companions beside it, so the imports resolve in place. Those imports are in the contract text, so every harness that gets `<root>/AGENTS.md` needs the companions there too — including a Command Code-only install, which expands `@`-imports and would otherwise load the contract with four dangling pointers. Grok scans `<root>/.grok/rules`; it does not expand imports, so the root companions are unused there and the rules directory carries them whole.
    """
    agent = root / "AGENTS.md"
    plans = {
        "claude": HarnessPlan(
            "claude",
            {agent: CONTRACT_DIR / "AGENTS.md", root / "CLAUDE.md": CONTRACT_DIR / "AGENTS.md"},
            None,
            copy=True,
        ),
        "commandcode": HarnessPlan(
            "commandcode", {agent: CONTRACT_DIR / "AGENTS.md"}, None, copy=True
        ),
        "grok": HarnessPlan(
            "grok", {agent: CONTRACT_DIR / "AGENTS.md"}, root / ".grok" / "rules", copy=True
        ),
    }
    for plan in plans.values():
        for name in COMPANIONS:
            plan.links[root / name] = CONTRACT_DIR / name
    return plans


def _skill_files(skill_dir: Path) -> dict[str, str]:
    """Return every vendorable file's POSIX path and sha256 in the skill source.

    Rules:   Key by POSIX relative path so a manifest written on Linux still matches on a clone, and hash content rather than size or mtime so a real edit is distinguishable from a touch. Skip bytecode the same way the copy does, or the manifest records files that are never installed.
    """
    return {
        path.relative_to(skill_dir).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(skill_dir.rglob("*"))
        if path.is_file() and not any(path.match(pat) for pat in _VENDOR_IGNORE)
    }


def _manifest_path(root: Path, name: str) -> Path:
    """Return the manifest that records what a vendor run installed.

    Rules:   Live inside the vendored directory, so it travels with the copy and a stale manifest cannot outlive the files it describes. Take the skill's directory name rather than hardcoding it: the manifest must sit beside the files it describes even when the source copy is named something else.
    """
    return root / ".agents" / "skills" / name / ".vendored.json"


def _read_manifest(root: Path, name: str) -> dict[str, str] | None:
    """Return the recorded hashes, or None when there is no usable manifest.

    Rules:   A missing or unreadable manifest returns None rather than empty, because the two mean different things: empty is "we recorded nothing", None is "we cannot tell what we installed", and the caller must fall back to refusing on any difference.
    """
    try:
        data = json.loads(_manifest_path(root, name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    files = data.get("files") if isinstance(data, dict) else None
    return files if isinstance(files, dict) else None


def vendor_skill(root: Path, skill_dir: Path, dry_run: bool) -> list[str]:
    """Copy the skill beside the project's contract so its hook can run there.

    Rules:   The project hook command addresses the script through the workspace root, so the skill must exist inside the project — a path into the installer's checkout would be dead on any other clone. Replace rather than merge, because a partial copy from an earlier version leaves stale modules that import cleanly and behave wrongly. Skip the caches so a vendored copy stays reviewable in a diff. Record every installed file's hash in the manifest as the copy is written; without it a later run cannot tell a local edit from a stale upstream copy.
    """
    target = root / ".agents" / "skills" / skill_dir.name
    if dry_run:
        return [f"project: vendor {target} (dry run)"]
    files = _skill_files(skill_dir)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(skill_dir, target, ignore=shutil.ignore_patterns(*_VENDOR_IGNORE))
    _write_manifest(root, skill_dir.name, files)
    return [f"project: vendored {target}"]


def _write_manifest(root: Path, name: str, files: dict[str, str]) -> Path:
    """Write the vendored-file manifest.

    Rules:   Write through a staged sibling and move it into place, so an interrupted run cannot leave a half-written manifest that makes every later run refuse for the wrong reason. Create the directory first — a caller may vendor into a root that does not exist yet.
    """
    path = _manifest_path(root, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_name(path.name + ".staged")
    staged.write_text(
        json.dumps({"files": files}, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(staged, path)
    return path


def find_vendored_edits(root: Path, skill_dir: Path) -> list[Path]:
    """Return files inside a vendored skill copy that differ from what was installed.

    Rules:   Compare against the manifest, not the current source: a file that differs from the recorded hash was edited locally and must be refused, while a file that matches the manifest is ours to replace even when upstream has moved on. A file the manifest does not mention is a local addition and counts as an edit. With no usable manifest, fall back to refusing anything that differs from the source, since a wrong refusal only costs a --force while a wrong replace loses the edit.
    """
    target = root / ".agents" / "skills" / skill_dir.name
    if not target.is_dir():
        return []
    recorded = _read_manifest(root, skill_dir.name)
    current = _skill_files(target)
    if recorded is None:
        source = _skill_files(skill_dir)
        return sorted(
            target / name
            for name, digest in current.items()
            if name != ".vendored.json" and source.get(name) != digest
        )
    return sorted(
        target / name
        for name, digest in current.items()
        if name != ".vendored.json" and recorded.get(name) != digest
    )


def _link(target: Path, source: Path, dry_run: bool = False) -> str:
    """Point target at source and report what happened.

    Rules:   Replace a stale link or an existing file, because a leftover copy shadows the contract and drifts from it — that is the failure this script exists to end. Create the parent directory first; a harness directory may not exist yet. A dry run reports the same decision and changes nothing, so `--dry-run` distinguishes current wiring (`unchanged`) from real drift.
    """
    current = target.is_symlink() and Path(os.path.realpath(target)) == source
    if current:
        return "unchanged"
    action = "replaced" if (target.is_symlink() or target.exists()) else "linked"
    if dry_run:
        return action
    target.parent.mkdir(parents=True, exist_ok=True)
    if action == "replaced":
        target.unlink()
    target.symlink_to(source)
    return action


def find_conflicts(
    plans: dict[str, HarnessPlan], chosen: tuple[str, ...], contract_dir: Path
) -> list[Path]:
    """Return existing files an install would overwrite with different content.

    Rules:   A symlink is never a conflict — it is wiring this script owns and repoints. A regular file whose bytes already match the contract is not a conflict either, so a re-run stays quiet. Anything else is somebody's own file and overwriting it destroys their instructions, so it must be refused rather than replaced. Grok's rules files count too: they are written by apply_plan outside `links`, so guarding only `links` left a user's own .grok/rules/RTK.md silently clobbered.
    """
    conflicts: list[Path] = []

    def note(target: Path, expected: bytes) -> None:
        if target in conflicts or target.is_symlink() or not target.is_file():
            return
        if target.read_bytes() != expected:
            conflicts.append(target)

    for harness, plan in plans.items():
        if harness not in chosen:
            continue
        for target, source in plan.links.items():
            note(target, source.read_bytes())
        if plan.rules_dir is not None:
            for name, text in render_grok_rules(contract_dir).items():
                note(plan.rules_dir / name, text.encode())
    return conflicts


def backup(target: Path, into: Path | None = None) -> Path:
    """Copy target to a .bak before it is overwritten.

    Rules:   Never overwrite an existing backup, since that would destroy the oldest copy of the user's file — suffix with a counter instead. `into` moves the backup to another directory, which a vendored-skill backup requires: vendor_skill replaces that whole directory, so a .bak written beside the file is deleted by the very operation it was meant to protect against. Return the path written so the caller can report it.
    """
    if into is None:
        directory, stem = target.parent, target.name
    else:
        directory, stem = into, f"{target.parent.name}-{target.name}"
    directory.mkdir(parents=True, exist_ok=True)
    candidate = directory / f"{stem}.bak"
    counter = 1
    while candidate.exists():
        candidate = directory / f"{stem}.bak{counter}"
        counter += 1
    shutil.copyfile(target, candidate)
    return candidate


def _copy(target: Path, source: Path, dry_run: bool = False) -> str:
    """Write source's contents to target and report what happened.

    Rules:   Compare bytes so a re-run reports `unchanged` instead of rewriting — a project install is committed, and a spurious write would show as churn in every diff. Write through a staged sibling and move it into place so a concurrent read never sees a partial file. A dry run reports the decision and writes nothing.
    """
    same = target.is_file() and not target.is_symlink() and target.read_bytes() == source.read_bytes()
    if same:
        return "unchanged"
    action = "replaced" if (target.is_symlink() or target.exists()) else "wrote"
    if dry_run:
        return action
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = target.with_name(target.name + ".staged")
    shutil.copyfile(source, staged)
    os.replace(staged, target)
    return action


def apply_plan(plan: HarnessPlan, contract_dir: Path, dry_run: bool) -> list[str]:
    """Create one harness's links or copies and Grok rule files, reporting each change.

    Rules:   Verify each written path resolves before reporting it, since a link to a missing source loads nothing and fails silently in every harness. Report every action in file order so a partial run shows exactly what landed. A copy plan writes file contents; a link plan points at the contract.
    """
    actions: list[str] = []
    writer = _copy if plan.copy else _link
    for target, source in plan.links.items():
        if dry_run:
            actions.append(f"{plan.harness}: {writer(target, source, dry_run=True)} {target}")
            continue
        action = writer(target, source)
        if not target.exists():
            raise SystemExit(f"install: {target} does not resolve after writing")
        actions.append(f"{plan.harness}: {action} {target}")
    if plan.rules_dir is None:
        return actions
    for name, text in render_grok_rules(contract_dir).items():
        target = plan.rules_dir / name
        same = target.is_file() and target.read_text(encoding="utf-8") == text
        if dry_run:
            actions.append(
                f"{plan.harness}: {'unchanged' if same else 'write'} {target} (dry run)"
            )
            continue
        if same:
            actions.append(f"{plan.harness}: unchanged {target}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        staged = target.with_name(target.name + ".staged")
        staged.write_text(text, encoding="utf-8")
        os.replace(staged, target)
        actions.append(f"{plan.harness}: wrote {target}")
    return actions


def main(argv: list[str] | None = None) -> int:
    """Wire the contract into every harness, then sync the skill mirror.

    Rules:   Refuse to run when the contract source is missing — a half-installed contract is worse than none, because the harness would load a stale copy. Print every action; exit 0 whether or not anything changed, so a re-run is safe in a script.
    """
    parser = argparse.ArgumentParser(
        description="Install the lowheat contract into each harness."
    )
    parser.add_argument("--home", default=str(Path.home()), help="home to wire")
    parser.add_argument(
        "--harness", choices=(*HARNESSES, "all"), default="all", help="which to wire"
    )
    parser.add_argument(
        "--scope",
        choices=("user", "project"),
        default="user",
        help="user scope wires ~/.<harness>; project scope writes the repo root",
    )
    parser.add_argument(
        "--root", default=".", help="project root for --scope project"
    )
    parser.add_argument("--dry-run", action="store_true", help="report, do not write")
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing AGENTS.md, keeping a .bak of it",
    )
    parser.add_argument(
        "--no-hooks", action="store_true", help="skip the RTK/discovery hook wiring"
    )
    args = parser.parse_args(argv)

    if not (CONTRACT_DIR / "AGENTS.md").is_file():
        print(f"install: {CONTRACT_DIR / 'AGENTS.md'} is missing", file=sys.stderr)
        return 1

    home = Path(args.home).expanduser()
    chosen = HARNESSES if args.harness == "all" else (args.harness,)
    project_root = None if args.scope == "user" else Path(args.root).expanduser().resolve()
    if project_root is not None and project_root == _HERE:
        print(
            f"install: {project_root} is the lowheat source checkout, not a project — "
            "project scope would duplicate contract/ back into the repo root",
            file=sys.stderr,
        )
        return 1
    plans = (
        plan_harnesses(home)
        if args.scope == "user"
        else plan_project(project_root)
    )

    conflicts = find_conflicts(plans, chosen, CONTRACT_DIR)
    vendored: list[Path] = []
    if project_root is not None and not args.no_hooks:
        vendored = find_vendored_edits(project_root, SKILL_DIR)
        conflicts.extend(vendored)
    if conflicts and not args.force:
        for path in conflicts:
            print(f"install: refusing to overwrite {path}", file=sys.stderr)
        if vendored:
            print(
                "install: local edits inside the vendored skill are deleted by a reinstall",
                file=sys.stderr,
            )
        print(
            "install: that file is not ours; re-run with --force to keep a .bak and replace it",
            file=sys.stderr,
        )
        return 1
    if conflicts:
        keep = project_root / ".agents" / "removed-skill-edits" if project_root else None
        for path in conflicts:
            into = keep if path in vendored else None
            if args.dry_run:
                print(f"install: would back up {path} to {path.name}.bak")
            else:
                print(f"install: backed up {path} to {backup(path, into)}")

    if not args.dry_run:
        mirror = sync_contract_mirror(CONTRACT_DIR, SKILL_DIR)
        print(f"contract: wrote {mirror}")

    emitted: set[Path] = set()
    for harness, plan in plans.items():
        if harness not in chosen:
            continue
        unique = HarnessPlan(
            plan.harness,
            {t: s for t, s in plan.links.items() if t not in emitted},
            plan.rules_dir,
            plan.copy,
        )
        emitted.update(unique.links)
        for action in apply_plan(unique, CONTRACT_DIR, args.dry_run):
            print(action)

    if project_root is not None and not args.no_hooks:
        for action in vendor_skill(project_root, SKILL_DIR, args.dry_run):
            print(action)

    if not args.no_hooks:
        sys.path.insert(0, str(SKILL_DIR / "hooks"))
        import install_hooks

        for harness in chosen:
            changes = install_hooks.install(
                harness, home, root=project_root, dry_run=args.dry_run
            )
            for change in changes:
                detail = f" ({change.detail})" if change.detail else ""
                print(f"hooks: {change.action} {change.path}{detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
