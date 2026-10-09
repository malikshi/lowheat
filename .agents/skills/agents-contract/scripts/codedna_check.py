"""codedna_check.py — Report CodeDNA header drift and out-of-contract comment content.

exports: DEFAULT_IGNORED_DIRS | SOURCE_SUFFIXES | LanguageProfile | check_file | check_comment_content | check_examples | collect_source_files | main
used_by: tests/test_codedna_check.py → main, check_file, check_comment_content, check_examples, collect_source_files, DEFAULT_IGNORED_DIRS [cascade]
used_by: AGENTS.md → CodeDNA editing protocol (checker mentions)
related: .agents/skills/agents-contract/SKILL.md (CodeDNA section)
rules:   Read-only — report findings carrying line numbers; never rewrite a file; shebangs, rust doc, and per-dialect directives are exempt.
agent:   grok-build-plan | 9router | 2026-10-08 | 01a11c14-e6f9-7581-9248-a9b2f058a3e8 | added checker, tests, and contract-example linting
agent:   grok-4.6 | xai | 2026-10-09 | 01a1165a-8f16-7702-b7e8-488efac69c7e | rewrite: line-numbered findings, 15 language profiles, comment-content scan, agent-entry shape, field order, header-window relief
agent:   claude-fable-5 | anthropic | 2026-10-09 | ddf225f-review | fixed mask_code OR-precedence, HTML double-report, dup type_body_depth reset; dropped dead HEADER_LINE_LIMIT; --skip-content now also skips contract examples
message: Content scanning is line-based (no per-language parser): a permitted summary line needs a declaration below; the scan reports when unsure. In contract examples, repeat a field label on every docstring line after the summary.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

SOURCE_SUFFIXES = (
    ".py",
    ".go",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".rs",
    ".sh",
    ".bash",
    ".zsh",
    ".css",
    ".html",
    ".htm",
)
AGENT_HISTORY_LIMIT = 5
L1_FIELDS = ("exports", "used_by", "related", "rules", "agent", "message")
L2_FIELDS = ("rules", "message")
REQUIRED_L1 = ("exports", "used_by", "rules", "agent")
SUMMARY_WORD_LIMIT = 15
ARROW = "→"
EM_DASH = "—"
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

_FIELD_LINE = re.compile(
    r"^\s*(?://+|#+|\*+|!|<!--|\*/|/\*)?\s*(exports|used_by|related|rules|agent|message):\s*(.*)$"
)
_L2_LABEL_LINE = re.compile(
    r"^\s*(?://+|#+|\*+|!|<!--|\*/|/\*)?\s*(Rules|message):\s*(.*)$"
)
_DOC_LABEL = re.compile(r"^\s*(exports|used_by|related|rules|Rules|agent|message):\s*(.*)$")
_COMMENT_LABEL = re.compile(r"^#\s*(Rules|message):")
_AGENT_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_AGENT_PIPE = re.compile(r"(?<!/)\|")
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
_PY_DOCSTRING = re.compile(r'^\s*(?:#[^\n]*\n)*\s*("""|\'\'\')(.*?)\1', re.DOTALL)
_PY_FENCE = re.compile(r"```python[ \t]*\n(.*?)```", re.DOTALL)
_EXPORT_SPLIT = re.compile(r"[|,]")
_GROUP_DECL = re.compile(r"^\s*(func|type|var|const|class|def|fn|let|export|pub)\b")
_STRUCT_MEMBER = re.compile(r"^\s+[A-Za-z_*\[\]<>\"']\w*\s*(=|:|\[|\(|$)")
_TYPE_DECL = re.compile(r"\s*type\s+\w+\s+(struct|interface)\b")
_TODO_MARKER = re.compile(r"\b(TODO|FIXME|XXX|HACK|WIP)\b")
_CODEISH_LINE = re.compile(
    r"(\{\s*$|;\s*$|:=|\breturn\b|\bif\b|\bfor\b|\bwhile\b|\bdefer\b|\bselect\b|\bswitch\b|\bcase\b|\berr\s*!=\s*nil\b|\bfunction\b|=>)"
)
_DIRECTIVES: dict[str, tuple[str, ...]] = {
    ".go": ("//go:", "//export ", "//sys ", "//line ", "//cgo:", "// +build", "//nolint", "//lint:", "// Code generated"),
    ".py": ("# type:", "# noqa", "# pylint:", "# ruff:", "# yapf:", "# fmt:", "# flake8:", "# isort:", "# mypy:"),
    ".js": ("// eslint", "/* eslint", "// @ts-", "/* jshint", "/* global", "/*!", "//# sourceurl"),
    ".ts": ("// eslint", "/* eslint", "/// <reference", "// @ts-", "/* jshint", "/* global", "/*!"),
    ".rs": ("/// ", "//! ", "#![", "#["),
    ".sh": ("# shellcheck",),
    ".bash": ("# shellcheck",),
    ".zsh": ("# shellcheck",),
}


