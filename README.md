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

## Installation

Three files power the contract. Copy them into your environment so every agent
session picks them up:

| File | Copy to | Purpose |
|---|---|---|
| `AGENTS.md` | project root (this repo already has it) | Cross-agent source of truth — operating contract, Command Style, CodeDNA, git workflow |
| `CLAUDE.md` | project root (this repo already has it) | Claude Code adapter: per-tool deltas, hooks, tool usage |
| `RTK.md` | `~/.claude/RTK.md` | RTK command reference — the CLI proxy that compresses shell output |

`AGENTS.md` and `CLAUDE.md` live at the project root and are picked up
automatically. `RTK.md` is installed globally so every project inherits the
token-optimization rules.

### Direct download (curl)

Prefer cloning (above) for the full repo; to pull individual files without git:

**AGENTS.md** → project root

```bash
curl -fsSL https://raw.githubusercontent.com/malikshi/lowheat/main/AGENTS.md -o AGENTS.md
```

**CLAUDE.md** → project root

```bash
curl -fsSL https://raw.githubusercontent.com/malikshi/lowheat/main/CLAUDE.md -o CLAUDE.md
```

**RTK.md** → `~/.claude/RTK.md` (global)

```bash
curl -fsSL https://raw.githubusercontent.com/malikshi/lowheat/main/RTK.md -o ~/.claude/RTK.md
```

### Required plugin / skill

The contract references one plugin for workflow skills:

```bash
claude plugin install superpowers@claude-plugins-official
```

`superpowers` provides the workflow skills referenced in `AGENTS.md` — TDD,
planning, debugging, parallel work, and verification. Verify it's active:

```bash
claude plugin list
```

### Required binary: RTK

`RTK.md` documents the [RTK](https://github.com/rtk-ai/rtk) CLI proxy, which
compresses shell command output before it reaches the LLM context window.
Install it from the upstream repository, then confirm:

```bash
rtk --version
```

> RTK is optional but recommended. If `rtk` is not on PATH, agents run commands
> normally and skip the token optimization — work is never blocked on it.

### Global config

Hooks and plugins configure themselves from the user-global
`~/.claude/settings.json`, which is managed by Claude Code itself (via
`claude plugin install` and the marketplace commands). CodeDNA is a hand-applied
annotation convention with no binary, validator, or ledger file — see the
CodeDNA section in `AGENTS.md`.

## Operating contract

Adapted from [jbarbier/CLAUDE.md](https://github.com/jbarbier/CLAUDE.md) —
complete real fixes, search before building, separate reasoning from deterministic
checks, verify before completion, apply the confusion protocol on high-stakes
ambiguity.

Karpathy behavioral guidelines apply: think before coding, simplicity first,
surgical changes, goal-driven execution. No speculative abstractions; every changed
line traces back to a request.
