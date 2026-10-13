"""codedna_headers.py — Parse module headers and report L1 drift with line numbers.

exports: check_file
used_by: .agents/skills/agents-contract/scripts/codedna_check.py → check_file [cascade]
used_by: .agents/skills/agents-contract/scripts/codedna_content.py → header line zones and css/html block grammar [cascade]
related: codedna_spec.py hosts the field tuples and regexes every check here reads.
rules:   Report-only — findings carry the line an agent edits; Python reads the module docstring, other languages the leading comment block; a missing L1 and a first line without the em dash stop the run instead of guessing below them.
agent:   unknown | xai | 2026-10-14 | 01a1373b-7fa0-7851-ae9d-4cd27c951a27 | split out of codedna_check.py; check_file became view collection plus finding assembly, both under the 50-line rule.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

from codedna_spec import (
    AGENT_HISTORY_LIMIT,
    ARROW,
    EM_DASH,
    L1_FIELDS,
    REQUIRED_L1,
    LanguageProfile,
    profile_for,
    _AGENT_SHAPE,
    _EXPORT_SPLIT,
    _FIELD_LINE,
    _LOOSE_DATE,
    _PATH_LOOKING,
    _PY_DOCSTRING,
    _TYPE_WORDS,
)


class _HeaderView(NamedTuple):
    first_no: int
    first_text: str
    fields: dict[str, list[str]]
    labels: dict[str, int]
    exports_body: str


def check_file(path: Path, root: Path) -> list[str]:
    """Return the L1 header findings for one source file.

    Rules:   Report only; empty means clean; findings carry the offending field's line number where known.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        return [f"unreadable: {error}"]
    view = _header_view(path, text)
    if view is None:
        return ["missing L1 header"]
    return _header_findings(view, root)


def _header_view(path: Path, text: str) -> _HeaderView | None:
    """Collect the first line, fields, labels, and code body of one header.

    Rules:   Python reads its module docstring; other languages read the leading comment block; None means the file carries no L1.
    """
    profile = profile_for(path)
    lines = text.splitlines()
    entries = _header_entries(profile, lines)
    if path.suffix == ".py":
        doc_match = _PY_DOCSTRING.match(text)
        if doc_match is None:
            return None
        doc = doc_match.group(2).splitlines()
        first_no = text[: doc_match.start(2)].count("\n") + 1
        first_text = next((row.strip() for row in doc if row.strip()), "")
        fields, labels = _docstring_fields(doc_match.group(2), first_no)
        return _HeaderView(first_no, first_text, fields, labels, text[doc_match.end():])
    if not entries:
        return None
    first_no, raw_first = entries[0]
    first_text = profile.strip(raw_first.strip()) or raw_first.strip()
    if profile.name in ("css", "html"):
        inner = raw_first.strip()
        for opener in ("/*", "<!--"):
            if inner.startswith(opener):
                first_text = inner[len(opener):].strip()
                break
    fields, labels = _read_header_fields(profile, entries)
    header_last = entries[-1][0]
    return _HeaderView(first_no, first_text, fields, labels, "\n".join(lines[header_last:]))


def _header_findings(view: _HeaderView, root: Path) -> list[str]:
    """Check one collected header against the L1 contract.

    Rules:   A first line without the em dash stops the run — field drift below it cannot be trusted.
    """
    if EM_DASH not in view.first_text:
        return [
            f"{view.first_no}: first header line lacks the filename {EM_DASH} description form: {view.first_text[:60]}"
        ]
    labels = view.labels
    findings: list[str] = []
    order = [name for name in labels if name in L1_FIELDS]
    canonical_index = {name: index for index, name in enumerate(L1_FIELDS)}
    observed = [canonical_index[name] for name in order]
    if observed != sorted(observed):
        findings.append(
            f"{next(iter(labels.values()), view.first_no)}: L1 field order drifts from exports/used_by/related/rules/agent/message: {', '.join(order)}"
        )
    for label in REQUIRED_L1:
        if label not in labels:
            findings.append(f"{view.first_no}: missing L1 field: {label}")
    findings.extend(
        f"{labels.get('exports', view.first_no)}: {finding}"
        for finding in _exports_findings(view.fields.get("exports", []), view.exports_body)
    )
    findings.extend(
        f"{labels.get('used_by', view.first_no)}: {finding}"
        for finding in _used_by_findings(view.fields.get("used_by", []), root)
    )
    findings.extend(
        f"{labels.get('agent', view.first_no)}: {finding}"
        for finding in _agent_findings(view.fields.get("agent", []))
    )
    return findings


def header_text(path: Path, text: str) -> str:
    """Return the module header text of one source file.

    Rules:   Python reads the module docstring; other languages read the leading comment block after an optional shebang; empty means no L1.
    """
    if path.suffix == ".py":
        match = _PY_DOCSTRING.match(text)
        return match.group(2) if match else ""
    profile = profile_for(path)
    entries = _header_entries(profile, text.splitlines())
    return "\n".join(entry[1] for entry in entries if entry[1])