class LanguageProfile:
    """Per-language comment grammar for header and content scanning.

    Rules:   Profiles are pure data; shared scan logic decides exemptions so every dialect receives the same contract checks.
    """

    def __init__(
        self,
        name: str,
        starts: tuple[str, ...],
        directives: tuple[str, ...] = (),
        shebang: bool = False,
        prefixes: tuple[str, ...] | None = None,
    ) -> None:
        self.name = name
        self.line_starts = tuple(sorted(starts, key=len, reverse=True))
        self.lowered_directives = tuple(d.lower() for d in directives)
        self.shebang = shebang
        self.strip_prefixes = prefixes if prefixes is not None else self.line_starts

    def is_comment(self, stripped: str) -> bool:
        """Classify one stripped line.

        Rules:   Callers pass string-literal interiors masked, so a quote inside a template never reaches here.
        """
        if not stripped:
            return False
        return any(stripped.startswith(p) for p in self.strip_prefixes)

    def strip(self, stripped: str) -> str | None:
        """Return the comment body of one stripped line, or None when it is code.

        Rules:   Prefix match is longest-first so `//go:` strips as a directive comment, not code.
        """
        for prefix in self.strip_prefixes:
            if stripped.startswith(prefix):
                return stripped[len(prefix):]
        return None

    def is_directive(self, stripped: str) -> bool:
        """Judge a stripped line a per-language tool directive.

        Rules:   A shebang line counts for shell profiles; directive matches are case-insensitive.
        """
        if self.shebang and stripped.startswith("#!"):
            return True
        lowered = stripped.lower()
        return any(lowered.startswith(d) for d in self.lowered_directives)


def _profile(name: str, starts, directives=(), shebang=False, prefixes=None) -> LanguageProfile:
    """Build one profile.

    Rules:   Keep directive lists conservative — a missed directive gets reported as prose rather than wrongly exempt.
    """
    return LanguageProfile(name, starts, directives, shebang, prefixes)


_proflies: dict[str, LanguageProfile] = {
    ".go": _profile("go", ("//",), _DIRECTIVES[".go"], prefixes=("//", "/*", "*/")),
    ".py": _profile("python", ("#",), _DIRECTIVES[".py"], prefixes=("#",)),
    ".js": _profile("javascript", ("//",), _DIRECTIVES[".js"], prefixes=("//", "/*", "*/")),
    ".jsx": _profile("jsx", ("//",), _DIRECTIVES[".js"], prefixes=("//", "/*", "*/")),
    ".ts": _profile("typescript", ("//",), _DIRECTIVES[".ts"], prefixes=("//", "/*", "*/")),
    ".tsx": _profile("tsx", ("//",), _DIRECTIVES[".ts"], prefixes=("//", "/*", "*/")),
    ".rs": _profile("rust", ("//",), _DIRECTIVES[".rs"], prefixes=("//", "/*", "*/")),
    ".sh": _profile("shell", ("#",), _DIRECTIVES[".sh"], shebang=True, prefixes=("#",)),
    ".bash": _profile("shell", ("#",), _DIRECTIVES[".sh"], shebang=True, prefixes=("#",)),
    ".zsh": _profile("shell", ("#",), _DIRECTIVES[".sh"], shebang=True, prefixes=("#",)),
    ".css": _profile("css", ("/*", "*/"), prefixes=("/*", "*/")),
    ".html": _profile("html", ("<!--", "-->"), prefixes=("<!--", "-->")),
    ".htm": _profile("html", ("<!--", "-->"), prefixes=("<!--", "-->")),
}
_proflies[".mjs"] = _proflies[".js"]
_proflies[".cjs"] = _proflies[".js"]
_profiles = _proflies


