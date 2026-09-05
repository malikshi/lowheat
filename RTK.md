# RTK — Rust Token Killer

Token-optimized CLI proxy. Prefix shell commands with `rtk` for 60-90% token
savings on dev operations. Full reference: `rtk --help`.

## The one rule: decide by intent, never by size

RTK compresses **shell command output** before it enters the context window.
Used well it cuts tokens on noisy commands *and* sharpens context (less noise →
better reasoning). Used badly — compressing output you actually needed — it
hides detail and forces re-runs that cost *more* than they save.

You cannot know an output's size before the command runs, so **size is never a
decision input**. Pick the mode once, *before* running, based only on what you
will do with the output:

| You will… | Mode | Why |
|---|---|---|
| Skim for signal — status, logs, listings, test/build runs | `rtk <cmd>` | compresses noise, keeps errors, diffs, and exit codes |
| Apply or parse exact output — a diff/patch, JSON, CSV, `--format` | **raw** | compression corrupts structure and exact bytes |
| Read or search a file with line numbers | **native Read/Grep tools** | lossless; never shell for this |
| Follow output that grows — `tail -f`, watch, live logs | **raw** | RTK buffers, so it can hang |
| Judge pass/fail | `rtk <cmd>` | RTK preserves exit codes and, on failure, its tee fallback keeps full output; if a verdict is ever unclear, confirm raw or with `rtk proxy <cmd>` |

That is the whole decision: **wrap what you skim, keep exact what you need
exact.** One command, one mode, chosen up front — no measuring, no double run.

### Lossy modes are opt-in

Plain `rtk <cmd>` keeps the signal — errors, diffs, stack traces, exit codes —
and strips only noise. `--ultra-compact`, `rtk read … -l aggressive`, and
`rtk smart` (2-line summary) are **lossy**: they discard detail on purpose.
Reach for them only to skim something huge and unimportant, never as a default.

> **`-u` doesn't work.** RTK's own README still lists a `-u` short form for
> `--ultra-compact`; it was removed upstream and using it fails outright. Use the
> long flag.

### The fallback is one-way

If a wrapped view hid something you needed, re-run **raw once** — that pair is
a net loss, so note the command type and stop wrapping it (`rtk discover`
surfaces exactly this). The reverse — raw first, then wrapping — is never
worth it: raw output is exact, so there is nothing left to recover.

## Fidelity zones (mnemonic)

- 🟢 **Wrap freely** — noisy, low-stakes output you'll only skim: `rtk ls`,
  `rtk git status`, `rtk git log`, `rtk docker ps`, `rtk pip list`, and big
  test/build runs (`rtk cargo test`, `rtk err <cmd>`, `rtk pytest`).
- 🔴 **Run raw** — exact bytes, line numbers, or structure matter:
  - A diff/patch you'll apply (`git diff`, `git show` raw)
  - Output you'll parse or redirect (JSON, `--format`) — use `rtk json file`
    only to *explore* structure
  - Secrets / credentials / exact config
  - Streaming/follow output (`-f`, `tail -f`, a growing log)
  - Any command you'll feed into a pipe or file for later use
- ⚪ **Native tools first** — for reading and searching files, use the
  harness's own Read/Grep/Glob tools instead of `rtk read/grep/find`: lossless,
  line numbers, and they bypass RTK entirely. Reserve `rtk` for shell commands.

## Harness notes — works with or without hooks

RTK ships hook processors for Claude Code, Codex, Copilot, Gemini, OpenCode,
Cursor, and others (`rtk init --agent <name>`). The rules above hold either
way; hooks only change *who* applies them:

- **With hooks installed**, a raw shell command may be rewritten to its `rtk`
  form and come back compressed — that is expected, not a broken wrapper. When
  you need exact `line:content` anyway, use the native Grep tool; hooks don't
  touch it.
- **Without hooks**, apply the intent rule yourself: wrap for skim, stay raw
  for exact.
