# RTK — Rust Token Killer

Token-optimized CLI proxy. Prefix shell commands with `rtk` to cut the bash
output your agent reads by 60-90% on dev operations. Full reference:
`rtk --help`. This catalogue is verified against **rtk 1.0.1** — run
`rtk --version` for your build, and treat anything missing from `rtk --help` as
unsupported.

## The one rule: decide by intent, never by size

RTK compresses **shell command output** before it enters the context window.
Wrap what you will only *read*; keep raw what you will *use* — apply, parse,
redirect, or edit from. Used well it cuts noise and sharpens context; used
badly it hides detail and forces re-runs that cost *more* than they save.

You cannot know an output's size before the command runs, so **size is never a
decision input**. Pick the mode once, *before* running, from what you will do
with the result:

| You will… | Mode | Why |
|---|---|---|
| Skim for signal — status, listings, logs, test/build runs | `rtk <cmd>` | noise compressed; errors, diffs, and exit codes kept |
| Judge pass/fail | `rtk <cmd>` | exit codes pass through, and on failure the tee fallback keeps the full output |
| Explore structure rather than values — trees, deps, `rtk json --keys-only` | `rtk <cmd>` | the structure is the signal; bodies are noise |
| Apply or parse exact output — a diff/patch, JSON, CSV, `--format`, a redirect | **raw** | compression corrupts bytes and structure |
| Handle secrets, credentials, or exact config | **raw** | RTK does not mask, and it records commands plus elided output under `~/.local/share/rtk/` |
| Follow output that grows — `tail -f`, watch, live logs | **raw** | RTK buffers, so it can hang |
| Read a file with line numbers, any size | `rtk read <file> -n` | copies the file verbatim at the default level; `-n` adds numbers, normalizes CRLF→LF, and exits 1 on non-UTF-8 |
| Read a file and line endings or bytes must stay exact | **native Read/Grep tools** | lossless; read caps at 1000 lines per call, and native Grep truncates very long lines |

That is the whole decision: **wrap what you skim, keep exact what you need
exact.** One command, one mode, chosen up front — no measuring, no double run.
Anything not listed under Commands still runs through plain `rtk <cmd>`.

### Lossy modes are opt-in

Plain `rtk <cmd>` keeps the signal — errors, diffs, stack traces, exit codes —
and strips only noise. The lossy switches are **opt-in**: `--ultra-compact`,
`rtk read -l minimal`, `rtk read -l aggressive`, `rtk read -m` (structure
only), and `rtk smart` (2-line summary). Reach for them only to skim something
huge and unimportant, never as a default. `rtk read` with no `-l` copies the
file verbatim.

> **`-u` doesn't work.** RTK's own README still lists a `-u` short form for
> `--ultra-compact`; it was removed upstream and using it fails outright
> (verified on 1.0.1: `rtk -u ls` errors). Use the long flag. Placed after a
> subcommand, `-u` goes to the wrapped command instead — `rtk ls -u` runs
> `ls -u`.

### The fallback is one-way

If a wrapped view hid something you needed, re-run **raw once** — that pair is
a net loss, so note the command type and stop wrapping it (`rtk discover`
surfaces exactly this). The reverse — raw first, then wrapping — is never
worth it: raw output is exact, so there is nothing left to recover.

RTK also falls back on its own: a flag the filter does not recognize makes
it run the command raw (`rtk wget -q …` is one), which looks like a filter
that did nothing. `rtk gain --failures` lists those — if an example here
seems unfiltered on your build, check there before trusting it.

## Fidelity zones (mnemonic)

- 🟢 **Wrap freely** — noisy output you will only skim, where counts, trees,
  and summaries are the point: `rtk ls`, `rtk tree`, `rtk git status`,
  `rtk git log`, `rtk docker ps`, `rtk pip list`, `rtk deps`, and test/build
  runs (`rtk cargo test`, `rtk pytest`, `rtk err <cmd>`). Expect truncation
  with an inline recovery hint — `[+3431 hidden: rtk recall 0eabbc130600]`.