def profile_for(path: Path) -> LanguageProfile:
    """Return the language profile for one scanned suffix.

    Rules:   Unknown suffixes get a generic profile so they never bypass the header check.
    """
    return _profiles.get(path.suffix) or _profile(path.suffix.lstrip("."), ("#", "//"))


def _strip_html_ctrl(stripped: str) -> str:
    """Reduce an HTML line to the comment grammar it carries.

    Rules:   Markup without comment grammar must not read as header continuation.
    """
    if stripped.startswith("<!--") or stripped == "-->":
        return stripped
    return re.sub(r"</?script[^>]*>|</?style[^>]*>|<!DOCTYPE[^>]*>", "", stripped, flags=re.IGNORECASE)


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
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append(re.sub(r"[^\n]", " ", text[i:j]))
            i = j
            continue
        if suffix in (".sh", ".bash", ".zsh") and c == "#":
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
            continue
        if c in ('"', "'"):
            quote = c
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] in ("\n", quote):
                    break
                j += 1
            end = j + 1 if j < n and text[j] == quote else j
            out.append(re.sub(r"[^\n]", " ", text[i:end]))
            i = end
            continue
        if c == "`":
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if js_family and text[j] == "$" and j + 1 < n and text[j + 1] == "{":
                    depth = 1
                    k = j + 2
                    while k < n and depth:
                        if text[k] == "{":
                            depth += 1
                        elif text[k] == "}":
                            depth -= 1
                        elif text[k] == "`":
                            depth = -1
                            break
                        k += 1
                    j = k
                    continue
                if text[j] == "`":
                    break
                j += 1
            end = j + 1 if j < n and text[j] == "`" else j
            out.append(re.sub(r"[^\n]", " ", text[i:end]))
            i = end
            continue
        if c == "/" and js_family and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
            continue
        out.append(c)
        i += 1
    return "".join(out)


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

    Rules:   Golden rule: the returned style string feeds _block_close only.
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


