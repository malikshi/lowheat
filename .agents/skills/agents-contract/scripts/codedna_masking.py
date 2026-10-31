"""codedna_masking.py — Blank strings, comments, and literal interiors so the scanner sees only comment lines.

exports: mask_code
used_by: .agents/skills/agents-contract/scripts/codedna_content.py → mask_code and the Python and heredoc scanners [cascade]
rules:   Masking preserves every newline and the line structure; string, template, and comment interiors blank so quotes and `#` inside them never read as comments; optional spans expose each comment range to the content scan; an unterminated heredoc opener never silences the rest of the file — a false opener must fail open. Block and line markers come from the language profile, never from a suffix test: a marker inside a literal is consumed by the literal first, and a line marker needs a code position so `https://` and `a//b` stay code.
agent:   unknown | xai | 2026-10-14 | 01a1373b-7fa0-7851-ae9d-4cd27c951a27 | split out of codedna_check.py; mask_code's template-literal branch became two helpers and the masking pass is now a flat branch list.
agent:   fx | unknown | 2026-10-31 | unknown | added optional comment spans, HTML comment masking, and restricted `//` to Go/Rust/JS so CSS and shell URLs stay code
agent:   grok-4.6 | xai | 2026-10-31 | unknown | restricted `/* */` to C-style profiles after an HTML page with `<b>provider/*</b>` masked the rest of the file as one block comment
agent:   grok-4.6 | xai | 2026-10-31 | unknown | made masking profile-driven: block markers, line and word markers, quoting styles, Lua long brackets, and nested blocks
"""
from __future__ import annotations

import io
import re
import tokenize

from codedna_spec import _HEREDOC_OPEN, _PY_MASKED_TOKENS, BlockMarker, LanguageProfile


def mask_code(
    profile: LanguageProfile,
    text: str,
    spans: list[tuple[int, int]] | None = None,
) -> str:
    """Blank code so the scanner sees only comment lines.

    Rules:   Block markers are tried longest-first and before line markers; `nested` counts the opener again inside the body; an `at_line_start` marker opens only at column 0. String, template, and long-bracket interiors blank; JS templates track `${...}` nesting; newlines preserved. When `spans` is passed, append each comment's absolute `(start, end)` range so the content scanner can inspect trailing and multiline comment bodies.
    """
    js_family = profile.backtick == "js"
    in_php = False
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "\n":
            out.append(c)
            i += 1
            continue
        if profile.php_mode and not in_php:
            opener = _php_opener(text, i)
            if opener:
                out.append(opener)
                i += len(opener)
                in_php = True
            else:
                out.append(c)
                i += 1
            continue
        if profile.php_mode and text.startswith("?>", i):
            out.append("?>")
            i += 2
            in_php = False
            continue
        if profile.percent_literals and c == "%":
            percent_end = _percent_literal_end(text, i)
            if percent_end is not None:
                out.append(re.sub(r"[^\n]", " ", text[i:percent_end]))
                i = percent_end
                continue
        if profile.sigils and c == "~":
            sigil_end = _sigil_end(text, i)
            if sigil_end is not None:
                out.append(re.sub(r"[^\n]", " ", text[i:sigil_end]))
                i = sigil_end
                continue
        long_comment = _long_bracket_at(profile.long_bracket, text, i)
        if long_comment is not None:
            start = i
            opener_end, closer = long_comment
            i = _mask_through(text, start, opener_end, closer, out)
            if spans is not None:
                spans.append((start, i))
            continue
        block = _block_at(profile, text, i)
        if block is not None:
            start = i
            i = _mask_block(text, i, block, out)
            if spans is not None:
                spans.append((start, i))
            continue
        long_string = _long_bracket_at(profile.long_string, text, i)
        if long_string is not None:
            opener_end, closer = long_string
            i = _mask_through(text, i, opener_end, closer, out)
            continue
        marker = profile.line_marker_at(text, i)
        if marker is not None:
            start = i
            i = _mask_to_eol(text, i, out)
            if spans is not None:
                spans.append((start, i))
            continue
        if profile.triple_quotes and text.startswith('"""', i):
            end = text.find('"""', i + 3)
            end = n if end < 0 else end + 3
            out.append(re.sub(r"[^\n]", " ", text[i:end]))
            i = end
            continue
        if profile.triple_single_quotes and text.startswith("'''", i):
            end = text.find("'''", i + 3)
            end = n if end < 0 else end + 3
            out.append(re.sub(r"[^\n]", " ", text[i:end]))
            i = end
            continue
        if profile.raw_strings and text.startswith('R"', i):
            raw_end = _raw_string_end(text, i)
            if raw_end is not None:
                out.append(re.sub(r"[^\n]", " ", text[i:raw_end]))
                i = raw_end
                continue
        if profile.here_strings and (
            text.startswith('@"', i) or text.startswith("@'", i)
        ):
            here_end = _here_string_end(text, i)
            if here_end is not None:
                out.append(re.sub(r"[^\n]", " ", text[i:here_end]))
                i = here_end
                continue
        if c in profile.string_quotes:
            i = _mask_quoted(text, i, out, profile.doubled_quotes)
            continue
        if c == "`" and profile.backtick:
            i = _mask_template(text, i, js_family, out)
            continue
        regex_end = _regex_literal_end(profile, text, i)
        if regex_end is not None:
            out.append(re.sub(r"[^\n]", " ", text[i:regex_end]))
            i = regex_end
            continue
        out.append(c)
        i += 1
    return "".join(out)


