# RTK Command Catalogue

RTK is a token-optimized CLI proxy (60–90% token savings). Full reference:
`RTK.md` in the repo root, and `rtk --help`.

## When to wrap and when to run raw

Decide by intent, never by size — you cannot know an output's size before
running, so never measure. Pick the mode once, up front:

- 🟢 **Wrap by default** — output you'll only skim for signal (status, logs,
  listings, test/build runs): plain `rtk <cmd>` compresses noise and keeps
  errors, diffs, and exit codes. Never `--ultra-compact` on output where
  failures matter.
- 🔴 **Run raw** — you'll apply, parse, redirect, or need exact bytes/line
  numbers: diffs you'll apply (`git diff`, `git show`), JSON/`--format` to
  parse (use `rtk json file` only to explore structure), secrets/credentials,
  streaming output (`tail -f`, growing logs — RTK buffers and can hang).
- ⚪ **Native tools first** — for reading and searching files, use the
  harness's own Read/Grep/Glob tools: lossless, line numbers, bypass RTK.

The fallback is one-way: if a wrapped view hid something you needed, re-run
raw once — that pair is a net loss, so stop wrapping that command. The reverse
(raw then wrap) is never worth it. `rtk proxy <cmd>` runs raw but tracks
savings; `rtk run <cmd>` runs raw with no filtering or tracking.

Hooks (`rtk init --agent`: Claude Code, Codex, Copilot, Gemini, OpenCode,
Cursor, …) may rewrite raw shell commands to their `rtk` form and compress the
output — expected, not a broken wrapper. Piped/non-TTY output is unsafe to
compress (RTK #1282): run anything you'll parse or redirect raw, and set
`NO_COLOR=1` defensively if ANSI codes leak (#1409). On failure RTK's tee
fallback keeps the full output.

`--ultra-compact`, `rtk read -l aggressive`, and `rtk smart` are **lossy** —
opt in only for skimming something huge and unimportant.

**`-u` doesn't work.** The short form of `--ultra-compact` was removed
upstream; use the long flag.

**Grep is lossy by design.** `rtk grep` and `rtk rg` group matches by file,
strip whitespace, and truncate lines. Correct for surveys and rough counts; for
exact `line:content` use the native Grep tool.

## Catalogue

| Area | Commands |
|---|---|
| Core navigation | `rtk ls`, `rtk tree`, `rtk read <file>`, `rtk smart <file>`, `rtk find -name "*.go"`, `rtk grep "p" path`, `rtk rg "p" path`, `rtk wc <file>`, `rtk diff` |
| Git | `rtk git status`, `rtk git log --oneline -10`, `rtk git diff`, `rtk git show <commit>`, `rtk git blame <file>`, `rtk gt stack` |
| Go | `rtk go build ./...`, `rtk go test ./...`, `rtk go vet ./...`, `rtk go mod tidy`, `rtk golangci-lint run` |
| JS/frontend | `rtk npm test`, `rtk npx tsc --noEmit`, `rtk pnpm test`, `rtk bun test`, `rtk bunx`, `rtk jest`, `rtk vitest`, `rtk tsc --noEmit`, `rtk next build`, `rtk lint .`, `rtk prettier --check .`, `rtk format .`, `rtk playwright test`, `rtk prisma generate`, `rtk ctest` |
| Python | `rtk pytest -q`, `rtk ruff check .`, `rtk ruff format --check .`, `rtk mypy .`, `rtk pip list`, `rtk uv run <cmd>`, `rtk deno test` |
| Rust/Ruby/.NET/Android | `rtk cargo test`, `rtk rake test`, `rtk rubocop`, `rtk rspec`, `rtk dotnet test`, `rtk gradlew test`, `rtk sbt test`, `rtk mvn test`, `rtk mvnd test` |
| PHP | `rtk php artisan list`, `rtk phpunit`, `rtk phpstan analyze`, `rtk phpt`, `rtk pest`, `rtk paratest`, `rtk ecs`, `rtk pint` |
| GitHub | `rtk gh pr list`, `rtk gh pr view <number>`, `rtk gh issue list`, `rtk gh run list`, `rtk glab mr list` |
| Cloud/containers/DB | `rtk aws sts get-caller-identity`, `rtk docker ps`, `rtk kubectl get pods`, `rtk oc get pods`, `rtk psql -c "select 1"`, `rtk curl <url>`, `rtk wget <url>` |
| Test/lint helpers | `rtk test <cmd>`, `rtk err <cmd>`, `rtk lint <cmd>`, `rtk log <file-or-cmd>`, `rtk summary <cmd>` |
| Data/config | `rtk json <file>`, `rtk json --keys-only <file>`, `rtk deps`, `rtk env`, `rtk pipe` |
| Meta/analytics | `rtk gain`, `rtk gain --history`, `rtk gain --graph`, `rtk gain --quota`, `rtk gain --failures`, `rtk gain --all --format json`, `rtk cc-economics`, `rtk config`, `rtk telemetry`, `rtk learn`, `rtk proxy <cmd>`, `rtk run <cmd>`, `rtk discover`, `rtk session` |
| Hooks | `rtk init` (default Claude Code; `--codex`, `--copilot`, `--gemini`, `--opencode`, `--agent cursor`), `rtk hook claude`, `rtk rewrite <cmd>`, `rtk hook-audit`, `rtk trust`, `rtk untrust`, `rtk verify` |
| Options | `-v/--verbose`, `--ultra-compact`, `--skip-env` |

Measure **net** savings, not gross: `rtk gain --history` shows per-command
savings — a command re-run raw right after its `rtk` version was a net loss,
so stop wrapping that command. `rtk discover` surfaces new opportunities;
don't blanket-apply.
