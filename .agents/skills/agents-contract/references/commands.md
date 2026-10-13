# RTK Command Catalogue

RTK is a token-optimized CLI proxy that cuts 60–90% of the bash output an agent
reads — estimated as `bytes / 4`, so a share of output, never of the bill.
Full reference: `RTK.md` in the repo root, and `rtk --help`. Verified against
rtk 0.51.0.

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
  harness's own Read/Grep/Glob tools: lossless and numbered, and they bypass
  RTK. Caveats: native Grep truncates very long lines, and `rtk read -n` is
  the bulk alternative (verbatim content plus numbers; non-UTF-8 exits 1).

The fallback is one-way: if a wrapped view hid something you needed, re-run
raw once — that pair is a net loss, so stop wrapping that command. The reverse
(raw then wrap) is never worth it. `rtk proxy <cmd>` runs raw but tracks
savings; `rtk run <cmd>` runs raw with no filtering or tracking.

Piped/non-TTY output is unsafe to compress (RTK #1282): run anything you'll
parse or redirect raw, and set `NO_COLOR=1` defensively if ANSI codes leak
(#1409). On failure RTK's tee fallback keeps the full output.

`--ultra-compact`, `rtk read -l minimal`, `rtk read -l aggressive`,
`rtk read -m` (structure only), and `rtk smart` are **lossy** — opt in only
for skimming something huge and unimportant. `rtk read` with no `-l` copies
the file verbatim.

**`-u` doesn't work.** The short form of `--ultra-compact` was removed
upstream; use the long flag. After a subcommand, `-u` goes to the wrapped
command instead — `rtk ls -u` runs `ls -u`.

**Grep is lossy by design.** `rtk grep` and `rtk rg` group matches by file,
strip whitespace, and truncate lines. Correct for surveys and rough counts, and
`rtk recall <hash>` recovers what they elided (`rtk config recall` sets the
recovery mode); for exact `line:content` use the native Grep tool.

## Catalogue

| Area | Commands |
|---|---|
| Core navigation | `rtk ls`, `rtk tree`, `rtk read <file>`, `rtk smart <file>`, `rtk find "*.go" .`, `rtk grep -rn "p" dir`, `rtk rg "p" dir`, `rtk ast-grep run -p '<pat>'`, `rtk wc <file>`, `rtk diff <f1> <f2>` |
| Git | `rtk git status`, `rtk git log --oneline -10`, `rtk git diff`, `rtk git show <commit>`, `rtk git blame <file>`, `rtk git add/commit/push/pull`, `rtk git branch`, `rtk gt stack` |
| Go | `rtk go build ./...`, `rtk go test ./...`, `rtk go vet ./...`, `rtk go mod tidy`, `rtk golangci-lint run` |
| JS/frontend | `rtk npm test`, `rtk npx tsc --noEmit`, `rtk pnpm test`, `rtk pnpm list`, `rtk pnpm outdated`, `rtk bun test`, `rtk bun install/build`, `rtk bunx`, `rtk jest`, `rtk vitest`, `rtk tsc --noEmit`, `rtk next build`, `rtk lint .`, `rtk prettier --check .`, `rtk format .`, `rtk playwright test`, `rtk prisma generate`, `rtk ctest` |
| Python | `rtk pytest -q`, `rtk ruff check .`, `rtk ruff format --check .`, `rtk mypy .`, `rtk pip list`, `rtk pip outdated`, `rtk uv run <cmd>`, `rtk sqlfluff lint models/`, `rtk deno test`, `rtk deno lint/check` |
| Rust/Ruby/.NET/Android | `rtk cargo test`, `rtk cargo build/clippy`, `rtk rake test`, `rtk rubocop`, `rtk rspec`, `rtk dotnet test`, `rtk gradlew test`, `rtk sbt test`, `rtk mvn test`, `rtk mvnd test` |
| PHP | `rtk php artisan list`, `rtk phpunit`, `rtk phpstan analyze`, `rtk phpt`, `rtk pest`, `rtk paratest`, `rtk ecs`, `rtk pint` |
| GitHub | `rtk gh pr list`, `rtk gh pr view <number>`, `rtk gh issue list`, `rtk gh run list`, `rtk glab mr list` |
| Cloud/containers/DB | `rtk aws sts get-caller-identity`, `rtk docker ps`, `rtk docker images/logs <c>`, `rtk docker compose ps`, `rtk kubectl pods`, `rtk kubectl logs <pod>`, `rtk oc pods/logs <pod>`, `rtk psql -c "select 1"`, `rtk curl <url>`, `rtk wget <url>` |
| Test/lint helpers | `rtk test <cmd>`, `rtk err <cmd>`, `rtk run -c '<script>'`, `rtk lint <cmd>`, `rtk log <file-or-cmd>`, `rtk summary <cmd>` |
| Data/config | `rtk json <file>`, `rtk json --keys-only <file>`, `rtk deps`, `rtk env -f <FILTER>`, `rtk pipe` |
| Meta/analytics | `rtk gain`, `rtk gain --history`, `rtk gain --graph`, `rtk gain --daily`, `rtk gain --quota`, `rtk gain --failures`, `rtk gain --recalls`, `rtk gain --all --format json`, `rtk cc-economics`, `rtk config`, `rtk config recall [mode]`, `rtk telemetry`, `rtk learn`, `rtk recall <hash>`, `rtk proxy <cmd>`, `rtk run <cmd>`, `rtk discover`, `rtk session` |
| Options | `-v/--verbose`, `--ultra-compact`, `--skip-env` |

Measure **net** savings, not gross: `rtk gain --history` shows per-command
savings — a command re-run raw right after its `rtk` version was a net loss,
so stop wrapping that command. `rtk discover` surfaces new opportunities;
don't blanket-apply. `rtk gain --recalls` shows what compression cost back in
recalls; `rtk gain --daily` gives the day-by-day trend.