# Rules: these characters can precede a regex literal; a closing `)` is absent because `(a) / b` is division.
_REGEX_PRECEDERS = set("=(:,[!&|?{;~")
_REGEX_KEYWORDS = frozenset(
    {"return", "typeof", "case", "delete", "void", "in", "of", "yield", "await", "else", "do", "when"}
)


def _regex_literal_end(profile: LanguageProfile, text: str, index: int) -> int | None:
    """Return the index after one regex literal starting at a slash, or None.

    Rules:   A regex starts only after an operator, a bracket, or a keyword — `a / b` is division; `//` and `/*` are comments; a newline aborts the scan; a character class may hold a raw `/`.
    """
    if not profile.regex_literals or text[index] != "/":
        return None
    if text[index + 1:index + 2] in ("/", "*"):
        return None
    if not _regex_can_start(text, index):
        return None
    cursor = index + 1
    in_class = False
    n = len(text)
    while cursor < n:
        char = text[cursor]
        if char == "\\":
            cursor += 2
            continue
        if char == "\n":
            return None
        if char == "[":
            in_class = True
        elif char == "]":
            in_class = False
        elif char == "/" and not in_class:
            return cursor + 1
        cursor += 1
    return None


def _regex_can_start(text: str, index: int) -> bool:
    """Judge a slash position a regex opener by what precedes it.

    Rules:   Line start and the operator set open a regex; a preceding keyword (`return`, `when`, ...) does too; an identifier or a closing bracket means division.
    """
    cursor = index - 1
    while cursor >= 0 and text[cursor] in " \t":
        cursor -= 1
    if cursor < 0 or text[cursor] == "\n":
        return True
    if text[cursor] in _REGEX_PRECEDERS:
        return True
    end = cursor + 1
    while cursor >= 0 and (text[cursor].isalnum() or text[cursor] == "_"):
        cursor -= 1
    return text[cursor + 1:end] in _REGEX_KEYWORDS


# Rules: Ruby percent literals start with `%` plus an optional type letter plus a delimiter; a space, a digit, or a closing bracket means the modulo operator.
_PERCENT_TYPES = frozenset("qQwWiIrxs")
_PAIRED_DELIMITERS = {"(": ")", "[": "]", "{": "}", "<": ">"}


