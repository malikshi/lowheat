"""install.py — Put the contract in front of every harness that reads it.

exports: HARNESSES | SPECS | HarnessPlan | HarnessSpec | detect | find_conflicts | main | plan_harnesses | plan_project | render_grok_rules | sync_contract_mirror
used_by: README.md → the install section
used_by: tests/test_install.py → CONTRACT_DIR, HARNESSES, HOME_DIR, SKILL_DIR, HarnessPlan, apply_plan, detect, find_conflicts, main, plan_harnesses, plan_project, render_grok_rules, sync_contract_mirror [cascade]
related: contract/AGENTS.md is the source and contract/*.md are its companions.
rules:   Emit per harness from SPECS, never hand-copy. AGENTS.md is the thin core and names its companions by bare filename, so every harness receives the contract plus the companions beside it, or as standalone rules where the harness scans a rules directory. User scope symlinks unless a harness refuses links; fx gets regular files and a real skill copy. Project scope copies. A harness with `skill_dir` also gets the skill linked into that directory; harnesses that discover the central `.agents/skills` leave it unset. `global_files` and `project_files` map extra config files, such as Aider's `.aider.conf.yml`, to a contract source. A broken symlink contributes nothing, so verify every emitted path before reporting success. Never overwrite a file the user owns: a differing regular file or directory is refused unless --force writes a .bak first. Directory comparisons and copies ignore Python bytecode caches, which tests recreate.
agent:   fx | unknown | 2026-10-31 | unknown | thin-contract restructure: AGENTS.md drops @-imports, CodeDNA moves to its own companion, and the skill mirrors contract plus CodeDNA plus RTK on demand
agent:   fx | unknown | 2026-10-31 | unknown | replaced the three hardcoded harnesses with a HarnessSpec registry and added detection, Codex, OpenCode, Factory, Kilo, Pi, Cline, Gemini, Cursor, Aider, and Qwen adapters
agent:   fx | unknown | 2026-10-31 | unknown | added Aider's config file, dropped Gemini's duplicate skill link because Gemini discovers the central .agents/skills, and verified Command Code, Grok, and OpenCode load Contract-Version 2026-10-31
agent:   fx | unknown | 2026-10-31 | unknown | added fx, hermes, claw, jcode, omp, forge, smelt, codewhale, and copilot adapters; fx now gets regular instruction files and a real skill copy because it refuses symlinks
agent:   fx | unknown | 2026-10-31 | unknown | ignored Python bytecode caches when comparing and copying the fx skill, so test runs no longer look like source drift
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

_HERE = Path(__file__).resolve().parent
CONTRACT_DIR = _HERE / "contract"
SKILL_DIR = _HERE / ".agents" / "skills" / "agents-contract"
COMPANIONS = ("codedna.md", "RTK.md", "semble.md", "caveman.md", "ponytail.md")
_COPY_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")


@dataclass(frozen=True)
class HarnessSpec:
    """One harness's installation surface.

    Rules:   `memory` names the files the harness reads as global instructions; each resolves to AGENTS.md. `global_base` overrides the directory those files land in (Jcode uses the home directory). `companions` is `beside` when the harness reads sibling files, or `rules` when it scans a directory of standalone rule documents. `project_alias` adds a project-root filename for a harness that does not read AGENTS.md. `project_rules_dir` writes the companions as standalone files under that directory. `global_files` and `project_files` map extra config files to a file under `contract/`. `skill_dir` is unset for harnesses that discover the central `.agents/skills` or read no skills. `copy_global` writes real files because fx refuses symlinked instructions; `copy_skill` recursively copies the skill because fx refuses linked skill directories. `global_install` is false for project-only harnesses whose global memory is UI-managed.
    """

    name: str
    binaries: tuple[str, ...]
    config_dir: str
    memory: tuple[str, ...]
    skill_dir: str | None = "skills"
    companions: str = "beside"
    project_alias: str | None = None
    project_rules_dir: str | None = None
    global_base: str | None = None
    global_files: tuple[tuple[str, str], ...] = ()
    project_files: tuple[tuple[str, str], ...] = ()
    copy_global: bool = False
    copy_skill: bool = False
    global_install: bool = True
    tier: str = "native"


SPECS = (
    HarnessSpec("claude", ("claude",), ".claude", ("AGENTS.md", "CLAUDE.md"), project_alias="CLAUDE.md"),
    HarnessSpec("codex", ("codex",), ".codex", ("AGENTS.md",)),
    HarnessSpec("commandcode", ("commandcode", "command-code"), ".commandcode", ("AGENTS.md",)),
    HarnessSpec("grok", ("grok",), ".grok", ("AGENTS.md",), companions="rules", project_rules_dir=".grok/rules"),
    HarnessSpec("opencode", ("opencode",), ".config/opencode", ("AGENTS.md",), skill_dir=None),
    HarnessSpec("factory", ("droid",), ".factory", ("AGENTS.md",)),
    HarnessSpec("kilo", ("kilo", "kilocode"), ".config/kilo", ("AGENTS.md",), skill_dir=None),
    HarnessSpec("pi", ("pi",), ".pi/agent", ("AGENTS.md",)),
    HarnessSpec("cline", ("cline",), ".agents", ("AGENTS.md",)),
    HarnessSpec("agents", (), ".agents", ("AGENTS.md",), tier="agents"),
    HarnessSpec("gemini", ("gemini",), ".gemini", ("GEMINI.md",), skill_dir=None, project_alias="GEMINI.md", tier="agents"),
    HarnessSpec("crush", ("crush",), ".config/crush", ("CRUSH.md",), skill_dir=None, project_alias="CRUSH.md", tier="agents"),
    HarnessSpec("cursor", ("cursor",), ".cursor", (), skill_dir=None, global_install=False, tier="agents"),
    HarnessSpec("continue", ("cn",), ".continue", (), skill_dir=None, global_install=False, project_files=((".continue/rules/agents-contract.md", "continue.md"),), tier="alias"),
    HarnessSpec("aider", ("aider",), ".aider", (), skill_dir=None, project_alias="CONVENTIONS.md", global_files=((".aider.conf.yml", "aider.conf.yml"),), project_files=((".aider.conf.yml", "aider.conf.yml"),), tier="alias"),
    HarnessSpec("qwen", ("qwen", "qwen-code"), ".qwen", ("QWEN.md",), skill_dir=None, project_alias="QWEN.md", tier="alias"),
    HarnessSpec("fx", ("fx",), ".fx", ("AGENTS.md",), copy_global=True, copy_skill=True, tier="agents"),
    HarnessSpec("hermes", ("hermes",), ".hermes", (), skill_dir="skills", tier="agents"),
    HarnessSpec("claw", ("openclaw", "claw"), ".openclaw", ("AGENTS.md",), skill_dir=None, global_base=".openclaw/workspace", tier="agents"),
    HarnessSpec("jcode", ("jcode",), ".jcode", ("AGENTS.md",), skill_dir="skills", global_base="", tier="agents"),
    HarnessSpec("omp", ("omp",), ".omp/agent", ("AGENTS.md",), skill_dir=None, tier="agents"),
    HarnessSpec("forge", ("forge",), "forge", ("AGENTS.md",), skill_dir="skills", tier="agents"),
    HarnessSpec("smelt", ("smelt",), ".config/smelt", ("AGENTS.md",), skill_dir="skills", tier="agents"),
    HarnessSpec("codewhale", ("codewhale", "codew"), ".codewhale", (), skill_dir="skills", tier="agents"),
    HarnessSpec("copilot", ("copilot",), ".copilot", (), skill_dir=None, global_files=((".copilot/copilot-instructions.md", "AGENTS.md"),), tier="agents"),
)

HARNESSES = tuple(spec.name for spec in SPECS)
HOME_DIR = {spec.name: spec.config_dir for spec in SPECS}
SPEC_BY_NAME = {spec.name: spec for spec in SPECS}


@dataclass(frozen=True)
class HarnessPlan:
    """One harness's install shape and the paths it needs.

    Rules:   `links` maps a path to create to the contract or skill source. `rules_dir` names a directory whose companion files are written whole because that harness scans it. `copy` writes contents instead of a symlink, required for project scope where a link into the installer's checkout is dead on another clone.
    """

    harness: str
    links: dict[Path, Path]
    rules_dir: Path | None
    copy: bool = False
    dirs: dict[Path, Path] = field(default_factory=dict)


def detect(spec: HarnessSpec, home: Path) -> bool:
    """Return whether a harness looks installed under one home.

    Rules:   A binary on PATH or an existing config directory counts. Detection never proves the harness loaded the contract; it only decides which adapters `--harness auto` selects.
    """
    return any(shutil.which(binary) for binary in spec.binaries) or (home / spec.config_dir).is_dir()


def render_grok_rules(contract_dir: Path) -> dict[str, str]:
    """Return the companion files a rules-directory harness needs as standalone documents.

    Rules:   These harnesses read every `*.md` directly inside the rules directory, so each companion ships whole. Keep the filename stem: a stable alphabetical order keeps the prompt cache warm.
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


