# lowheat

Minimal agent-operations bootstrap — the single, self-contained multi-agent
workspace contract lives in `AGENTS.md`.

## Layout

| Path | Purpose |
|---|---|
| `AGENTS.md` | Canonical contract — operating principles, Work Loop, engineering standards, CodeDNA, execution & delivery, environment |
| `.agents/skills/agents-contract/SKILL.md` | Repo-local skill encoding the AGENTS.md contract as executable steps |
| `.agents/skills/agents-contract/references/contract.md` | Verbatim mirror of `AGENTS.md` (do not edit directly — re-sync from `AGENTS.md`) |
| `LICENSE` | MIT |

## Contract structure

`AGENTS.md` is the cross-agent source of truth. Six top-level sections:

| Section | Covers |
|---|---|
| How to use this file | Task → section routing table |
| Operating Principles | Task sizing, think before coding, smallest change, verify don't assume, confusion protocol, operations discipline |
| The Work Loop | 7-step delivery loop — each step ends with a verify gate |
| Engineering Standards | Definition of Done, Verification, Coding Style, CodeDNA, Testing Requirements, Security Guidelines |
| Execution & Delivery | Command Style, Git Workflow (commit format + session trailers), Code Review Standards |
| Environment & Source Repositories | Installed plugins / skills, context window management, knowledge capture, source repositories |

## Bootstrapping

```bash
git clone https://github.com/malikshi/lowheat.git lowheat
cd lowheat
```

## Installation

Copy the contract and its skill into your project root so every agent session
picks them up:

| File | Copy to | Purpose |
|---|---|---|
| `AGENTS.md` | project root | Cross-agent source of truth |
| `.agents/skills/agents-contract/` | project root | Skill encoding the contract as executable steps |

Both live at the project root and are picked up automatically.

### Keeping the mirror in sync

`references/contract.md` is `AGENTS.md` copied verbatim under a two-line
header; the skill reads it when the steps in `SKILL.md` need detail. Edit
`AGENTS.md` only, then re-sync:

```bash
{ head -n 2 .agents/skills/agents-contract/references/contract.md; cat AGENTS.md; } \
  > .agents/skills/agents-contract/references/contract.md.tmp \
  && mv .agents/skills/agents-contract/references/contract.md.tmp \
        .agents/skills/agents-contract/references/contract.md
```

Verify the mirror matches `AGENTS.md` (no output means in sync):

```bash
diff AGENTS.md <(tail -n +3 .agents/skills/agents-contract/references/contract.md)
```

Both commands were verified on this repo. The verify command uses process
substitution, so it needs bash or zsh; the sync command is POSIX and runs in
any shell.

### Direct download (curl)

Prefer cloning (above) for the full repo; to pull the contract file without git:

**AGENTS.md** → project root

```bash
curl -fsSL https://raw.githubusercontent.com/malikshi/lowheat/main/AGENTS.md -o AGENTS.md
```

## Required plugin / skill

The contract references one plugin for workflow skills. For Claude Code:

```bash
claude plugin install superpowers@claude-plugins-official
```

`superpowers` (source: [`github.com/obra/superpowers`](https://github.com/obra/superpowers))
provides the workflow skills referenced in `AGENTS.md` — TDD, planning,
debugging, parallel work, and verification. Verify it's active:

```bash
claude plugin list
```

If your agent surface has a different skill or plugin mechanism, install
Superpowers there — or read the tracked `SKILL.md` files directly; the contract
is plain Markdown.

## Operating contract sources

`AGENTS.md` adapts material from:

| Source | Contribution |
|---|---|
| [`jbarbier/CLAUDE.md`](https://github.com/jbarbier/CLAUDE.md) | Operating-contract influence — complete real fixes, search before building, verify before completion |
| [`multica-ai/andrej-karpathy-skills`](https://github.com/multica-ai/andrej-karpathy-skills) | Karpathy behavioral guidelines — think before coding, simplicity first, surgical changes |
| [`affaan-m/ECC`](https://github.com/affaan-m/ECC) | Rule packs for coding style, security, testing, git workflow, code review |
| [`Larens94/codedna`](https://github.com/Larens94/codedna) | CodeDNA source-annotation convention — hand-applied, no binary, validator, or ledger |

## License

MIT — see [`LICENSE`](./LICENSE).
