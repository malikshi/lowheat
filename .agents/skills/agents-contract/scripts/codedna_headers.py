"""codedna_headers.py — Parse module headers and report L1 drift with line numbers.

exports: check_file | header_text | header_fields
used_by: .agents/skills/agents-contract/scripts/codedna_check.py → check_file [cascade]
used_by: .agents/skills/agents-contract/scripts/codedna_content.py → header line zones [cascade]
related: codedna_spec.py hosts the field tuples and regexes every check here reads.
rules:   Report-only — findings carry the line an agent edits; Python reads the module docstring, other languages the leading comment block; a missing L1 and a first line without the em dash stop the run instead of guessing below them; a leading `#!` is never the header title in any dialect; a css/html header keeps the line that carries its closing marker, so a field or agent entry written there stays in the header zone; an `exports:` entry and a `used_by:` consumer are cut at the arrow before a name or a path is read, so `sym(sig) → type` yields the symbol; the header may sit below a license banner or a required declaration, but only a line carrying the em dash moves the start.
agent:   grok-4.6 | xai | 2026-10-31 | unknown | header collection now reads the profile's block markers and prologue, so block-only dialects (OCaml, F#, Lua) and `<?php` files parse; suffix checks are case-insensitive
agent:   grok-4.6 | xai | 2026-11-01 | unknown | review fixes: directive banners below the title are skipped, doc-marker headers keep their fields, directive-only leading blocks no longer end the search
agent:   fx | unknown | 2026-11-05 | unknown | split header start and collection helpers out of _header_entries
agent:   fx | unknown | 2026-11-06 | unknown | exports and used_by now cut the arrow themselves, so an upstream `sym(sig) → type` export names the symbol and a `|`-joined used_by line loses no consumer
agent:   fx | unknown | 2026-11-06 | unknown | skipped license banners and package/namespace prologues, and judged Python exports against the AST symbol set; added header_fields for the import proof
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

from codedna_python import module_symbols
from codedna_spec import (
    AGENT_HISTORY_LIMIT,
    EM_DASH,
    L1_FIELDS,
    REQUIRED_L1,
    BlockMarker,
    LanguageProfile,
    profile_for,
    _AGENT_SHAPE,
    _ARG_LIST,
    _ARROW_SPLIT,
    _DECLARATION_LINE,
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
    return _header_findings(view, root, path)


def _header_view(path: Path, text: str) -> _HeaderView | None:
    """Collect the first line, fields, labels, and code body of one header.

    Rules:   Python reads its module docstring; other languages read the leading comment block; None means the file carries no L1.
    """
    profile = profile_for(path)
    lines = text.splitlines()
    entries = _header_entries(profile, lines)
    if path.suffix.lower() == ".py":
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
    fields, labels = _read_header_fields(profile, entries)
    header_last = entries[-1][0]
    return _HeaderView(first_no, first_text, fields, labels, "\n".join(lines[header_last:]))


def _header_findings(view: _HeaderView, root: Path, path: Path | None = None) -> list[str]:
    """Check one collected header against the L1 contract.

    Rules:   A first line without the em dash stops the run — field drift below it cannot be trusted. The path lets a Python file judge exports against its real symbols instead of the body text.
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
        for finding in _exports_findings(view.fields.get("exports", []), view.exports_body, path)
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


