# Claude Code Instructions

This file is the **Claude Code adapter**. It records only Claude-specific deltas
and must not duplicate the cross-agent contract in `AGENTS.md`. For the operating
contract, plugins, skills, RTK, CodeGraph, source repositories, and writing rules,
read `AGENTS.md` first.

This project uses Claude Code directly. It does not use external shared bootstrap
repos, generated bootstrap caches, or shared-config user hooks.

The operating contract in `AGENTS.md` includes the selected guidance from
`https://github.com/jbarbier/CLAUDE.md`: complete real fixes, separate reasoning
from deterministic checks, verify before completion, use the confusion protocol
for high-stakes ambiguity, preserve safety boundaries, and report restart needs;
plus the Karpathy behavioral guidelines adopted from
`https://github.com/multica-ai/andrej-karpathy-skills`: think before coding,
simplicity first, surgical changes, and goal-driven execution.

**Do not replace this adapter with the upstream template, and do not symlink
`AGENTS.md` and `GEMINI.md`** unless the project owner explicitly requests that
migration.

## Material differences from AGENTS.md

The following entries are specific to the Claude Code surface and do not appear in
`AGENTS.md`. Everything else is inherited from that file.

### Claude Code Surfaces

- Project Claude hooks are configured in `.claude/settings.json` (SessionStart,
  PreToolUse, PostToolUse, Stop). The hook scripts live under `tools/`. See the
  "Hooks" section of `AGENTS.md` for the contract; this file just lists the
  tool surface.
- Claude skills live under `.claude/skills/` (symlinks to `.agents/skills`); repo
  engineering skills live under `.agents/skills`. See the Project Skills and
  Installed Plugins sections of `AGENTS.md` for the full catalogue and boundaries.
- Use plugin skills through the `Skill` tool surface when available; otherwise read
  the tracked `.agents/skills/<name>/SKILL.md` file for project guidance.
- CodeGraph MCP tools (`codegraph_*`) are available. Two MCP servers (`codegraph`
  and `caveman-shrink`) both expose the `codegraph_*` family; they are equivalent,
  so either tool prefix is fine. When neither is available, fall back to the
  `rg`/`find` search table in `GEMINI.md`.

### Tools

| Tool | Purpose |
|---|---|
| **Bash** | Run commands via `rtk` wrapper per `RTK.md`. The PreToolUse hook auto-rewrites raw `grep` → `rtk grep`, so raw shell `grep` returns compressed output — use the `Grep` tool when you need exact `line:content` for an edit. |
| **Read / Write / Edit** | File operations. PostToolUse runs the CodeDNA validator; PreToolUse reminds the agent to read docstrings before editing source. |
| **Grep / Glob** | Pattern and file search. Use `Grep` for exact matches; `rtk grep`/`rtk rg` is lossy by design. |
| **Skill** | Invoke installed skills from the catalogue in `AGENTS.md`. |
| **Agent** | Spawn sub-agents for isolated or parallel work. |
| **WebFetch / WebSearch** | External research within ECC guidelines. |

### Permissions

Allowed by `.claude/settings.json`:

- `Bash(rtk:*)`, `Bash(git:*)`, `Bash(gh:*)`, `Bash(python:*)`, `Bash(ls:*)`,
  `Bash(cd:*)`, `Bash(export PATH=*)`, `Bash(pip:*)`, `Bash(pytest:*)`,
  `Bash(conda:*)`, `Bash(mamba:*)`, `Bash(mkdir:*)`, `Bash(cp:*)`, `Bash(mv:*)`,
  `Bash(curl:*)`
- `Edit`, `Write`, `Read`, `Grep`, `Glob`, `Skill`, `WebFetch`, `WebSearch`

This repo is governed by **explicit approval** for `git commit` and `git push`
despite any upstream template defaults.

### Hooks — Claude Code specifics

Full contract is in `AGENTS.md`. This block lists the per-hook Claude runtime:

| Hook | Matcher | Script | Runtime behavior |
|---|---|---|---|
| `SessionStart` | — | `tools/claude_hook_session_start.sh` | Prints project + module count banner; prints RTK reminder if `rtk` on PATH |
| `PreToolUse` | `Bash` | `rtk hook claude` | Rewrites raw shell commands into RTK equivalents |
| `PreToolUse` | `Write\|Edit` | `tools/claude_hook_pretooluse.sh` | Reminds the agent to check CodeDNA annotations before editing source |
| `PostToolUse` | `Write\|Edit` | `tools/claude_hook_codedna.sh` | Validates CodeDNA headers; emits L2 `Rules:` reminders |
| `Stop` | — | `tools/claude_hook_stop.sh` | Blocks completion until `.codedna` has an `agent_sessions` entry when tracked or untracked project files changed; prints RTK session savings on success |

These hooks are **Claude Code-specific**. `CODEX.md` and `GEMINI.md` restate the
CodeDNA session-ledger contract as a manual responsibility.

<REDACTED> CodeDNA

When tracked or untracked project files are changed, update `.codedna` with an
`agent_sessions` entry before the final response. The Stop hook blocks completion
when project files changed but `.codedna` is not part of the diff.

Required `agent_sessions` fields: `agent`, `provider`, `date`, `session_id`, `task`,
`changed`, `visited`, `message`.

After editing, adding, deleting, or staging Python source, run
`codedna init <path> --no-llm` or `codedna update <path>` on the touched path
before commit validation.

### CodeDNA header format (Python)

```python
"""filename.py — purpose ≤15 words.

exports: function(arg) -> type
used_by: caller.py → caller_fn
rules:   constraint the agent must respect
agent:   model-id | provider | YYYY-MM-DD | session_id | what you implemented and what you noticed
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

## Command Style

Always prefer RTK-wrapped shell commands per the Command Style section of
`AGENTS.md`. Use only subcommands listed by `rtk --help` or `RTK.md`. Fall back to
raw commands when RTK is unavailable, the subcommand is unsupported, or output must
be machine-parsed without compression.

Avoid compound `cd <path> && <command>` chains. Use `git -C <path> ...`, pass the
target path as an argument, or set the tool working directory.

## Verification

Before claiming completion, run the smallest checks that prove the change:

- For config or docs edits, run syntax checks or targeted grep checks.
- For Python source edits, run CodeDNA validation and the relevant `rtk pytest`
  targets.
- For Go source edits, run `rtk go build ./...` and `rtk go vet ./...`.
- For browser-facing work, verify with a real browser when possible.
- Report any check that could not run and why.

<!-- BEGIN agent-style v0.3.5 -->
## Agent Style

This repository uses `agent-style` `v0.3.5` from
`https://github.com/yzhao062/agent-style` for technical prose. Full rule bodies are
pinned in `.agent-style/RULES.md` and imported via `@.agent-style/claude-code.md`
from the root `CLAUDE.md`. When asked "is agent-style active?" or "what writing
rules apply here?", answer:

> agent-style v0.3.5 active: 21 rules (RULE-01..12 canonical + RULE-A..I
> field-observed); full bodies at .agent-style/RULES.md.

The 21 rules (RULE-01 through RULE-12 canonical + RULE-A through RULE-I
field-observed) cover passive voice, needless words, claim calibration,
transition-word overuse, and handwavy claims. Apply them to `.md`, `.tex`, `.rst`,
`.txt`, PR descriptions, and API docs. Do not apply them to code comments, log
output, or other machine-oriented text.

Writing defaults for this agent surface:

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

Do not load `.agent-style/RULES.md` into context globally. Reference it on demand.
<!-- END agent-style -->

## Source Repositories

Same table as `AGENTS.md`; this file links rather than duplicates it:

- `https://github.com/rtk-ai/rtk` — RTK CLI and command reference
- `https://github.com/JuliusBrussee/caveman` — Caveman plugin and cavecrew skills
- `https://github.com/Larens94/codedna` — CodeDNA source map tool
- `https://github.com/colbymchenry/codegraph` — CodeGraph MCP server
- `https://github.com/obra/superpowers` — Superpowers plugin
- `https://github.com/addyosmani/agent-skills` — Addy Osmani engineering skills
- `https://github.com/ciembor/agent-rules-books` — Book-derived engineering rules
- `https://github.com/jbarbier/CLAUDE.md` — Operating-contract influence
- `https://github.com/multica-ai/andrej-karpathy-skills` — Karpathy behavioral guidelines
- `https://github.com/yzhao062/agent-style` — Pinned prose rules in `.agent-style/`
