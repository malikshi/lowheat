"""codedna_spec.py — Shared contract constants, regexes, and per-language comment profiles.

exports: SOURCE_SUFFIXES | TOOL_OWNED_DIRS | DEFAULT_IGNORED_DIRS | L1_FIELDS | L2_FIELDS | REQUIRED_L1 | AGENT_HISTORY_LIMIT | SUMMARY_WORD_LIMIT | ARROW | EM_DASH | LanguageProfile | profile_for
used_by: .agents/skills/agents-contract/scripts/codedna_masking.py → LanguageProfile and masking regexes [cascade]
used_by: .agents/skills/agents-contract/scripts/codedna_headers.py → profiles and L1 constants [cascade]
used_by: .agents/skills/agents-contract/scripts/codedna_content.py → limits and label regexes [cascade]
used_by: .agents/skills/agents-contract/scripts/codedna_check.py → re-exports for tests and main [cascade]
rules:   Constants are single sources of truth — a consumer module never repeats them. A profile change reaches every dialect at once, so the shared scan logic stays free of per-language branches. SPDX lines are exempt in every dialect the contract scans.
agent:   unknown | xai | 2026-10-14 | 01a1373b-7fa0-7851-ae9d-4cd27c951a27 | split out of codedna_check.py verbatim: constants, regexes, and the 15 suffix profiles unchanged, and the _proflies typo is gone.
"""
from __future__ import annotations

import re
import tokenize
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

_FIELD_LINE = re.compile(
    r"^\s*(?://+|#+|\*+|!|<!--|\*/|/\*)?\s*(exports|used_by|related|rules|agent|message):\s*(.*)$"
)
_L2_LABEL_LINE = re.compile(
    r"^\s*(?://+|#+|\*+|!|<!--|\*/|/\*)?\s*(Rules|message):\s*(.*)$"
)
_DOC_LABEL = re.compile(r"^\s*(exports|used_by|related|rules|Rules|agent|message):\s*(.*)$")
_COMMENT_LABEL = re.compile(r"^#\s*(Rules|message):")
_AGENT_SHAPE = re.compile(r"(?<!/)\|[^|\n]*(?<!/)\|[^|\n]*\d{4}-\d{2}-\d{2}")
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
    ".py": ("# type:", "# noqa", "# pylint:", "# ruff:", "# yapf:", "# fmt:", "# flake8:", "# isort:", "# mypy:", "# -*-", "# pragma:"),
    ".js": ("// eslint", "/* eslint", "// @ts-", "/* jshint", "/* global", "/*!", "//# sourceurl"),
    ".ts": ("// eslint", "/* eslint", "/// <reference", "// @ts-", "/* jshint", "/* global", "/*!"),
    ".rs": ("/// ", "//! ", "#![", "#["),
    ".sh": ("# shellcheck",),
    ".bash": ("# shellcheck",),
    ".zsh": ("# shellcheck",),
}
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
        if _SPDX_WORD.lower() in lowered:
            return True
        return any(lowered.startswith(d) for d in self.lowered_directives)


def _profile(name: str, starts, directives=(), shebang=False, prefixes=None) -> LanguageProfile:
    """Build one profile.

    Rules:   Keep directive lists conservative — a missed directive gets reported as prose rather than wrongly exempt.
    """
    return LanguageProfile(name, starts, directives, shebang, prefixes)


_profiles: dict[str, LanguageProfile] = {
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
_profiles[".mjs"] = _profiles[".js"]
_profiles[".cjs"] = _profiles[".js"]


def profile_for(path: Path) -> LanguageProfile:
    """Return the language profile for one scanned suffix.

    Rules:   Unknown suffixes get a generic profile so they never bypass the header check.
    """
    return _profiles.get(path.suffix) or _profile(path.suffix.lstrip("."), ("#", "//"))
