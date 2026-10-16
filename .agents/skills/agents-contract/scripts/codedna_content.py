"""codedna_content.py — Report comment lines outside the permitted CodeDNA content set.

exports: check_comment_content | check_examples
used_by: .agents/skills/agents-contract/scripts/codedna_check.py → check_comment_content and check_examples [cascade]
rules:   Permitted content is fixed: a declaration summary, L1 field lines, Rules:/message: lines and their continuations; the scan is line-based and errs toward reporting — a false positive means the comment belongs under Rules:/message:. Data lines (heredoc bodies) are never comments.
agent:   unknown | xai | 2026-10-14 | 01a1373b-7fa0-7851-ae9d-4cd27c951a27 | split out of codedna_check.py; the 138-line content scan is now one loop plus state and classification helpers.
agent:   unknown | unknown | 2026-10-16 | s_gapfix | killed the Python header-zone exemption: docstring-adjacent `#` prose and TODO markers report now; probes confirmed non-Python string masking already correct.
message: The scan is line-based: a permitted summary line needs a declaration below it, and when unsure it reports. Known gaps: a multi-line string in a non-Python dialect (Go raw string, JS template) can read as comments; an unterminated shell heredoc body reports as prose, because a missing terminator must never silence the rest of the file. In contract examples, repeat a field label on every docstring line after the summary.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import NamedTuple

from codedna_headers import (
    _block_close,
    _block_open,
    _block_style,
    _header_entries,
    _strip_html_ctrl,
)
from codedna_masking import _python_scan_inputs, _shell_heredoc_lines, mask_code
from codedna_spec import (
    L1_FIELDS,
    L2_FIELDS,
    SUMMARY_WORD_LIMIT,
    LanguageProfile,
    profile_for,
    _CODEISH_LINE,
    _COMMENT_LABEL,
    _DOC_LABEL,
    _FIELD_LINE,
    _GROUP_DECL,
    _L2_LABEL_LINE,
    _PY_DOCSTRING,
    _PY_FENCE,
    _TODO_MARKER,
    _TYPE_DECL,
)


class _ScanContext(NamedTuple):
    profile: LanguageProfile
    masked: list[str]
    originals: list[str]
    skip_lines: frozenset[int]
    comment_lines: frozenset[int] | None
    header_zone: int


class _ScanState(NamedTuple):
    depth: int
    type_body_depth: int
    paren_group_depth: int
    paren_depth: int
    prev_label: str | None
    in_block: bool
    block_style: str


_START_STATE = _ScanState(0, 0, 0, 0, None, False, "")


def _word_count(line: str) -> int:
    """Count tokens carrying an alphanumeric character.

    Rules:   Punctuation-only tokens such as an em dash are not words.
    """
    return sum(1 for token in line.split() if any(ch.isalnum() for ch in token))


def _docstring_findings(docstring: str, allowed_fields, where: str) -> list[str]:
    """Lint one Python docstring against the permitted content set.

    Rules:   The first line may be a summary; every later line repeats a label; wrapped continuations report on purpose.
    """
    findings: list[str] = []
    lines = [line for line in docstring.splitlines() if line.strip()]
    if not lines:
        return findings
    summary = lines[0].strip()
    summary_words = _word_count(summary)
    if summary_words > SUMMARY_WORD_LIMIT:
        findings.append(
            f"{where}: summary line holds {summary_words} words; cap is {SUMMARY_WORD_LIMIT}: {summary[:60]}"
        )
    for line in lines[1:]:
        match = _DOC_LABEL.match(line)
        if match:
            if match.group(1).lower() in allowed_fields:
                continue
            findings.append(f"{where}: field `{match.group(1)}:` is not permitted here")
            continue
        findings.append(f"{where}: line is outside the permitted content: {line.strip()[:60]}")
    return findings


def _parse_python(text: str) -> ast.Module | None:
    """Return the parsed module, or None when the source does not parse.

    Rules:   ValueError covers the null-byte refusal ast.parse raises on binary content — that must not abort the run.
    """
    try:
        return ast.parse(text)
    except (SyntaxError, ValueError):
        return None


def check_comment_content(path: Path) -> list[str]:
    """Return findings for comment lines outside the permitted CodeDNA content.

    Rules:   Permitted: declaration summaries, L1 field lines, Rules:/message: lines and continuations; exemptions: tool directives, the shell shebang, rust doc, SPDX license lines, and shell heredoc bodies; line numbers address the comment's own line; a Python file that does not parse still gets its `#` comments scanned, and a Python file that does not tokenize gets its docstrings checked only.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        return [f"unreadable: {error}"]
    profile = profile_for(path)
    findings: list[str] = []
    if path.suffix == ".py":
        module_doc = _PY_DOCSTRING.match(text)
        if module_doc:
            findings.extend(_docstring_findings(module_doc.group(2), L1_FIELDS, f"{path.name} module"))
        tree = _parse_python(text)
        if tree is not None:
            for node in ast.walk(tree):
                if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                docstring = ast.get_docstring(node, clean=False)
                if docstring is None:
                    continue
                findings.extend(
                    _docstring_findings(docstring, L2_FIELDS, f"{path.name} [{getattr(node, 'name', '')}]")
                )
        scan_inputs = _python_scan_inputs(text)
        if scan_inputs is None:
            return findings
        masked_text, comment_lines = scan_inputs
        findings.extend(
            _scan_content(
                profile, masked_text.split("\n"), text.split("\n"), comment_lines=comment_lines
            )
        )
        return findings
    masked = mask_code(profile, text, path.suffix)
    skip_lines = _shell_heredoc_lines(text) if profile.name == "shell" else frozenset()
    findings.extend(_scan_content(profile, masked.splitlines(), text.splitlines(), skip_lines))
    return findings


