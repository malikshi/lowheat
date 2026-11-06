"""codedna_spec.py — Shared contract constants, regexes, and per-language comment profiles.

exports: SOURCE_SUFFIXES | COMPOUND_SUFFIXES | EXPLICIT_SUFFIXES | TOOL_OWNED_DIRS | DEFAULT_IGNORED_DIRS | L1_FIELDS | L2_FIELDS | REQUIRED_L1 | AGENT_HISTORY_LIMIT | SUMMARY_WORD_LIMIT | ARROW | EM_DASH | BlockMarker | LanguageProfile | profile_for | suffix_for
used_by: .agents/skills/agents-contract/scripts/codedna_masking.py → LanguageProfile and masking regexes [cascade]
used_by: .agents/skills/agents-contract/scripts/codedna_headers.py → profiles and L1 constants [cascade]
used_by: .agents/skills/agents-contract/scripts/codedna_content.py → limits and label regexes [cascade]
used_by: .agents/skills/agents-contract/scripts/codedna_check.py → re-exports for tests and main [cascade]
used_by: .agents/skills/agents-contract/scripts/codedna_python.py → arrow and export regexes [cascade]
used_by: tests/test_codedna_check.py → profile_for, suffix_for [cascade]
rules:   Constants are single sources of truth — a consumer module never repeats them. A profile change reaches every dialect at once, so the shared scan logic stays free of per-language branches. SPDX lines are exempt in every dialect the contract scans; an agent history entry carries exactly the five contract fields, and a Python module docstring may carry a raw or unicode prefix. Suffix matching is case-insensitive. A suffix with two real languages takes one superset profile that never reports inside valid code. `->` and `→` are the same arrow: drop the return type before naming an export, and cut the symbol after it when resolving a used_by consumer. A compound suffix wins over its last component: `.blade.php` is Blade, never PHP.
agent:   fx | unknown | 2026-10-31 | unknown | tightened the agent-history regex to require session and note, and allowed raw/unicode Python docstring prefixes
agent:   grok-4.6 | xai | 2026-10-31 | unknown | replaced the suffix switch tables with explicit per-language profiles (line, word, and block markers) covering the declared language set
agent:   grok-4.6 | xai | 2026-11-01 | unknown | review fixes: `#` after `{`/`$` and PHP `#[` stay code, Clojure character literals stay code, functional profiles drop the single-quote string form
agent:   fx | unknown | 2026-11-06 | unknown | added _ARROW_SPLIT so upstream's `sym(sig) → type` exports and its `|`-separated used_by consumers parse; the consumed-suffix note lives in the message below
agent:   fx | unknown | 2026-11-06 | unknown | registered the Blade, Jinja/Twig/Volt, ERB/EJS, Handlebars/Mustache, and Razor families plus compound suffix resolution, so template headers parse instead of failing as PHP or going unscanned
message: The 87 suffix profiles are data, not branches. Keeping them in one module avoids import cycles between the masker, header parser, and content scanner; the file exceeds the 800-line soft ceiling by accepted data volume, not by unreviewed logic.
"""
from __future__ import annotations

