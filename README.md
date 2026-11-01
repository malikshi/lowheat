# lowheat

Minimal agent-operations bootstrap — a thin cross-agent contract in
`contract/AGENTS.md`, with detailed references loaded on demand.

## Layout

| Path | Purpose |
|---|---|
| `install.py` | Adapter-driven installer — links or copies the contract, companions, aliases, skill, and rules files where each harness reads them |
| `contract/AGENTS.md` | Canonical thin contract — operating principles, Work Loop, engineering standards, execution & delivery, environment |
| `contract/codedna.md` | Full CodeDNA convention — module headers, function annotations, inline rules, checker behaviour |
| `contract/RTK.md` | RTK command reference — decision rule, fidelity zones, and the full CLI catalogue |
| `contract/semble.md` | Semble code-search reference — discovery ladder, CLI verbs, MCP fallback, caveats |
| `contract/caveman.md` | Caveman reply-mode reference — voice rules, modes, commit and review formats, optional layer |
| `contract/ponytail.md` | Ponytail posture reference — ladder, never-cut list, shortcut and disclosure conventions |
| `contract/aider.conf.yml` | Aider config that reads the project `CONVENTIONS.md` alias |
| `contract/continue.md` | Continue project rule that points at `AGENTS.md` and its companions |
| `.agents/skills/agents-contract/SKILL.md` | Repo-local skill encoding the AGENTS.md contract as executable steps |
| `.agents/skills/agents-contract/references/contract.md` | Byte-identical mirror of `contract/AGENTS.md`, written by `install.py` (do not edit directly) |
| `.agents/skills/agents-contract/references/codedna.md` | Byte-identical mirror of `contract/codedna.md`, written by `install.py` (do not edit directly) |
| `.agents/skills/agents-contract/references/commands.md` | Byte-identical mirror of `contract/RTK.md`, written by `install.py` (do not edit directly) |
| `.agents/skills/agents-contract/scripts/codedna_check.py` | CodeDNA checker — L1 header drift + out-of-contract comment content, 15 file suffixes, line-numbered (read-only). Skips tool-owned directories (`.claude`, `.codex`, `.commandcode`, editors) at any depth below the scanned path; `--exclude NAME` skips one more |
| `tests/test_codedna_check.py` | Tests for the checker (`python3 -m pytest tests`) |
| `tests/test_install.py` | Tests for the adapter registry, per-harness install shapes, Grok rules rendering, skill links, and all three mirrors |
| `tests/test_docs.py` | Tests for contract thinness, version line, named companions, skill mirrors, and reference paths |
| `HARNESSES.md` | Supported harnesses, install surfaces, verified versions, and smoke-test status |
| `bench/discovery_tokens.py` | Code-discovery token benchmark — semble vs `rtk grep` vs native grep+read (`python3 bench/discovery_tokens.py <corpus>`) |
| `tests/test_discovery_tokens.py` | Tests for the benchmark helpers |
| `LICENSE` | MIT |

## Contract structure

`contract/AGENTS.md` is the thin cross-agent core. Its six top-level sections:

| Section | Covers |
|---|---|
| How to use this file | Task → section routing, companion table, precedence order, staleness check |
| Operating Principles | Task sizing, think before coding, smallest change, verify don't assume, confusion protocol, operations discipline |
| The Work Loop | 7-step delivery loop — each step ends with a verify gate |
| Engineering Standards | Definition of Done, Verification, Coding Style, CodeDNA summary, Testing Requirements, Security Guidelines |
| Execution & Delivery | Command Style, Communication Style, Git Workflow, Code Review Standards |
| Environment & Source Repositories | Installed plugins / skills, context management, knowledge capture, sources |

The companions hold the detail the core points to: `codedna.md` for annotations,
`RTK.md` for command fidelity and catalogue, `semble.md` for discovery,
`caveman.md` for reply modes, and `ponytail.md` for scope discipline.

## Bootstrapping

```bash
git clone https://github.com/malikshi/lowheat.git lowheat
cd lowheat
```

## Installation

One command wires the contract into every harness, with no hand-copied files:

```bash
python3 install.py                        # all supported harnesses, user scope
python3 install.py --dry-run              # show what would change
python3 install.py --list-harnesses       # registry, binaries, config dirs
python3 install.py --detect               # installed vs missing
python3 install.py --harness auto         # only detected harnesses
python3 install.py --harness grok         # one harness
python3 install.py --scope project --root /path/to/repo   # commit with the repo
python3 install.py --scope project --root . --force       # replace a foreign AGENTS.md
```

Each harness gets the shape it can actually read. User scope links; project
scope copies.

