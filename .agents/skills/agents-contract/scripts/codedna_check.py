"""codedna_check.py — Report CodeDNA L1 header drift in annotated source files.

exports: main | check_file | collect_source_files | DEFAULT_IGNORED_DIRS
used_by: tests/test_codedna_check.py → main, check_file, collect_source_files, DEFAULT_IGNORED_DIRS [cascade]
         AGENTS.md → CodeDNA editing protocol
related: .agents/skills/agents-contract/SKILL.md (CodeDNA section)
rules:   Read-only — report findings and exit non-zero; never rewrite a file.
         Findings name the file and the field; the exit code carries the verdict.
agent:   grok-build-plan | 9router | 2026-10-08 | 01a11c14-e6f9-7581-9248-a9b2f058a3e8 | added checker and tests
message: The model slot carries the harness agent profile — this harness exposes no raw model id.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SOURCE_SUFFIXES = (
    ".py",
    ".go",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".rs",
    ".sh",
    ".bash",
    ".zsh",
)
HEADER_LINE_LIMIT = 40
REQUIRED_FIELDS = ("exports", "used_by", "rules", "agent")
AGENT_HISTORY_LIMIT = 5
ARROW = "→"
DEFAULT_IGNORED_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "node_modules",
        "dist",
        "build",
        "vendor",
        "target",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
    }
)

_PY_DOCSTRING = re.compile(r'^\s*(?:#[^\n]*\n)*\s*("""|\'\'\')(.*?)\1', re.DOTALL)
_COMMENT_PREFIX = re.compile(r"^\s*(?://+|#+|\*+|!)\s*")
_FIELD_LABEL = re.compile(
    r"^\s*(?://+|#+|\*+|!)?\s*(exports|used_by|related|rules|agent|message):\s*(.*)$"
)
_EXPORT_SPLIT = re.compile(r"[|,]")
_AGENT_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_TYPE_WORDS = frozenset(
    {
        "class",
        "def",
        "func",
        "function",
        "type",
        "interface",
        "struct",
        "enum",
        "const",
        "let",
        "var",
        "trait",
        "impl",
        "namespace",
        "module",
    }
)
_PATH_LOOKING = re.compile(r"[/\\]|\.[A-Za-z0-9]{1,5}$")


def header_text(path: Path, text: str) -> str:
    """Return the module header text of one source file.

    Rules:   Python reads the module docstring; other languages read the leading comment block.
             An empty return means the file carries no L1 header.
    """
    if path.suffix == ".py":
        match = _PY_DOCSTRING.match(text)
        return match.group(2) if match else ""
    collected: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            if collected:
                collected.append("")
            continue
        if _COMMENT_PREFIX.match(line):
            collected.append(line)
            continue
        break
    return "\n".join(collected).strip("\n")


def split_header_fields(header: str) -> dict[str, list[str]]:
    """Map each L1 field name to its value lines.

    Rules:   A line that opens no field continues the field above it; blank lines are dropped.
    """
    fields: dict[str, list[str]] = {}
    current: str | None = None
    for line in header.splitlines()[:HEADER_LINE_LIMIT]:
        match = _FIELD_LABEL.match(line)
        if match:
            current = match.group(1)
            fields.setdefault(current, [])
            value = match.group(2).strip()
            if value:
                fields[current].append(value)
            continue
        if current is None:
            continue
        value = _COMMENT_PREFIX.sub("", line).strip()
        if value:
            fields[current].append(value)
    return fields


# Rules: a `used_by` entry is `consumer_file → symbol(s)`; entries without a path stay out of scope.
def _used_by_findings(values: list[str], root: Path) -> list[str]:
    findings: list[str] = []
    for entry in [part for value in values for part in value.split(",")]:
        target = entry.split(ARROW)[0].replace("[cascade]", "").strip()
        if not target or target.lower() == "none":
            continue
        if "*" in target or "<" in target:
            continue
        if not _PATH_LOOKING.search(target):
            continue
        if not (root / target).exists():
            findings.append(f"used_by target not found: {target}")
    return findings


# Rules: a symbol named in `exports:` must appear in the file body, per the exports contract.
def _exports_findings(values: list[str], body: str) -> list[str]:
    findings: list[str] = []
    names: list[str] = []
    for value in values:
        for chunk in _EXPORT_SPLIT.split(value.split("->")[0]):
            chunk = chunk.strip().strip("`")
            if not chunk or chunk.lower() == "none":
                continue
            token = chunk.split()[-1].strip("(){}[];:,")
            if token and token not in _TYPE_WORDS:
                names.append(token)
    for name in names:
        if not re.search(rf"\b{re.escape(name)}\b", body):
            findings.append(f"exports symbol absent from the file: {name}")
    return findings


def collect_source_files(roots, ignored_dirs=DEFAULT_IGNORED_DIRS) -> list[Path]:
    """Return the candidate source files under each root.

    Rules:   Skip ignored directory names at any depth; follow no symlinks.
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
            if ignored_dirs.intersection(path.parts):
                continue
            found.append(path)
    return found


def check_file(path: Path, root: Path) -> list[str]:
    """Return the L1 header findings for one source file.

    Rules:   Report only; the caller holds the exit code. An empty list means a clean header.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        return [f"unreadable: {error}"]

    header = header_text(path, text)
    if not header.strip():
        return ["missing L1 header"]
    fields = split_header_fields(header)
    findings: list[str] = []

    first_line = next((line for line in header.splitlines() if line.strip()), "")
    if "—" not in first_line:
        findings.append("first header line lacks the filename — description form")

    for field in REQUIRED_FIELDS:
        if not fields.get(field):
            findings.append(f"missing L1 field: {field}")

    body = text.replace(header, "", 1)
    findings.extend(_exports_findings(fields.get("exports", []), body))
    findings.extend(_used_by_findings(fields.get("used_by", []), root))
    history = len(_AGENT_DATE.findall(" ".join(fields.get("agent", []))))
    if history > AGENT_HISTORY_LIMIT:
        findings.append(f"agent history holds {history} entries; keep the last {AGENT_HISTORY_LIMIT}")
    return findings


def main(argv=None) -> int:
    """Run the checker over the given paths.

    Rules:   Exit 1 when any finding exists, 0 when every header is clean.
    """
    parser = argparse.ArgumentParser(description="Report CodeDNA L1 header drift in source files.")
    parser.add_argument("paths", nargs="*", help="files or directories to scan (default: .)")
    parser.add_argument("--root", default=".", help="root that used_by targets resolve against")
    args = parser.parse_args(argv)

    roots = [Path(item) for item in args.paths] or [Path(".")]
    root = Path(args.root)
    files = collect_source_files(roots)
    total = 0
    for path in files:
        findings = check_file(path, root)
        for finding in findings:
            print(f"{path}: {finding}")
        total += len(findings)
    print(f"codedna_check: {total} finding(s) in {len(files)} file(s)")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