def _scan_content(
    profile: LanguageProfile,
    masked: list[str],
    originals: list[str],
    skip_lines: frozenset[int] = frozenset(),
    comment_lines: frozenset[int] | None = None,
) -> list[str]:
    """Report comment lines outside the permitted CodeDNA content set.

    Rules:   Permitted: L1 field lines with continuations, one summary line per declaration (top-level, grouped, or struct member), Rules:/message: lines with continuations, tool directives, rust doc, the shell shebang. Context comes from masked code: brace depth for type bodies, paren depth for groups, declarations for summaries. `skip_lines` holds data lines (shell heredoc bodies) that are never comments; `comment_lines` replaces the prefix test with exact positions when the caller knows them (Python).
    """
    context = _ScanContext(
        profile, masked, originals, skip_lines, comment_lines, _header_line_count(profile, originals)
    )
    state = _START_STATE
    findings: list[str] = []
    for index, raw in enumerate(originals):
        line_findings, state = _scan_line(context, state, index, raw)
        findings.extend(line_findings)
    return findings


def _scan_line(
    context: _ScanContext, state: _ScanState, index: int, raw: str
) -> tuple[list[str], _ScanState]:
    """Route one line: data, code context, or comment inspection.

    Rules:   Order matters — skip lines, blanks, block bodies, and directives settle before comment classification; only a code line advances the depth counters.
    """
    line_no = index + 1
    stripped = raw.strip()
    if line_no in context.skip_lines or not stripped:
        return [], state._replace(prev_label=None)
    if state.in_block:
        return [], _block_continuation(state, stripped, context.profile)
    if context.profile.is_directive(stripped) or stripped.startswith("#!"):
        return [], state._replace(prev_label=None)
    if context.profile.name == "rust" and (stripped.startswith("///") or stripped.startswith("//!")):
        return [], state
    if context.profile.name == "html" and "<!--" in stripped:
        probe = _html_inline_probe(stripped, line_no)
        if probe is not None:
            return probe, state
    if not _is_comment_line(context, stripped, line_no):
        return [], _advance_code_state(context, state, index)
    if line_no <= context.header_zone:
        return [], state
    return _comment_line(context, state, index, stripped)


def _is_comment_line(context: _ScanContext, stripped: str, line_no: int) -> bool:
    """Judge one line a comment line for its dialect.

    Rules:   Python callers pass exact comment positions; css/html count an opener line; stripped markup never counts.
    """
    if context.comment_lines is not None:
        return line_no in context.comment_lines
    is_comment = context.profile.is_comment(stripped) or (
        context.profile.name in ("css", "html") and _block_open(stripped)
    )
    if context.profile.name == "html" and not _strip_html_ctrl(stripped).strip():
        return False
    return is_comment