def _percent_literal_end(text: str, index: int) -> int | None:
    """Return the index after one Ruby percent literal, or None.

    Rules:   A modulo operand (`a % b`, `a %w[x]` directly after a value) is not a literal; paired delimiters nest; an unterminated literal runs to the end.
    """
    if index and (text[index - 1].isalnum() or text[index - 1] in "_)]"):
        return None
    cursor = index + 1
    if text[cursor:cursor + 1] in _PERCENT_TYPES:
        cursor += 1
    delimiter = text[cursor:cursor + 1]
    if not delimiter or delimiter.isalnum() or delimiter.isspace() or delimiter == "%":
        return None
    return _delimited_literal_end(text, cursor)


def _sigil_end(text: str, index: int) -> int | None:
    """Return the index after one Elixir sigil literal, or None.

    Rules:   A sigil is `~`, one or more name letters, then a non-alphanumeric delimiter; an unterminated sigil runs to the end.
    """
    cursor = index + 1
    start = cursor
    while text[cursor:cursor + 1].isalpha():
        cursor += 1
    if cursor == start:
        return None
    delimiter = text[cursor:cursor + 1]
    if not delimiter or delimiter.isalnum() or delimiter.isspace() or delimiter == "~":
        return None
    return _delimited_literal_end(text, cursor)


def _delimited_literal_end(text: str, delimiter_index: int) -> int:
    """Return the index after the closing delimiter of one delimited literal.

    Rules:   Paired delimiters nest; a backslash escapes; an unterminated literal runs to the end.
    """
    delimiter = text[delimiter_index]
    closer = _PAIRED_DELIMITERS.get(delimiter, delimiter)
    nested = delimiter in _PAIRED_DELIMITERS
    depth = 1
    cursor = delimiter_index + 1
    n = len(text)
    while cursor < n:
        char = text[cursor]
        if char == "\\":
            cursor += 2
            continue
        if nested and char == delimiter:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return cursor + 1
        cursor += 1
    return n


def _php_opener(text: str, index: int) -> str:
    """Return the PHP open tag starting at one position, or an empty string.

    Rules:   Both `<?php` and the short echo `<?=` switch modes; markup before an open tag is data, so its `#` lines never read as comments.
    """
    for opener in ("<?php", "<?="):
        if text.startswith(opener, index):
            return opener
    return ""


def _block_at(profile: LanguageProfile, text: str, index: int) -> BlockMarker | None:
    """Return the block-comment marker opening at one position, if any.

    Rules:   Longest open marker wins; an `at_line_start` marker opens only at column 0.
    """
    for marker in profile.block_markers:
        if not text.startswith(marker.open, index):
            continue
        if marker.at_line_start and index and text[index - 1] != "\n":
            continue
        return marker
    return None


def _long_bracket_at(prefix: str | None, text: str, index: int) -> tuple[int, str] | None:
    """Match one Lua long bracket at a position and return its body start and closer.

    Rules:   A long bracket is the prefix, then `[`, any number of `=`, then `[`; the closer mirrors the equals count. A single `[` that does not start a long bracket is ordinary code.
    """
    if prefix is None or not text.startswith(prefix, index):
        return None
    cursor = index + len(prefix)
    if text[cursor:cursor + 1] != "[":
        return None
    cursor += 1
    equals = 0
    while text[cursor:cursor + 1] == "=":
        equals += 1
        cursor += 1
    if text[cursor:cursor + 1] != "[":
        return None
    return cursor + 1, "]" + "=" * equals + "]"


def _mask_block(text: str, start: int, block: BlockMarker, out: list[str]) -> int:
    """Blank one block comment through its closing marker.

    Rules:   A nested opener raises the depth; an unterminated block runs to the end of the text; newlines survive.
    """
    depth = 1
    cursor = start + len(block.open)
    n = len(text)
    while cursor < n:
        if block.nested and text.startswith(block.open, cursor):
            depth += 1
            cursor += len(block.open)
            continue
        if text.startswith(block.close, cursor):
            depth -= 1
            cursor += len(block.close)
            if depth == 0:
                break
            continue
        cursor += 1
    out.append(re.sub(r"[^\n]", " ", text[start:cursor]))
    return cursor


