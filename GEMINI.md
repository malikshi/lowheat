# Gemini Instructions

This file is the **Gemini adapter**. It records only Gemini-specific deltas and
must not duplicate the cross-agent contract in `AGENTS.md`. For the operating
contract, plugins, skills, RTK, CodeGraph, source repositories, and writing rules,
read `AGENTS.md` first.

This project operates with Gemini as one of its development agents. Gemini may not
have Claude Code or Codex-specific tools, hooks, MCP servers, or plugins, but the
repository rules still apply unless a capability is unavailable.

The behavior contract adapted from `https://github.com/jbarbier/CLAUDE.md` lives
in `AGENTS.md`. Follow that contract through the Gemini tool surface: complete real
fixes, separate reasoning from deterministic checks, verify before completion, use
the confusion protocol for high-stakes ambiguity, preserve safety boundaries, and
report restart needs;
plus the Karpathy behavioral guidelines adopted from
`https://github.com/multica-ai/andrej-karpathy-skills`: think before coding,
simplicity first, surgical changes, and goal-driven execution.

**Do not replace this adapter with the upstream template, and do not symlink the
agent surfaces** unless the project owner explicitly requests that migration.

## Material differences from AGENTS.md

Everything in `AGENTS.md` applies to Gemini unless a capability is unavailable. This
section lists Gemini-specific deltas only.

### Tools

Gemini has access to shell commands and file read/write/edit. It does **not** have
the `Skill` tool, the `Agent` tool, CodeGraph MCP tools, or the Claude Code hook
surface. Use the Bash tool for shell commands and the Read/Write/Edit tools for
file operations.

### Code Navigation

This project has a CodeGraph index (tree-sitter parsed knowledge graph) when used
from Claude Code or Codex. Gemini does **not** have direct access to CodeGraph MCP
tools. Use standard search instead:

| Task | Command |
|---|---|
| Find symbol definition | `rg "func FunctionName" --type go` or `rg "type StructName" --type go` |
| Find callers | `rg "FunctionName(" --type go` |
| Find file | `find . -name "*.go" \| xargs rg "pattern"` |
| Check imports | `rg "import" path/to/file.go` |
| Find Python symbol | `rg "def function_name" --type py` or `rg "class ClassName" --type py` |
| Find Python callers | `rg "function_name(" --type py` |

### CodeDNA — manual contract

Gemini does **not** run the Claude Code Stop hook. The CodeDNA session-ledger
contract is a **manual responsibility** for Gemini:

- Treat `.codedna` as the repo-local source map and session ledger.
- When tracked or untracked project files are changed, update `.codedna` with an
  `agent_sessions` entry before the final response. Required fields: `agent`,
  `provider`, `date`, `session_id`, `task`, `changed`, `visited`, `message`.
- If the `codedna` CLI is available and source files were changed, run the relevant
  CodeDNA validation described in `AGENTS.md`. If it is unavailable, update
  `.codedna` manually and report that CLI validation could not run.

### CodeDNA header format (Python)

The Python module-header and L2 function-annotation formats live in `AGENTS.md`
under "### CodeDNA header format (Python)". Edit them there; do not duplicate them
in this adapter.

## Agent Style

For technical prose, follow the `Agent Style` section in `AGENTS.md`. Gemini may
not follow Claude `@path` imports, so read `.agent-style/RULES.md` before writing
or editing substantial prose. When asked "is agent-style active?", use the
self-verification response (version string and the 21-rule list) defined in
`AGENTS.md` under "## Agent Style". Do not duplicate the writing defaults or the
rule list here.

Dyslexia-friendly output formatting is available on request (opt-in; does not
change default output). Triggers: `/i-have-dyslexia`, "dyslexia fit", "fit". Gemini
has no Skill surface, so read the pinned rules directly at
`.agents/dyslexia/i-have-dyslexia.md`. Canonical guidance and precedence live in
`AGENTS.md` under "### Dyslexia-Friendly Output (opt-in)". Do not duplicate the
rules here.

## Book-Derived Guidance

For architecture, refactoring, legacy-code, production reliability, DDD,
data-intensive design, enterprise patterns, or code-quality decisions, read
`.agents/skills/agent-rules-books/SKILL.md`. Load only the relevant book rules:
`references/mini/<rule-set>.mini.md` first, `references/nano/` only for tight
context, and `references/full/<rule-set>.md` only when mini is insufficient.

## Command Style

- Prefer RTK-wrapped commands when `rtk` is available: `rtk git status`,
  `rtk rg "pattern" path`, `rtk grep "pattern" path`, and `rtk pytest -q`.
- Use standard shell commands (`git status`, `rg "pattern" path`, `pytest -q`)
  only when RTK is unavailable, raw output is needed, or RTK cannot run the
  command.
- Avoid compound `cd <path> && <command>` chains. Use `git -C <path> ...` or
  pass the target path as an argument.
- **Never run `git commit` or `git push` without explicit user approval.**

### Grep is lossy by design

`rtk grep` and `rtk rg` group matches by file, strip whitespace, and truncate
lines. That is correct for surveys, but it loses exact `line:content`. When you
need a precise line number or the full matching line (for example, to feed an
edit), use the shell `grep -n` directly rather than `rtk grep`.

## Verification

Before claiming completion, run the smallest checks that prove the change:

- For config or docs edits, run syntax checks or targeted grep checks.
- For Python source edits, run CodeDNA validation and the relevant `rtk pytest`
  targets.
- For Go source edits, run `go build ./...` and `go vet ./...`.
- For browser-facing work, verify with a real browser when possible.
- Report any check that could not run and why.

## Tooling Reference

These tools are used by the primary Claude Code / Codex workflow. Gemini may not
have direct access to all of them. Use a tool when it is available in the current
session; otherwise treat it as project context and use the fallback noted in this
file.

| Tool | Purpose |
|---|---|
| RTK | CLI proxy that wraps commands for token efficiency; use it when installed |
| CodeGraph | MCP server providing symbol/edge/file knowledge graph; **unavailable in Gemini**, use `rg`/`find` fallback above |
| CodeDNA | Source map and session ledger (`.codedna`); update the ledger even without hooks |

## Source Repositories

| Source | Purpose |
|---|---|
| `https://github.com/rtk-ai/rtk` | RTK CLI and command reference |
| `https://github.com/colbymchenry/codegraph` | CodeGraph MCP server |
| `https://github.com/Larens94/codedna` | CodeDNA source map tool |
| `https://github.com/ciembor/agent-rules-books` | Book-derived engineering rules in `.agents/skills/agent-rules-books` |
| `https://github.com/yzhao062/agent-style` | Pinned prose rules in `.agent-style/` |
| `https://github.com/jbarbier/CLAUDE.md` | Operating-contract influence merged into `AGENTS.md` |
| `https://github.com/multica-ai/andrej-karpathy-skills` | Karpathy behavioral guidelines |