- 🔴 **Run raw** — the bytes are the point:
  - a diff or patch you will apply (`git diff`, `git show` raw)
  - output you will parse or redirect (JSON, `--format`, `> file`)
  - secrets, credentials, exact config
  - streaming output (`tail -f`, `-f`, a growing log)
  - anything you will feed into a pipe or another command
- 🟡 **Not sure? Wrap once.** Wrapping first beats guessing: the fallback is
  one-way, and `rtk discover` shows which commands should have gone raw.

### When compression is unsafe

Piped output is unsafe to compress: on a non-TTY pipe RTK can substitute a
compressed summary (a redirected `grep` writing a line-count summary instead of
the matches — RTK [#1282](https://github.com/rtk-ai/rtk/issues/1282), a
correctness bug), and it has emitted ANSI codes into piped output before (RTK
[#1409](https://github.com/rtk-ai/rtk/issues/1409), fixed) — run anything
you'll parse or redirect raw, and set `NO_COLOR=1` defensively if escape codes
leak through.

Failures are never lost: when a command fails, RTK's tee fallback saves the
full output to a log, so error detail survives compression on the cases that
matter.

## Grep is lossy by design

`rtk grep` and `rtk rg` group matches by file, strip whitespace, and truncate
lines. That is correct for surveys ("which files mention X", rough counts), but
it loses exact `line:content`. When you need a precise line number or the full
matching line (for example, to feed an edit), use the native Grep tool — it
bypasses RTK entirely, though it truncates very long lines and says so. When a
filter elides output, RTK prints a recovery hint inline — `[+4 hidden: rtk
recall 6f88169463a3]` — and `rtk recall <hash>` returns the elided part (kept
gzipped in `~/.local/share/rtk/recall.db`, with the command that produced it)
instead of re-running it. `rtk config recall` sets the recovery mode (`sqlite`
is exact, `tee` logs the full output, `disabled` turns it off);
`rtk gain --recalls` reports how often elisions were actually recalled.

Three `rtk grep` behaviors to know before trusting its output (verified on
1.0.1):

- **`--max` and `--max-len` must use the `=` form and precede the pattern**
  (`rtk grep --max=100000 -rn "p" dir`). With a space, or after the pattern,
  they leak to the wrapped GNU grep and it exits with an error instead of
  results.
- **The default output caps at 200 results and truncates lines at 80 chars.**
  A broad search silently reports a subset; the reported match *count* is
  accurate, but the file labels are collapsed and elided, so it cannot be used
  to enumerate files.
- **`rtk find` filters dot-directories and caches** (`.agents`, `.commandcode`,
  `__pycache__`, `.pytest_cache`, …) and elides them behind `[+N hidden]`.
  Use it to skim, or native `find`/Glob when you must enumerate every match.

## When to use RTK — quick rules

Three questions, asked before the command runs:

1. **Will I use the output, or only read it?** Using it — applying a patch,
   parsing, redirecting, editing from it — means **raw**. Reading it for signal
   means wrap.
2. **Is it secret, exact, or alive?** Credentials, exact config, and streaming
   output (`tail -f`, a growing log) are always **raw**: RTK masks, truncates,
   and buffers.
3. **Then wrap it.** `rtk <cmd>` for a shell command, or the matching form
   under Commands (`rtk read`, `rtk git status`, `rtk pytest`, …).

If a wrapped view hides something you needed, re-run that one command raw and
stop wrapping it. `rtk bypass <cmd>` runs raw while tracking savings;
`rtk run <cmd>` runs fully raw with no tracking. Anything missing from
`rtk --help` is unsupported — run it raw.

## Commands

### Core Navigation

```bash
rtk ls                         # List directory contents (compact)
rtk tree                       # Directory tree (compact)
rtk read <file>                # Read file with intelligent filtering
rtk read -l aggressive <file>  # Read with lossy aggressive filtering (opt-in)
rtk read --head-lines 40 <file> # First N lines, byte-exact at the default level
rtk smart <file>               # Generate a 2-line technical summary (lossy)
rtk find "*.go" .              # Find files (pattern first; "-name" before the path fails)
rtk grep -rn "pattern" dir    # Compact grep; flags pass through, -r walks directories
rtk grep "pattern" file        # Single file: no -r needed
rtk rg "pattern" dir --type go # ripgrep flags (--type, -g) work with rtk rg only
rtk ast-grep run -p '<pat>' .  # ast-grep via RTK (needs the ast-grep binary on PATH)
rtk wc <file>                  # Compact line/word/byte counts
rtk diff <file1> <file2>       # Condensed diff; exit 0 identical, 1 different, 2 read error
```

### Git Operations

```bash
rtk git status                 # Compact git status
rtk git log --oneline -10      # Compact log (default: last 10)
rtk git diff                   # Skim a review diff (raw for applying/parsing)
rtk git show <commit>          # Compact commit view
rtk git blame <file>           # Blame (passes through to git)
rtk git add / commit / push / pull  # One-line confirmations ("ok <hash>", "ok <branch>")
rtk git branch                 # Compact listing: current, local, remote
rtk git fetch / stash / worktree    # Compact forms of each
rtk git -C <path> <cmd>        # Run against another checkout (like git -C)
rtk gt stack                   # Graphite stacked PR commands, when gt is installed
```

### Go Development

```bash
rtk go build ./...             # Go build with compact output
rtk go test ./...              # Go test with compact output
rtk go vet ./...               # Go vet with compact output
rtk go mod tidy                # Go mod tidy with compact output
rtk golangci-lint run          # Go linting with compact output
```

### JavaScript And Frontend Development

```bash
rtk npm test                   # npm run with filtered output
rtk npx tsc --noEmit           # npx routes known tools to compact filters
rtk pnpm test                  # pnpm with ultra-compact output
rtk pnpm list                  # Dependency tree (ultra-dense)
rtk pnpm outdated              # Outdated packages: "pkg: old → new"
rtk pnpm typecheck             # Typecheck via the tsc filter
rtk bun test                   # Bun runtime with compact output
rtk bun install / build / run  # Package, build, and script output, filtered
rtk bunx                       # bunx passthrough + auto-filter
rtk jest                       # Jest with compact output
rtk vitest                     # Vitest with compact output
rtk tsc --noEmit               # TypeScript compiler with grouped errors
rtk next build                 # Next.js build with compact output
rtk lint .                     # ESLint with grouped rule violations
rtk prettier --check .         # Prettier format checker
rtk format .                   # Universal format checker
rtk playwright test            # Playwright E2E with compact output
rtk prisma generate            # Prisma with compact output
rtk ctest                      # CTest with compact output
```

### Python Development

```bash
rtk pytest -q                  # Pytest with compact output
rtk ruff check .               # Ruff linting with compact output
rtk ruff format --check .      # Ruff format check with compact output
rtk mypy .                     # Type checking with grouped errors
rtk pip list                   # Pip list with compact output (auto-detects uv)
rtk pip outdated               # Outdated packages
rtk sqlfluff lint models/      # SQLFluff SQL linting with compact output
rtk uv run <cmd>               # uv run with compact output (preserves uv-managed env)
rtk deno test                  # Deno runtime with compact output
rtk deno lint / check          # Deno lint and type-check, download noise stripped
```

### Rust, Ruby, .NET, And Android

```bash
rtk cargo test                 # Cargo with compact output
rtk cargo build / clippy / check / nextest  # Same filters, per cargo subcommand
rtk rake test                  # Rake/Rails test with compact output
rtk rubocop                    # RuboCop linter with compact output
rtk rspec                      # RSpec test runner with compact output
rtk dotnet test                # .NET commands with compact output
rtk gradlew test               # Android Gradle wrapper with compact output
rtk sbt test                   # SBT (Scala Build Tool) with compact output
rtk mvn test                   # Maven with compact output (test, package, deploy…)
rtk mvnd test                  # Maven Daemon (mvnd) with compact output — same filters as rtk mvn
```

### PHP Development

```bash
rtk php artisan list           # PHP runner with compact artisan/syntax output
rtk phpunit                    # PHPUnit test runner with compact output
rtk phpstan analyze            # PHPStan analyzer with compact output
rtk phpt                       # PHP run-tests.php (.phpt) with compact output
rtk pest                       # Pest test runner with compact output
rtk paratest                   # ParaTest parallel test runner with compact output
rtk ecs                        # EasyCodingStandard code style fixer with compact output
rtk pint                       # Laravel Pint (PHP-CS-Fixer) with compact output
```

### GitHub CLI

```bash
rtk gh pr list                 # PR list with compact output
rtk gh pr view <number>        # PR view with compact output
rtk gh issue list              # Issue list with compact output
rtk gh run list                # Workflow runs with compact output
rtk glab mr list               # GitLab CLI with compact output
```

### Cloud, Containers, And Databases

```bash
rtk aws sts get-caller-identity # AWS CLI with compact JSON output
rtk docker ps                  # Docker with compact output
rtk docker images / logs <c>   # Image list; deduplicated container logs
rtk docker compose ps          # Compose services
rtk kubectl pods               # Pod list (kubectl get pods also works)
rtk kubectl services           # Service list
rtk kubectl logs <pod>         # Deduplicated pod logs
rtk oc pods / services / logs <pod>  # Same shapes for OpenShift (oc)
rtk psql -c "select 1"         # PostgreSQL output with compact tables
rtk curl https://example.com   # Curl with auto-JSON detection
rtk wget <url>                 # Download with compact progress output
```

### Testing & Linting

```bash
rtk test <cmd>                 # Run tests, show only failures
rtk err <cmd>                  # Run command, show only errors/warnings
rtk err --shell <sh> '<script>' # One quoted command string through that shell
rtk run -c '<script>'          # Shell string through sh (cmd on Windows)
rtk run --shell fish -c '<script>'  # Explicit shell for shell-specific syntax
rtk lint <cmd>                 # ESLint with grouped rule violations
rtk lint biome                 # Other linters supported (biome, …)
rtk log <file>                 # Filter/deduplicate a log file (stdin if omitted; not a command)
rtk summary <cmd>              # Run command and show heuristic summary
```

`rtk run`, `rtk err`, `rtk test`, and `rtk summary` execute argv directly — no
glob expansion, variables, or operators. A missing program exits `127`; a path
that is a directory or not executable exits `126`. Reach for `-c` / `--shell`
only when a command needs shell syntax.

### Data & Config

```bash
rtk json <file>                # Show JSON (compact values)
rtk json --keys-only <file>    # Keys and types for large/nested JSON; small files stay compact
rtk deps                       # Summarize project dependencies
rtk env -f <FILTER>            # Env vars by name (e.g. -f PATH, -f AWS); values print in full
rtk pipe                       # Read stdin, apply an RTK filter, print filtered output
```

## Meta Commands

```bash
rtk gain                       # Token savings summary
rtk gain --graph               # ASCII graph of daily savings
rtk gain --history             # Command-level savings history
rtk gain --daily               # Day-by-day breakdown
rtk gain --quota               # Monthly quota savings estimate
rtk gain --recalls             # Recall efficiency per filter (elisions vs recalls)
rtk gain --all --format json   # All-time breakdowns, machine-readable (run raw to parse)
rtk cc-economics               # Claude Code spending vs RTK savings analysis
rtk config                     # Show or create RTK configuration
rtk config recall [mode]       # Recovery mode: sqlite (exact) | tee | disabled
rtk telemetry                  # Manage telemetry consent and data
rtk learn                      # Learn CLI corrections from Claude Code error history
rtk bypass <cmd>               # Run raw, but track usage (former rtk proxy)
rtk run <cmd>                  # Run raw, no filtering or tracking
rtk recall <hash>              # Recall output a filter elided, by content hash
rtk discover                   # Missed-savings scan (current project)
rtk discover --all --since 7   # All projects, last 7 days (also --limit, --format json)
rtk session                    # Show RTK adoption across Claude Code sessions
```

> `rtk proxy` is a **deprecated alias** for `rtk bypass` — identical behavior,
> no deprecation notice, kept so instructions written before the rename keep
> working. Use `rtk bypass` in new text.

## Hooks & Filters

RTK 1.0 ships a project-local filter and hook surface. None of it is required
for the wrap/raw decision above; reach for it only when adding a custom filter
or debugging one.

```bash
rtk init                       # Install RTK instructions into an agent config
rtk init -g                    # ...into the global assistant config dir
rtk rewrite <cmd>              # Rewrite a raw command to its RTK equivalent
rtk hook <tool>                # Hook processor for an LLM CLI (Gemini CLI, Copilot, ...)
rtk hook-audit                 # Hook rewrite audit metrics (needs RTK_HOOK_AUDIT=1)
rtk trust                      # Trust project-local TOML filters in this directory
rtk untrust                    # Revoke trust for project-local TOML filters
rtk verify                     # Verify hook integrity and run TOML filter inline tests
rtk verify --require-all       # CI mode — fail if any filter has no inline tests
rtk pipeline                   # Inspect, validate, and test the compression pipeline
rtk methods list               # List registered compression methods and contracts
rtk plugins new|list|build     # Author and link your own Rust pipeline methods
rtk tasks list                 # List configured delegation tasks and bindings
rtk llm-proxy <start|stop|...> # Transparent LLM proxy daemon
```

`rtk rewrite` carries a hook contract: exit `0` = rewrite printed and every
command is allow-covered; `1` = nothing printed, run unchanged; `2` = a deny
matched, block; `3` = rewrite printed but approval is deferred to the host.
A hook must handle all four.

## Analytics — measure *net* savings, not just gross

`rtk gain` reports **gross** tokens saved. The number that actually matters is
**net**: gross savings minus (a) tokens spent re-running commands when a
compressed view hid something, and (b) the standing cost of these instructions
in context. Optimize for net.

| Command | Use it to |
|---|---|
| `rtk gain` | session summary: tokens saved, efficiency |
| `rtk gain --graph` | 30-day savings trend |
| `rtk gain --history` | per-command savings — see where RTK actually pays off |
| `rtk gain --daily` | day-by-day breakdown |
| `rtk gain --quota` | monthly quota savings estimate |
| `rtk gain --failures` | show commands that fell back to raw execution |
| `rtk gain --recalls` | recall efficiency: elisions vs how many were recalled |
| `rtk discover` | find *good* new opportunities (don't blanket-apply) |
| `rtk session` | RTK adoption across recent sessions |
| `rtk gain --all --format json` | export for dashboards (run raw if you'll parse it) |

### Reading the signal

- **High `--history` savings on noisy commands** → working as intended; keep
  going.
- **Low or zero savings on a command** (visible in `--history`, or surfaced by
  `rtk discover`) → it's a poor fit; run it raw and stop wrapping it.
- **You re-ran a command raw right after its `rtk` version** → that pair was a
  net *loss*. Note the command type and stop compressing it.
- **`rtk discover`** surfaces high-volume, noisy commands worth wrapping — a far
  better guide than wrapping everything by reflex.

Savings vary by command and output size; let `rtk gain` show your real numbers
rather than assuming the headline 60–90%.

### Read the numbers as estimates

RTK ships no tokenizer: it estimates tokens as `bytes / 4`, so the percentages
are reliable and the absolute counts are approximate. Savings also measure
**bash output only** — that output is one contributor to input tokens, and
input tokens are one part of the bill, so "up to 90%" never means 90% off the
bill. Judge RTK by its net effect on your context: `rtk gain --history` for
what paid off, `rtk gain --recalls` for what compression cost you back.

## Common Workflows

### Inspect a failing test
```bash
rtk go test ./... -run TestName -v
rtk pytest -q -k test_name
```

### Review changes before commit (skim → wrap)
```bash
rtk git diff
rtk git diff --cached
```

### Apply or export a diff (exact → raw)
```bash
git diff > change.patch        # raw: bytes must be exact
git apply change.patch
```

### Search for a symbol or pattern
```bash
rtk grep -rn "TODO|FIXME" .            # plain grep flags; -r walks directories
rtk rg "func HandleRequest" --type go  # ripgrep flags (--type, -g) need rtk rg
# Need exact line:content for an edit? Use the native Grep tool instead.
```

### Check project health
```bash
rtk go vet ./...
rtk golangci-lint run
rtk ruff check .
```

## Options

```bash
-v, --verbose        # Verbosity level (-v, -vv, -vvv) — only before the subcommand
--ultra-compact      # Ultra-compact mode: ASCII icons, inline format (lossy — opt-in)
--skip-env           # Set SKIP_ENV_VALIDATION=1 for child processes
```