def _mask_through(
    text: str, start: int, body_start: int, closer: str, out: list[str]
) -> int:
    """Blank one long-bracket comment or string from its opener through its closer.

    Rules:   An unterminated bracket runs to the end; newlines survive.
    """
    found = text.find(closer, body_start)
    cursor = len(text) if found < 0 else found + len(closer)
    out.append(re.sub(r"[^\n]", " ", text[start:cursor]))
    return cursor


def _mask_to_eol(text: str, start: int, out: list[str]) -> int:
    """Blank one line tail through the newline, which stays intact.

    Rules:   Line comments end at the newline; word markers and `::` labels work the same way.
    """
    end = text.find("\n", start)
    end = len(text) if end < 0 else end
    out.append(" " * (end - start))
    return end


def _raw_string_end(text: str, index: int) -> int | None:
    """Return the index after one C++ raw string, or None when the form is incomplete.

    Rules:   The delimiter sits between `R"` and `(`; the closer is `)`, the same delimiter, then `"`; a newline before the opener bracket means this is not a raw string.
    """
    cursor = index + 2
    n = len(text)
    while cursor < n and text[cursor] not in "(\n":
        cursor += 1
    if cursor >= n or text[cursor] != "(":
        return None
    closer = ")" + text[index + 2:cursor] + '"'
    found = text.find(closer, cursor + 1)
    return n if found < 0 else found + len(closer)


def _here_string_end(text: str, index: int) -> int | None:
    """Return the index after one PowerShell here-string, or None.

    Rules:   The opener is `@"` or `@'` with only whitespace after it on its line; the closer is `"@` or `'@` as the first token of a later line; an unterminated here-string runs to the end.
    """
    quote = text[index + 1]
    line_end = text.find("\n", index + 2)
    if line_end < 0 or text[index + 2:line_end].strip():
        return None
    closer = quote + "@"
    cursor = line_end + 1
    n = len(text)
    while cursor < n:
        candidate_end = text.find("\n", cursor)
        candidate_end = n if candidate_end < 0 else candidate_end
        if text[cursor:candidate_end].strip() == closer:
            return candidate_end
        cursor = candidate_end + 1
    return n


def _mask_quoted(text: str, start: int, out: list[str], doubled: bool) -> int:
    """Blank one quoted run through its closing quote.

    Rules:   Backslashes escape; with `doubled`, a repeated quote is an escaped quote inside the literal (C#, VB, SQL); an unterminated or newline-broken run ends at the boundary it reached.
    """
    quote = text[start]
    end = start + 1
    n = len(text)
    while end < n:
        if text[end] == "\\":
            end += 2
            continue
        if text[end] == quote:
            if doubled and text[end + 1:end + 2] == quote:
                end += 2
                continue
            break
        if text[end] == "\n":
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


def _python_scan_inputs(
    text: str,
) -> tuple[str, frozenset[int], dict[int, tuple[str, ...]]] | None:
    """Blank Python strings and comments, and report comment bodies by line.

    Rules:   tokenize decides what is a string, so a `#` inside a docstring, template, or f-string never reads as a comment; a comment that trails code is not a comment line, matching the line-based dialects, but its body is still returned for the content scan; only characters are replaced, so line structure is preserved; returns None when the file does not tokenize.
    """
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return None
    source_lines = text.split("\n")
    rows = [list(row) for row in source_lines]
    comment_lines: set[int] = set()
    comment_bodies: dict[int, list[str]] = {}
    for token in tokens:
        if token.type == tokenize.COMMENT:
            row_number = token.start[0]
            if not source_lines[row_number - 1][: token.start[1]].strip():
                comment_lines.add(row_number)
            body = source_lines[row_number - 1][token.start[1] + 1:].strip()
            if body:
                comment_bodies.setdefault(row_number, []).append(body)
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
    return (
        "\n".join("".join(row) for row in rows),
        frozenset(comment_lines),
        {line: tuple(bodies) for line, bodies in comment_bodies.items()},
    )


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