- **Piped output is unsafe to compress**: RTK can substitute a compressed
  summary on a non-TTY pipe (e.g. a redirected `grep` writing a line-count
  summary instead of the matches — RTK
  [#1282](https://github.com/rtk-ai/rtk/issues/1282), a correctness bug). Run
  anything you'll parse or redirect raw. RTK has also emitted ANSI codes into
  piped output before (RTK
  [#1409](https://github.com/rtk-ai/rtk/issues/1409), fixed) — set `NO_COLOR=1`
  defensively if escape codes leak through.
- **Failures are never lost**: when a command fails, RTK's tee fallback saves
  the full output to a log, so error detail survives compression on the cases
  that matter.

### Grep is lossy by design

`rtk grep` and `rtk rg` group matches by file, strip whitespace, and truncate
lines. That is correct for surveys ("which files mention X", rough counts), but
it loses exact `line:content`. When you need a precise line number or the full
matching line (for example, to feed an edit), use the native Grep tool — it
bypasses RTK entirely.

## When to use RTK — quick rules

- **Wrap by default** for output you'll only read for signal.
- **Skip RTK** when you'll apply, parse, redirect, or edit from the output, or
  when RTK is unavailable — fall back to raw without ceremony.
- Prefer the forms listed under Commands; for anything unlisted, plain
  `rtk <cmd>` still filters. Use `rtk proxy <cmd>` to run raw while tracking
  savings, or `rtk run <cmd>` for fully raw execution with no tracking.
- Check `rtk --help` when in doubt; treat commands missing from it as
  unsupported and run them raw.

## Commands

### Core Navigation

```bash
rtk ls                         # List directory contents (compact)
rtk tree                       # Directory tree (compact)
rtk read <file>                # Read file with intelligent filtering
rtk read -l aggressive <file>  # Read with lossy aggressive filtering (opt-in)
rtk smart <file>               # Generate a 2-line technical summary (lossy)
rtk find -name "*.go"          # Find files (compact tree output)
rtk grep "pattern" path        # Compact grep - strips whitespace, groups by file
rtk rg "pattern" path          # Ripgrep-compatible search through RTK
rtk wc <file>                  # Compact line/word/byte counts
rtk diff                       # Ultra-condensed diff (only changed lines)
```

### Git Operations

```bash
rtk git status                 # Compact git status
rtk git log --oneline -10      # Compact log (default: last 10)
rtk git diff                   # Skim a review diff (raw for applying/parsing)
rtk git show <commit>          # Compact commit view
rtk git blame <file>           # Compact blame output
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
rtk bun test                   # Bun runtime with compact output
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
rtk uv run <cmd>               # uv run with compact output (preserves uv-managed env)
rtk deno test                  # Deno runtime with compact output
```

### Rust, Ruby, .NET, And Android

```bash
rtk cargo test                 # Cargo with compact output
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
rtk kubectl get pods           # Kubectl with compact output
rtk oc get pods                # OpenShift CLI (oc) with compact output
rtk psql -c "select 1"         # PostgreSQL output with compact tables
rtk curl https://example.com   # Curl with auto-JSON detection
rtk wget <url>                 # Download with compact progress output
```

### Testing & Linting

```bash
rtk test <cmd>                 # Run tests, show only failures
rtk err <cmd>                  # Run command, show only errors/warnings
rtk lint <cmd>                 # ESLint with grouped rule violations
rtk log <file-or-cmd>          # Filter and deduplicate log output
rtk summary <cmd>              # Run command and show heuristic summary
```

### Data & Config

```bash
rtk json <file>                # Show JSON (compact values)
rtk json --keys-only <file>    # Show JSON keys only
rtk deps                       # Summarize project dependencies
rtk env                        # Show environment variables (filtered, sensitive masked)
rtk pipe                       # Read stdin, apply an RTK filter, print filtered output
```

## Meta Commands

```bash
rtk gain                       # Token savings summary
rtk gain --graph               # ASCII graph of daily savings
rtk gain --history             # Command-level savings history
rtk gain --quota               # Monthly quota savings estimate
rtk gain --all --format json   # All-time breakdowns, machine-readable (run raw to parse)
rtk cc-economics               # Claude Code spending vs RTK savings analysis
rtk config                     # Show or create RTK configuration
rtk telemetry                  # Manage telemetry consent and data
rtk learn                      # Learn CLI corrections from Claude Code error history
rtk proxy <cmd>                # Run raw, but track usage
rtk run <cmd>                  # Run raw, no filtering or tracking
rtk discover                   # Discover missed RTK savings from Claude Code history
rtk session                    # Show RTK adoption across Claude Code sessions
```

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
| `rtk gain --quota` | monthly quota savings estimate |
| `rtk gain --failures` | show commands that fell back to raw execution |
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
rtk grep "func HandleRequest" --type go
rtk grep "TODO|FIXME" --type go
rtk rg "func HandleRequest" --type go
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

## Hook Integration

RTK provides hook processors for LLM CLI tools:

```bash
rtk init             # Initialize RTK for Claude Code (default)
rtk init --codex     # Target Codex CLI (AGENTS.md + RTK.md, no hook patching)
rtk init --copilot   # Install GitHub Copilot integration (VS Code + CLI)
rtk init --gemini    # Initialize for Gemini CLI
rtk init --opencode  # Install OpenCode plugin
rtk init --agent cursor   # Target a specific agent (cursor, windsurf, cline, kilocode, …)
rtk init --show      # Show current configuration
rtk init --dry-run   # Preview changes without writing (combine -v to show content)
rtk hook             # Hook processors for Gemini CLI, Copilot, etc.
rtk rewrite <cmd>    # Rewrite a raw command to its RTK equivalent
rtk hook-audit       # Show hook rewrite audit metrics
rtk trust            # Trust project-local TOML filters in current directory
rtk untrust          # Revoke trust for project-local TOML filters
rtk verify           # Verify hook integrity and TOML filter tests
```

> `rtk init` targets **Claude Code by default**. `--agent` values: claude, cursor,
> windsurf, cline, kilocode, antigravity, kimi, pi, hermes, droid.
