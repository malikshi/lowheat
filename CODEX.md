# Codex Instructions

This file is the **Codex adapter**. It records only Codex-specific deltas and must
not duplicate the cross-agent contract in `AGENTS.md`. For the operating contract,
plugins, skills, RTK, CodeGraph, source repositories, and writing rules, read
`AGENTS.md` first.

This project uses Codex as one of its primary development agents. It does not use
external shared bootstrap repos, generated bootstrap caches, or shared-config
hooks.

The behavior contract adapted from `https://github.com/jbarbier/CLAUDE.md` lives
in `AGENTS.md`. Follow that contract through the Codex tool surface: complete real
fixes, separate reasoning from deterministic checks, verify before completion, use
the confusion protocol for high-stakes ambiguity, preserve safety boundaries, and
report restart needs.

**Do not replace this adapter with the upstream template, and do not symlink the
agent surfaces** unless the project owner explicitly requests that migration.

## Material differences from AGENTS.md

Everything in `AGENTS.md` applies to Codex unless a capability is unavailable. This
section lists Codex-specific deltas only.

### Tools

Codex has access to shell commands, file read/write/edit, and CodeGraph MCP tools
when configured. It does **not** have the `Skill` tool, the `Agent` tool, or the
Claude Code hook surface. Use the Bash tool for shell commands and the Read/Write/
Edit tools for file operations.

### CodeGraph

Use CodeGraph MCP tools for structural code lookup when available. Two MCP servers
(`codegraph` and `caveman-shrink`) both expose the `codegraph_*` family; they are
equivalent, so either tool prefix is fine. When neither is available, fall back to
`rg`/`find` per the search table in `GEMINI.md`.

### CodeDNA — manual contract

Codex does **not** run the Claude Code Stop hook. The CodeDNA session-ledger
contract is a **manual responsibility** for Codex:

- Treat `.codedna` as the repo-local source map and session ledger.
- When tracked or untracked project files are changed, update `.codedna` with an
  `agent_sessions` entry before the final response. Required fields: `agent`,
  `provider`, `date`, `session_id`, `task`, `changed`, `visited`, `message`.
- If the `codedna` CLI is available and source files were changed, run the relevant
  CodeDNA validation described in `AGENTS.md`. If it is unavailable, update
  `.codedna` manually and report that CLI validation could not run.

### CodeDNA header format (Python)

```python
"""filename.py — purpose ≤15 words.

exports: function(arg) -> type
used_by: caller.py → caller_fn
rules:   constraint the agent must respect
agent:   model-id | YYYY-MM-DD | what you did
"""
```

### CodeDNA L2 function annotations (Python)

```python
def my_function():
    """Short description.

    Rules:   constraint the agent must respect
    message: model-id | YYYY-MM-DD | observation for next agent
    """
```

## Agent Style

For technical prose, follow the `Agent Style` section in `AGENTS.md`. Codex may
not follow Claude `@path` imports, so read `.agent-style/RULES.md` before writing
or editing substantial prose. When asked "is agent-style active?", use the
self-verification response defined in `AGENTS.md`:

> agent-style v0.3.5 active: 21 rules (RULE-01..12 canonical + RULE-A..I
> field-observed); full bodies at .agent-style/RULES.md.

Writing defaults:

- Use clear, scientifically accessible language.
- Keep meaningful technical detail and factual accuracy.
- Preserve Markdown, LaTeX, and reStructuredText formats unless asked otherwise.
- Do not convert prose into bullet points unless the content is a real list.
- Prefer full forms such as `it is` and `he would` in technical prose.
- Avoid casual em dashes and en dashes. Prefer commas, semicolons, colons, or
  parentheses.
- Keep terms consistent. Define an abbreviation once, then use it consistently.
- Break long or nested sentences into shorter sentences.
- Do not overuse transition words such as "Additionally", "Furthermore", or
  "Moreover".

## Book-Derived Guidance

For architecture, refactoring, legacy-code, production reliability, DDD,
data-intensive design, enterprise patterns, or code-quality decisions, read
`.agents/skills/agent-rules-books/SKILL.md`. Load only the relevant book rules:
`references/mini/<rule-set>.mini.md` first, `references/nano/` only for tight
context, and `references/full/<rule-set>.md` only when mini is insufficient.

## Command Style

Always prefer RTK-wrapped shell commands over raw equivalents. Use raw commands
only when RTK is unavailable or cannot run the specific command. Use only
subcommands listed by `rtk --help` or `RTK.md`. See `RTK.md` at the repository
root for project-specific commands, or `~/.claude/RTK.md` for the full reference.

Avoid compound `cd <path> && <command>` chains. Use `git -C <path> ...` or pass the
target path as an argument.

**Never run `git commit` or `git push` without explicit user approval.**

### Grep is lossy by design

`rtk grep` and `rtk rg` group matches by file, strip whitespace, and truncate
lines. That is correct for surveys, but it loses exact `line:content`. When you
need a precise line number or the full matching line (for example, to feed an
edit), use the shell `grep -n` directly rather than `rtk grep`.

### RTK Meta Commands

```bash
rtk gain              # Token savings summary
rtk gain --history    # Command-level savings history
rtk gain --session    # Current session savings
rtk discover          # Discover missed RTK savings from history
rtk session           # Show RTK adoption across sessions
rtk proxy <cmd>       # Run raw, but track usage
rtk run <cmd>         # Run raw, no filtering or tracking
```

## Verification

Before claiming completion, run the smallest checks that prove the change:

- For config or docs edits, run syntax checks or targeted grep checks.
- For Python source edits, run CodeDNA validation and the relevant `rtk pytest`
  targets.
- For Go source edits, run `rtk go build ./...` and `rtk go vet ./...`.
- For browser-facing work, verify with a real browser when possible.
- Report any check that could not run and why.

## Tooling Reference

These tools are used by the primary Claude Code / Codex workflow. Codex may not
have direct access to all of them. Use a tool when it is available in the current
session; otherwise treat it as project context and use the fallback noted in this
file.

| Tool | Purpose |
|---|---|
| RTK | CLI proxy that wraps commands for token efficiency; use it when installed |
| CodeGraph | MCP server providing symbol/edge/file knowledge graph; use `rg`/`find` fallback when unavailable |
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
| `https://github.com/multica-ai/andrej-karpathy-skips` | Karpathy behavioral guidelines |