def _companion_links(base: Path) -> dict[Path, Path]:
    """Return the companion links that live beside one harness's AGENTS.md.

    Rules:   The contract names each companion by bare filename, so a harness reading sibling files gets all five. A rules-directory harness gets none here because its whole companions are written into the rules directory instead.
    """
    return {base / name: CONTRACT_DIR / name for name in COMPANIONS}


def plan_harnesses(home: Path) -> dict[str, HarnessPlan]:
    """Return the user-scope install shape for every harness with global memory.

    Rules:   Resolve every target under the caller's home so a test can point at a temporary directory and never touch real configs. Each spec supplies its memory filenames, companion mode, and skill directory. Harnesses whose global memory is UI-managed are skipped here and handled only in project scope.
    """
    plans: dict[str, HarnessPlan] = {}
    for spec in SPECS:
        if not spec.global_install:
            continue
        if not spec.memory and not spec.global_files and not spec.skill_dir:
            continue
        base = home / spec.config_dir
        memory_base = home / spec.global_base if spec.global_base is not None else base
        links: dict[Path, Path] = {
            memory_base / name: CONTRACT_DIR / "AGENTS.md" for name in spec.memory
        }
        dirs: dict[Path, Path] = {}
        rules_dir = memory_base / "rules" if spec.companions == "rules" else None
        if rules_dir is None and spec.memory:
            links.update(_companion_links(memory_base))
        if spec.skill_dir:
            target = base / spec.skill_dir / SKILL_DIR.name
            if spec.copy_skill:
                dirs[target] = SKILL_DIR
            else:
                links[target] = SKILL_DIR
        for target, source in spec.global_files:
            links[home / target] = CONTRACT_DIR / source
        plans[spec.name] = HarnessPlan(
            spec.name, links, rules_dir, copy=spec.copy_global, dirs=dirs
        )
    return plans


