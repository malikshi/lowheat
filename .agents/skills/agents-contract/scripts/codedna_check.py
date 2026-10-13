"""codedna_check.py — Report CodeDNA header drift and out-of-contract comment content.

exports: DEFAULT_IGNORED_DIRS | SOURCE_SUFFIXES | TOOL_OWNED_DIRS | LanguageProfile | check_file | check_comment_content | check_examples | collect_source_files | main
used_by: tests/test_codedna_check.py → main, check_file, check_comment_content, check_examples, collect_source_files, DEFAULT_IGNORED_DIRS, TOOL_OWNED_DIRS [cascade]
used_by: AGENTS.md → CodeDNA editing protocol (checker mentions)
related: codedna_spec.py, codedna_masking.py, codedna_headers.py, codedna_content.py hold the split implementation.
rules:   Read-only — report findings carrying line numbers; never rewrite a file. The sibling imports need this directory on sys.path first — the bootstrap below stays above them for direct execution and for importlib path loading. Re-export every name the tests load; the split must stay invisible from the command line.
agent:   grok-4.6 | xai | 2026-10-09 | 01a1165a-8f16-7702-b7e8-488efac69c7e | rewrite: line-numbered findings, 15 language profiles, comment-content scan, agent-entry shape, field order, header-window relief
agent:   claude-fable-5 | anthropic | 2026-10-09 | ddf225f-review | fixed mask_code OR-precedence, HTML double-report, dup type_body_depth reset; dropped dead HEADER_LINE_LIMIT; --skip-content also skips contract examples
agent:   claude-fable-5 | anthropic | 2026-10-09 | ddf225f-lowfix | agent-entry shape via two-pipe regex with per-line malformed reports; SPDX directive exemption; over-cap summary gets word-cap finding, not commented-code
agent:   grok-build | xai | 2026-10-09 | 01a120bc-e75a-79c3-8ab4-e055948b9a83 | skipped tool-owned dirs below the scanned root, added --exclude, scanned Python # comments via tokenize, made Python finding lines absolute, exempted shell heredoc bodies, survived binary input, and after review made a false heredoc opener fail open and the terminator match bash exactly
agent:   unknown | xai | 2026-10-14 | 01a1373b-7fa0-7851-ae9d-4cd27c951a27 | split the 1135-line scanner into codedna_spec, codedna_masking, codedna_headers, and codedna_content; this file is now the entry with the public surface unchanged
message: Keep this file thin — new scan logic belongs in the module named for its job, and tests load the entry by path, so re-check the sys.path bootstrap after any import edit.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Rules: direct execution puts this directory on sys.path already; importlib path loading does not — insert once, before the sibling imports below.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from codedna_content import check_comment_content, check_examples
from codedna_headers import check_file
from codedna_spec import DEFAULT_IGNORED_DIRS, SOURCE_SUFFIXES, LanguageProfile, TOOL_OWNED_DIRS


def collect_source_files(roots, ignored_dirs=DEFAULT_IGNORED_DIRS) -> list[Path]:
    """Return the candidate source files under each root.

    Rules:   Skip ignored directory names at any depth below the scanned root — a directory above it must never hide the tree; follow no symlinks; an explicitly named file is scanned wherever it sits.
    """
    found: list[Path] = []
    for root in roots:
        root_path = Path(root)
        if root_path.is_file():
            found.append(root_path)
            continue
        for path in sorted(root_path.rglob("*")):
            if path.is_symlink() or not path.is_file():
                continue
            if path.suffix not in SOURCE_SUFFIXES:
                continue
            if ignored_dirs.intersection(path.relative_to(root_path).parts):
                continue
            found.append(path)
    return found


def main(argv=None) -> int:
    """Run the checker over the given paths.

    Rules:   Exit 1 when any finding exists, 0 when every header is clean, 2 when a scanned path does not exist — a typo must never read as a clean run.
    """
    parser = argparse.ArgumentParser(description="Report CodeDNA L1 header drift and out-of-contract comment content.")
    parser.add_argument("paths", nargs="*", help="files or directories to scan (default: .)")
    parser.add_argument("--root", default=".", help="root that used_by targets resolve against")
    parser.add_argument("--skip-content", action="store_true", help="check headers only")
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="NAME",
        help="extra directory name to skip at any depth (repeatable)",
    )
    args = parser.parse_args(argv)

    roots = [Path(item) for item in args.paths] or [Path(".")]
    missing = [item for item in roots if not item.exists()]
    if missing:
        for item in missing:
            print(f"codedna_check: path not found: {item}")
        return 2
    root = Path(args.root)
    files = collect_source_files(roots, DEFAULT_IGNORED_DIRS | frozenset(args.exclude))
    documents = [
        item / "AGENTS.md"
        for item in roots
        if (item / "AGENTS.md").is_file()
    ]
    total = 0
    for path in files:
        findings = check_file(path, root)
        if not args.skip_content:
            findings.extend(check_comment_content(path))
        for finding in findings:
            print(f"{path}: {finding}")
        total += len(findings)
    for document in documents:
        if document in files:
            continue
        if args.skip_content:
            continue
        doc_findings = check_examples(document.read_text(encoding="utf-8", errors="replace"), str(document))
        for finding in doc_findings:
            print(finding)
        total += len(doc_findings)
    print(f"codedna_check: {total} finding(s) in {len(files)} file(s) and {len(documents)} contract(s)")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
