# lowheat

Minimal agent-operations bootstrap — the single, self-contained multi-agent
workspace contract lives in `AGENTS.md`.

## Layout

| Path | Purpose |
|---|---|
| `AGENTS.md` | Canonical contract — operating principles, Work Loop, engineering standards, CodeDNA, execution & delivery, environment |
| `RTK.md` | RTK command reference — decision rule, fidelity zones, and the full CLI catalogue |
| `caveman.md` | Caveman reply-mode reference — voice rules, modes, commit and review formats, optional layer |
| `ponytail.md` | Ponytail posture reference — ladder, never-cut list, shortcut and disclosure conventions |
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
| Execution & Delivery | Command Style, Communication Style (caveman), Git Workflow (commit format + session trailers), Code Review Standards |
| Environment & Source Repositories | Installed plugins / skills, context window management, knowledge capture, source repositories |

## Bootstrapping

```bash
git clone https://github.com/malikshi/lowheat.git lowheat
cd lowheat
```

## Installation

Copy the contract, its companion references, and its skill into your project
root so every agent session picks them up:

| File | Copy to | Purpose |
|---|---|---|
| `AGENTS.md` | project root | Cross-agent source of truth |
| `RTK.md` | project root | RTK command reference — the CLI proxy that compresses shell output |
| `caveman.md` | project root | Caveman reply-mode reference — terse replies, commit and review formats, optional layer |
| `ponytail.md` | project root | Ponytail posture reference — the laziness ladder and its conventions |
| `.agents/skills/agents-contract/` | project root | Skill encoding the contract as executable steps |

All five install under the project root and are picked up automatically. A
symlink to a checkout works as well as a copy, and re-syncs on every
`git pull`.

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

Run the contract's own checks:

```bash
python3 .agents/skills/agents-contract/scripts/codedna_check.py
python3 -m pytest tests
```

### Direct download (curl)

Prefer cloning (above) for the full repo; to pull individual files without git:

**AGENTS.md** → project root

```bash
curl -fsSL https://raw.githubusercontent.com/malikshi/lowheat/main/AGENTS.md -o AGENTS.md
```

**RTK.md** → project root

```bash
curl -fsSL https://raw.githubusercontent.com/malikshi/lowheat/main/RTK.md -o RTK.md
```

**caveman.md** → project root

```bash
curl -fsSL https://raw.githubusercontent.com/malikshi/lowheat/main/caveman.md -o caveman.md
```

**ponytail.md** → project root

```bash
curl -fsSL https://raw.githubusercontent.com/malikshi/lowheat/main/ponytail.md -o ponytail.md
```

## Required binary: RTK

`RTK.md` documents the [RTK](https://github.com/rtk-ai/rtk) CLI proxy, which
compresses shell command output before it reaches the LLM context window.
Upstream install options:

```bash
brew install rtk                 # Homebrew
winget install rtk-ai.rtk        # Windows
curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh
cargo install --git https://github.com/rtk-ai/rtk
```

Confirm the binary:

```bash
rtk --version    # should print 1.0.1 or newer — the catalogue is verified against 1.0.1
```

> The crates.io package named `rtk` is a different project (Rust Type Kit) —
> install from the GitHub repository above. RTK is optional but recommended: if
> `rtk` is not on PATH, agents run commands normally and skip the token
> optimization — work is never blocked on it, and the Command Style rules apply
> `rtk` by hand. Run `rtk --help` for your build's command list.

## Optional companions: caveman and ponytail

`caveman.md` and `ponytail.md` are text-level adaptations: `AGENTS.md` already
carries their rules, so every agent session picks them up with no install.
Installing the upstream tools adds the slash commands and, for caveman, the
optional layer that compresses what the agent reads. The contract rules work
without either install — caveman's CLI is optional and its rules are text;
ponytail ships as a skill and plugin, not a CLI.

Install (optional):

- Caveman replies only: `npx skills add JuliusBrussee/caveman -g`; full CLI +
  layer: `npm install -g @caveman-ai/cli && caveman setup --install`.
- Ponytail in Claude Code: `/plugin marketplace add DietrichGebert/ponytail`,
  then `/plugin install ponytail@ponytail`.
- Full install paths, modes, and caveats live in each companion file.

## Optional companion: semble

[`semble`](https://github.com/MinishLab/semble) is an MCP code-search server
that locates code by intent — "where is the header check implemented" — and
returns the file, line, and snippet. It is optional infrastructure like RTK:
if it is not connected, agents fall back to Grep/Glob and work is never
blocked on it.

Semble is a **discovery** aid, not a replacement for the native tools. Use
`search` to find *where* something lives, then read that file directly; keep
the harness's Read/Grep/Glob for exact `line:content`, all occurrences of a
literal string, and lossless reads (Command Style → native tools first).

Install (optional):

```bash
uv tool install "semble[mcp]"                      # or: pipx install "semble[mcp]"
uvx --from "semble[mcp]" semble search "query" .   # no-install fallback
semble install --agent claude --type mcp -y        # wire the MCP server into an agent
```

CLI equivalents of the two MCP tools (`--content code|docs|config|all`,
`-k/--top-k`, `--max-snippet-lines N`):

```bash
semble search "authentication flow" ./my-project --max-snippet-lines 10
semble search "deployment guide" ./my-project --content docs
semble find-related src/auth.py 42 ./my-project
```

The CLI subcommand is `find-related`; the MCP tool is `find_related`. The
index builds on first run and is cached; `semble clear` drops it, `semble
savings` reports token savings. Verified against semble 0.7.0.

## Operating contract sources

`AGENTS.md` adapts material from:

| Source | Contribution |
|---|---|
| [`rtk-ai/rtk`](https://github.com/rtk-ai/rtk) | RTK CLI and command catalogue — the token-optimized proxy wrapped by Command Style |
| [`MinishLab/semble`](https://github.com/MinishLab/semble) | Semble MCP code search — `search` and `find_related` for locating an implementation by intent |
| [`JuliusBrussee/caveman`](https://github.com/JuliusBrussee/caveman) | Caveman communication mode — terse replies, commit and review formats, optional read-compression layer |
| [`DietrichGebert/ponytail`](https://github.com/DietrichGebert/ponytail) | Ponytail laziness ladder — smallest complete change, root-cause fixes, disclosure line |
| [`jbarbier/CLAUDE.md`](https://github.com/jbarbier/CLAUDE.md) | Operating-contract influence — complete real fixes, search before building, verify before completion |
| [`multica-ai/andrej-karpathy-skills`](https://github.com/multica-ai/andrej-karpathy-skills) | Karpathy behavioral guidelines — think before coding, simplicity first, surgical changes |
| [`affaan-m/ECC`](https://github.com/affaan-m/ECC) | Rule packs for coding style, security, testing, git workflow, code review |
| [`Larens94/codedna`](https://github.com/Larens94/codedna) | CodeDNA source-annotation convention — hand-applied, no binary, validator, or ledger |

## License

MIT — see [`LICENSE`](./LICENSE).