def plan_project(root: Path) -> dict[str, HarnessPlan]:
    """Return the project-scope shape, rooted at one repository.

    Rules:   A project install lands real files, not links: the contract is committed, and a symlink into the installing machine's checkout is dead on another clone. Every plan shares root AGENTS.md and the companions so named references resolve. A harness that needs its own filename gets an alias; a rules-directory harness gets its companions written there too.
    """
    agent = root / "AGENTS.md"
    plans: dict[str, HarnessPlan] = {}
    for spec in SPECS:
        links: dict[Path, Path] = {agent: CONTRACT_DIR / "AGENTS.md"}
        if spec.project_alias:
            links[root / spec.project_alias] = CONTRACT_DIR / "AGENTS.md"
        links.update(_companion_links(root))
        for target, source in spec.project_files:
            links[root / target] = CONTRACT_DIR / source
        rules_dir = root / spec.project_rules_dir if spec.project_rules_dir else None
        plans[spec.name] = HarnessPlan(spec.name, links, rules_dir, copy=True)
    return plans


def _link(target: Path, source: Path, dry_run: bool = False) -> str:
    """Point target at source and report what happened.

    Rules:   Replace a stale link or an existing file, because a leftover copy shadows the contract and drifts from it — that is the failure this script exists to end. Remove a real directory only when the caller has already backed it up and chosen --force, since a skill directory is not a file to unlink. Create the parent directory first; a harness directory may not exist yet. A dry run reports the same decision and changes nothing.
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


def _same_tree(left: Path, right: Path) -> bool:
    """Return whether two directories contain the same relative files and bytes.

    Rules:   A copied skill is idempotent only when its file set and contents match; otherwise the next install must refresh it. Ignore directory mtimes and Python bytecode caches, which every test run changes.
    """
    if not left.is_dir() or left.is_symlink() or not right.is_dir():
        return False
    def source_files(root: Path) -> set[Path]:
        return {
            path.relative_to(root)
            for path in root.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.relative_to(root).parts
            and path.suffix not in (".pyc", ".pyo")
        }
    left_files = source_files(left)
    right_files = source_files(right)
    return left_files == right_files and all(
        (left / name).read_bytes() == (right / name).read_bytes()
        for name in left_files
    )


def find_conflicts(
    plans: dict[str, HarnessPlan], chosen: tuple[str, ...], contract_dir: Path
) -> list[Path]:
    """Return existing files an install would overwrite with different content.

    Rules:   A symlink is never a conflict — it is wiring this script owns and repoints. A regular file whose bytes already match the contract is not a conflict either, so a re-run stays quiet. Anything else is somebody's own file and overwriting it destroys their instructions, so it must be refused rather than replaced. A directory target is always refused because the only directory this script links is the skill, and a real directory there belongs to the user. Rules-directory files count too: they are written by apply_plan outside `links`.
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
        for target, source in plan.dirs.items():
            if target.is_symlink() or not target.exists():
                continue
            if not _same_tree(target, source) and target not in conflicts:
                conflicts.append(target)
        if plan.rules_dir is not None:
            for name, text in render_grok_rules(contract_dir).items():
                note(plan.rules_dir / name, text.encode())
    return conflicts


