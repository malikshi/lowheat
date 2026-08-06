# RTK — Rust Token Killer

Token-optimized CLI proxy. Prefix shell commands with `rtk` for 60-90% token
savings on dev operations. Full reference: `rtk --help` or `~/.claude/RTK.md`.

## The one rule: compress noise, preserve signal

RTK compresses **shell command output** before it enters the context window.
Used well it cuts tokens on noisy commands *and* sharpens context (less noise →
better reasoning). Used badly — compressing output you actually needed — it hides
detail and forces re-runs that cost *more* than they save.

Wrapping *everything* is counterproductive. A diff you need to apply, JSON you
need to parse, a streaming log that RTK buffers to a hang — these cost more
tokens in re-runs than they save. The skill is knowing **when** to wrap:

- 🟢 **Compress freely** — large, noisy, low-stakes output you only skim:
  `rtk ls`, `rtk git status`, `rtk git log`, `rtk docker ps`, `rtk pip list`,
  and big test/build runs (`rtk cargo test`, or `rtk err <cmd>` — RTK keeps
  the failures and drops the green).
- 🟡 **Default mode only** — worth compressing because it's big, but you need
  the failures: use plain `rtk` (which keeps errors/diffs), never
  `--ultra-compact`/aggressive.
- 🔴 **Keep full fidelity** — run raw; compression risks dropping what you need.

Plain `rtk <cmd>` keeps the signal — errors, diffs, stack traces, exit codes —
and strips only noise. `--ultra-compact`, `rtk read … -l aggressive`, and
`rtk smart` (2-line summary) are **lossy** — opt-in only for skimming something
huge and unimportant, never your default.

> **`-u` doesn't work.** RTK's own README still lists a `-u` short form for
> `--ultra-compact`; it was removed upstream and using it fails outright. Use the
> long flag.

### 🔴 Keep full fidelity — run raw (no `rtk`)

| Situation | Do this | Why |
|---|---|---|
| A diff/patch you'll apply | `git diff`, `git show` **raw** | exact bytes and line numbers matter |
| Output you'll parse (JSON, `--format`) | run raw; use `rtk json file` only to *explore* structure | compression can corrupt structure |
| Small output (≲30 lines) | run raw | nothing to save, real risk |
| Secrets / credentials / exact config | run raw | never reason about a lossy view |
| A file you'll **edit** | native Read tool | lossless + line numbers; bypasses RTK anyway |
| You need everything, just this once | `rtk proxy <cmd>` | passthrough + still tracks savings |

When unsure, start raw. Lean context comes from cutting *noise*, not *signal*.

### Harness safety — don't let it break the tool call

- **Don't wrap streaming/follow output** (`-f`, `tail -f`, a growing log): RTK
  buffers output to filter it, so it can hang the command. Run these raw.
- **When a pass/fail verdict matters** (tests, CI gates), trust the command's raw
  exit code. If you can't tell whether the `rtk` view preserved it, re-run raw or
  use `rtk proxy <cmd>`.
- **Piped output** → RTK can substitute its compressed summary for the real
  content on a non-TTY pipe (e.g. a redirected `grep` writing a line-count
  summary instead of the matches — RTK
  [#1282](https://github.com/rtk-ai/rtk/issues/1282), a correctness bug). Run
  anything you'll parse or redirect raw. RTK has also emitted ANSI codes into
  piped output before (RTK
  [#1409](https://github.com/rtk-ai/rtk/issues/1409), fixed) — set `NO_COLOR=1`
  defensively if escape codes leak through.
- **Prefer the native file/search tools** over `rtk ls/grep/find/read` — they're
  lossless, give line numbers, and don't pass through RTK anyway.

## When to use RTK

- **Prefer RTK-wrapped commands** by default for noisy, low-stakes output.
- **Bypass RTK** when raw output is required, RTK is unavailable, or RTK cannot
  run the command.
- Use the command names exposed by `rtk --help` and the compatibility forms
  validated in this file.
- If a command is listed below, call it through RTK first. If a command is not
  listed, use `rtk proxy <cmd>` when you want raw output tracked for savings, or
  `rtk run <cmd>` when you need completely raw execution with no filtering or
  tracking.

### Grep is lossy by design

`rtk grep` and `rtk rg` group matches by file, strip whitespace, and truncate
lines. That is correct for surveys ("which files mention X", rough counts), but
it loses exact `line:content`. When you need a precise line number or the full
matching line (for example, to feed an edit), use the Grep tool instead. The
PreToolUse hook rewrites a raw Bash `grep` into `rtk grep`, so a raw shell grep
also returns the compressed form; that is expected, not a broken wrapper.

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
rtk git diff                   # Ultra-condensed diff (only changed lines)
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
rtk jest                       # Jest with compact output
rtk vitest                     # Vitest with compact output
rtk tsc --noEmit               # TypeScript compiler with grouped errors
rtk next build                 # Next.js build with compact output
rtk lint .                     # ESLint with grouped rule violations
rtk prettier --check .         # Prettier format checker
rtk format .                   # Universal format checker
rtk playwright test            # Playwright E2E with compact output
rtk prisma generate            # Prisma with compact output
```

### Python Development

```bash
rtk pytest -q                  # Pytest with compact output
rtk ruff check .               # Ruff linting with compact output
rtk ruff format --check .      # Ruff format check with compact output
rtk mypy .                     # Type checking with grouped errors
rtk pip list                   # Pip list with compact output (auto-detects uv)
rtk uv run <cmd>               # uv run with compact output (preserves uv-managed env)
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
```

### PHP Development

```bash
rtk php artisan list           # PHP runner with compact artisan/syntax output
rtk phpunit                    # PHPUnit test runner with compact output
rtk phpstan analyze            # PHPStan analyzer with compact output
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
  `rtk discover`) → it's a poor fit; run it raw and stop wrapping it. And when a
  command *fails*, RTK's tee fallback has already saved the full output — so you
  never lose error detail on the cases that matter.
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

### Review changes before commit
```bash
rtk git diff
rtk git diff --cached
```

### Search for a symbol or pattern
```bash
rtk grep "func HandleRequest" --type go
rtk grep "TODO|FIXME" --type go
rtk rg "func HandleRequest" --type go
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

> `rtk init` targets **Claude Code by default** and has no `--command-code` flag
> in installed `rtk 0.44.2`; Command Code integration is done manually via
> `AGENTS.md` + this file. `--agent` values: claude, cursor, windsurf, cline,
> kilocode, antigravity, kimi, pi, hermes, droid.