def _advance_code_state(context: _ScanContext, state: _ScanState, index: int) -> _ScanState:
    """Update the depth counters after one code line.

    Rules:   The masked line drives the counters; a code line always closes the label window.
    """
    depth, type_body_depth, paren_group_depth, paren_depth = _code_depths(
        state, context.masked[index].strip()
    )
    return state._replace(
        depth=depth,
        type_body_depth=type_body_depth,
        paren_group_depth=paren_group_depth,
        paren_depth=paren_depth,
        prev_label=None,
    )


def _code_depths(state: _ScanState, masked_code: str) -> tuple[int, int, int, int]:
    """Return the new depth counters for one code line.

    Rules:   The type-body reset precedes brace counting; a struct/interface body opens one level down and closes when the depth falls back; a value group tracks parens until they balance.
    """
    depth = state.depth
    type_body_depth = state.type_body_depth
    if type_body_depth and depth < type_body_depth:
        type_body_depth = 0
    opens = masked_code.count("{")
    closes = masked_code.count("}")
    if not type_body_depth and _TYPE_DECL.match(masked_code) and opens > closes:
        type_body_depth = depth + 1
    paren_group_depth = state.paren_group_depth
    paren_depth = state.paren_depth
    if not paren_group_depth and masked_code.endswith("("):
        paren_group_depth = depth + 1
    depth += opens - closes
    paren_depth += masked_code.count("(") - masked_code.count(")")
    if paren_group_depth and paren_depth <= 0:
        paren_group_depth = 0
        paren_depth = 0
    return depth, type_body_depth, paren_group_depth, paren_depth


def _comment_line(
    context: _ScanContext, state: _ScanState, index: int, stripped: str
) -> tuple[list[str], _ScanState]:
    """Inspect one comment line that sits below the header zone.

    Rules:   Label lines open a continuation window; css/html inline comments keep their block state; everything else classifies by content; the window closes when a finding lands.
    """
    inner = context.profile.strip(stripped)
    inner = (inner if inner is not None else stripped).strip()
    if context.profile.name in ("css", "html"):
        consumed, state = _css_html_step(state, stripped, inner)
        if consumed:
            return [], state
    if not inner:
        return [], state
    if context.profile.name == "html" and _L2_LABEL_LINE.match(stripped):
        return [], state._replace(prev_label=stripped)
    if _L2_LABEL_LINE.match(stripped):
        return [], state._replace(prev_label=inner)
    if state.prev_label is not None:
        return [], state._replace(prev_label=inner)
    if _FIELD_LINE.match(stripped):
        return [], state
    return _classify_content(context, state, index, inner), state._replace(prev_label=None)


def _css_html_step(state: _ScanState, stripped: str, inner: str) -> tuple[bool, _ScanState]:
    """Advance the css/html block state for one comment line.

    Rules:   An unclosed opener starts a block; an empty body is consumed; unhandled lines return consumed=False.
    """
    if _block_open(stripped) and not stripped.endswith(_block_close(_block_style(stripped) or "/*")):
        return True, state._replace(in_block=True, block_style=_block_style(stripped) or "")
    if not inner:
        return True, state
    return False, state


def _block_continuation(
    state: _ScanState, stripped: str, profile: LanguageProfile
) -> _ScanState:
    """Decide whether one line inside a css/html block comment closes it.

    Rules:   A line without html comment grammar closes as well.
    """
    if profile.name == "html" and not _strip_html_ctrl(stripped).strip():
        return state._replace(in_block=False)
    if stripped.endswith(_block_close(state.block_style)):
        return state._replace(in_block=False)
    return state


def _html_inline_probe(stripped: str, line_no: int) -> list[str] | None:
    """Report inline HTML comments on one marked-up line, or None when it carries none.

    Rules:   A probed line already reported must not fall through to the general comment path — that double-reports.
    """
    findings: list[str] = []
    probe_hits = 0
    for probe_match in re.finditer(r"<!--(.*?)-->", stripped):
        body_comment = probe_match.group(1).strip()
        if body_comment and not _L2_LABEL_LINE.match(body_comment):
            probe_hits += 1
            findings.append(
                f"{line_no}: comment is outside the permitted content: {body_comment[:60]}"
            )
    if probe_hits:
        return findings
    if "<!--" in _strip_html_ctrl(stripped) or stripped == "-->":
        return findings
    return None


