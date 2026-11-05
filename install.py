"""install.py — Put the contract in front of every harness that reads it.

exports: HARNESSES | SPECS | HarnessPlan | HarnessSpec | detect | find_conflicts | main | plan_harnesses | plan_project | render_grok_rules | sync_contract_mirror
used_by: README.md → the install section
used_by: tests/test_install.py → CONTRACT_DIR, HARNESSES, HOME_DIR, SKILL_DIR, HarnessPlan, apply_plan, detect, find_conflicts, main, plan_harnesses, plan_project, render_grok_rules, sync_contract_mirror [cascade]
related: contract/AGENTS.md is the source and contract/*.md are its companions.
rules:   Emit per harness from SPECS, never hand-copy. AGENTS.md is the thin core and names its companions by bare filename, so every harness receives the contract plus the companions beside it, or as standalone rules where the harness scans a rules directory. User scope symlinks unless a harness refuses links; fx gets regular files and a real skill copy. Project scope copies. A harness with `skill_dir` also gets the skill linked into that directory; harnesses that discover the central `.agents/skills` leave it unset. `global_files` and `project_files` map extra config files, such as Aider's `.aider.conf.yml`, to a contract source. A broken symlink contributes nothing, so verify every emitted path before reporting success. Never overwrite a file the user owns: a differing regular file or directory is refused unless --force, which replaces it outright. Directory comparisons and copies ignore Python bytecode caches, which tests recreate.
agent:   fx | unknown | 2026-10-31 | unknown | ignored Python bytecode caches when comparing and copying the fx skill, so test runs no longer look like source drift
agent:   fx | unknown | 2026-11-01 | 01a196ba-7693-7c40-9caa-dff862b90cac | dropped the .bak backup from --force: repeated forced runs had piled up agents-contract.bak and .bak1 beside the fx skill copy
agent:   fx | unknown | 2026-11-05 | unknown | hardened install paths, force directory replacement, target verification, no-op reporting, and mirror idempotency
agent:   fx | unknown | 2026-11-05 | unknown | added read-only --check drift verification and documented the contract bootstrap
agent:   fx | unknown | 2026-11-05 | unknown | added loop.md to the companion set installed for every adapter
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
COMPANIONS = ("codedna.md", "RTK.md", "semble.md", "caveman.md", "ponytail.md", "loop.md")
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


def _sync_copy(source: Path, target: Path, dry_run: bool = False) -> str:
    """Copy source over target through the shared file writer.

    Rules:   Byte comparison and staged replacement live in `_copy`; a mirror re-run must report `unchanged` and a dry run must write nothing. The target is always a regular file, not a linked skill tree.
    """
    return _copy(target, source, dry_run)


def sync_contract_mirror(
    contract_dir: Path, skill_dir: Path, dry_run: bool = False
) -> list[tuple[Path, str]]:
    """Write the skill's copies of the contract, CodeDNA, and RTK catalogue.

    Rules:   The skill reads references/contract.md, references/codedna.md, and references/commands.md; each copy must match its source byte for byte — a stale mirror is what made the skill and the contract disagree. Compare before writing so a re-run reports `unchanged`; return every path with its action so the caller reports each one, and write nothing when `dry_run`.
    """
    references = skill_dir / "references"
    pairs = (
        (contract_dir / "AGENTS.md", references / "contract.md"),
        (contract_dir / "codedna.md", references / "codedna.md"),
        (contract_dir / "RTK.md", references / "commands.md"),
    )
    return [(target, _sync_copy(source, target, dry_run)) for source, target in pairs]


def _companion_links(base: Path) -> dict[Path, Path]:
    """Return the companion links that live beside one harness's AGENTS.md.

    Rules:   The contract names each companion by bare filename, so a harness reading sibling files gets all six. A rules-directory harness gets none here because its whole companions are written into the rules directory instead.
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

    Rules:   Replace a stale link or an existing file, because a leftover copy shadows the contract and drifts from it — that is the failure this script exists to end. Remove a real directory only when the caller chose --force, since a skill directory is not a file to unlink. Create the parent directory first; a harness directory may not exist yet. A dry run reports the same decision and changes nothing.
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


