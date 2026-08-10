# RTK Command Catalogue

RTK is a token-optimized CLI proxy (60–90% token savings). Full catalogue:
`RTK.md` in the repo root or `~/.claude/RTK.md`, and `rtk --help`.

**Grep is lossy by design.** `rtk grep` and `rtk rg` group matches by file,
strip whitespace, and truncate lines. Correct for surveys and rough counts; for
exact `line:content` use the native Grep tool.

| Area | Commands |
|---|---|
| Core navigation | `rtk ls`, `rtk tree`, `rtk read <file>`, `rtk smart <file>`, `rtk find -name "*.go"`, `rtk grep "p" path`, `rtk rg "p" path`, `rtk wc <file>` |
| Git | `rtk git status`, `rtk git log --oneline -10`, `rtk git diff`, `rtk git show <commit>`, `rtk git blame <file>` |
| Go | `rtk go build ./...`, `rtk go test ./...`, `rtk go vet ./...`, `rtk go mod tidy`, `rtk golangci-lint run` |
| JS/frontend | `rtk npm test`, `rtk npx tsc --noEmit`, `rtk pnpm test`, `rtk jest`, `rtk vitest`, `rtk tsc --noEmit`, `rtk next build`, `rtk lint .`, `rtk prettier --check .`, `rtk format .`, `rtk playwright test`, `rtk prisma generate` |
| Python | `rtk pytest -q`, `rtk ruff check .`, `rtk ruff format --check .`, `rtk mypy .`, `rtk pip list` |
| Rust/Ruby/.NET/Android | `rtk cargo test`, `rtk rake test`, `rtk rubocop`, `rtk rspec`, `rtk dotnet test`, `rtk gradlew test` |
| GitHub | `rtk gh pr list`, `rtk gh pr view <number>`, `rtk gh issue list`, `rtk gh run list`, `rtk glab mr list` |
| Cloud/containers/DB | `rtk aws sts get-caller-identity`, `rtk docker ps`, `rtk kubectl get pods`, `rtk psql -c "select 1"`, `rtk curl <url>`, `rtk wget <url>` |
| Test/lint helpers | `rtk test <cmd>`, `rtk err <cmd>`, `rtk lint <cmd>`, `rtk log <file-or-cmd>`, `rtk summary <cmd>` |
| Data/config | `rtk json <file>`, `rtk json --keys-only <file>`, `rtk deps`, `rtk env`, `rtk pipe` |
| Meta/analytics | `rtk gain`, `rtk gain --history`, `rtk gain --graph`, `rtk config`, `rtk telemetry`, `rtk learn`, `rtk proxy <cmd>`, `rtk run <cmd>`, `rtk discover`, `rtk session` |
| Hooks | `rtk hook claude`, `rtk rewrite <cmd>`, `rtk hook-audit`, `rtk init`, `rtk trust`, `rtk untrust`, `rtk verify` |
| Options | `-v/--verbose`, `--ultra-compact`, `--skip-env` |
