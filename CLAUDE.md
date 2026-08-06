# Claude Code Instructions

This file is the **Claude Code adapter**. It records only Claude-specific deltas
and must not duplicate the cross-agent contract in `AGENTS.md`. For the
operating contract, Command Style, CodeDNA, testing, git workflow, and writing
rules, read `AGENTS.md` first.

## Material differences from AGENTS.md

The following entries are specific to the Claude Code surface and do not appear
in `AGENTS.md`. Everything else is inherited from that file.

### Claude Code Surfaces

- **Configuration lives in the user-global `~/.claude/settings.json`**, not in
  this repo: the PreToolUse hook (`rtk hook claude`), enabled plugins, and
  permission allow/ask/deny rules are all user-scoped. There is no tracked
  project `.claude/settings.json`.
- The project `.claude/` directory holds only the untracked
  `settings.local.json`, which overrides nothing structural — it exists for
  local, machine-specific tool grants (e.g. paths to a local plugin cache).
- The PreToolUse hook rewrites raw Bash commands into RTK equivalents; a raw
  shell `grep` returns the compressed `rtk grep` form, which is expected, not a
  broken wrapper.
- Use plugin skills through the `Skill` tool surface when available; otherwise
  read the tracked `SKILL.md` file for project guidance.
- CodeDNA is a hand-applied annotation convention — there is no binary,
  validator, hook, or `.codedna` ledger. See the CodeDNA section of `AGENTS.md`
  for the protocol; git is the authoritative audit log.

### Tools

| Tool | Purpose |
|---|---|
| **Bash** | Run commands via `rtk` wrapper per `RTK.md`. The PreToolUse hook auto-rewrites raw `grep` → `rtk grep`, so use the `Grep` tool when you need exact `line:content` for an edit. |
| **Read / Write / Edit** | File operations. CodeDNA annotations are applied by hand per `AGENTS.md`; check the module header before editing source. |
| **Grep / Glob** | Pattern and file search. Use `Grep` for exact matches; `rtk grep`/`rtk rg` is lossy by design. |
| **Skill** | Invoke installed skills from the catalogue in `AGENTS.md`. |
| **Agent** | Spawn sub-agents for isolated or parallel work. |
| **WebFetch / WebSearch** | External research within ECC guidelines. |

### Hooks

| Hook | Matcher | Script | Runtime behavior |
|---|---|---|---|
| `PreToolUse` | `Bash` | `rtk hook claude` | Rewrites raw shell commands into RTK equivalents (user-global `~/.claude/settings.json`) |

These hooks are **Claude Code-specific** and configured at the user level. There
are no CodeDNA hooks — the annotation convention is applied by hand per the
CodeDNA section of `AGENTS.md`.

After editing source, keep the module header and `Rules:` blocks current per the
CodeDNA editing protocol in `AGENTS.md`.
