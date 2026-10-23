# lowheat

Minimal agent-operations bootstrap — the single, self-contained multi-agent
workspace contract lives in `AGENTS.md`.

## Layout

| Path | Purpose |
|---|---|
| `AGENTS.md` | Canonical contract — operating principles, Work Loop, engineering standards, CodeDNA, execution & delivery, environment |
| `RTK.md` | RTK command reference — decision rule, fidelity zones, and the full CLI catalogue |
| `semble.md` | Semble code-search reference — discovery ladder, CLI verbs, MCP fallback, caveats |
| `caveman.md` | Caveman reply-mode reference — voice rules, modes, commit and review formats, optional layer |
| `ponytail.md` | Ponytail posture reference — ladder, never-cut list, shortcut and disclosure conventions |
| `.agents/skills/agents-contract/SKILL.md` | Repo-local skill encoding the AGENTS.md contract as executable steps |
| `.agents/skills/agents-contract/references/contract.md` | Verbatim mirror of `AGENTS.md` (do not edit directly — re-sync from `AGENTS.md`) |
| `.agents/skills/agents-contract/scripts/codedna_check.py` | CodeDNA checker — L1 header drift + out-of-contract comment content, 15 languages, line-numbered (read-only). Skips tool-owned directories (`.claude`, `.codex`, `.commandcode`, editors) at any depth below the scanned path; `--exclude NAME` skips one more |
| `.agents/skills/agents-contract/hooks/` | Contract hook — harness detection, the Command Style and discovery decisions, and the installer that wires Claude Code, Grok, and Command Code |
| `tests/test_codedna_check.py` | Tests for the checker (`python3 -m pytest tests`) |
| `tests/test_contract_hook.py` | Tests for the hook policy, reply shapes, deny budgets, and entry point |
| `tests/test_install_hooks.py` | Tests for the installer merge, backup, and uninstall paths |
| `bench/discovery_tokens.py` | Code-discovery token benchmark — semble vs `rtk grep` vs native grep+read (`python3 bench/discovery_tokens.py <corpus>`) |
| `tests/test_discovery_tokens.py` | Tests for the benchmark helpers |
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
| `semble.md` | project root | Semble code-search reference — the discovery ladder, CLI verbs, and caveats |
| `caveman.md` | project root | Caveman reply-mode reference — terse replies, commit and review formats, optional layer |
| `ponytail.md` | project root | Ponytail posture reference — the laziness ladder and its conventions |
| `.agents/skills/agents-contract/` | project root | Skill encoding the contract as executable steps |

All six install under the project root and are picked up automatically. A
symlink to a checkout works as well as a copy, and re-syncs on every
`git pull`.

A symlink re-syncs the content the harness reads, not the hook wiring. The
installer records absolute interpreter and script paths, so a checkout that
moves leaves every harness running a hook path that no longer exists — and the
hook fails open, so the rules silently stop being enforced. `--dry-run` is the
check: current wiring prints `unchanged`, a moved checkout prints `write`.
Re-run the installer to repoint it.

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

**semble.md** → project root