def backup(target: Path) -> Path:
    """Copy target to a .bak before it is overwritten.

    Rules:   Never overwrite an existing backup, since that would destroy the oldest copy of the user's file — suffix with a counter instead. Copy a real directory recursively, since the only directory target is a skill and --force must preserve it whole. Return the path written so the caller reports it.
    """
    directory, stem = target.parent, target.name
    directory.mkdir(parents=True, exist_ok=True)
    candidate = directory / f"{stem}.bak"
    counter = 1
    while candidate.exists():
        candidate = directory / f"{stem}.bak{counter}"
        counter += 1
    if target.is_dir() and not target.is_symlink():
        shutil.copytree(target, candidate, ignore=_COPY_IGNORE)
    else:
        shutil.copyfile(target, candidate)
    return candidate


def _copy(target: Path, source: Path, dry_run: bool = False) -> str:
    """Write source's contents to target and report what happened.

    Rules:   Compare bytes so a re-run reports `unchanged` instead of rewriting — a project install is committed, and a spurious write shows as churn. Write through a staged sibling and move it into place so a concurrent read never sees a partial file. A dry run reports the decision and writes nothing.
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
    """Create one harness's links or copies and rules files, reporting each change.

    Rules:   Verify each written path resolves before reporting it, since a link to a missing source loads nothing. Report every action so a partial run shows exactly what landed. A copy plan writes file contents; a link plan points at the contract.
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
    for target, source in plan.dirs.items():
        same = _same_tree(target, source)
        if dry_run:
            action = "unchanged" if same else ("replaced" if target.is_symlink() or target.exists() else "wrote")
            actions.append(f"{plan.harness}: {action} {target}")
            continue
        if same:
            actions.append(f"{plan.harness}: unchanged {target}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        staged = target.with_name(target.name + ".staged")
        if staged.exists():
            shutil.rmtree(staged)
        shutil.copytree(source, staged, ignore=_COPY_IGNORE)
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.exists():
            shutil.rmtree(target)
        os.replace(staged, target)
        actions.append(f"{plan.harness}: wrote {target}")
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


def print_harnesses(home: Path) -> None:
    """Print the adapter registry with detection status.

    Rules:   Report the tier and every candidate binary so a missing install is actionable. Detection is advisory, not proof that the harness loads the contract.
    """
    for spec in SPECS:
        status = "detected" if detect(spec, home) else "missing"
        print(
            f"{spec.name:12} {spec.tier:7} {status:8} "
            f"config={spec.config_dir} binaries={','.join(spec.binaries) or '-'}"
        )


def main(argv: list[str] | None = None) -> int:
    """Wire the contract into harnesses, then sync the skill mirror.

    Rules:   Refuse to run when the contract source is missing — a half-installed contract is worse than none. Print every action; exit 0 whether or not anything changed, so a re-run is safe in a script. `--list-harnesses` and `--detect` are read-only.
    """
    parser = argparse.ArgumentParser(
        description="Install the lowheat contract into each harness."
    )
    parser.add_argument("--home", default=str(Path.home()), help="home to wire")
    parser.add_argument(
        "--harness",
        choices=(*HARNESSES, "all", "auto"),
        default="all",
        help="which to wire; auto selects detected harnesses",
    )
    parser.add_argument(
        "--scope",
        choices=("user", "project"),
        default="user",
        help="user scope wires harness config dirs; project scope writes the repo root",
    )
    parser.add_argument(
        "--root", default=".", help="project root for --scope project"
    )
    parser.add_argument("--dry-run", action="store_true", help="report, do not write")
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing contract file, keeping a .bak of it",
    )
    parser.add_argument(
        "--list-harnesses",
        action="store_true",
        help="print supported harnesses and exit",
    )
    parser.add_argument(
        "--detect",
        action="store_true",
        help="print harness detection status and exit",
    )
    args = parser.parse_args(argv)

    home = Path(args.home).expanduser()
    if args.list_harnesses or args.detect:
        print_harnesses(home)
        return 0

    if not (CONTRACT_DIR / "AGENTS.md").is_file():
        print(f"install: {CONTRACT_DIR / 'AGENTS.md'} is missing", file=sys.stderr)
        return 1

    project_root = None if args.scope == "user" else Path(args.root).expanduser().resolve()
    if project_root is not None and project_root == _HERE:
        print(
            f"install: {project_root} is the lowheat source checkout, not a project — "
            "project scope would duplicate contract/ back into the repo root",
            file=sys.stderr,
        )
        return 1

    if args.harness == "all":
        chosen = HARNESSES
    elif args.harness == "auto":
        chosen = tuple(spec.name for spec in SPECS if detect(spec, home))
        if not chosen:
            print("install: no harness detected under this home", file=sys.stderr)
            return 1
    else:
        chosen = (args.harness,)

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
            plan.dirs,
        )
        emitted.update(unique.links)
        emitted.update(unique.dirs)
        for action in apply_plan(unique, CONTRACT_DIR, args.dry_run):
            print(action)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
