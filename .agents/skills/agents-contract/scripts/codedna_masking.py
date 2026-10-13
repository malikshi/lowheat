"""codedna_masking.py — Blank strings, comments, and literal interiors so the scanner sees only comment lines.

exports: mask_code
used_by: .agents/skills/agents-contract/scripts/codedna_content.py → mask_code and the Python and heredoc scanners [cascade]
rules:   Masking preserves every newline and the line structure; string, template, and comment interiors blank so quotes and `#` inside them never read as comments; an unterminated heredoc opener never silences the rest of the file — a false opener must fail open.
agent:   unknown | xai | 2026-10-14 | 01a1373b-7fa0-7851-ae9d-4cd27c951a27 | split out of codedna_check.py; mask_code's template-literal branch became two helpers and the masking pass is now a flat branch list.
"""
from __future__ import annotations

import io
import re
import tokenize

from codedna_spec import _HEREDOC_OPEN, _PY_MASKED_TOKENS, LanguageProfile


def mask_code(profile: LanguageProfile, text: str, suffix: str) -> str:
    """Blank code so the scanner sees only comment lines.

    Rules:   String and template-literal interiors blank; template literals track `${...}` nesting for JS dialects; newlines preserved.
    """
    js_family = suffix in (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx")
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "\n":
            out.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/" and (suffix == ".go" or not js_family):
            i = _mask_to_eol(text, i, out)
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            i = _mask_block_comment(text, i, out)
            continue
        if suffix in (".sh", ".bash", ".zsh") and c == "#":
            i = _mask_to_eol(text, i, out)
            continue
        if c in ('"', "'"):
            i = _mask_quoted(text, i, out)
            continue
        if c == "`":
            i = _mask_template(text, i, js_family, out)
            continue
        if c == "/" and js_family and i + 1 < n and text[i + 1] == "/":
            i = _mask_to_eol(text, i, out)
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _mask_to_eol(text: str, start: int, out: list[str]) -> int:
    """Blank one line tail through the newline, which stays intact.

    Rules:   `//` and shell `#` comments end at the newline.
    """
    end = text.find("\n", start)
    end = len(text) if end < 0 else end
    out.append(" " * (end - start))
    return end


def _mask_block_comment(text: str, start: int, out: list[str]) -> int:
    """Blank one block comment through its closing marker.

    Rules:   An unterminated block runs to the end of the text.
    """
    end = text.find("*/", start + 2)
    end = len(text) if end < 0 else end + 2
    out.append(re.sub(r"[^\n]", " ", text[start:end]))
    return end


def _mask_quoted(text: str, start: int, out: list[str]) -> int:
    """Blank one quoted run through its closing quote.

    Rules:   Backslashes escape; an unterminated or newline-broken run ends at the boundary it reached.
    """
    quote = text[start]
    end = start + 1
    n = len(text)
    while end < n:
        if text[end] == "\\":
            end += 2
            continue
        if text[end] in ("\n", quote):
            break
        end += 1
    if end < n and text[end] == quote:
        end += 1
    out.append(re.sub(r"[^\n]", " ", text[start:end]))
    return end


def _mask_template(text: str, start: int, js_family: bool, out: list[str]) -> int:
    """Blank one backtick literal through its closing backtick.

    Rules:   JS dialects skip `${...}` expressions, which may contain braces and nested backticks.
    """
    end = _skip_template_literal(text, start, js_family)
    out.append(re.sub(r"[^\n]", " ", text[start:end]))
    return end


def _skip_template_literal(text: str, start: int, tracks_dollars: bool) -> int:
    """Return the index after the backtick closing one template literal.

    Rules:   With `tracks_dollars`, `${...}` expressions are skipped and the scan resumes on the closing backtick; a backslash escapes.
    """
    index = start + 1
    n = len(text)
    while index < n:
        char = text[index]
        if char == "\\":
            index += 2
            continue
        if tracks_dollars and char == "$" and index + 1 < n and text[index + 1] == "{":
            index = _skip_braced_expression(text, index + 1)
            continue
        if char == "`":
            return index + 1
        index += 1
    return n


def _skip_braced_expression(text: str, brace_start: int) -> int:
    """Return the index after the `}` closing one `${` expression.

    Rules:   A backtick inside restarts the literal and returns its own index; depth counts nested braces; an unterminated expression ends the text.
    """
    depth = 0
    index = brace_start
    n = len(text)
    while index < n:
        char = text[index]
        if char == "`":
            return index
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    return n


def _python_scan_inputs(text: str) -> tuple[str, frozenset[int]] | None:
    """Blank Python strings and comments, and report the lines that open a comment.

    Rules:   tokenize decides what is a string, so a `#` inside a docstring, template, or f-string never reads as a comment; a comment that trails code is not a comment line, matching the line-based dialects; only characters are replaced, so line structure is preserved; returns None when the file does not tokenize.
    """
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return None
    source_lines = text.split("\n")
    rows = [list(row) for row in source_lines]
    comment_lines: set[int] = set()
    for token in tokens:
        if token.type == tokenize.COMMENT:
            if not source_lines[token.start[0] - 1][: token.start[1]].strip():
                comment_lines.add(token.start[0])
        if token.type not in _PY_MASKED_TOKENS:
            continue
        start_row, start_col = token.start
        end_row, end_col = token.end
        for row_number in range(start_row, min(end_row, len(rows)) + 1):
            row = rows[row_number - 1]
            first = start_col if row_number == start_row else 0
            last = end_col if row_number == end_row else len(row)
            for column in range(min(first, len(row)), min(last, len(row))):
                row[column] = " "
    return "\n".join("".join(row) for row in rows), frozenset(comment_lines)


def _open_quote(line: str, column: int) -> str | None:
    """Return the quote character still open at one column, or None.

    Rules:   Backslashes escape outside single quotes only; a doubled quote inside single quotes reads as a close, so a marker after one still counts as an opener — the fail-open rule bounds what that costs.
    """
    quote: str | None = None
    index = 0
    while index < column:
        char = line[index]
        if char == "\\" and quote != "'":
            index += 2
            continue
        if quote is None and char in "\"'":
            quote = char
        elif quote == char:
            quote = None
        index += 1
    return quote


def _shell_heredoc_openers(line: str) -> list[tuple[str, bool]]:
    """Return the delimiter words and `<<-` flags one shell line opens, in order.

    Rules:   A marker inside a quoted run is prose, and `<<<` is a herestring — treating either as a heredoc would silence real comments below it.
    """
    openers: list[tuple[str, bool]] = []
    for match in _HEREDOC_OPEN.finditer(line):
        if _open_quote(line, match.start()) is None:
            openers.append((match.group(2), match.group(1) == "-"))
    return openers


def _heredoc_terminator(lines: list[str], start: int, word: str, strips_tabs: bool) -> int | None:
    """Return the line index that closes one heredoc, or None when none exists.

    Rules:   bash closes only on the bare word — leading tabs come off for `<<-` alone, and a trailing blank keeps the line in the body.
    """
    for index in range(start, len(lines)):
        candidate = lines[index].lstrip("\t") if strips_tabs else lines[index]
        if candidate == word:
            return index
    return None


def _shell_heredoc_lines(text: str) -> frozenset[int]:
    """Return the line numbers inside shell heredoc bodies.

    Rules:   A heredoc body is data, so a `#` line inside one is never a comment. A body is skipped only when its terminator is found below — an opener without one (a false match on arithmetic, a herestring, or a quoted marker) must never silence the rest of the file. Bodies close in the order their openers appear.
    """
    lines = text.split("\n")
    body_lines: set[int] = set()
    closers: list[int] = []
    for index, raw in enumerate(lines):
        while closers and index >= closers[0]:
            closers.pop(0)
        if closers:
            body_lines.add(index + 1)
            continue
        if raw.lstrip().startswith("#"):
            continue
        search_from = index + 1
        for word, strips_tabs in _shell_heredoc_openers(raw):
            closing = _heredoc_terminator(lines, search_from, word, strips_tabs)
            if closing is None:
                break
            closers.append(closing)
            search_from = closing + 1
    return frozenset(body_lines)
