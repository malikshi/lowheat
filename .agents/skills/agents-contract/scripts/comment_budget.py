"""comment_budget.py — Count permitted comment lines and enforce a shrinking baseline.

exports: bootstrap_project | compare_budget | count_comments | load_baseline | main
used_by: tests/test_comment_budget.py → count_comments, compare_budget, load_baseline, main [cascade]
used_by: tests/test_comment_bootstrap.py → bootstrap_project, main [cascade]
used_by: README.md → the comment-budget section
related: codedna_check.py owns the ban itself; this script only measures the annotation surface.
rules:   Read-only unless --update or --bootstrap is passed. Two numbers only: `comments` (every permitted annotation line) and `open_notes` (message: lines, the genuinely unresolved items). Directive bodies and shebangs are not debt; a bare separator line is. --update may lower or hold a number and must refuse to raise one without --force — that refusal is the ratchet. --bootstrap is the only action that may create a baseline, needs an explicit --template-dir, and never overwrites an existing file or resets a corrupt one. Exit 1 when a number exceeds the baseline, an update would raise it, or a bootstrap is missing pieces; 2 on a missing path, an unreadable baseline, or malformed input, so a typo never reads clean.
agent:   unknown | nexrouter | 2026-11-21 | unknown | added the annotation budget and its ratchet after measuring the comment surface
agent:   unknown | nexrouter | 2026-11-21 | unknown | added explicit --bootstrap so a user-scope install can bootstrap a plain project without weakening --update
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from codedna_check import collect_source_files
from codedna_content import _comment_bodies, _is_directive_body
from codedna_masking import _python_scan_inputs, _shell_heredoc_lines, mask_code
from codedna_spec import DEFAULT_IGNORED_DIRS, profile_for

_FIELDS = ("comments", "open_notes")


def _python_comment_lines(
    path: Path, text: str
) -> tuple[set[int], dict[int, tuple[str, ...]]]:
    """Return the comment-bearing line numbers and their bodies for Python source.

    Rules:   `comment_bodies` covers full-line and trailing `#` comments; a shebang and a directive body are not debt, matching the other dialects; a file that does not tokenize yields nothing.
    """
    scan_inputs = _python_scan_inputs(text)
    if scan_inputs is None:
        return set(), {}
    _, comment_lines, bodies = scan_inputs
    lines = text.split("\n")
    counted = {
        line
        for line, parts in bodies.items()
        if _has_content(profile_for(path), parts) and not _is_shebang(lines, line)
    }
    return counted, bodies


def _generic_comment_lines(path: Path, text: str) -> tuple[set[int], dict[int, tuple[str, ...]]]:
    """Return the comment-bearing line numbers and their bodies for a non-Python dialect.

    Rules:   Spans come from the profile-aware masker, so a marker inside a literal is never a comment; a shebang on line 1 is not debt in any dialect.
    """
    profile = profile_for(path)
    spans: list[tuple[int, int]] = []
    mask_code(profile, text, spans)
    bodies = _comment_bodies(profile, text, spans)
    lines = text.split("\n")
    data_lines = _shell_heredoc_lines(text) if profile.name == "shell" else frozenset()
    counted = {
        line
        for line, parts in bodies.items()
        if line not in data_lines
        and _has_content(profile, parts)
        and not _is_shebang(lines, line)
    }
    return counted, bodies


def _has_content(profile, parts: tuple[str, ...]) -> bool:
    """Judge a comment line's bodies worth counting as debt."""
    return any(part and not _is_directive_body(profile, part) for part in parts)


def _is_shebang(lines: list[str], line_no: int) -> bool:
    """Judge one line the executable shebang rather than a comment."""
    return line_no == 1 and lines[0].startswith("#!")


def _docstring_lines(text: str) -> list[str]:
    """Return the non-blank content lines of every docstring in one Python module.

    Rules:   The module docstring, and every class and function docstring, count once per non-blank line; a file that does not parse contributes none.
    """
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return []
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        docstring = ast.get_docstring(node, clean=False)
        if docstring is None:
            continue
        found.extend(line.strip() for line in docstring.splitlines() if line.strip())
    return found


