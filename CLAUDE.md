# Claude Code Instructions

This file is the **Claude Code adapter**. It records only Claude-specific deltas
and must not duplicate the cross-agent contract in `AGENTS.md`. For the operating
contract, plugins, skills, RTK, source repositories, and writing rules,
read `AGENTS.md` first.

This project uses Claude Code directly. It does not use external shared bootstrap
repos, generated bootstrap caches, or shared-config user hooks.

**Do not replace this adapter with the upstream template, and do not symlink
`AGENTS.md`** unless the project owner explicitly requests that migration.

## Material differences from AGENTS.md

The following entries are specific to the Claude Code surface and do not appear in
`AGENTS.md`. Everything else is inherited from that file.

### Claude Code Surfaces

- Project Claude hooks are configured in `.claude/settings.json`. The PreToolUse
  hook rewrites raw Bash commands into RTK equivalents.
- Use plugin skills through the `Skill` tool surface when available; otherwise read
  the tracked `SKILL.md` file for project guidance.
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

| Hook | Matcher | Script | Runtime behavior |
|---|---|---|---|
| `PreToolUse` | `Bash` | `rtk hook claude` | Rewrites raw shell commands into RTK equivalents |

These hooks are **Claude Code-specific**. There are no CodeDNA hooks — the
annotation convention is applied by hand per the CodeDNA section of `AGENTS.md`.

After editing source, keep the module header and `Rules:` blocks current per the
CodeDNA editing protocol in `AGENTS.md`.
