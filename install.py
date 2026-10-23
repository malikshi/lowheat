"""install.py — Put the contract in front of every harness that reads it.

exports: HARNESSES | HarnessPlan | main | plan_harnesses | plan_project | render_grok_rules | sync_contract_mirror
used_by: README.md → the install section
related: contract/AGENTS.md is the source; contract/*.md are its companions; .agents/skills/agents-contract/hooks/install_hooks.py wires the hook.
rules:   Emit per harness; never hand-copy. Claude Code and Command Code expand `@path` imports in AGENTS.md, so they get one symlink to the contract. Grok does not expand imports — verified on grok 1.0.67, where a marker in an @-imported file was absent from the instruction context — so it gets the companions as separate files in a rules directory it scans. Both mechanisms load only files that exist: a broken symlink silently contributes nothing, so every emitted path is verified before the run reports success.
agent:   deepseek-v4.1-flash | nexrouter | 2026-10-23 | 81e2ea63-c0ca-489d-a506-5ec094106a17 | first cut: replaced the hand-maintained symlink-and-copy install with one per-harness emitter, after Grok was measured not to expand @-imports; project scope shares one AGENTS.md link across the three harnesses so it emits once
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
COMPANIONS = ("RTK.md", "semble.md", "caveman.md", "ponytail.md")
HARNESSES = ("claude", "commandcode", "grok")

HOME_DIR = {
    "claude": ".claude",
    "commandcode": ".commandcode",
    "grok": ".grok",
}


@dataclass(frozen=True)
class HarnessPlan:
    """One harness's install shape and the paths it needs.

    Rules:   `links` maps a path to create to the contract file it should resolve to; `rules_dir` names the directory Grok scans for companion files. A harness that expands imports gets `links` only, because its one AGENTS.md already reaches the companions.
    """

    harness: str
    links: dict[Path, Path]
    rules_dir: Path | None


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

    Rules:   A project install writes at the repo root so the file travels with the repository and every teammate gets it on clone. Claude Code and Command Code read <root>/AGENTS.md; Grok scans <root>/.grok/rules. Claude additionally reads <root>/CLAUDE.md, which is written as a link so the two can never disagree.
    """
    agent = root / "AGENTS.md"
    plans = {
        "claude": HarnessPlan(
            "claude", {agent: CONTRACT_DIR / "AGENTS.md", root / "CLAUDE.md": CONTRACT_DIR / "AGENTS.md"}, None
        ),
        "commandcode": HarnessPlan(
            "commandcode", {agent: CONTRACT_DIR / "AGENTS.md"}, None
        ),
        "grok": HarnessPlan(
            "grok", {agent: CONTRACT_DIR / "AGENTS.md"}, root / ".grok" / "rules"
        ),
    }
    return plans


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


def apply_plan(plan: HarnessPlan, contract_dir: Path, dry_run: bool) -> list[str]:
    """Create one harness's links and Grok rule files, reporting each change.

    Rules:   Verify each written path resolves before reporting it, since a link to a missing source loads nothing and fails silently in every harness. Report every action in file order so a partial run shows exactly what landed.
    """
    actions: list[str] = []
    for target, source in plan.links.items():
        if dry_run:
            actions.append(f"{plan.harness}: {_link(target, source, dry_run=True)} {target}")
            continue
        action = _link(target, source)
        if not target.exists():
            raise SystemExit(f"install: {target} does not resolve after linking")
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
        "--no-hooks", action="store_true", help="skip the RTK/discovery hook wiring"
    )
    args = parser.parse_args(argv)

    if not (CONTRACT_DIR / "AGENTS.md").is_file():
        print(f"install: {CONTRACT_DIR / 'AGENTS.md'} is missing", file=sys.stderr)
        return 1

    home = Path(args.home).expanduser()
    chosen = HARNESSES if args.harness == "all" else (args.harness,)
    plans = (
        plan_harnesses(home)
        if args.scope == "user"
        else plan_project(Path(args.root).expanduser().resolve())
    )

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
        )
        emitted.update(unique.links)
        for action in apply_plan(unique, CONTRACT_DIR, args.dry_run):
            print(action)

    if not args.no_hooks and not args.dry_run and args.scope == "user":
        sys.path.insert(0, str(SKILL_DIR / "hooks"))
        import install_hooks

        for harness in chosen:
            for change in install_hooks.install(harness, home):
                print(f"hooks: {change.action} {change.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
