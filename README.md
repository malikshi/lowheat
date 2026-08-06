# lowheat

Minimal agent-operations bootstrap — multi-agent workspace contract lives in `AGENTS.md`.

## Layout

| Path | Purpose |
|---|---|
| `AGENTS.md` | Cross-agent source of truth — operating, security, testing, CodeDNA, RTK, agent-style |
| `CLAUDE.md` | Per-tool adapter deltas |
| `RTK.md` | RTK command reference (root-level) |
| `LICENSE` | Apache-2.0 |

## Bootstrapping

```bash
git clone <repo> lowheat
cd lowheat
```

Hooks and plugins configure themselves from `.claude/settings.json`. CodeDNA is a hand-applied annotation convention with no binary, validator, or ledger file — see the CodeDNA section in `AGENTS.md`.

## Operating contract

Adapted from [jbarbier/CLAUDE.md](https://github.com/jbarbier/CLAUDE.md) — complete real fixes, search before building, separate reasoning from deterministic checks, verify before completion, apply the confusion protocol on high-stakes ambiguity.

Karpathy behavioral guidelines apply: think before coding, simplicity first, surgical changes, goal-driven execution. No speculative abstractions; every changed line traces back to a request.