def _docstring_fields(doc: str):
    """Map L1 labels to values inside a Python docstring.

    Rules:   Line numbers count docstring rows so the agent edits at the right line.
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
            labels.setdefault(current, offset)
            value = match.group(2).strip()
            if value:
                fields[current].append(value)
            continue
        if current is None or not stripped:
            continue
        fields[current].append(stripped)
    return fields, labels


def check_file(path: Path, root: Path) -> list[str]:
    """Return the L1 header findings for one source file.

    Rules:   Report only; empty means clean; findings carry the offending field's line number where known.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        return [f"unreadable: {error}"]

    findings: list[str] = []
    profile = profile_for(path)
    lines = text.splitlines()
    entries = _header_entries(profile, lines)

    if path.suffix == ".py":
        doc_match = _PY_DOCSTRING.match(text)
        if doc_match is None:
            return ["missing L1 header"]
        doc = doc_match.group(2).splitlines()
        first_no = text[: doc_match.start(2)].count("\n") + 1
        first_text = next((row.strip() for row in doc if row.strip()), "")
        fields, labels = _docstring_fields(doc_match.group(2))
    else:
        if not entries:
            return ["missing L1 header"]
        first_no, raw_first = entries[0]
        first_text = profile.strip(raw_first.strip()) or raw_first.strip()
        if profile.name in ("css", "html"):
            inner = raw_first.strip()
            for opener in ("/*", "<!--"):
                if inner.startswith(opener):
                    first_text = inner[len(opener):].strip()
                    break
        fields, labels = _read_header_fields(profile, entries)

    if EM_DASH not in first_text:
        findings.append(
            f"{first_no}: first header line lacks the filename {EM_DASH} description form: {first_text[:60]}"
        )
        return findings

    order: list[str] = []
    order_no = 0
    if path.suffix == ".py":
        doc_match = _PY_DOCSTRING.match(text)
        if doc_match:
            base = text[: doc_match.start(2)].count("\n") + 1
            for offset, raw in enumerate(doc_match.group(2).splitlines(), start=1):
                match = _FIELD_LINE.match(raw.strip())
                if match and match.group(1) not in order:
                    order.append(match.group(1))
                    order_no = order_no or base + offset
    else:
        for line_no, raw_entry in entries:
            match = _FIELD_LINE.match(raw_entry.strip())
            if match and match.group(1) not in order:
                order.append(match.group(1))
                order_no = order_no or line_no
    canonical_index = {name: index for index, name in enumerate(L1_FIELDS)}
    observed = [canonical_index[name] for name in order if name in canonical_index]
    if observed != sorted(observed):
        findings.append(
            f"{order_no}: L1 field order drifts from exports/used_by/related/rules/agent/message: {', '.join(order)}"
        )

    for label in REQUIRED_L1:
        if label not in labels:
            findings.append(f"{first_no}: missing L1 field: {label}")

    if path.suffix == ".py":
        doc_match = _PY_DOCSTRING.match(text)
        exports_body = text[doc_match.end():] if doc_match else text
    else:
        header_last = entries[-1][0] if entries else 0
        exports_body = "\n".join(lines[header_last:]) if header_last else text
    findings.extend(
        f"{labels.get('exports', first_no)}: {finding}"
        for finding in _exports_findings(fields.get("exports", []), exports_body)
    )
    findings.extend(
        f"{labels.get('used_by', first_no)}: {finding}"
        for finding in _used_by_findings(fields.get("used_by", []), root)
    )
    findings.extend(
        f"{labels.get('agent', first_no)}: {finding}"
        for finding in _agent_findings(fields.get("agent", []))
    )
    return findings


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

    Rules:   A continuation line belongs to the last entry and is never malformed; the 5-entry cap counts dated entries; a field with no shaped entry at all is the drift.
    """
    findings: list[str] = []
    history: list[str] = []
    for entry in entries:
        if _AGENT_DATE.search(entry) and _AGENT_PIPE.search(entry):
            history.append(entry)
    if entries and not history:
        findings.append(
            f"malformed agent history entry (model | provider | date | session | note): {entries[0][:60]}"
        )
    if len(history) > AGENT_HISTORY_LIMIT:
        findings.append(
            f"agent history holds {len(history)} entries; keep the last {AGENT_HISTORY_LIMIT}"
        )
    return findings


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


def check_comment_content(path: Path) -> list[str]:
    """Return findings for comment lines outside the permitted CodeDNA content.

    Rules:   Permitted: declaration summaries, L1 field lines, Rules:/message: lines and continuations; exemptions: tool directives, the shell shebang, and rust doc comments; line numbers address the comment's own line.
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
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return findings
        for node in ast.walk(tree):
            if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            docstring = ast.get_docstring(node, clean=False)
            if docstring is None:
                continue
            findings.extend(
                _docstring_findings(docstring, L2_FIELDS, f"{path.name} [{getattr(node, 'name', '')}]")
            )
        return findings
    masked = mask_code(profile, text, path.suffix)
    findings.extend(_scan_content(profile, masked.splitlines(), text.splitlines()))
    return findings