def _copy(target: Path, source: Path, dry_run: bool = False) -> str:
    """Write source's contents to target and report what happened.

    Rules:   Compare bytes so a re-run reports `unchanged` instead of rewriting — a project install is committed, and a spurious write shows as churn. Write through a staged sibling and move it into place so a concurrent read never sees a partial file. A directory or symlink at the target is removed before the move: `--force` must replace the shape the user had, and `os.replace` cannot put a file over a directory. A dry run reports the decision and writes nothing.
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
    if target.is_symlink():
        target.unlink()
    elif target.exists() and not target.is_file():
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    os.replace(staged, target)
    return action


def _verify_target(target: Path, expected: str) -> None:
    """Raise when a written install path is missing or the wrong shape.

    Rules:   A link to a missing source and a copy that landed in the wrong shape both load nothing, so verify after every write. `file` rejects a directory; `dir` rejects a symlink because a copied skill must be real files.
    """
    if expected == "dir":
        ok = target.is_dir() and not target.is_symlink()
    elif expected == "link":
        ok = target.exists()
    else:
        ok = target.is_file()
    if not ok:
        raise OSError(f"{target} is not a {expected} after writing")


def _apply_links(plan: HarnessPlan, dry_run: bool) -> list[str]:
    """Write or report one plan's file and skill links.

    Rules:   A dry run reports the decision without checking resolution, since nothing was written. A real write is verified before it is reported.
    """
    actions: list[str] = []
    writer = _copy if plan.copy else _link
    for target, source in plan.links.items():
        action = writer(target, source, dry_run)
        if not dry_run:
            _verify_target(target, "link" if source.is_dir() else "file")
        actions.append(f"{plan.harness}: {action} {target}")
    return actions


def _apply_dirs(plan: HarnessPlan, dry_run: bool) -> list[str]:
    """Copy or report one plan's directory trees, such as a real skill copy.

    Rules:   Compare the whole tree first so a re-run stays `unchanged`; stage the copy before replacing the target, because replacing first would lose the old tree when the copy fails. Ignore bytecode caches in both comparison and copy.
    """
    actions: list[str] = []
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
        _verify_target(target, "dir")
        actions.append(f"{plan.harness}: wrote {target}")
    return actions


def _write_text(target: Path, text: str) -> str:
    """Write text through a staged sibling and report the action.

    Rules:   Write the staged file before removing a directory or symlink at the target, so a failed write cannot destroy the user's existing path. Return `unchanged` when the bytes already match.
    """
    same = target.is_file() and not target.is_symlink() and target.read_text(encoding="utf-8") == text
    if same:
        return "unchanged"
    action = "replaced" if target.is_symlink() or target.exists() else "wrote"
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = target.with_name(target.name + ".staged")
    staged.write_text(text, encoding="utf-8")
    if target.is_symlink():
        target.unlink()
    elif target.exists() and not target.is_file():
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    os.replace(staged, target)
    return action


def _apply_rules(plan: HarnessPlan, contract_dir: Path, dry_run: bool) -> list[str]:
    """Write or report the standalone companion files a rules-directory harness scans.

    Rules:   Each companion ships whole; a dry run reports the decision and writes nothing; a real write is verified as a regular file.
    """
    if plan.rules_dir is None:
        return []
    actions: list[str] = []
    for name, text in render_grok_rules(contract_dir).items():
        target = plan.rules_dir / name
        same = target.is_file() and target.read_text(encoding="utf-8") == text
        if dry_run:
            action = "unchanged" if same else "write"
            actions.append(f"{plan.harness}: {action} {target} (dry run)")
            continue
        action = _write_text(target, text)
        _verify_target(target, "file")
        actions.append(f"{plan.harness}: {action} {target}")
    return actions


def apply_plan(plan: HarnessPlan, contract_dir: Path, dry_run: bool) -> list[str]:
    """Create one harness's links or copies and rules files, reporting each change.

    Rules:   Verify each written path resolves before reporting it, since a link to a missing source loads nothing. Report every action so a partial run shows exactly what landed. A copy plan writes file contents; a link plan points at the contract.
    """
    actions = _apply_links(plan, dry_run)
    actions.extend(_apply_dirs(plan, dry_run))
    actions.extend(_apply_rules(plan, contract_dir, dry_run))
    return actions


def print_harnesses(home: Path, show_status: bool = True) -> None:
    """Print the adapter registry, optionally with detection status.

    Rules:   Report the tier and every candidate binary so a missing install is actionable. `--list-harnesses` omits detection so it stays a pure registry; `--detect` adds it. Detection is advisory, not proof that the harness loads the contract.
    """
    for spec in SPECS:
        base = f"{spec.name:12} {spec.tier:7} "
        if show_status:
            base += f"{'detected' if detect(spec, home) else 'missing':8} "
        print(f"{base}config={spec.config_dir} binaries={','.join(spec.binaries) or '-'}")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse the installer command line.

    Rules:   Defaults stay safe: user scope, all harnesses, no writes when `--dry-run`. Every harness name is a valid choice so a typo fails in argparse rather than silently installing nothing.
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
    parser.add_argument("--root", default=".", help="project root for --scope project")
    parser.add_argument("--dry-run", action="store_true", help="report, do not write")
    parser.add_argument(
        "--check",
        action="store_true",
        help="read-only: exit 1 when a selected path is stale",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing contract file or directory",
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
    return parser.parse_args(argv)


def _require_directory(path: Path, label: str) -> str | None:
    """Return a clean error when a CLI path is missing or not a directory.

    Rules:   Validate before any mirror or target write; a file at the path would otherwise raise from `mkdir` or `os.replace` after partial work.
    """
    if not path.exists():
        return f"install: {label} {path} does not exist"
    if not path.is_dir():
        return f"install: {label} {path} is not a directory"
    return None


def _resolve_scope(args: argparse.Namespace, home: Path) -> tuple[Path | None, str | None]:
    """Return the resolved project root, or validate the user-scope home.

    Rules:   Project scope accepts an existing repository outside the lowheat checkout; nesting inside it would overwrite `contract/` sources. User scope needs an existing home but never touches the project root.
    """
    if args.scope == "project":
        root = Path(args.root).expanduser().resolve()
        error = _require_directory(root, "project root")
        if error is not None:
            return None, error
        if root == _HERE or root.is_relative_to(_HERE) or _HERE.is_relative_to(root):
            return None, (
                f"install: {root} overlaps the lowheat source checkout, not a project — "
                "project scope would duplicate contract/ into that tree"
            )
        return root, None
    error = _require_directory(home, "home")
    return (None, error) if error is not None else (None, None)


def _select_harnesses(args: argparse.Namespace, home: Path) -> tuple[tuple[str, ...], str | None]:
    """Return the harnesses the request selected.

    Rules:   `all` is the full registry; `auto` selects detected harnesses and refuses an empty result; one name is passed through. A harness without a user-scope plan is reported by the caller, not treated as a detection failure.
    """
    if args.harness == "all":
        return HARNESSES, None
    if args.harness == "auto":
        chosen = tuple(spec.name for spec in SPECS if detect(spec, home))
        if not chosen:
            return (), "install: no harness detected under this home"
        return chosen, None
    return (args.harness,), None


def _selected_plans(
    plans: dict[str, HarnessPlan], chosen: tuple[str, ...]
) -> dict[str, HarnessPlan]:
    """Return the plans for the selected harnesses only.

    Rules:   Project-only harnesses have no user-scope plan; dropping them here is what makes a no-op explicit instead of installing nothing silently.
    """
    return {name: plan for name, plan in plans.items() if name in chosen}


def _sync_mirrors(dry_run: bool) -> list[str]:
    """Write or report the three skill mirrors.

    Rules:   Report `unchanged` instead of rewriting equal bytes, and honor `--dry-run` so the report matches a real run. Return every line so `--check` can decide whether any mirror is stale.
    """
    actions: list[str] = []
    for path, action in sync_contract_mirror(CONTRACT_DIR, SKILL_DIR, dry_run):
        line = f"contract: {action} {path}"
        print(line)
        actions.append(line)
    return actions


def _apply_selected(
    plans: dict[str, HarnessPlan], chosen: tuple[str, ...], dry_run: bool
) -> list[str]:
    """Apply each selected harness once, skipping paths an earlier harness already emitted.

    Rules:   Cline and the central `.agents` adapter share the same targets; custom adapters may overlap too. Deduplicate links and tree targets before writing so the second harness never repeats a write. Return every action for `--check`.
    """
    emitted: set[Path] = set()
    actions: list[str] = []
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
        for action in apply_plan(unique, CONTRACT_DIR, dry_run):
            print(action)
            actions.append(action)
    return actions


def _refuse_conflicts(
    plans: dict[str, HarnessPlan], chosen: tuple[str, ...], force: bool
) -> bool:
    """Report and refuse foreign files unless the caller forced replacement.

    Rules:   Every conflicting path is printed before the run exits, and `--force` bypasses the refusal entirely. A missing conflict means the install may proceed.
    """
    conflicts = find_conflicts(plans, chosen, CONTRACT_DIR)
    if not conflicts or force:
        return False
    for path in conflicts:
        print(f"install: refusing to overwrite {path}", file=sys.stderr)
    print(
        "install: that file is not ours; re-run with --force to replace it",
        file=sys.stderr,
    )
    return True


def _is_unchanged_action(line: str) -> bool:
    """Return whether a reported action is `unchanged`, not merely a path match.

    Rules:   Match the leading verb after `harness: `, because a target path may itself contain the word `unchanged`. A dry-run rules action reports `write`, which is drift.
    """
    body = line.split(": ", 1)[-1]
    return body.split(maxsplit=1)[0] == "unchanged"


def _execute(
    args: argparse.Namespace,
    plans: dict[str, HarnessPlan],
    selected: dict[str, HarnessPlan],
) -> int:
    """Run the selected install, or the read-only drift check.

    Rules:   `--check` never writes: conflicts and any action other than `unchanged` mean drift and exit 1. A normal run keeps the existing conflict refusal, then writes mirrors and harness plans.
    """
    try:
        if args.check:
            conflicts = find_conflicts(plans, tuple(selected), CONTRACT_DIR)
            if conflicts:
                for path in conflicts:
                    print(f"install: stale {path}", file=sys.stderr)
                return 1
        elif _refuse_conflicts(plans, tuple(selected), args.force):
            return 1
        dry_run = args.dry_run or args.check
        actions = _sync_mirrors(dry_run)
        actions.extend(_apply_selected(plans, tuple(selected), dry_run))
    except OSError as error:
        print(f"install: {error}", file=sys.stderr)
        return 1
    if not args.check:
        return 0
    stale = [action for action in actions if not _is_unchanged_action(action)]
    if stale:
        for action in stale:
            print(f"install: stale {action}", file=sys.stderr)
        return 1
    print("install: all selected paths match")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Wire the contract into harnesses, then sync the skill mirror.

    Rules:   Refuse to run when the contract source is missing — a half-installed contract is worse than none. Validate paths before writing, report project-only selections instead of silently doing nothing, and print every action; exit 0 whether or not anything changed, so a re-run is safe in a script. `--check`, `--list-harnesses`, and `--detect` are read-only.
    """
    args = _parse_args(argv)
    home = Path(args.home).expanduser()
    if args.list_harnesses or args.detect:
        print_harnesses(home, show_status=args.detect)
        return 0

    if not (CONTRACT_DIR / "AGENTS.md").is_file():
        print(f"install: {CONTRACT_DIR / 'AGENTS.md'} is missing", file=sys.stderr)
        return 1

    project_root, error = _resolve_scope(args, home)
    if error is not None:
        print(error, file=sys.stderr)
        return 1

    chosen, error = _select_harnesses(args, home)
    if error is not None:
        print(error, file=sys.stderr)
        return 1

    plans = plan_harnesses(home) if args.scope == "user" else plan_project(project_root)
    selected = _selected_plans(plans, chosen)
    skipped = [name for name in chosen if name not in plans]
    if skipped and args.harness != "all":
        print(
            f"install: {', '.join(skipped)} not available in user scope; use --scope project",
            file=sys.stderr,
        )
    if not selected:
        if args.check:
            print(
                "install: no installable surface to check; use --scope project",
                file=sys.stderr,
            )
            return 1
        return 0
    return _execute(args, plans, selected)


if __name__ == "__main__":
    raise SystemExit(main())