def _header_entries(profile: LanguageProfile, lines: list[str]) -> list[tuple[int, str]]:
    """Return (line_number, stripped-comment-text) for the leading header.

    Rules:   Shell skips the shebang; css/html blocks span to their close; blank comment separators join the block.
    """
    start = 0
    if profile.shebang:
        for index, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#!"):
                start = index + 1
            break
    collected: list[tuple[int, str]] = []
    inside_open = False
    block_style = ""
    for index in range(start, len(lines)):
        stripped = lines[index].strip()
        if not stripped:
            continue
        if profile.name == "html":
            body = _strip_html_ctrl(stripped)
            if not body.strip():
                continue
            stripped = body
        if inside_open:
            if profile.name == "html" and not _strip_html_ctrl(stripped).strip():
                inside_open = False
                break
            if stripped.endswith(_block_close(block_style)):
                inside_open = False
                break
            body = _strip_html_ctrl(stripped) if profile.name == "html" else stripped
            collected.append((index + 1, body))
            continue
        if profile.is_directive(stripped):
            continue
        if profile.is_comment(stripped):
            if profile.shebang and stripped.startswith("#!"):
                break
            collected.append((index + 1, stripped))
            if profile.name in ("css", "html") and _single_line_block(stripped):
                break
            if profile.name in ("css", "html") and _block_open(stripped):
                inside_open = True
                block_style = _block_style(stripped) or ""
            continue
        break
    return collected


def _block_open(stripped: str) -> bool:
    """Judge one stripped CSS/HTML line a comment opener.

    Rules:   Bare terminators (`*/`, `-->`) are closers, not openers.
    """
    return stripped.startswith("/*") or stripped.startswith("<!--")


def _block_style(stripped: str) -> str | None:
    """Return the block-comment style a stripped line opened, if any.

    Rules:   The returned style string feeds _block_close only.
    """
    if stripped.startswith("/*"):
        return "/*"
    if stripped.startswith("<!--"):
        return "<!--"
    return None


def _block_close(style: str) -> str:
    """Return the terminator of one block style.

    Rules:   css uses `*/`; html uses `-->`.
    """
    return "*/" if style == "/*" else "-->"


def _single_line_block(stripped: str) -> bool:
    """Judge one stripped css/html line an open-and-close comment.

    Rules:   The line must carry both markers to break the header.
    """
    return (
        (stripped.startswith("/*") and stripped.endswith("*/") and len(stripped) > 4)
        or (stripped.startswith("<!--") and stripped.endswith("-->") and len(stripped) > 7)
    )


def _strip_html_ctrl(stripped: str) -> str:
    """Reduce an HTML line to the comment grammar it carries.

    Rules:   Markup without comment grammar must not read as header continuation.
    """
    if stripped.startswith("<!--") or stripped == "-->":
        return stripped
    return re.sub(r"</?script[^>]*>|</?style[^>]*>|<!DOCTYPE[^>]*>", "", stripped, flags=re.IGNORECASE)


def _read_header_fields(
    profile: LanguageProfile, entries: list[tuple[int, str]]
) -> tuple[dict[str, list[str]], dict[str, int]]:
    """Map L1 field labels to values and label line numbers.

    Rules:   A line that opens no field continues the field above it; the label line is where the agent fixes a finding.
    """
    fields: dict[str, list[str]] = {}
    labels: dict[str, int] = {}
    current: str | None = None
    for line_no, raw in entries:
        stripped = raw.strip()
        match = _FIELD_LINE.match(stripped)
        if match:
            current = match.group(1)
            fields.setdefault(current, [])
            labels.setdefault(current, line_no)
            value = match.group(2).strip()
            if value:
                fields[current].append(value)
            continue
        if current is None:
            continue
        text = profile.strip(stripped)
        if text is None:
            text = stripped
        if text.strip():
            fields[current].append(text.strip())
    return fields, labels


def _docstring_fields(doc: str, base: int):
    """Map L1 labels to values and absolute label line numbers inside a Python docstring.

    Rules:   The docstring's first line is file line `base`, so every finding points at the line the agent edits.
    """
    fields: dict[str, list[str]] = {}
    labels: dict[str, int] = {}
    current: str | None = None
    for offset, raw in enumerate(doc.splitlines(), start=1):
        stripped = raw.strip()
        match = _FIELD_LINE.match(stripped)
        if match:
            current = match.group(1)
            fields.setdefault(current, [])
            labels.setdefault(current, base + offset - 1)
            value = match.group(2).strip()
            if value:
                fields[current].append(value)
            continue
        if current is None or not stripped:
            continue
        fields[current].append(stripped)
    return fields, labels


def _exports_findings(values: list[str], body: str) -> list[str]:
    """Check every named export appears in the file body.

    Rules:   The body excludes the header/docstring itself — a symbol that only exists in exports: is absent.
    """
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


def _used_by_findings(values: list[str], root: Path) -> list[str]:
    """Check each used_by consumer path exists under root.

    Rules:   Glob and template entries are out of scope; entry format is consumer_file → symbol(s).
    """
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


def _agent_findings(entries: list[str]) -> list[str]:
    """Check the agent history's entry shape and age cap.

    Rules:   A line without a date is a continuation and never malformed; a genuine entry carries a pipe before the date — a loose date mid-note neither counts as history nor passes unnoticed; every mimicking line reports, and a field with no shaped entry at all is the drift.
    """
    findings: list[str] = []
    history = [entry for entry in entries if _AGENT_SHAPE.search(entry)]
    malformed = [
        entry
        for entry in entries
        if not _AGENT_SHAPE.search(entry) and _LOOSE_DATE.search(entry)
    ]
    for entry in malformed:
        findings.append(
            f"malformed agent history entry (model | provider | date | session | note): {entry.strip()[:60]}"
        )
    if entries and not history and not malformed:
        findings.append(
            f"malformed agent history entry (model | provider | date | session | note): {entries[0][:60]}"
        )
    if len(history) > AGENT_HISTORY_LIMIT:
        findings.append(
            f"agent history holds {len(history)} entries; keep the last {AGENT_HISTORY_LIMIT}"
        )
    return findings