def _scan_content(profile: LanguageProfile, masked: list[str], originals: list[str]) -> list[str]:
    """Report comment lines outside the permitted CodeDNA content set.

    Rules:   Permitted: L1 field lines with continuations, one summary line per declaration (top-level, grouped, or struct member), Rules:/message: lines with continuations, tool directives, rust doc, the shell shebang. Context comes from masked code: brace depth for type bodies, paren depth for groups, declarations for summaries.
    """
    findings: list[str] = []
    header_zone = _header_line_count(profile, originals)
    depth = 0
    type_body_depth = 0
    paren_group_depth = 0
    paren_depth = 0
    prev_label: str | None = None
    in_block_comment = False
    block_style = ""
    for index, raw in enumerate(originals):
        line_no = index + 1
        masked_code = masked[index].strip()
        stripped = raw.strip()
        if not stripped:
            prev_label = None
            continue
        if in_block_comment:
            if profile.name == "html" and not _strip_html_ctrl(stripped).strip():
                in_block_comment = False
            elif stripped.endswith(_block_close(block_style)):
                in_block_comment = False
            continue
        if profile.is_directive(stripped) or stripped.startswith("#!"):
            prev_label = None
            continue
        if profile.name == "rust" and (stripped.startswith("///") or stripped.startswith("//!")):
            continue
        if profile.name == "html" and "<!--" in stripped:
            probe_hits = 0
            for probe_match in re.finditer(r"<!--(.*?)-->", stripped):
                body_comment = probe_match.group(1).strip()
                if body_comment and not _L2_LABEL_LINE.match(body_comment):
                    probe_hits += 1
                    findings.append(
                        f"{line_no}: comment is outside the permitted content: {body_comment[:60]}"
                    )
            # Rules: a probed line already reported must not fall through to the general comment path — that double-reports.
            if probe_hits:
                continue
            if "<!--" in _strip_html_ctrl(stripped) or stripped == "-->":
                continue
        is_comment = profile.is_comment(stripped) or (
            profile.name in ("css", "html") and (in_block_comment or _block_open(stripped))
        )
        is_comment = is_comment and not (profile.name == "html" and _strip_html_ctrl(stripped).strip() == "")
        if not is_comment:
            if type_body_depth and depth < type_body_depth:
                type_body_depth = 0
            opens = masked_code.count("{")
            closes = masked_code.count("}")
            if not type_body_depth and _TYPE_DECL.match(masked_code) and opens > closes:
                type_body_depth = depth + 1
            if not paren_group_depth and masked_code.endswith("("):
                paren_group_depth = depth + 1
            depth += opens - closes
            paren_depth += masked_code.count("(") - masked_code.count(")")
            if paren_group_depth and paren_depth <= 0:
                paren_group_depth = 0
                paren_depth = 0
            prev_label = None
            continue
        if line_no <= header_zone:
            continue
        inner = profile.strip(stripped)
        if inner is None:
            inner = stripped
        inner = inner.strip()
        if profile.name in ("css", "html"):
            open_now = _block_open(stripped)
            close_now = stripped.endswith(_block_close(_block_style(stripped) or "/*")) if open_now else False
            if open_now and not close_now:
                in_block_comment = True
                block_style = _block_style(stripped) or ""
                continue
            if open_now and close_now and line_no <= header_zone:
                continue
            if not inner:
                continue
        if not inner:
            continue
        if profile.name == "html" and _L2_LABEL_LINE.match(stripped):
            prev_label = stripped
            continue
        if _L2_LABEL_LINE.match(stripped):
            prev_label = inner
            continue
        if prev_label is not None:
            if _FIELD_LINE.match(stripped):
                prev_label = inner
                continue
            prev_label = inner
            continue
        if _FIELD_LINE.match(stripped):
            continue
        if _summary_permitted(
            profile, masked, index, masked_code, type_body_depth, depth, paren_group_depth, paren_depth
        ):
            if _word_count(inner) <= SUMMARY_WORD_LIMIT and not _TODO_MARKER.search(inner):
                prev_label = None
                continue
        if _TODO_MARKER.search(inner):
            findings.append(
                f"{line_no}: mid-stream TODO marker outside Rules:/message: — port it to a Rules block or delete: {inner[:60]}"
            )
        elif _CODEISH_LINE.search(inner):
            findings.append(
                f"{line_no}: commented-out code is outside the permitted content: {inner[:60]}"
            )
        else:
            findings.append(
                f"{line_no}: comment is outside the permitted content (publish as Rules:/message: or delete): {inner[:60]}"
            )
        prev_label = None
    return findings


def _header_line_count(profile: LanguageProfile, originals: list[str]) -> int:
    """Return the leading header's last line number for exemption.

    Rules:   The header zone covers only the leading block; code-side field lines later in the file still report.
    """
    entries = _header_entries(profile, originals)
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


def main(argv=None) -> int:
    """Run the checker over the given paths.

    Rules:   Exit 1 when any finding exists, 0 when every header is clean; findings carry either header or comment line numbers.
    """
    parser = argparse.ArgumentParser(description="Report CodeDNA L1 header drift and out-of-contract comment content.")
    parser.add_argument("paths", nargs="*", help="files or directories to scan (default: .)")
    parser.add_argument("--root", default=".", help="root that used_by targets resolve against")
    parser.add_argument("--skip-content", action="store_true", help="check headers only")
    args = parser.parse_args(argv)

    roots = [Path(item) for item in args.paths] or [Path(".")]
    root = Path(args.root)
    files = collect_source_files(roots)
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
