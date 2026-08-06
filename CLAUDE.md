# Claude Code Instructions

This file is the **Claude Code adapter**. It records only Claude-specific deltas
and must not duplicate the cross-agent contract in `AGENTS.md`. For the operating
contract, plugins, skills, RTK, source repositories, and writing rules,
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
`AGENTS.md`** unless the project owner explicitly requests that migration.

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
- CodeDNA is a hand-applied annotation convention — there is no binary, validator,
  hook, or `.codedna` ledger. See the CodeDNA section of `AGENTS.md` for the
  protocol; git is the authoritative audit log.

### Tools

| Tool | Purpose |
|---|---|
| **Bash** | Run commands via `rtk` wrapper per `RTK.md`. The PreToolUse hook auto-rewrites raw `grep` → `rtk grep`, so raw shell `grep` returns compressed output — use the `Grep` tool when you need exact `line:content` for an edit. |
| **Read / Write / Edit** | File operations. CodeDNA annotations are applied by hand per `AGENTS.md`; check the module header before editing source. |
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

These hooks are **Claude Code-specific**. There are no CodeDNA hooks — the
annotation convention is applied by hand per the CodeDNA section of `AGENTS.md`.

After editing source, keep the module header and `Rules:` blocks current per the
CodeDNA editing protocol in `AGENTS.md`.

### CodeDNA header format (Python)

The Python module-header and L2 function-annotation formats live in `AGENTS.md`
under "### CodeDNA header format (Python)". Edit them there; do not duplicate them
in this adapter.

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
- For Python source edits, run the relevant `rtk pytest`
  targets.
- For Go source edits, run `rtk go build ./...` and `rtk go vet ./...`.
- For browser-facing work, verify with a real browser when possible.
- Report any check that could not run and why.

<!-- BEGIN agent-style v0.3.5 -->
## Agent Style

Agent Style is canonical in `AGENTS.md` under `## Agent Style`. Full rule bodies are
pinned in `.agent-style/RULES.md`; read on demand, do not load globally. When asked
"is agent-style active?" or "what writing rules apply here?", answer:

> agent-style v0.3.5 active: 21 rules (RULE-01..12 canonical + RULE-A..I
> field-observed); full bodies at .agent-style/RULES.md.

This adapter adds no prose rules; it only routes to the canonical section. Apply the
rules to `.md`, `.tex`, `.rst`, `.txt`, PR descriptions, and API docs; not to code
comments, log output, or other machine-oriented text.
<!-- END agent-style -->

## Dyslexia-Friendly Output (opt-in)

Dyslexia-friendly output formatting is available on request. It restructures a
response for faster decoding without simplifying content. It is **opt-in** and does
not change default output. Triggers: `/i-have-dyslexia`, "dyslexia fit", "fit", or
an explicit request. On Claude Code it is also invocable through the
`i-have-dyslexia` plugin/Skill surface. Canonical rules and precedence live in
`AGENTS.md` under "### Dyslexia-Friendly Output (opt-in)"; full rule bodies and the
interview are pinned in `.agents/dyslexia/i-have-dyslexia.md`. Read on demand; do
not duplicate the rules here.

## Source Repositories

Same table as `AGENTS.md`; this file links rather than duplicates it:

- `https://github.com/rtk-ai/rtk` — RTK CLI and command reference
- `https://github.com/obra/superpowers` — Superpowers plugin
- `https://github.com/ciembor/agent-rules-books` — Book-derived engineering rules
- `https://github.com/jbarbier/CLAUDE.md` — Operating-contract influence
- `https://github.com/multica-ai/andrej-karpathy-skills` — Karpathy behavioral guidelines
- `https://github.com/yzhao062/agent-style` — Pinned prose rules in `.agent-style/`