def _count_file(path: Path) -> tuple[int, int]:
    """Return the comment-line and open-note counts for one file."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0, 0
    if path.suffix.lower() == ".py":
        counted, bodies = _python_comment_lines(path, text)
        docstring = _docstring_lines(text)
        comments = len(counted) + len(docstring)
        notes = sum(1 for line in docstring if line.startswith("message:"))
        notes += sum(
            1 for parts in bodies.values() for part in parts if part.startswith("message:")
        )
        return comments, notes
    counted, bodies = _generic_comment_lines(path, text)
    notes = sum(
        1 for line in counted for part in bodies.get(line, ()) if part.startswith("message:")
    )
    return len(counted), notes


def count_comments(paths, ignored_dirs=DEFAULT_IGNORED_DIRS) -> dict[str, int]:
    """Return the `comments` and `open_notes` totals for the given paths.

    Rules:   File collection follows the checker's ignore rules, so the budget measures the same tree the ban covers.
    """
    comments = 0
    open_notes = 0
    for path in collect_source_files(paths, ignored_dirs):
        file_comments, file_notes = _count_file(path)
        comments += file_comments
        open_notes += file_notes
    return {"comments": comments, "open_notes": open_notes}


def compare_budget(observed: dict[str, int], baseline: dict[str, int]) -> list[str]:
    """Return the metric names whose observed value exceeds the baseline.

    Rules:   A missing baseline key reads as zero, so an unset number cannot hide growth.
    """
    return [name for name in _FIELDS if observed.get(name, 0) > baseline.get(name, 0)]


def load_baseline(path: Path) -> dict[str, int] | None:
    """Return the stored baseline counts, or None when the file is absent or malformed.

    Rules:   Every field must be a non-negative real integer; a bool, a string, a negative, a missing key, or a non-object makes the whole baseline unreadable rather than silently defaulting a number to zero, because a defaulted key is a free ratchet reset.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    if not all(_is_count(data.get(name)) for name in _FIELDS):
        return None
    return {name: data[name] for name in _FIELDS}


def _is_count(value) -> bool:
    """Judge one stored baseline number well formed.

    Rules:   `bool` is an `int` subclass, so it is rejected explicitly; a negative count cannot describe a surface.
    """
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


_BOOTSTRAP_FILES = (
    ("adr/0000-template.md", Path("adr") / "0000-template.md"),
    ("adr/README.md", Path("adr") / "README.md"),
    ("comment-debt.md", Path("comment-debt.md")),
)


def bootstrap_project(
    baseline_path: Path, template_dir: Path, observed: dict[str, int]
) -> tuple[bool, list[str]]:
    """Create a first-run baseline and audit templates without overwriting anything.

    Rules:   `template_dir` is the source docs root holding `adr/` and `comment-debt.md`, and targets are written beside the baseline in the same layout. A baseline that exists but is unreadable is an error, never a reset — a corrupt file may hold a real ceiling that must not be discarded. Every template must exist before anything is copied, so a half-installed skill cannot produce a broken project. Existing files stay byte-for-byte intact.
    """
    if baseline_path.exists() and load_baseline(baseline_path) is None:
        return False, [f"existing baseline at {baseline_path} is unreadable"]

    source_root = Path(template_dir)
    missing = [
        name for name, _ in _BOOTSTRAP_FILES if not (source_root / name).is_file()
    ]
    if missing:
        return False, [f"template docs missing: {', '.join(missing)}"]

    created: list[str] = []
    try:
        if not baseline_path.exists():
            baseline_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"version": 1, **{name: observed[name] for name in _FIELDS}}
            baseline_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            created.append(str(baseline_path))
        docs_dir = baseline_path.parent
        for name, relative in _BOOTSTRAP_FILES:
            target = docs_dir / relative
            source = source_root / name
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
            created.append(str(target))
    except OSError as error:
        return False, [f"cannot write bootstrap files: {error}"]
    return True, created


