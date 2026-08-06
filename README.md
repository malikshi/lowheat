# lowheat

Minimal agent-operations bootstrap — the single, self-contained multi-agent
workspace contract lives in `AGENTS.md`.

## Layout

| Path | Purpose |
|---|---|
| `AGENTS.md` | Single source of truth — operating contract, Command Style, CodeDNA, security, testing, git workflow |
| `CLAUDE.md` | Claude Code adapter: per-tool deltas only |
| `RTK.md` | RTK command reference (root-level; installed copy: `~/.claude/RTK.md`) |
| `.claude/settings.local.json` | Local Claude Code grants (untracked; user-global config lives in `~/.claude/settings.json`) |
| `LICENSE` | Apache-2.0 |

## Bootstrapping

```bash
git clone <repo> lowheat
cd lowheat
```

Hooks and plugins configure themselves from the user-global
`~/.claude/settings.json`. CodeDNA is a hand-applied annotation convention with
no binary, validator, or ledger file — see the CodeDNA section in `AGENTS.md`.

## Operating contract

Adapted from [jbarbier/CLAUDE.md](https://github.com/jbarbier/CLAUDE.md) —
complete real fixes, search before building, separate reasoning from deterministic
checks, verify before completion, apply the confusion protocol on high-stakes
ambiguity.

Karpathy behavioral guidelines apply: think before coding, simplicity first,
surgical changes, goal-driven execution. No speculative abstractions; every changed
line traces back to a request.
