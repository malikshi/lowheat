# RTK - Rust Token Killer

Token-optimized CLI proxy. Prefix shell commands with `rtk` for 60-90% token
savings on dev operations. Full reference: `rtk --help` or `~/.claude/RTK.md`.

## Rule

Always prefer RTK-wrapped commands. Bypass only when raw output is required,
RTK is unavailable, or RTK cannot run the command.

Use the command names exposed by `rtk --help` and the compatibility forms
validated in this file.

If a command is listed below, call it through RTK first. If a command is not
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
rtk smart <file>               # Generate a 2-line technical summary
rtk find -name "*.go"          # Find files (compact tree output)
rtk grep "pattern" path        # Compact grep - strips whitespace, groups by file
rtk rg "pattern" path          # Ripgrep-compatible search through RTK
rtk wc <file>                  # Compact line/word/byte counts
```

### Git Operations

```bash
rtk git status                 # Compact git status
rtk git log --oneline -10      # Compact log (default: last 10)
rtk git diff                   # Ultra-condensed diff (only changed lines)
rtk diff                       # Ultra-condensed native diff wrapper
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
rtk pip list                   # Pip list with compact output
```

### Rust, Ruby, .NET, And Android

```bash
rtk cargo test                 # Cargo with compact output
rtk rake test                  # Rake/Rails test with compact output
rtk rubocop                    # RuboCop linter with compact output
rtk rspec                      # RSpec test runner with compact output
rtk dotnet test                # .NET commands with compact output
rtk gradlew test               # Android Gradle wrapper with compact output
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
rtk gain --history             # Command-level savings history
rtk gain --session             # Current session savings
rtk cc-economics               # Claude Code spending vs RTK savings analysis
rtk config                     # Show or create RTK configuration
rtk telemetry                  # Manage telemetry consent and data
rtk learn                      # Learn CLI corrections from Claude Code error history
rtk proxy <cmd>                # Run raw, but track usage
rtk run <cmd>                  # Run raw, no filtering or tracking
rtk discover                   # Discover missed RTK savings from Claude Code history
rtk session                    # Show RTK adoption across Claude Code sessions
```

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
-v, --verbose        # Verbosity level (-v, -vv, -vvv)
--ultra-compact      # Ultra-compact mode: ASCII icons, inline format
--skip-env           # Set SKIP_ENV_VALIDATION=1 for child processes
```

## Hook Integration

RTK provides hook processors for LLM CLI tools:

```bash
rtk hook             # Hook processors for Gemini CLI, Copilot, etc.
rtk rewrite <cmd>    # Rewrite a raw command to its RTK equivalent
rtk hook-audit       # Show hook rewrite audit metrics
rtk init             # Initialize RTK instructions for assistant CLI usage
rtk trust            # Trust project-local TOML filters in current directory
rtk untrust          # Revoke trust for project-local TOML filters
rtk verify           # Verify hook integrity and TOML filter tests
```
