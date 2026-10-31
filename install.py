"""install.py — Put the contract in front of every harness that reads it.

exports: HARNESSES | HarnessPlan | find_conflicts | main | plan_harnesses | plan_project | render_grok_rules | sync_contract_mirror
used_by: README.md → the install section
used_by: tests/test_install.py → CONTRACT_DIR, HARNESSES, SKILL_DIR, HarnessPlan, apply_plan, find_conflicts, main, plan_harnesses, plan_project, render_grok_rules, sync_contract_mirror [cascade]
related: contract/AGENTS.md is the source and contract/*.md are its companions.
rules:   Emit per harness; never hand-copy. AGENTS.md is the thin core and names its companions by bare filename, so every harness receives the contract plus the companions beside it and reads the one it needs on demand. Claude Code and Command Code get symlinks in user scope; Grok gets the companions as standalone files in a rules directory it scans, because it does not expand imports. Every user-scope harness also gets the skill linked into its skills directory, so the agent reads the same skill the checkout carries instead of a stale vendored copy. A broken symlink silently contributes nothing, so every emitted path is verified before the run reports success. Never overwrite a file the user owns: a differing regular file or directory is refused unless --force writes a .bak first.
agent:   deepseek-v4.1-flash | nexrouter | 2026-10-23 | 81e2ea63-c0ca-489d-a506-5ec094106a17 | closed the last overwrite gap: provenance was unknowable from a path comparison alone, so a vendored file edited in place was replaced silently; vendor_skill now writes .vendored.json and find_vendored_edits diffs against it, which also keeps a stale upstream copy replaceable
agent:   deepseek-v4.1-flash | nexrouter | 2026-10-24 | 372685f1-d81d-4c7c-8fbb-7e8e636e8b48 | plan_project attached the companions to claude only, though all three plans share the root AGENTS.md whose tail imports them — a commandcode-only project install loaded the contract with four dangling @-pointers. Companions now attach to every plan; main's emitted-set dedup keeps a multi-harness run to one write each. Also dry_run now reports hook changes instead of silently skipping them.
agent:   fx | unknown | 2026-10-31 | unknown | removed the hook runtime and installer wiring, then deleted the one-shot cleanup tool; install now writes the contract only
agent:   fx | unknown | 2026-10-31 | unknown | user scope now links the companions beside AGENTS.md and links the skill into each harness skills directory; the skill mirror also syncs commands.md from RTK.md, closing the stale global-copy and catalogue drift
agent:   fx | unknown | 2026-10-31 | unknown | thin-contract restructure: AGENTS.md drops @-imports, CodeDNA moves to its own companion, and the skill mirrors contract plus CodeDNA plus RTK on demand
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
CONTRACT_DIR = _HERE / "contract"
SKILL_DIR = _HERE / ".agents" / "skills" / "agents-contract"
COMPANIONS = ("codedna.md", "RTK.md", "semble.md", "caveman.md", "ponytail.md")
HARNESSES = ("claude", "commandcode", "grok")

HOME_DIR = {
    "claude": ".claude",
    "commandcode": ".commandcode",
    "grok": ".grok",
}


@dataclass(frozen=True)
class HarnessPlan:
    """One harness's install shape and the paths it needs.

    Rules:   `links` maps a path to create to the contract file it should resolve to; `rules_dir` names the directory Grok scans for companion files. Every harness gets the companions because AGENTS.md names them by bare filename for on-demand reads. `copy` writes the file's contents instead of a symlink — required for project scope, where a link into the installer's checkout is dead on any other clone.
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


def _sync_copy(source: Path, target: Path) -> Path:
    """Copy source over target through a staged sibling.

    Rules:   Write through a temporary sibling and move it into place, so a concurrent read never sees a partial file. Copy bytes, not text, so the mirror comparison stays exact.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = target.with_name(target.name + ".staged")
    shutil.copyfile(source, staged)
    os.replace(staged, target)
    return target


def sync_contract_mirror(contract_dir: Path, skill_dir: Path) -> list[Path]:
    """Write the skill's copies of the contract, CodeDNA, and RTK catalogue.

    Rules:   The skill reads references/contract.md, references/codedna.md, and references/commands.md; each copy must match its source byte for byte — a stale mirror is what made the skill and the contract disagree. Rewrite all three on every install; return every path written so the caller reports each one.
    """
    references = skill_dir / "references"
    return [
        _sync_copy(contract_dir / "AGENTS.md", references / "contract.md"),
        _sync_copy(contract_dir / "codedna.md", references / "codedna.md"),
        _sync_copy(contract_dir / "RTK.md", references / "commands.md"),
    ]


def plan_harnesses(home: Path) -> dict[str, HarnessPlan]:
    """Return the user-scope install shape for each harness under one home.

    Rules:   Resolve every target under the caller's home so a test can point at a temporary directory and never touch real configs. Claude Code reads CLAUDE.md and AGENTS.md, so it gets both; Command Code reads AGENTS.md only. Both land beside the harness's own config directory, which is where each looks for global memory. Every harness gets the companions beside its AGENTS.md so the named references resolve on demand, and the skill linked into its skills directory so the loader reads the checkout's skill rather than a stale copy.
    """
    plans: dict[str, HarnessPlan] = {}
    for harness in HARNESSES:
        base = home / HOME_DIR[harness]
        links: dict[Path, Path] = {base / "AGENTS.md": CONTRACT_DIR / "AGENTS.md"}
        if harness == "claude":
            links[base / "CLAUDE.md"] = CONTRACT_DIR / "AGENTS.md"
        if harness != "grok":
            for name in COMPANIONS:
                links[base / name] = CONTRACT_DIR / name
        links[base / "skills" / SKILL_DIR.name] = SKILL_DIR
        rules_dir = base / "rules" if harness == "grok" else None
        plans[harness] = HarnessPlan(harness, links, rules_dir)
    return plans


def plan_project(root: Path) -> dict[str, HarnessPlan]:
    """Return the project-scope shape, rooted at one repository.

    Rules:   A project install lands real files, not links: the contract is committed, and a symlink into the installing machine's checkout resolves to nothing on a teammate's clone. Claude Code and Command Code read `<root>/AGENTS.md` and the companions beside it, where the contract's named references resolve for on-demand reads. Every harness plan carries the companions because they share one root AGENTS.md. Grok scans `<root>/.grok/rules`; its rules directory carries them whole as well.
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