import re
import tokenize
from pathlib import Path
from typing import NamedTuple

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
    ".c",
    ".h",
    ".cc",
    ".cpp",
    ".cxx",
    ".hpp",
    ".hh",
    ".hxx",
    ".m",
    ".mm",
    ".cs",
    ".java",
    ".kt",
    ".kts",
    ".scala",
    ".sc",
    ".groovy",
    ".gradle",
    ".swift",
    ".rb",
    ".rake",
    ".gemspec",
    ".ru",
    ".php",
    ".phtml",
    ".pl",
    ".pm",
    ".lua",
    ".hs",
    ".lhs",
    ".ex",
    ".exs",
    ".erl",
    ".hrl",
    ".clj",
    ".cljs",
    ".cljc",
    ".dart",
    ".sql",
    ".ps1",
    ".psm1",
    ".psd1",
    ".bat",
    ".cmd",
    ".vb",
    ".vbs",
    ".frm",
    ".fs",
    ".fsi",
    ".fsx",
    ".ml",
    ".mli",
    ".r",
    ".jl",
    ".zig",
    ".nim",
    ".cr",
    ".d",
    ".sol",
    ".tf",
    ".tfvars",
    ".hcl",
    ".f",
    ".for",
    ".f90",
    ".f95",
    ".f03",
    ".f08",
    ".elm",
    ".vue",
    ".svelte",
    ".astro",
    ".blade.php",
    ".j2",
    ".jinja2",
    ".twig",
    ".volt",
    ".erb",
    ".ejs",
    ".hbs",
    ".mustache",
    ".cshtml",
    ".razor",
)
AGENT_HISTORY_LIMIT = 5
L1_FIELDS = ("exports", "used_by", "related", "rules", "agent", "message")
L2_FIELDS = ("rules", "message")
REQUIRED_L1 = ("exports", "used_by", "rules", "agent")
SUMMARY_WORD_LIMIT = 15
ARROW = "→"
EM_DASH = "—"
# Rules: a new agent CLI or editor that writes its own dot-directory belongs in TOOL_OWNED_DIRS, or the run reports findings in code the project does not own; --exclude covers one-off names.
TOOL_OWNED_DIRS = frozenset(
    {
        ".claude",
        ".commandcode",
        ".codex",
        ".cursor",
        ".gemini",
        ".grok",
        ".opencode",
        ".aider",
        ".continue",
        ".specstory",
        ".windsurf",
        ".roo",
        ".cline",
        ".kilocode",
        ".crush",
        ".qwen",
        ".augment",
        ".factory",
        ".amp",
        ".goose",
        ".plandex",
        ".vscode",
        ".idea",
        ".fleet",
        ".zed",
        ".history",
    }
)
DEFAULT_IGNORED_DIRS = (
    frozenset(
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
    | TOOL_OWNED_DIRS
)

_MARKER_PREFIX = (
    r"(?://!|//+|<!--|-->|/\*|\*/|\{-|-\}|\(\*|\*\)|<#|#>|"
    r"=begin|=end|=pod|=cut|\*+|#+|;+|--+|%+|'+|!+|::+|@?(?i:REM)\b)"
)
_FIELD_LINE = re.compile(
    rf"^\s*(?:{_MARKER_PREFIX})?\s*(exports|used_by|related|rules|agent|message):\s*(.*)$"
)
_L2_LABEL_LINE = re.compile(
    rf"^\s*(?:{_MARKER_PREFIX})?\s*(Rules|message):\s*(.*)$"
)
_DOC_LABEL = re.compile(r"^\s*(exports|used_by|related|rules|Rules|agent|message):\s*(.*)$")
_COMMENT_LABEL = re.compile(r"^#\s*(Rules|message):")
_AGENT_SHAPE = re.compile(
    r"(?<!/)\|[^|\n]+(?<!/)\|[^|\n]*\d{4}-\d{2}-\d{2}\s*\|\s*[^|\n]+\s*\|\s*[^|\n]+"
)
_LOOSE_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
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
_PY_DOCSTRING = re.compile(r'^\s*(?:#[^\n]*\n)*\s*[rRuU]?("""|\'\'\')(.*?)\1', re.DOTALL)
_PY_FENCE = re.compile(r"```python[ \t]*\n(.*?)```", re.DOTALL)
_EXPORT_SPLIT = re.compile(r"[|,]")
_ARROW_SPLIT = re.compile(r"→|->")
_ARG_LIST = re.compile(r"\([^)]*\)")
_GROUP_DECL = re.compile(r"^\s*(func|type|var|const|class|def|fn|let|export|pub)\b")
_STRUCT_MEMBER = re.compile(r"^\s+[A-Za-z_*\[\]<>\"']\w*\s*(=|:|\[|\(|$)")
_TYPE_DECL = re.compile(r"\s*type\s+\w+\s+(struct|interface)\b")
_TODO_MARKER = re.compile(r"\b(TODO|FIXME|XXX|HACK|WIP)\b")
# Rules: only the declarations a language requires above the module header are skipped; imports, attributes, and annotations stay code, so a header written after them is still reported.
_DECLARATION_LINE = re.compile(r"^\s*(?:package|namespace|using)\b")
_CODEISH_LINE = re.compile(
    r"(\{\s*$|;\s*$|:=|\breturn\b|\bif\b|\bfor\b|\bwhile\b|\bdefer\b|\bselect\b|\bswitch\b|\bcase\b|\berr\s*!=\s*nil\b|\bfunction\b|=>)"
)
# Rules: SPDX license identifiers are code metadata in every dialect the contract scans; is_directive matches the token case-insensitively.
_SPDX_WORD = "SPDX-License-Identifier:"
_PY_MASKED_TOKENS = frozenset(
    {tokenize.STRING, tokenize.COMMENT}
    | {
        getattr(tokenize, name)
        for name in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END")
        if hasattr(tokenize, name)
    }
)
_HEREDOC_OPEN = re.compile(r"(?<!<)<<(-?)\s*\\?['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?")

# Rules: a marker is recognized only outside a scanned string — the masking pass consumes literal interiors first — so `://` in a URL never opens a comment.
_WORD_BOUNDARY = re.compile(r"[^A-Za-z0-9_]")


def _starts_line(text: str, index: int, allow: tuple[str, ...] = ("@", ":")) -> bool:
    """Judge one position the first token on its line.

    Rules:   Leading whitespace is fine, and so is one statement prefix character (`@REM` in batch, `: REM` in VB) — nothing else may precede a label-style marker.
    """
    if index == 0:
        return True
    line_start = text.rfind("\n", 0, index) + 1
    prefix = text[line_start:index].strip()
    return not prefix or prefix in allow


def _word_marker_at(lowered: str, word: str) -> bool:
    """Judge one word marker a standalone token.

    Rules:   The marker must be followed by a non-word character or the end of the line; `REMARK` is not `REM`.
    """
    if not lowered.startswith(word):
        return False
    rest = lowered[len(word):]
    return not rest or bool(_WORD_BOUNDARY.match(rest))


class BlockMarker(NamedTuple):
    """One block-comment grammar: open marker, close marker, and its flags.

    Rules:   `nested` counts the opener again inside the body; `at_line_start` accepts the opener only at column 0 (Ruby `=begin`, Perl `=pod`); `long_bracket` is unused here and lives on the profile for Lua's variable-equals form.
    """

    open: str
    close: str
    nested: bool = False
    at_line_start: bool = False


class LanguageProfile:
    """Per-language comment grammar for header and content scanning.

    Rules:   Profiles are pure data; shared scan logic decides exemptions so every dialect receives the same contract checks. Line markers are matched only at a code position, word markers with a word boundary, block markers longest-first. A quote character that is also a line marker (VB `'`) is handled by the marker list and left out of `string_quotes`.
    """

    def __init__(
        self,
        name: str,
        line_markers: tuple[str, ...] = (),
        block_markers: tuple[BlockMarker, ...] = (),
        directives: tuple[str, ...] = (),
        word_markers: tuple[str, ...] = (),
        shebang: bool = False,
        string_quotes: tuple[str, ...] = ('"', "'"),
        doubled_quotes: bool = False,
        backtick: str | None = "plain",
        doc_markers: tuple[str, ...] = (),
        prologue: tuple[str, ...] = (),
        long_bracket: str | None = None,
        long_string: str | None = None,
        regex_literals: bool = False,
        triple_quotes: bool = False,
        triple_single_quotes: bool = False,
        raw_strings: bool = False,
        here_strings: bool = False,
        php_mode: bool = False,
        percent_literals: bool = False,
        sigils: bool = False,
        prefixes: tuple[str, ...] | None = None,
    ) -> None:
        self.name = name
        self.line_markers = tuple(sorted(line_markers, key=len, reverse=True))
        self.word_markers = tuple(word.lower() for word in word_markers)
        self.block_markers = tuple(
            sorted(block_markers, key=lambda marker: len(marker.open), reverse=True)
        )
        self.lowered_directives = tuple(d.lower() for d in directives)
        self.shebang = shebang
        self.string_quotes = string_quotes
        self.doubled_quotes = doubled_quotes
        self.backtick = backtick
        self.doc_markers = doc_markers
        self.prologue = prologue
        self.long_bracket = long_bracket
        self.long_string = long_string
        self.regex_literals = regex_literals
        self.triple_quotes = triple_quotes
        self.triple_single_quotes = triple_single_quotes
        self.raw_strings = raw_strings
        self.here_strings = here_strings
        self.php_mode = php_mode
        self.percent_literals = percent_literals
        self.sigils = sigils
        self._init_strip_prefixes(self.line_markers, self.word_markers, self.block_markers, prefixes)

    def _init_strip_prefixes(
        self,
        line_markers: tuple[str, ...],
        word_markers: tuple[str, ...],
        block_markers: tuple[BlockMarker, ...],
        prefixes: tuple[str, ...] | None,
    ) -> None:
        """Build the longest-first prefix list shared by stripping and line starts.

        Rules:   An explicit `prefixes` argument wins; otherwise every line, word, and block marker contributes. Longest-first keeps `//go:` ahead of `//`.
        """
        strip = list(line_markers) + list(word_markers)
        for marker in block_markers:
            strip.extend((marker.open, marker.close))
        self.strip_prefixes = tuple(
            sorted(prefixes if prefixes is not None else strip, key=len, reverse=True)
        )
        self.line_starts = self.strip_prefixes

    def is_comment(self, stripped: str) -> bool:
        """Classify one stripped line.

        Rules:   Callers pass string-literal interiors masked, so a quote inside a template never reaches here.
        """
        if not stripped:
            return False
        if any(stripped.startswith(p) for p in self.line_markers):
            return True
        lowered = stripped[1:] if stripped.startswith("@") else stripped
        lowered = lowered.lower()
        if any(_word_marker_at(lowered, word) for word in self.word_markers):
            return True
        return any(
            stripped.startswith(marker.open) or stripped.startswith(marker.close)
            for marker in self.block_markers
        )

    def strip(self, stripped: str) -> str | None:
        """Return the comment body of one stripped line, or None when it is code.

        Rules:   Prefix match is longest-first so `//go:` strips as a directive comment, not code; word markers match case-insensitively at a word boundary.
        """
        for prefix in self.strip_prefixes:
            if stripped.startswith(prefix):
                return stripped[len(prefix):]
        offset = 1 if stripped.startswith("@") else 0
        lowered = stripped[offset:].lower()
        for word in self.word_markers:
            if _word_marker_at(lowered, word):
                return stripped[offset + len(word):]
        return None

    def is_directive(self, stripped: str) -> bool:
        """Judge a stripped line a per-language tool directive.

        Rules:   A shebang line counts for shell profiles; directive matches are case-insensitive.
        """
        if self.shebang and stripped.startswith("#!"):
            return True
        lowered = stripped.lower()
        if _SPDX_WORD.lower() in lowered:
            return True
        return any(lowered.startswith(d) for d in self.lowered_directives)

    def line_marker_at(self, text: str, index: int) -> str | None:
        """Return the line-comment marker starting at one position, if any.

        Rules:   The marker must sit at a code position — after whitespace or one of the inline prefix characters — so `https://` and `a//b` stay code; a `--` followed by `>` is the Haskell operator; batch `::` and `REM` must be the first token on their line.
        """
        previous = text[index - 1] if index else ""
        if previous and (previous.isalnum() or previous in "_:"):
            return None
        for marker in self.line_markers:
            if not text.startswith(marker, index):
                continue
            if previous in "/":
                continue
            if marker == "#" and previous in "${":
                continue
            if marker == "#" and self.php_mode and text.startswith("#[", index):
                continue
            if marker == ";" and previous == "\\":
                continue
            if marker == "--" and text.startswith("-->", index):
                continue
            if marker == "::" and not _starts_line(text, index):
                continue
            return marker
        lowered = text[index:index + 16].lower()
        for word in self.word_markers:
            if not lowered.startswith(word) or not _starts_line(text, index):
                continue
            if not _word_marker_at(lowered, word):
                continue
            return text[index:index + len(word)]
        return None


def _profile(name: str, line_markers=(), block_markers=(), **kwargs) -> LanguageProfile:
    """Build one profile.

    Rules:   Keep directive lists conservative — a missed directive gets reported as prose rather than wrongly exempt.
    """
    return LanguageProfile(name, line_markers, block_markers, **kwargs)


_C_BLOCK = BlockMarker("/*", "*/")
_NESTED_C_BLOCK = BlockMarker("/*", "*/", nested=True)
_C_DIRECTIVES = (
    "#include",
    "#define",
    "#undef",
    "#pragma",
    "#if",
    "#ifdef",
    "#ifndef",
    "#elif",
    "#else",
    "#endif",
    "#error",
    "#line",
    "#warning",
    "// NOLINT",
    "/* NOLINT",
    "// clang-format",
    "/* clang-format",
    "// IWYU",
)
_JS_DIRECTIVES = (
    "// eslint",
    "/* eslint",
    "// @ts-",
    "/* jshint",
    "/* global",
    "/*!",
    "//# sourceurl",
    "//# sourceMappingURL",
)
_TS_DIRECTIVES = _JS_DIRECTIVES + ("/// <reference", "// @ts-")
_DOC_SLASHES = ("///", "//!")
_BARE_DIRECTIVES = (
    "//noinspection",
    "// @formatter:off",
    "// @formatter:on",
    "// NOLINT",
    "/* NOLINT",
    "// prettier-ignore",
)

_profiles: dict[str, LanguageProfile] = {}


def _register(suffixes: tuple[str, ...], profile: LanguageProfile) -> None:
    """Bind one profile to every suffix in its family.

    Rules:   One table entry per family keeps the suffix list and the profile map from drifting.
    """
    for suffix in suffixes:
        _profiles[suffix] = profile


_register(
    (".go",),
    _profile(
        "go",
        ("//",),
        (_C_BLOCK,),
        directives=("//go:", "//export ", "//sys ", "//line ", "//cgo:", "// +build", "//nolint", "//lint:", "// Code generated"),
        prefixes=("//", "/*", "*/"),
    ),
)
_register(
    (".py",),
    _profile(
        "python",
        ("#",),
        directives=("# type:", "# noqa", "# pylint:", "# ruff:", "# yapf:", "# fmt:", "# flake8:", "# isort:", "# mypy:", "# -*-", "# pragma:"),
        prefixes=("#",),
    ),
)
_register(
    (".js", ".jsx", ".mjs", ".cjs"),
    _profile(
        "javascript",
        ("//",),
        (_C_BLOCK,),
        directives=_JS_DIRECTIVES,
        backtick="js",
        regex_literals=True,
        prologue=(),
        prefixes=("//", "/*", "*/"),
    ),
)
_register(
    (".ts", ".tsx"),
    _profile(
        "typescript",
        ("//",),
        (_C_BLOCK,),
        directives=_TS_DIRECTIVES,
        backtick="js",
        regex_literals=True,
        prefixes=("//", "/*", "*/"),
    ),
)
_register(
    (".rs",),
    _profile(
        "rust",
        ("//",),
        (_NESTED_C_BLOCK,),
        directives=("/// ", "//! ", "#![", "#["),
        doc_markers=_DOC_SLASHES,
        backtick="plain",
        prefixes=("//", "/*", "*/"),
    ),
)
_register(
    (".sh", ".bash", ".zsh"),
    _profile(
        "shell",
        ("#",),
        directives=("# shellcheck",),
        shebang=True,
        backtick="plain",
        prefixes=("#",),
    ),
)
_register(
    (".css",),
    _profile("css", (), (_C_BLOCK,), prefixes=("/*", "*/")),
)
_register(
    (".html", ".htm"),
    _profile("html", (), (BlockMarker("<!--", "-->"),), prefixes=("<!--", "-->")),
)
_register(
    (".vue",),
    _profile("vue", (), (BlockMarker("<!--", "-->"),), prefixes=("<!--", "-->")),
)
_register(
    (".svelte",),
    _profile("svelte", (), (BlockMarker("<!--", "-->"),), prefixes=("<!--", "-->")),
)
_register(
    (".astro",),
    _profile("astro", (), (BlockMarker("<!--", "-->"),), prefixes=("<!--", "-->")),
)
_register(
    (".c", ".h"),
    _profile("c", ("//",), (_C_BLOCK,), directives=_C_DIRECTIVES, prefixes=("//", "/*", "*/")),
)
_register(
    (".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx"),
    _profile(
        "cpp",
        ("//",),
        (_C_BLOCK,),
        directives=_C_DIRECTIVES,
        raw_strings=True,
        prefixes=("//", "/*", "*/"),
    ),
)
_register(
    (".m", ".mm"),
    _profile("objective-c", ("//",), (_C_BLOCK,), directives=_C_DIRECTIVES, prefixes=("//", "/*", "*/")),
)
_register(
    (".cs",),
    _profile(
        "csharp",
        ("//",),
        (_C_BLOCK,),
        directives=_BARE_DIRECTIVES + ("//#region", "//#endregion", "/// <"),
        doc_markers=("///",),
        triple_quotes=True,
        prefixes=("//", "/*", "*/"),
    ),
)
_register(
    (".java",),
    _profile(
        "java",
        ("//",),
        (_C_BLOCK,),
        directives=_BARE_DIRECTIVES,
        triple_quotes=True,
        prefixes=("//", "/*", "*/"),
    ),
)
_register(
    (".kt", ".kts"),
    _profile(
        "kotlin",
        ("//",),
        (_NESTED_C_BLOCK,),
        directives=_BARE_DIRECTIVES + ("// language=",),
        triple_quotes=True,
        prefixes=("//", "/*", "*/"),
    ),
)
_register(
    (".scala", ".sc"),
    _profile("scala", ("//",), (_NESTED_C_BLOCK,), directives=_BARE_DIRECTIVES, triple_quotes=True, prefixes=("//", "/*", "*/")),
)
_register(
    (".groovy", ".gradle"),
    _profile(
        "groovy",
        ("//",),
        (_C_BLOCK,),
        directives=_BARE_DIRECTIVES,
        triple_single_quotes=True,
        prefixes=("//", "/*", "*/"),
    ),
)
_register(
    (".swift",),
    _profile(
        "swift",
        ("//",),
        (_NESTED_C_BLOCK,),
        directives=_BARE_DIRECTIVES,
        doc_markers=("///",),
        triple_quotes=True,
        prefixes=("//", "/*", "*/"),
    ),
)
_register(
    (".dart",),
    _profile(
        "dart",
        ("//",),
        (_NESTED_C_BLOCK,),
        directives=_BARE_DIRECTIVES,
        doc_markers=("///",),
        triple_quotes=True,
        prefixes=("//", "/*", "*/"),
    ),
)
_register(
    (".zig",),
    _profile("zig", ("//",), directives=(), doc_markers=_DOC_SLASHES, prefixes=("//",)),
)
_register(
    (".d",),
    _profile(
        "d",
        ("//",),
        (_C_BLOCK, BlockMarker("/+", "+/", nested=True)),
        doc_markers=("///", "/++"),
        prefixes=("//", "/*", "*/", "/+", "+/"),
    ),
)
_register(
    (".sol",),
    _profile(
        "solidity",
        ("//",),
        (_C_BLOCK,),
        doc_markers=("///",),
        prefixes=("//", "/*", "*/"),
    ),
)
_register(
    (".php", ".phtml"),
    _profile(
        "php",
        ("//", "#"),
        (_C_BLOCK,),
        php_mode=True,
        prologue=("<?php", "<?"),
        prefixes=("//", "#", "/*", "*/"),
    ),
)
_register(
    (".rb", ".rake", ".gemspec", ".ru"),
    _profile(
        "ruby",
        ("#",),
        (BlockMarker("=begin", "=end", at_line_start=True),),
        directives=(
            "# frozen_string_literal:",
            "# encoding:",
            "# rubocop:",
            "# typed:",
            "# :nodoc:",
            "# NOLINT",
            "# vim:",
            "# -*-",
        ),
        regex_literals=True,
        percent_literals=True,
        prefixes=("#", "=begin", "=end"),
    ),
)
_register(
    (".pl", ".pm"),
    _profile(
        "perl",
        ("#",),
        (BlockMarker("=pod", "=cut", at_line_start=True),),
        directives=("# no critic", "# NOLINT", "# vim:", "# -*-"),
        prefixes=("#", "=pod", "=cut"),
    ),
)
_register(
    (".lua",),
    _profile(
        "lua",
        ("--",),
        long_bracket="--",
        long_string="",
        prefixes=("--",),
    ),
)
_register(
    (".hs", ".lhs"),
    _profile(
        "haskell",
        ("--",),
        (BlockMarker("{-", "-}", nested=True),),
        directives=("{-#", "{- |", "-- |"),
        string_quotes=('"',),
        prefixes=("--", "{-", "-}"),
    ),
)
_register(
    (".ex", ".exs"),
    _profile("elixir", ("#",), triple_quotes=True, sigils=True, prefixes=("#",)),
)
_register(
    (".erl", ".hrl"),
    _profile("erlang", ("%",), prefixes=("%",)),
)
_register(
    (".clj", ".cljs", ".cljc"),
    _profile("clojure", (";",), string_quotes=('"',), prefixes=(";",)),
)
_register(
    (".sql",),
    _profile("sql", ("--",), (_C_BLOCK,), doubled_quotes=True, prefixes=("--", "/*", "*/")),
)
_register(
    (".ps1", ".psm1", ".psd1"),
    _profile(
        "powershell",
        ("#",),
        (BlockMarker("<#", "#>"),),
        here_strings=True,
        prefixes=("#", "<#", "#>"),
    ),
)
_register(
    (".bat", ".cmd"),
    _profile(
        "batch",
        ("::",),
        word_markers=("rem",),
        string_quotes=(),
        prologue=("@echo off",),
        prefixes=("::", "rem",),
    ),
)
_register(
    (".vb", ".vbs", ".frm"),
    _profile(
        "vb",
        ("'",),
        word_markers=("rem",),
        string_quotes=('"',),
        doubled_quotes=True,
        prefixes=("'", "rem"),
    ),
)
_register(
    (".fs", ".fsi", ".fsx"),
    _profile(
        "fsharp",
        ("//",),
        (BlockMarker("(*", "*)", nested=True),),
        directives=("#if", "#else", "#endif", "#load", "#r ", "#light", "#nowarn"),
        string_quotes=('"',),
        prefixes=("//", "(*", "*)"),
    ),
)
_register(
    (".ml", ".mli"),
    _profile(
        "ocaml",
        (),
        (BlockMarker("(*", "*)", nested=True),),
        string_quotes=('"',),
        prefixes=("(*", "*)"),
    ),
)
_register(
    (".r",),
    _profile("r", ("#",),  prefixes=("#",)),
)
_register(
    (".jl",),
    _profile("julia", ("#",), (BlockMarker("#=", "=#", nested=True),), triple_quotes=True, prefixes=("#", "#=", "=#")),
)
_register(
    (".nim",),
    _profile(
        "nim",
        ("#",),
        (BlockMarker("#[", "]#", nested=True),),
        doc_markers=("##",),
        prefixes=("#", "#[", "]#"),
    ),
)
_register(
    (".cr",),
    _profile("crystal", ("#",),  prefixes=("#",)),
)
_register(
    (".tf", ".tfvars", ".hcl"),
    _profile("hcl", ("#", "//"), (_C_BLOCK,), prefixes=("#", "//", "/*", "*/")),
)
_register(
    (".f", ".for", ".f90", ".f95", ".f03", ".f08"),
    _profile("fortran", ("!",), prefixes=("!",)),
)
_register(
    (".elm",),
    _profile("elm", ("--",), (BlockMarker("{-", "-}", nested=True),), prefixes=("--", "{-", "-}")),
)


COMPOUND_SUFFIXES = (".blade.php",)


def suffix_for(name: str) -> str:
    """Return the scanned suffix for one file name.

    Rules:   A compound suffix wins over its last component (`x.blade.php` is a Blade template, never PHP); matching is case-insensitive.
    """
    lowered = name.lower()
    for suffix in COMPOUND_SUFFIXES:
        if lowered.endswith(suffix):
            return suffix
    return Path(lowered).suffix


_register(
    (".blade.php",),
    _profile("blade", (), (BlockMarker("{{--", "--}}"),), prefixes=("{{--", "--}}")),
)
_register(
    (".j2", ".jinja2", ".twig", ".volt"),
    _profile("jinja", (), (BlockMarker("{#", "#}"),), prefixes=("{#", "#}")),
)
_register(
    (".erb", ".ejs"),
    _profile("erb", (), (BlockMarker("<%#", "%>"),), prefixes=("<%#", "%>")),
)
_register(
    (".hbs", ".mustache"),
    _profile("handlebars", (), (BlockMarker("{{!", "}}"),), prefixes=("{{!", "}}")),
)
_register(
    (".cshtml", ".razor"),
    _profile("razor", (), (BlockMarker("@*", "*@"),), prefixes=("@*", "*@")),
)

EXPLICIT_SUFFIXES = frozenset(_profiles)


def profile_for(path: Path) -> LanguageProfile:
    """Return the language profile for one scanned suffix.

    Rules:   Suffix matching is case-insensitive (`.R`, `.C`) and compound-aware (`.blade.php`); unknown suffixes get a generic profile so they never bypass the header check.
    """
    suffix = suffix_for(path.name)
    return _profiles.get(suffix) or _profile(
        suffix.lstrip("."), ("#", "//"), (_C_BLOCK,)
    )
