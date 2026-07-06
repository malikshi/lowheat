#!/usr/bin/env python3
"""tools/codedna_staged_check.py — Fast staged-file CodeDNA validator for git hooks.

exports: SOURCE_EXTENSIONS | staged_source_files(repo_root) | main()
used_by: .git/hooks/pre-commit → main
rules:   Keep staged-file selection aligned with .codedna excludes and validate_manifests.py; do not require the external codedna CLI.
agent:   gpt-5.5 | openai | 2026-05-28 | s_20260528_codedna_consistency | added local staged-blob validator for pre-commit.
message:
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_FOR_IMPORT))

from tools import validate_manifests

SOURCE_EXTENSIONS = ({".py"} | set(validate_manifests.COMMENT_PREFIX)) - {".sh"}


def _get_ext(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".blade.php"):
        return ".blade.php"
    return path.suffix.lower()


def _repo_root() -> Path:
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return Path.cwd()
    return Path(output.strip())


def _is_skipped(path: Path) -> bool:
    return any(part in validate_manifests.SKIP_DIRS for part in path.parts)


def staged_source_files(repo_root: Path) -> list[Path]:
    """Return staged source files that should pass CodeDNA validation.

    Rules:   Match the git hook diff filter ACM and skip generated, agent, vendored, and environment paths.
    """
    try:
        output = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            cwd=repo_root,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []

    files: list[Path] = []
    for line in output.splitlines():
        rel_path = Path(line)
        if _is_skipped(rel_path):
            continue
        if _get_ext(rel_path) not in SOURCE_EXTENSIONS:
            continue
        full_path = repo_root / rel_path
        if full_path.is_file():
            files.append(rel_path)
    return files


def main() -> int:
    """Run CodeDNA validation for staged source files.

    Rules:   Return zero when no relevant staged files exist; otherwise mirror validate_manifests.py exit semantics.
    """
    repo_root = _repo_root()
    files = staged_source_files(repo_root)
    if not files:
        return 0

    print("CodeDNA v0.9 — validating staged files...")
    results = []
    with tempfile.TemporaryDirectory(prefix="codedna-staged-") as temp_dir:
        temp_root = Path(temp_dir)
        for rel_path in files:
            staged_path = temp_root / rel_path.name
            try:
                staged_bytes = subprocess.check_output(
                    ["git", "show", f":{rel_path.as_posix()}"],
                    cwd=repo_root,
                    stderr=subprocess.DEVNULL,
                )
            except (OSError, subprocess.CalledProcessError):
                print(f"Commit blocked: cannot read staged content for {rel_path}")
                return 1
            staged_path.write_bytes(staged_bytes)
            result = validate_manifests.validate_file(staged_path)
            result.path = str(rel_path)
            results.append(result)

    return validate_manifests.print_results(results, verbose=False)


if __name__ == "__main__":
    sys.exit(main())