def _classify_content(
    context: _ScanContext, state: _ScanState, index: int, inner: str
) -> list[str]:
    """Classify one comment body into its findings.

    Rules:   A summary line needs the declaration probe below it; TODO markers and code-shaped bodies report their own messages.
    """
    masked_code = context.masked[index].strip()
    if _summary_permitted(
        context.profile,
        context.masked,
        index,
        masked_code,
        state.type_body_depth,
        state.depth,
        state.paren_group_depth,
        state.paren_depth,
    ):
        if _word_count(inner) <= SUMMARY_WORD_LIMIT and not _TODO_MARKER.search(inner):
            return []
        return [
            f"{index + 1}: summary line holds {_word_count(inner)} words; cap is {SUMMARY_WORD_LIMIT}: {inner[:60]}"
        ]
    if _TODO_MARKER.search(inner):
        return [
            f"{index + 1}: mid-stream TODO marker outside Rules:/message: — port it to a Rules block or delete: {inner[:60]}"
        ]
    if _CODEISH_LINE.search(inner):
        return [f"{index + 1}: commented-out code is outside the permitted content: {inner[:60]}"]
    return [
        f"{index + 1}: comment is outside the permitted content (publish as Rules:/message: or delete): {inner[:60]}"
    ]


def _header_line_count(profile: LanguageProfile, originals: list[str]) -> int:
    """Return the leading header's last line number for exemption.

    Rules:   Python has no header zone — the docstring carries the L1 fields and tokenized comment_lines already classify its `#` lines separately, so no docstring-adjacent `#` line rides the exemption; other languages exempt their leading comment block.
    """
    entries = _header_entries(profile, originals)
    if profile.name == "python":
        return 0
    return entries[-1][0] if entries else 0


def _summary_permitted(
    profile: LanguageProfile,
    masked: list[str],
    index: int,
    masked_code: str,
    type_body_depth: int,
    depth: int,
    paren_group_depth: int = 0,
    paren_depth: int = 0,
) -> bool:
    """Decide whether one comment line documents the declaration below it.

    Rules:   The next non-blank masked line must start a declaration, or sit inside a struct body or an open value group; a statement never qualifies; the probe skips comment-masked blank rows within 60 lines.
    """
    if _CODEISH_LINE.search(masked_code):
        return False
    hops = 0
    for follow in range(index + 1, min(index + 60, len(masked))):
        nxt = masked[follow].strip()
        if not nxt:
            continue
        if _GROUP_DECL.match(nxt) or _TYPE_DECL.match(nxt):
            return True
        if type_body_depth and depth == type_body_depth:
            return True
        if paren_group_depth and depth == paren_group_depth:
            return True
        if paren_depth > 0:
            return True
        hops += 1
        if hops >= 8:
            return False
    return False


def _example_block_findings(block: str, where: str) -> list[str]:
    """Lint one fenced example.

    Rules:   Comments must be CodeDNA content; a block that does not parse as Python reports the parse error.
    """
    findings = [
        f"{where}: comment is outside the permitted content: {line.strip()[:60]}"
        for line in block.splitlines()
        if line.strip().startswith("#") and not _COMMENT_LABEL.match(line.strip())
    ]
    try:
        tree = ast.parse(block)
    except SyntaxError as error:
        findings.append(f"{where}: block does not parse as Python (line {error.lineno})")
        return findings
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        docstring = ast.get_docstring(node, clean=False)
        if docstring is None:
            continue
        allowed = L1_FIELDS if isinstance(node, ast.Module) else L2_FIELDS
        findings.extend(
            _docstring_findings(docstring, allowed, f"{where} [{getattr(node, 'name', 'module')}]")
        )
    return findings


def check_examples(text: str, source: str = "AGENTS.md") -> list[str]:
    """Return the findings for the Python examples inside a contract document.

    Rules:   Lint every fenced python block — examples are the artifact agents copy, so they obey the same content rules this document states.
    """
    findings: list[str] = []
    for index, block in enumerate(_PY_FENCE.findall(text), start=1):
        findings.extend(_example_block_findings(block, f"{source} example {index}"))
    return findings