def _write_baseline(path: Path, observed: dict[str, int]) -> bool:
    """Write the observed counts as the new baseline, reporting whether the write landed.

    Rules:   An unwritable path is reported rather than raised, so a bad `--baseline` value exits cleanly instead of printing a traceback.
    """
    payload = {"version": 1, **{name: observed[name] for name in _FIELDS}}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError as error:
        print(f"comment_budget: cannot write {path}: {error}")
        return False
    return True


def main(argv=None) -> int:
    """Measure the comment surface and enforce or update the baseline.

    Rules:   A missing scanned path exits 2 before any measurement. `--update` holds or lowers and refuses to raise without `--force`; a baseline that is absent or malformed still refuses, because letting it through would reset the ratchet for free. Without `--update`, an unreadable baseline exits 2 rather than reporting a false clean run.
    """
    parser = argparse.ArgumentParser(description="Count permitted comment lines against a shrinking baseline.")
    parser.add_argument("paths", nargs="*", help="files or directories to scan (default: .)")
    parser.add_argument("--baseline", default="docs/comment-budget.json", help="baseline JSON path")
    parser.add_argument("--update", action="store_true", help="write the observed counts as the baseline")
    parser.add_argument("--force", action="store_true", help="allow --update to raise a number")
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="create a first-run baseline and ADR/debt templates in the baseline's docs directory",
    )
    parser.add_argument(
        "--template-dir",
        default=None,
        help="directory holding 0000-template.md, README.md, and comment-debt.md (required with --bootstrap)",
    )
    parser.add_argument(
        "--against",
        default=None,
        help="compare the baseline against an older baseline file; exit 1 if it grew",
    )
    parser.add_argument("--quiet", action="store_true", help="print nothing on success")
    args = parser.parse_args(argv)

    if args.against:
        current = load_baseline(Path(args.baseline))
        previous = load_baseline(Path(args.against))
        if current is None or previous is None:
            print(
                f"comment_budget: need two readable baselines to compare "
                f"{args.against} -> {args.baseline}"
            )
            return 2
        raised = [name for name in _FIELDS if current[name] > previous[name]]
        for name in raised:
            print(
                f"comment_budget: baseline {name} grew {previous[name]} -> {current[name]}; "
                "a baseline may only be lowered or held"
            )
        return 1 if raised else 0

    roots = [Path(item) for item in args.paths] or [Path(".")]
    missing = [item for item in roots if not item.exists()]
    if missing:
        for item in missing:
            print(f"comment_budget: path not found: {item}")
        return 2

    observed = count_comments(roots)
    baseline_path = Path(args.baseline).resolve()
    baseline = load_baseline(baseline_path)

    if args.bootstrap:
        if not args.template_dir:
            print("comment_budget: --bootstrap needs --template-dir")
            return 2
        ok, detail = bootstrap_project(
            Path(args.baseline), Path(args.template_dir), observed
        )
        if not ok:
            for line in detail:
                print(f"comment_budget: {line}")
            return 2
        if not args.quiet:
            if detail:
                for path in detail:
                    print(f"comment_budget: created {path}")
            else:
                print(f"comment_budget: bootstrap already complete at {args.baseline}; all files kept")
        return 0

    if args.update:
        if baseline is None and not args.force:
            print(
                f"comment_budget: no readable baseline at {baseline_path}; "
                "refusing to create one without --force"
            )
            return 1
        if baseline is not None and not args.force:
            raised = [name for name in _FIELDS if observed[name] > baseline[name]]
            if raised:
                for name in raised:
                    print(
                        f"comment_budget: refusing to raise {name} "
                        f"{baseline[name]} -> {observed[name]} (use --force)"
                    )
                return 1
        if not _write_baseline(baseline_path, observed):
            return 2
        if not args.quiet:
            print(f"comment_budget: updated {baseline_path} {observed}")
        return 0

    if baseline is None:
        print(f"comment_budget: no readable baseline at {baseline_path}")
        return 2
    exceeded = compare_budget(observed, baseline)
    for name in _FIELDS:
        if not args.quiet:
            print(f"comment_budget: {name} {observed[name]} / {baseline[name]}")
    if exceeded:
        for name in exceeded:
            print(
                f"comment_budget: {name} exceeds baseline "
                f"{baseline[name]} by {observed[name] - baseline[name]}"
            )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