| Harness | User scope | Project scope |
|---|---|---|
| Claude Code | `~/.claude/{AGENTS,CLAUDE}.md`, companions, `skills/agents-contract` | `AGENTS.md`, companions, `CLAUDE.md` |
| Codex | `~/.codex/AGENTS.md`, companions, `skills/agents-contract` | `AGENTS.md`, companions |
| Command Code | `~/.commandcode/AGENTS.md`, companions, `skills/agents-contract` | `AGENTS.md`, companions |
| Grok | `~/.grok/AGENTS.md`, `.grok/rules/*.md`, `skills/agents-contract` | `AGENTS.md`, companions, `.grok/rules/*.md` |
| OpenCode | `~/.config/opencode/AGENTS.md`, companions | `AGENTS.md`, companions |
| Factory Droid | `~/.factory/AGENTS.md`, companions, `skills/agents-contract` | `AGENTS.md`, companions |
| Kilo | `~/.config/kilo/AGENTS.md`, companions | `AGENTS.md`, companions |
| Pi | `~/.pi/agent/AGENTS.md`, companions, `skills/agents-contract` | `AGENTS.md`, companions |
| Central `.agents` | `~/.agents/AGENTS.md`, companions, `skills/agents-contract` | `AGENTS.md`, companions |
| Cline | `~/.agents/AGENTS.md`, companions, `skills/agents-contract` | `AGENTS.md`, companions |
| Gemini CLI | `~/.gemini/GEMINI.md`, companions | `GEMINI.md`, companions |
| Crush | `~/.config/crush/CRUSH.md`, companions | `CRUSH.md`, companions |
| Qwen Code | `~/.qwen/QWEN.md`, companions | `QWEN.md`, companions |
| fx | `~/.fx/AGENTS.md`, companions as regular files, `~/.fx/skills/agents-contract` | `AGENTS.md`, companions |
| Hermes | `~/.hermes/skills/agents-contract`; project instructions only | `AGENTS.md`, companions |
| OpenClaw / claw | `~/.openclaw/workspace/AGENTS.md`, companions; `.agents/skills` fallback | `AGENTS.md`, companions |
| Jcode | `~/AGENTS.md`, companions, `~/.jcode/skills/agents-contract` | `AGENTS.md`, companions |
| OMP | `~/.omp/agent/AGENTS.md`, companions; `.agents/skills` fallback | `AGENTS.md`, companions |
| Forge | `~/forge/AGENTS.md`, companions, `~/forge/skills/agents-contract` | `AGENTS.md`, companions |
| Smelt | `~/.config/smelt/AGENTS.md`, companions, `~/.config/smelt/skills/agents-contract` | `AGENTS.md`, companions |
| Codewhale | `~/.codewhale/skills/agents-contract`; project instructions only | `AGENTS.md`, companions |
| Copilot CLI | `~/.copilot/copilot-instructions.md`; `.agents/skills` fallback | `AGENTS.md`, companions |
| Aider | `~/.aider.conf.yml` → reads project `CONVENTIONS.md` | `CONVENTIONS.md`, `.aider.conf.yml`, companions |
| Cursor | — (project only) | `AGENTS.md`, companions |
| Continue | — (project only) | `AGENTS.md`, companions, `.continue/rules/agents-contract.md` |

The Grok row is the one worth knowing: Grok scans standalone rule files and
does not expand imports, so its companions are written into `.grok/rules`.
Every other adapter receives the five companions beside the contract or alias;
`AGENTS.md` names them by bare filename for on-demand reads.

**User scope normally links; project scope copies.** A user install symlinks the
contract, companions, and skill, so a `git pull` in the checkout re-syncs what
every harness reads; Grok's rules directory is refreshed on each installer run.
`fx` is the exception: it refuses symlinked instructions and linked skill
directories, so its adapter writes regular files and a real skill copy. A project
install writes real files, because its output is committed: a symlink into the
installing machine's checkout resolves to nothing on a teammate's clone.

A broken symlink contributes nothing and fails silently — every emitted path is
checked before the run reports success, and a re-run reports `unchanged`.

**Nothing is overwritten by accident.** The installer refuses to replace any
existing file whose contents differ from the contract — a project's own
`AGENTS.md`, a hand-written `.grok/rules/RTK.md`, or a real skill directory —
and exits 1 without touching it. `--force` replaces it outright; copy anything
you want to keep before running it. Project scope also refuses to run against
the lowheat checkout itself, where it would duplicate `contract/` back into the
repo root.

### Keeping the mirrors in sync

`references/contract.md` is written by `install.py` from `contract/AGENTS.md`,
`references/codedna.md` from `contract/codedna.md`, and
`references/commands.md` from `contract/RTK.md`, on every run; do not edit the
copies by hand. Edit the source under `contract/`, then re-run the installer.
To verify without writing:

```bash
cmp contract/AGENTS.md .agents/skills/agents-contract/references/contract.md
cmp contract/codedna.md .agents/skills/agents-contract/references/codedna.md
cmp contract/RTK.md .agents/skills/agents-contract/references/commands.md
```

Run the contract's own checks:

