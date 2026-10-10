# lowheat

Minimal agent-operations bootstrap — the single, self-contained multi-agent
workspace contract lives in `AGENTS.md`.

## Layout

| Path | Purpose |
|---|---|
| `AGENTS.md` | Canonical contract — operating principles, Work Loop, engineering standards, CodeDNA, execution & delivery, environment |
| `.agents/skills/agents-contract/SKILL.md` | Repo-local skill encoding the AGENTS.md contract as executable steps |
| `.agents/skills/agents-contract/references/contract.md` | Verbatim mirror of `AGENTS.md` (do not edit directly — re-sync from `AGENTS.md`) |
| `.agents/skills/agents-contract/scripts/codedna_check.py` | CodeDNA checker — L1 header drift + out-of-contract comment content, 15 languages, line-numbered (read-only). Skips tool-owned directories (`.claude`, `.codex`, `.commandcode`, editors) at any depth below the scanned path; `--exclude NAME` skips one more |
| `tests/test_codedna_check.py` | Tests for the checker (`python3 -m pytest tests`) |
| `LICENSE` | MIT |

## Contract structure

`AGENTS.md` is the cross-agent source of truth. Six top-level sections:

| Section | Covers |
|---|---|
| How to use this file | Task → section routing table, precedence order, staleness check |
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

Both live at the project root and are picked up automatically. A symlink to a
checkout works as well as a copy, and re-syncs on every `git pull`.

### One canonical copy per machine

Agent surfaces read instructions from fixed paths, and independent copies drift
silently. This contract's own deployment lost a rule that way in October 2026:
three copies were live on one machine, and two of them lacked the newest rule.
Keep one canonical file and point the other surfaces at it.

| Surface | Path it reads | Wiring |
|---|---|---|
| Grok Build | `~/.grok/AGENTS.md`, `<project>/AGENTS.md` | symlink to the canonical file |
| Claude Code | `<project>/CLAUDE.md`, `~/.claude/CLAUDE.md` | one `@AGENTS.md` import line, or a symlink |
| Cursor | `<project>/.cursor/rules/` | one `.mdc` rule that points at `AGENTS.md` |
| Any other agent | `<project>/AGENTS.md` | copy or symlink |

```bash
mkdir -p ~/.grok ~/.claude
ln -sfn /path/to/lowheat/AGENTS.md ~/.grok/AGENTS.md
ln -sfn /path/to/lowheat/AGENTS.md ~/.claude/AGENTS.md
sha256sum ~/.grok/AGENTS.md ~/.claude/AGENTS.md AGENTS.md
```

`Contract-Version:` on line 3 names the revision. A copy that shows a different
value, or none, is stale — refresh it from the canonical file. A symlink
resolves to the file on the checked-out branch, so point it at a checkout that
sits on the default branch.

Run the contract's own checks:

```bash
python3 .agents/skills/agents-contract/scripts/codedna_check.py
python3 -m pytest tests
```

### Keeping the mirror in sync

`references/contract.md` is a byte-identical copy of `AGENTS.md`; the skill
reads it when the steps in `SKILL.md` need detail. Edit `AGENTS.md` only, then
re-sync:

```bash
cp AGENTS.md .agents/skills/agents-contract/references/contract.md
```

Verify the mirror matches `AGENTS.md` (no output means in sync):

```bash
cmp AGENTS.md .agents/skills/agents-contract/references/contract.md
```

Both commands were verified on this repo.

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