def _link(target: Path, source: Path, dry_run: bool = False) -> str:
    """Point target at source and report what happened.

    Rules:   Replace a stale link or an existing file, because a leftover copy shadows the contract and drifts from it — that is the failure this script exists to end. Remove a real directory only when the caller has already backed it up and chosen --force, since a skill directory is not a file to unlink. Create the parent directory first; a harness directory may not exist yet. A dry run reports the same decision and changes nothing, so `--dry-run` distinguishes current wiring (`unchanged`) from real drift.
    """
    current = target.is_symlink() and Path(os.path.realpath(target)) == source
    if current:
        return "unchanged"
    action = "replaced" if (target.is_symlink() or target.exists()) else "linked"
    if dry_run:
        return action
    target.parent.mkdir(parents=True, exist_ok=True)
    if action == "replaced":
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()
    target.symlink_to(source)
    return action


def find_conflicts(
    plans: dict[str, HarnessPlan], chosen: tuple[str, ...], contract_dir: Path
) -> list[Path]:
    """Return existing files an install would overwrite with different content.

    Rules:   A symlink is never a conflict — it is wiring this script owns and repoints. A regular file whose bytes already match the contract is not a conflict either, so a re-run stays quiet. Anything else is somebody's own file and overwriting it destroys their instructions, so it must be refused rather than replaced. A directory target is always refused because the only directory this script links is the skill, and a real directory there belongs to the user. Grok's rules files count too: they are written by apply_plan outside `links`, so guarding only `links` left a user's own .grok/rules/RTK.md silently clobbered.
    """
    conflicts: list[Path] = []

    def note(target: Path, expected: bytes) -> None:
        if target in conflicts or target.is_symlink():
            return
        if target.is_file():
            if target.read_bytes() != expected:
                conflicts.append(target)
        elif target.exists():
            conflicts.append(target)

    def note_directory(target: Path) -> None:
        if target in conflicts or target.is_symlink() or not target.exists():
            return
        conflicts.append(target)

    for harness, plan in plans.items():
        if harness not in chosen:
            continue
        for target, source in plan.links.items():
            if source.is_dir():
                note_directory(target)
            else:
                note(target, source.read_bytes())
        if plan.rules_dir is not None:
            for name, text in render_grok_rules(contract_dir).items():
                note(plan.rules_dir / name, text.encode())
    return conflicts


def backup(target: Path) -> Path:
    """Copy target to a .bak before it is overwritten.

    Rules:   Never overwrite an existing backup, since that would destroy the oldest copy of the user's file — suffix with a counter instead. Copy a real directory recursively, since the only directory target is a skill and --force must preserve it whole. Return the path written so the caller can report it.
    """
    directory, stem = target.parent, target.name
    directory.mkdir(parents=True, exist_ok=True)
    candidate = directory / f"{stem}.bak"
    counter = 1
    while candidate.exists():
        candidate = directory / f"{stem}.bak{counter}"
        counter += 1
    if target.is_dir() and not target.is_symlink():
        shutil.copytree(target, candidate)
    else:
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
    if conflicts and not args.force:
        for path in conflicts:
            print(f"install: refusing to overwrite {path}", file=sys.stderr)
        print(
            "install: that file is not ours; re-run with --force to keep a .bak and replace it",
            file=sys.stderr,
        )
        return 1
    if conflicts:
        for path in conflicts:
            if args.dry_run:
                print(f"install: would back up {path} to {path.name}.bak")
            else:
                print(f"install: backed up {path} to {backup(path)}")

    if not args.dry_run:
        for mirror in sync_contract_mirror(CONTRACT_DIR, SKILL_DIR):
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