```bash
python3 .agents/skills/agents-contract/scripts/codedna_check.py
python3 -m pytest tests
```

### Direct download (curl)

Prefer cloning (above) for the full repo; to pull individual files without git.
Every contract file lives under `contract/` in the repository, so fetch it from
there and write it where the harness reads it — `AGENTS.md` and the companions
side by side in the project root, or the companions alone in `.grok/rules/`.

```bash
mkdir -p .grok/rules
for f in AGENTS.md codedna.md RTK.md semble.md caveman.md ponytail.md; do
  curl -fsSL "https://raw.githubusercontent.com/malikshi/lowheat/main/contract/$f" -o "$f"
done
for f in codedna.md RTK.md semble.md caveman.md ponytail.md; do
  cp "$f" ".grok/rules/$f"
done
```

That reproduces what `install.py --scope project` does for the contract files,
so prefer the installer for the per-harness layout and cleanup.

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

## Instruction-only enforcement

`AGENTS.md` states the Command Style and discovery rules. No harness hook
rewrites or refuses a command: the agent must invoke RTK and the semble ladder
itself. The instructions are the only enforcement surface.

An older release shipped a contract hook that rewrote shell commands and
refused native searches. It is gone. Hooks installed by that release point at a
deleted script and fail open; remove those entries from harness settings
manually. The deny-budget cache, if present, is `~/.cache/lowheat-hooks`.

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

## Code discovery: semble

[`semble`](https://github.com/MinishLab/semble) is an MCP code-search server
that locates code by intent and returns ranked chunks with file and line. It
is the top rung of the discovery ladder in `AGENTS.md` → Command Style →
**Tool ladder for code discovery**: semble MCP → semble CLI → `rtk grep` →
native Grep/Glob. Each absent rung drops to the next; discovery is never
blocked on an install.

Semble is a **discovery** aid, not a replacement for the native tools. Use it
to find *where* something lives, then read that file directly; keep native
Read/Grep/Glob for exact `line:content`, all occurrences of a literal string,
and lossless reads.

The MCP tool is `mcp__semble__search` on Claude Code and Command Code,
`semble__search` on Grok, whose catalog carries no `mcp__` prefix. Calling the
wrong name fails with `Tool not found`, so use the server's name from
`search_tool` / the tool list rather than assuming one prefix. On Grok both the
direct `semble__search` tool and the `search_tool` → `use_tool` route reach the
same key, and a server whose handshake is still running is missing from the
first prompt — send a second prompt before concluding it is absent.

Install (optional):

```bash
uv tool install "semble[mcp]"                      # or: pipx install "semble[mcp]"
semble install --agent claude --type mcp -y        # wire the MCP server into an agent
semble search "firewall install" . --max-snippet-lines 10   # CLI fallback
```

The CLI subcommand for related code is `find-related` (`find_related` as an
MCP tool). The index builds on first run and is cached under `~/.cache/semble`;
`semble clear` drops it, `semble savings` reports token savings. Verified
against semble 0.7.0.

### Benchmark

`bench/discovery_tokens.py` measures tokens *an agent ingests* per query across
the ladder, with `tiktoken` when installed (`bytes/4` otherwise). On an ~466-file
Python corpus it measured **semble ~99.5% and `rtk grep`+read ~28%** below
native grep+read. `rtk read` was excluded on purpose: it is byte-identical to
`cat`, so it has no token advantage — the measured savings come from `rtk grep`.
Reproduce against any corpus:

```bash
python3 bench/discovery_tokens.py /path/to/repo
```

## Operating contract sources

`AGENTS.md` adapts material from:

| Source | Contribution |
|---|---|
| [`rtk-ai/rtk`](https://github.com/rtk-ai/rtk) | RTK CLI and command catalogue — the token-optimized proxy wrapped by Command Style |
| [`JuliusBrussee/caveman`](https://github.com/JuliusBrussee/caveman) | Caveman communication mode — terse replies, commit and review formats, optional read-compression layer |
| [`DietrichGebert/ponytail`](https://github.com/DietrichGebert/ponytail) | Ponytail laziness ladder — smallest complete change, root-cause fixes, disclosure line |
| [`jbarbier/CLAUDE.md`](https://github.com/jbarbier/CLAUDE.md) | Operating-contract influence — complete real fixes, search before building, verify before completion |
| [`multica-ai/andrej-karpathy-skills`](https://github.com/multica-ai/andrej-karpathy-skills) | Karpathy behavioral guidelines — think before coding, simplicity first, surgical changes |
| [`affaan-m/ECC`](https://github.com/affaan-m/ECC) | Rule packs for coding style, security, testing, git workflow, code review |
| [`Larens94/codedna`](https://github.com/Larens94/codedna) | CodeDNA source-annotation convention — hand-applied, no binary, validator, or ledger |

## License

MIT — see [`LICENSE`](./LICENSE).