```bash
curl -fsSL https://raw.githubusercontent.com/malikshi/lowheat/main/semble.md -o semble.md
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

## Hook wiring (enforcement)

`AGENTS.md` states the Command Style and discovery rules; the hook makes them
hold, because instructions alone lose to a harness's default tool choice.

These rules are enforced where the harness allows it. The contract hook in the
agents-contract skill (`hooks/`) rewrites a shell command to its `rtk` form on
Claude Code and Grok; on Command Code, which cannot rewrite tool input, it
refuses one raw command per session with the `rtk` form to re-issue. It refuses
the first native Grep and the first native Glob of a session once each, naming
the cheapest rung it has verified it can run. Refusals are budgeted per session
in `~/.cache/lowheat-hooks/` and every other path fails open. Wire it, or remove
it, with
`python3 .agents/skills/agents-contract/hooks/install_hooks.py [--uninstall]`; a
harness left unwired follows the rules by hand.

One hook script serves all three harnesses:

| Harness | Config it writes | What the hook does there |
|---|---|---|
| Claude Code | `~/.claude/settings.json` | rewrites a shell command to its `rtk` form via `hookSpecificOutput.updatedInput`, and injects the session digest |
| Grok | `~/.grok/hooks/contract.json` | same rewrite rules; Grok also reads `~/.claude/settings.json` and deduplicates handlers that run the same command. It ignores hook output on SessionStart, so it gets no digest |
| Command Code | `~/.commandcode/settings.json` | cannot rewrite tool input, so it refuses one raw command per session with the rtk form to re-issue, and injects the session digest. Its matcher names the display names `SHELL`, `SEARCH`, and `GLOB` — a bare `SHELL` skipped the discovery nudges entirely, because Command Code matches a regex against those display names rather than the tool id |

The first native `Grep` and the first native `Glob` of a session are each
refused once on every wired harness, with the cheapest rung the hook has
verified it can run: the semble MCP tool, then `semble search` when the CLI can
launch, then `rtk grep`. A `semble` shim on `PATH` whose interpreter is gone is
detected — the hook reads the shim's shebang and drops that rung rather than
recommending a command that exits 127. It never runs the CLI to find out:
`semble -V` costs 3–5 s because it imports the embedding stack. Everything else
is fail-open: a missing `rtk`, an unreadable cache, or a malformed payload
leaves the tool call alone, and each refusal fires once per session.

Deny budgets live in `~/.cache/lowheat-hooks/`, one state file per session,
swept after seven days; an exclusive lock keeps parallel tool calls from
spending the same budget twice.

```bash
python3 .agents/skills/agents-contract/hooks/install_hooks.py --dry-run
python3 .agents/skills/agents-contract/hooks/install_hooks.py
python3 .agents/skills/agents-contract/hooks/install_hooks.py --uninstall
```

`--harness claude|grok|commandcode|all` narrows the run. The installer merges
rather than overwrites, keeps every existing hook and key, and copies the
pristine file to `<name>.lowheat-bak` before the first write — including the
Grok hook file, which it creates rather than owns. Every wired command ends on
`; exit 0`, because Command Code reads exit `2` from `PreToolUse` as a refusal:
when this checkout moved from `/root/lowheat` to `/home/git/lowheat`, the
recorded absolute script path went dead and the resulting `No such file or
directory` blocked tool calls outright (three on 2026-10-23, the day of the
move). The refusal travels in the hook's JSON, so forcing a zero exit loses
nothing. `--uninstall` removes our
handlers and writes that copy back when only the hook wiring had changed, so the
file returns byte for byte (`cmp` verified on both); a file that gained foreign
handlers since the install keeps them, and the Grok file is deleted only when
nothing else remains in it.

Compression is the point of the rewrite and also its sharp edge: a command whose
output is the answer can come back empty. Plain `git add -n --verbose <paths>`
printed five `add '…'` lines here; through `rtk git add -n --verbose <paths>` it
printed none and still exited 0. The rewrite has no budget — every shell call
with an rtk form is compressed — so `rtk bypass <command>` is the route to
untouched output: the engine never rewrites it, and both the rewrite reason and
the refusal name it. `rtk gain --history` shows the form that actually ran.
Nothing else signals a rewrite on Grok, so the reason text, `RTK.md`, and this
section are how an agent learns of it.

A rewrite grants no approval. The reply carries `updatedInput` and no
`permissionDecision`, so the harness applies its own permission rules to the
rewritten command — an earlier revision sent `permissionDecision: "allow"` on
Claude Code, which skipped the prompt and would have run a wrapped `git push`
without the approval `AGENTS.md` requires. Verified with `claude -p` on 2.1.296:
one payload in, one reply holding only `updatedInput`, and `rtk gain --history`
records `rtk git status --short --branch` executing. One process cost stays:
every shell tool call spawns `rtk hook claude` to ask for the rewrite, bounded
by a 3 s timeout.

That `rtk` spawn is skipped once it can no longer change the answer. On Command
Code the refusal is budgeted to one per session, so the hook reads the spent
budget first and returns no opinion without spawning anything; the rewriting
harnesses keep paying it, because they rewrite every shell call. What remains is
interpreter start: measured here over 40 calls, 105 ms median and 154 ms p90 for
a Command Code payload after the first, against 7,611 recorded real calls at a
138 ms median and 364 ms p95. `python3 -S` bought no measurable time, so the hook
does not depend on it.

Verified end to end on all three harnesses — the model emits the raw command and
`rtk gain --history` records the rtk form running:

| Harness | Evidence |
|---|---|
| Claude Code 2.1.296 | `claude -p "run rg ..."` reported the raw form; `rtk gain --history` recorded `rtk rg` |
| Grok 1.0.62 | `grok -p ... --output-format streaming-json` shows `rawInput.command` as the raw form and the executed command as `rtk ls -la /tmp \| head -3`; `grok inspect` lists the hook with no load errors |
| Command Code 1.84.0 | `cmd -p ... --yolo`: the raw form is refused once, the model re-issues the rtk form, which runs |

Headless Command Code runs need `--yolo` (`--permission-mode yolo` does not grant
the shell tool) and take their model from `~/.commandcode/config.json`; pass
`-m <provider>/<model>` to override it.

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
