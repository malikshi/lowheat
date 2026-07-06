# CommandCode Instructions

This file is the **CommandCode adapter**. It records only CommandCode-specific
deltas and must not duplicate the cross-agent contract in `AGENTS.md`. For the
operating contract, plugins, skills, RTK, CodeGraph, source repositories, and
writing rules, read `AGENTS.md` first.

This project operates with CommandCode as one of its development agents.
CommandCode reads `~/.commandcode/AGENTS.md` as always-on memory for every
session. When used with this repo, the repository rules below apply through the
CommandCode tool surface.

**Do not replace this adapter with the upstream template, and do not symlink the
agent surfaces** unless the project owner explicitly requests that migration.

## Material differences from AGENTS.md

Everything in `AGENTS.md` applies to CommandCode unless a capability is
unavailable. This section lists CommandCode-specific deltas only.

### Tools

CommandCode has access to shell commands and file read/write/edit. It does
**not** have the `Skill` tool, the `Agent` tool, CodeGraph MCP tools, or the
Claude Code hook surface. It also does not have the `Grep` / `Glob` tools — use
shell `grep` / `rg` directly.

Use the native file and search tools over `rtk read` / `rtk grep`; they preserve
exact line numbers and content.

### Command Style

Always prefer RTK-wrapped shell commands over raw equivalents.

This repository does **not** have auto-rewrite for CommandCode yet — the
CommandCode `PreToolUse` hook to auto-prefix raw commands with `rtk` is not yet
implemented upstream. **Prefix commands yourself** per the tiers below.

Use raw commands when output is:
- A **diff or patch** you will apply, or a hunk you will edit.
- **Structured output you will parse** — JSON, `--format=…`, anything piped to another tool.
- **Small** (roughly 30 lines or fewer).
- **Secrets or exact config**.
- A file you intend to edit — use the native Read tool.

Otherwise prefix with `rtk`:

| Category | Through RTK? |
|---|---|
| `git status`, `ls`, `tree`, `find`, `docker ps`, `kubectl get pods`, `pip list`, `pnpm list` | yes |
| Big test/build runs — `rtk cargo test`, `rtk pytest`, `rtk err <cmd>` | yes (plain mode keeps failures) |
| Logs — `rtk log app.log` static dumps | yes |
| `git diff`, `git show`, diffs you will apply | run raw |
| `--format json` or parsed output | run raw |
| Files you will edit | use Read tool |
| `-f` / `tail -f` / streaming follow | run raw (RTK buffers, can hang) |

### Grep is lossy by design

`rtk grep` and `rtk rg` group matches by file, strip whitespace, and truncate
lines. That is correct for surveys ("which files mention X"), but it loses exact
`line:content`. When you need a precise line number or the full matching line
(for example, to feed an edit), use shell `grep -n` directly.

### CodeDNA — manual contract

CommandCode does **not** run the Claude Code Stop hook. The CodeDNA
session-ledger contract is a **manual responsibility** for CommandCode:

- Treat `.codedna` as the repo-local source map and session ledger.
- When tracked or untracked project files are changed, update `.codedna` with an
  `agent_sessions` entry before the final response. Required fields: `agent`,
  `provider`, `date`, `session_id`, `task`, `changed`, `visited`, `message`.
- If the `codedna` CLI is available and source files were changed, run the
  relevant CodeDNA validation described in `AGENTS.md`. If it is unavailable,
  update `.codedna` manually and report that CLI validation could not run.

### CodeDNA header format (Python)

```python
"""filename.py — purpose ≤15 words.

exports: function(arg) -> type
used_by: caller.py → caller_fn
rules:   constraint the agent must respect
agent:   model-id | provider | YYYY-MM-DD | session_id | what you implemented
         message: "<open hypothesis or observation for the next agent>"
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

For technical prose, follow the `Agent Style` section in `AGENTS.md`.

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

## Harness safety

- **Don't wrap streaming/follow output** (`-f`, `tail-f`, growing logs): RTK
  buffers output, so it can hang the command.
- **Pass/fail verdicts:** trust the command's raw exit code. If unsure whether
  `rtk` preserved it, run raw, or use `rtk proxy <cmd>`.
- **Avoid lossy modes by default** — `--ultra-compact`, and `rtk smart` are for
  skimming only, never the default. The signal-preserving plain `rtk <cmd>` is
  correct.
- When unsure, start raw.

## Verification

Before claiming completion, run the smallest checks that prove the change:

- For config or docs edits, run syntax checks or targeted grep checks.
- For Python source edits, run CodeDNA validation and the relevant `pytest`
  targets.
- For Go source edits, run `go build ./...` and `go vet ./...`.
- For browser-facing work, verify with a real browser when possible.
- Report any check that could not run and why.

## Tooling Reference

These tools are used by the primary Claude Code / Codex workflow. CommandCode
may not have direct access to all of them. Use a tool when it is available in
the current session; otherwise treat it as project context and use the fallback
noted in this file.

| Tool | Purpose |
|---|---|
| RTK | CLI proxy that wraps commands for token efficiency; use it when installed |
| CodeGraph | MCP server providing symbol/edge/file knowledge graph; **unavailable in CommandCode**, use `rg`/`find` fallback |
| CodeDNA | Source map and session ledger (`.codedna`); update the ledger even without hooks |

## Source Repositories

| Source | Purpose |
|---|---|
| `https://github.com/rtk-ai/rtk` | RTK CLI and command reference |
| `https://github.com/Coding-Dev-Tools/rtk-command-code` | RTK integration for Command Code CLI |
| `https://github.com/Larens94/codedna` | CodeDNA source map tool |
| `https://github.com/ciembor/agent-rules-books` | Book-derived engineering rules in `.agents/skills/agent-rules-books` |
| `https://github.com/yzhao062/agent-style` | Pinned prose rules in `.agent-style/` |
| `https://github.com/jbarbier/CLAUDE.md` | Operating-contract influence merged into `AGENTS.md` |
| `https://github.com/multica-ai/andrej-karpathy-skills` | Karpathy behavioral guidelines |