def header_fields(path: Path) -> dict[str, list[str]]:
    """Return the L1 field values of one file, empty when it carries no header.

    Rules:   Empty also covers an unreadable file — the header check already reports that, and this reader adds evidence, never a second finding.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    view = _header_view(path, text)
    return view.fields if view is not None else {}


def header_text(path: Path, text: str) -> str:
    """Return the module header text of one source file.

    Rules:   Python reads the module docstring; other languages read the leading comment block after an optional shebang; empty means no L1.
    """
    if path.suffix.lower() == ".py":
        match = _PY_DOCSTRING.match(text)
        return match.group(2) if match else ""
    profile = profile_for(path)
    entries = _header_entries(profile, text.splitlines())
    return "\n".join(entry[1] for entry in entries if entry[1])


def _header_start(profile: LanguageProfile, lines: list[str]) -> int:
    """Return the index where a leading header may begin.

    Rules:   Skip a leading `#!`, the profile's prologue (`<?php`), blank lines, a required declaration (`package`, `namespace`, `using`), and a license banner that carries no em dash. A banner is skipped only when a real header follows it; otherwise the first comment stays the start so the finding points at it.
    """
    total = len(lines)
    index = 0
    while index < total:
        stripped = lines[index].strip()
        if not stripped or stripped.startswith("#!") or any(
            stripped.startswith(item) for item in profile.prologue
        ):
            index += 1
            continue
        if _DECLARATION_LINE.match(stripped) and not profile.is_comment(stripped):
            index += 1
            continue
        break
    if index >= total:
        return total
    if profile.is_comment(lines[index].strip()):
        banner_end = _banner_skip(profile, lines, index)
        if banner_end is not None:
            return banner_end
    return index


def _banner_skip(profile: LanguageProfile, lines: list[str], start: int) -> int | None:
    """Return the first header line after a license banner, or None when there is none.

    Rules:   Blank lines and declarations do not end a banner; a line carrying an em dash is the header; the first real code line ends the search with no candidate, and the scan stops after 40 lines. Only the title moves the start, so a header missing its em dash still reports at its own first line.
    """
    in_block = False
    block_start = start
    for index in range(start, min(len(lines), start + 40)):
        stripped = lines[index].strip()
        if not stripped:
            continue
        opened = _line_block_open(profile, lines[index], stripped)
        line_in_block = in_block or opened is not None
        is_comment = line_in_block or profile.is_comment(stripped)
        closes = any(stripped.endswith(marker.close) for marker in profile.block_markers)
        if opened is not None:
            block_start = index
            in_block = not opened[2]
        elif in_block and closes:
            in_block = False
        if not is_comment:
            if _DECLARATION_LINE.match(stripped):
                continue
            return None
        if EM_DASH in stripped:
            if index == start:
                return None
            return block_start if line_in_block else index
    return None


def _collect_header(
    profile: LanguageProfile, lines: list[str], start: int
) -> list[tuple[int, str]]:
    """Collect `(line_number, stripped-comment-text)` from the header block.

    Rules:   Bare directives and directive-only blocks before the title are skipped without ending the search; block-comment headers run to their close marker; blank comment separators join the block; a block body line loses one leading `*` decoration.
    """
    collected: list[tuple[int, str]] = []
    close_marker = ""
    for index in range(start, len(lines)):
        raw = lines[index]
        stripped = raw.strip()
        if not stripped:
            continue
        if close_marker:
            if stripped.startswith(close_marker):
                body = stripped[len(close_marker):].strip()
                if body and not _header_directive(profile, body, not collected):
                    collected.append((index + 1, body))
                close_marker = ""
                if collected:
                    break
                continue
            body = _block_body(stripped)
            if body and not _header_directive(profile, body, not collected):
                collected.append((index + 1, body))
            continue
        if _header_directive(profile, stripped, not collected):
            opened = _line_block_open(profile, raw, stripped)
            if opened is not None and not opened[2]:
                close_marker = opened[0].close
            continue
        opened = _line_block_open(profile, raw, stripped)
        if opened is not None:
            marker, body, closed = opened
            if body and not _header_directive(profile, body, not collected):
                collected.append((index + 1, body))
            if closed:
                if collected:
                    break
                continue
            close_marker = marker.close
            continue
        if profile.is_comment(stripped):
            collected.append((index + 1, stripped))
            continue
        break
    return collected


def _header_entries(profile: LanguageProfile, lines: list[str]) -> list[tuple[int, str]]:
    """Return (line_number, stripped-comment-text) for the leading header.

    Rules:   A leading `#!` and a profile prologue (`<?php`) are skipped; bare directives and directive-only blocks before the header are skipped without ending the search; block-comment headers run to their close marker; blank comment separators join the block; a block body line loses one leading `*` decoration.
    """
    return _collect_header(profile, lines, _header_start(profile, lines))


def _header_directive(
    profile: LanguageProfile, stripped: str, at_title: bool
) -> bool:
    """Judge one line a directive that cannot be header content.

    Rules:   An L1 field line is always content; only the first line may be a directive title (`// Code generated — ...`); below the title every directive is skipped so an em-dash banner never folds into the field above it.
    """
    if not profile.is_directive(stripped):
        return False
    if _FIELD_LINE.match(stripped) is not None:
        return False
    return not (at_title and EM_DASH in stripped)


def _line_block_open(
    profile: LanguageProfile, raw: str, stripped: str
) -> tuple[BlockMarker, str, bool] | None:
    """Match one block-comment opener on a header line.

    Rules:   An `at_line_start` opener must sit at column 0 of the raw line; a line that also carries the closer is a single-line header.
    """
    long_marker = _long_header_marker(profile, stripped)
    if long_marker is not None:
        marker, inner = long_marker
        if inner.rstrip().endswith(marker.close):
            return marker, inner.rstrip()[: -len(marker.close)].strip(), True
        return marker, inner.strip(), False
    for marker in profile.block_markers:
        if not stripped.startswith(marker.open):
            continue
        if marker.at_line_start and not raw.startswith(marker.open):
            continue
        inner = stripped[len(marker.open):]
        if inner.startswith("*"):
            inner = inner[1:]
        trimmed = inner.rstrip()
        if trimmed.endswith(marker.close):
            return marker, trimmed[: -len(marker.close)].strip(), True
        return marker, inner.strip(), False
    return None


def _long_header_marker(
    profile: LanguageProfile, stripped: str
) -> tuple[BlockMarker, str] | None:
    """Match one Lua long-comment header opener and return its marker and remainder.

    Rules:   The closer mirrors the `=` count between the brackets; a lone `[[` string is not a comment and never opens a header.
    """
    prefix = profile.long_bracket
    if not prefix or not stripped.startswith(prefix + "["):
        return None
    cursor = len(prefix) + 1
    equals = 0
    while stripped[cursor:cursor + 1] == "=":
        equals += 1
        cursor += 1
    if stripped[cursor:cursor + 1] != "[":
        return None
    opener = stripped[: cursor + 1]
    closer = "]" + "=" * equals + "]"
    return BlockMarker(opener, closer), stripped[cursor + 1:]


def _block_body(stripped: str) -> str:
    """Strip one leading block-decoration star from a header body line.

    Rules:   Only a `*` that decorates the line is removed; a lone `*/` never reaches here because the close branch handles it first.
    """
    if stripped.startswith("* ") or stripped == "*":
        return stripped[1:].strip()
    return stripped


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


def _exports_findings(values: list[str], body: str, path: Path | None = None) -> list[str]:
    """Check every named export appears in the file body.

    Rules:   The body excludes the header/docstring itself — a symbol that only exists in exports: is absent. Drop the argument list and the return type after `->`/`→` per entry, so upstream's `sym(a, b) → type` form names the symbol instead of its type or its second argument. A parseable Python body is judged against its real public symbols, so a name that only appears in a string never satisfies exports:; an unparseable body falls back to the text probe.
    """
    findings: list[str] = []
    names: list[str] = []
    for value in values:
        for chunk in _EXPORT_SPLIT.split(_ARG_LIST.sub(" ", value)):
            chunk = _ARROW_SPLIT.split(chunk, maxsplit=1)[0].strip().strip("`")
            if not chunk or chunk.lower() == "none":
                continue
            token = chunk.split()[-1].strip("(){}[];:,")
            if token and token not in _TYPE_WORDS:
                names.append(token)
    if path is not None and path.suffix.lower() == ".py":
        symbols = module_symbols(body)
        if symbols is not None:
            return [
                f"exports symbol absent from the file: {name}"
                for name in names
                if name not in symbols
            ]
    for name in names:
        if not re.search(rf"\b{re.escape(name)}\b", body):
            findings.append(f"exports symbol absent from the file: {name}")
    return findings


def _used_by_findings(values: list[str], root: Path) -> list[str]:
    """Check each used_by consumer path exists under root.

    Rules:   Glob and template entries are out of scope; entry format is consumer_file → symbol(s); `|` or `,` separates several consumers on one line, and every one of them is checked; an ASCII `->` marks the symbol boundary too.
    """
    findings: list[str] = []
    for entry in [part for value in values for part in _EXPORT_SPLIT.split(value)]:
        target = _ARROW_SPLIT.split(entry, maxsplit=1)[0].replace("[cascade]", "").strip()
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
