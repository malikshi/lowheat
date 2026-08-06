# Agent Instructions

This repository operates as a multi-agent workspace. This file is the single,
self-contained instruction surface and the **cross-agent source of truth**.
Agent adapters (such as `CLAUDE.md`) add tool-specific deltas only; they never
duplicate this file.

## How to use this file

Read the Operating Principles and the Work Loop once — they apply to every task.
Then use the table to find the section you need, and follow it literally.

| When you are… | Read |
|---|---|
| Starting any task | Operating Principles → Work Loop |
| Running a command | Command Style |
| Writing or editing code | Coding Style → CodeDNA |
| Writing a test | Testing Requirements |
| Touching auth, secrets, user input, or data | Security Guidelines |
| About to commit | Git Workflow (Session trailers are mandatory) |
| Done with a change | Definition of Done → Verification |
| Unclear, blocked, or ambiguous | Operating Principles → Confusion Protocol |

Do not read the whole file into context for a small task. Load the sections that
apply, follow them, and move on.

## Operating Principles

This contract adapts guidance from `https://github.com/jbarbier/CLAUDE.md` (an
influence, not a live bootstrap dependency) and Karpathy behavioral guidelines
from `https://github.com/multica-ai/andrej-karpathy-skills`. Bias toward caution;
use judgment on trivial tasks.

### Think before coding

State assumptions explicitly. If multiple interpretations exist, present them —
do not pick silently. If a simpler approach exists, say so. If unclear, stop and
ask. Never start writing code when the requirement is vague; name the outcome
first: the metric, workflow step, user-visible behavior, or operational trace
that should improve. If you cannot state what "done" looks like, you are not
ready to start.

### Do the smallest thing that works

- **Simplicity first.** No speculative features, no abstractions for single-use
  code, no error handling for impossible scenarios. If 200 lines could be 50,
  rewrite. Ask: "Would a senior engineer call this overcomplicated?"
- **Search before building.** Check existing project code, standard libraries,
  and proven dependencies before creating a new abstraction or helper. Prefer
  boring technology; add a dependency only when it is clearly better than the
  existing path.
- **Surgical changes.** Touch only what you must. Do not "improve" adjacent
  code. Match existing style. Remove only orphans your changes created; never
  touch pre-existing dead code. Every changed line must trace back to the
  request.

### Verify, don't assume

- **Split deterministic work from reasoning work.** Use scripts, tests,
  formatters, schema checks, and targeted shell commands for repeatable facts:
  file lookups, parsing, counting, transformations, validation.
- **Tie every claim to visible evidence** — a test result, config check, log
  line, metric, or diff inspection. Features and bug fixes need deterministic
  tests; LLM, prompt, and ranking behavior needs an eval or documented manual
  rubric; config and docs changes need syntax, diff, link, and marker checks.
- **Report final status honestly** as one of `DONE`, `DONE_WITH_CONCERNS`,
  `BLOCKED`, or `NEEDS_CONTEXT`, with the evidence that supports it.

### Complete real fixes

Do not leave work as a workaround, loose plan, or follow-up note when finishing
now is safer and practical. Tests passing is necessary evidence, not sufficient:
think through the failure modes and what would break if the assumption is wrong.

### Curate context deliberately

Load the relevant contract, CodeDNA entry, source files, tests, and examples.
Do not dump unrelated files into context. Use skills when the task matches an
installed skill; if a repo-local skill is unavailable through the current tool
surface, read its tracked `SKILL.md` for project guidance.

### Codify repeated work

By the third time a manual flow is needed, turn it into a script, skill, hook,
or documented workflow.

### Confusion protocol

For high-stakes ambiguity — destructive operations, contradictory requirements,
unclear production impact, competing architectures — stop, name the ambiguity,
present two or three real options with trade-offs, and ask before proceeding.

### Operations discipline

- **Background jobs and backfills are operations, not fire-and-forget.**
  Snapshot or document the rollback path first, monitor from a deterministic
  state, produce a before/after report with file paths and metrics. Ask before
  snapshotting if data volume is large or production impact is unclear.
- **Report restart needs as changes.** If a service, bot, daemon, shell
  session, or browser needs a restart, list the exact command for the human to
  run. Never run `sudo` restarts yourself unless explicitly authorized.
- **Preserve safety boundaries.** Never commit secrets, destructive commands,
  production mutations, force pushes, hook bypasses, binaries, or model weights
  without explicit approval and a rollback plan.
- **Fan out independent work only when boundaries are clear.** Use isolated
  sessions, worktrees, or subagents for independent units; coordinate through
  contracts and avoid overlapping write sets.
- **Keep architecture parallel-friendly.** New subsystems have clear
  ownership, contracts, tests, and docs. Follow the current repository layout
  unless the task explicitly includes restructuring.

## Command Style

- Wrap shell commands through **RTK**. RTK supports `git`, `go`, `pytest`,
  `ruff`, `npm`, `cargo`, `docker`, `kubectl`, `psql`, `curl`, `ls`, `tree`,
  `find`, `grep`, `read`, `wc`, `json`, `env`, `deps`, `log`, and many more.
  Run `rtk --help` to confirm support before reaching for a raw command.
- The mapping is transparent: `git status` becomes `rtk git status`,
  `cat file.py` becomes `rtk read file.py`, `python3 -m pytest -q` becomes
  `rtk pytest -q`. Treat any command missing from `rtk --help` as unsupported.
- Fall back to raw commands only when RTK is not installed, the subcommand is
  unsupported, or output must be machine-parsed without compression. See
  `RTK.md` for the full command catalogue or `rtk discover` for missed-savings
  hints.
- **PreToolUse is behavior, not a broken wrapper.** The PreToolUse hook
  rewrites a raw Bash `grep` into `rtk grep`, so a raw shell `grep` returns
  compressed output. That is expected; use the `Grep` tool instead when you
  need exact `line:content` for an edit.
- Avoid compound `cd <path> && <command>` chains. Use `git -C <path> ...`,
  pass the target path as an argument, or set the tool working directory.
- **Never run `git commit` or `git push` without explicit user approval.** This
  repository rule overrides any upstream templates that suggest automatic
  commit and push behavior.

### RTK quick reference

RTK is a token-optimized CLI proxy (60–90% token savings). Full catalogue:
`RTK.md` or `~/.claude/RTK.md`, and `rtk --help`.

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
| Meta/analytics | `rtk gain`, `rtk gain --history`, `rtk gain --session`, `rtk config`, `rtk telemetry`, `rtk learn`, `rtk proxy <cmd>`, `rtk run <cmd>`, `rtk discover`, `rtk session` |
| Hooks | `rtk hook claude`, `rtk rewrite <cmd>`, `rtk hook-audit`, `rtk init`, `rtk trust`, `rtk untrust`, `rtk verify` |
| Options | `-v/--verbose`, `--ultra-compact`, `--skip-env` |

## The Work Loop

This is the canonical way every task is delivered. It is the difference between
a junior firing code and a senior shipping a change: each step ends with a
verification point before the next begins.

1. **Understand.** Read the request twice. State the problem, the *why* behind
   it, and the acceptance criteria.
   → Verify: you can say what "done" looks like.
2. **Read first.** Read the files you will touch, their CodeDNA headers, and
   their tests. Never propose changes to code you have not read.
   → Verify: you know what exists before you add anything.
3. **Plan the smallest change.** Name the risks and the revert path. For
   multi-step tasks, state a brief: `1. [Step] → verify: [check]`.
   → Verify: the plan fits the request and nothing else.
4. **Implement with TDD.** RED → GREEN → IMPROVE per Testing Requirements.
   Work in small increments; verify each step before starting the next.
   → Verify: the targeted tests pass, not just the suite.
5. **Self-review the diff.** Run the Definition of Done checklist on your own
   work before anyone else sees it.
   → Verify: every changed line traces back to the request.
6. **Prove it.** Run the smallest check that proves the change per the
   Verification section.
   → Verify: evidence exists for every claim you will make.
7. **Report and record.** Report status honestly; if files changed, commit with
   the session trailers under Git Workflow.

If any step fails, stop and fix the root cause — do not work around it, do not
declare done.

## Engineering Standards

### Definition of Done

Before any change is complete, self-review, committed, or merged, every item
must hold:

- [ ] Readable, well-named identifiers; no magic numbers (named constants)
- [ ] Functions focused (<50 lines); files cohesive (<800 lines); no nesting
  deeper than 4 levels
- [ ] Errors handled explicitly at every level; nothing silently swallowed
- [ ] No hardcoded secrets or credentials; user input validated at every
  boundary
- [ ] No leftover debug statements; no dead code introduced
- [ ] Tests exist for new functionality; coverage meets the 80% minimum
- [ ] The change is the smallest that satisfies the request
- [ ] Evidence for the change exists per the Verification section

### Coding Style (adapted from ECC)

Core principles, adapted from the **Everything Claude Code** rule packs
(`https://github.com/affaan-m/ECC`). Read them as starting posture, not
universal law; relax what your task or agent surface does not need.

- **KISS** — simplest solution that works; clarity over cleverness.
- **DRY** — extract repeated logic; introduce abstractions only when repetition
  is real.
- **YAGNI** — no speculative features; start simple, refactor when pressure is
  real.
- **Immutability (CRITICAL)** — create new objects; never mutate in place.
  `update(orig, field, val)` returns a new copy; `modify(...)` in-place is
  rejected. Immutable data prevents hidden side effects, simplifies debugging,
  and enables safe concurrency.
- **File organization** — many small files over few large files: 200–400 lines
  typical, 800 max, high cohesion, low coupling, organized by feature/domain,
  not by type.
- **Error handling** — handle errors explicitly at every level. User-facing
  messages in UI code; detailed context server-side. Never silently swallow.
- **Input validation** — validate at every system boundary; schema-based where
  available; fast fail with clear messages. All external data is untrusted.
- **Naming conventions** — variables/functions: `camelCase`; booleans:
  `is`/`has`/`should`/`can` prefix; interfaces/types/components: `PascalCase`;
  constants: `UPPER_SNAKE_CASE`; tests: `snake_case` describing the behavior
  under test.

### Testing Requirements

**Minimum coverage: 80%.** All three test types are required:
1. **Unit tests** — individual functions, utilities, components.
2. **Integration tests** — API endpoints, database operations.
3. **E2E tests** — critical user flows (framework chosen per language).

**Test-Driven Development (mandatory):**
1. Write the test first (RED) — it must fail.
2. Write the minimal implementation (GREEN) — it must pass.
3. Refactor (IMPROVE).
4. Verify coverage (80%+).

**Test structure:** AAA pattern — Arrange / Act / Assert — with descriptive
names explaining the behavior under test.

**When tests fail, troubleshoot in order:**
1. Verify test isolation — each test runs independently of others.
2. Verify mocks — mock assumptions match real behavior.
3. Fix the implementation — not the tests, unless the test is wrong.

### Security Guidelines

**Mandatory checks before any commit:**
- [ ] No hardcoded secrets (API keys, passwords, tokens)
- [ ] All user inputs validated
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (sanitized HTML)
- [ ] CSRF protection enabled
- [ ] Authentication/authorization verified
- [ ] Rate limiting on appropriate surfaces
- [ ] Error messages do not leak sensitive data

**Secret management:** never hardcode secrets. Use environment variables or a
secret manager; validate required secrets at startup; rotate any exposed
secrets.

**Security response protocol:** on exposure, stop immediately. Identify the
exposed secret, credential, or entry point. Fix the vulnerability before
continuing. Rotate any exposed secrets. Review the codebase for similar issues.

## Git Workflow

### Commit message format

```
<type>: <description>

<optional body>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`.
Attribution is disabled globally via `~/.claude/settings.json`.

### Session trailers

At the end of every session that modified files, record the work in the commit.
When you create the commit (explicit user approval required per Command Style),
add these trailers:

```
AI-Agent:    <model-id>
AI-Provider: <provider>
AI-Session:  <session_id>
AI-Visited:  <comma-separated list of files read>
AI-Message:  <one-line summary of what was found or left open>
```

Git is the authoritative audit log; do not keep a separate ledger file.

### Pull requests

1. Analyze full commit history — not just the latest commit.
2. Use `git diff [base-branch]...HEAD` to see all changes.
3. Draft a comprehensive PR summary.
4. Include a test plan with TODOs.
5. Push with `-u` flag if on a new branch.

## Code Review Standards

Review is mandatory after writing or modifying code, before any commit to
shared branches, when security-sensitive code changes, and before merging.
Pre-review requirements: all automated checks (CI/CD) passing, no merge
conflicts, branch up to date with target.

**Severity levels:**

| Level | Meaning | Action |
|---|---|---|
| CRITICAL | Security vulnerability or data loss risk | BLOCK — must fix first |
| HIGH | Bug or significant quality issue | WARN — should fix first |
| MEDIUM | Maintainability concern | INFO — consider fixing |
| LOW | Style or minor suggestion | NOTE — optional |

**Approval criteria:** approve when no CRITICAL or HIGH issues remain; warn
when only HIGH issues remain; block on any CRITICAL issue.

## CodeDNA

CodeDNA is a source-annotation convention adapted from
`https://github.com/Larens94/codedna`. This repository uses the convention only.
It does not use the `codedna` binary, a validator, git hooks, or a `.codedna`
ledger file. Git is the authoritative audit log. Agents apply and maintain
these annotations by hand while reading and editing code.

### Scope

Apply CodeDNA annotations to every source file in the project whose language
supports comments: Python, Go, JavaScript, TypeScript, Rust, shell, and any
other commented source language. Do not annotate documentation, plain text, or
commentless data formats: `.md`, `.tex`, `.rst`, `.txt`, `.json`, and similar.

### Module header (L1)

Every source file begins with a module header written in the file's native
comment syntax. Python uses the module docstring; Go, JavaScript, TypeScript,
and Rust use leading `//` lines; shell uses leading `#` lines. Fields appear in
this order:

- First line: `filename — <what it does, 15 words or fewer>.`
- `exports:` public symbols this file provides, separated by ` | `. Use `->`
  for a return type.
- `used_by:` consumer files that depend on this file, one per line as
  `consumer_file → symbol(s)`. Tag a consumer `[cascade]` when an edit here must
  be verified against it.
- `related:` (optional) files that share the same pattern or logic without an
  import link.
- `rules:` the hard constraint agents must never violate, or `none`.
- `agent:` a rolling history of the last 5 sessions, oldest first, newest
  appended last: `model-id | provider | YYYY-MM-DD | session_id | what you did
  and what you noticed`.
- `message:` (optional) an open hypothesis or observation for the next agent,
  indented beneath `agent:`.

Python module docstring:

```python
"""src/config.py — Bot configuration with lazy environment loading.

exports: class Config | get_config()
used_by: manager/src/admin/menu.py → DB_FILE, logger [cascade]
rules:   Never read os.environ at import time; load lazily in get_config().
agent:   claude-fable-5 | anthropic | 2026-07-24 | s_example | tightened lazy load
"""
```

Go, TypeScript, JavaScript, or Rust leading comments:

```go
// auth.go — API-key middleware for the ZiVPN HTTP surface.
//
// exports: Middleware
// used_by: ZiVPN/cmd/zivpn-api/main.go → Middleware
// rules:   none
// agent:   claude-fable-5 | anthropic | 2026-07-24 | s_example | reviewed guard
```

### Function annotation (L2)

Every public function carries a `Rules:` block in its docstring or leading
comment stating what the agent must or must not do there. Omit it only for
trivial functions with no domain constraint.

```python
def charge(amount_cents: int) -> None:
    """Charge the customer for a completed order.

    Rules:   amount_cents is in cents, not euros; divide by 100 before display.
    """
```

### Inline annotations on complex logic

Place a `# Rules:` or `# message:` comment (native comment syntax) directly
above a block when the block encodes a business rule, filters or transforms in a
non-obvious way, depends on step order, or works around an edge case. Skip
simple getters and setters, obvious control flow, and standard library calls.

```python
# Rules: skip cancelled orders — status=4 means cancelled in the legacy DB.
```

### Agent protocols

**Reading files.** Read the module header before any code. Parse `exports:`,
the symbols you must never rename or remove without explicit instruction. Parse
`used_by:` and `related:`, then follow only the callers whose domain intersects
your current task, not all of them blindly. Parse `rules:`, the hard constraints
for every edit in this file. Parse `agent:`, the session history that explains
why the current state exists. Read the `Rules:` block of any function before
writing logic in it.

**Writing new files.** Begin every new source file with a complete L1 module
header, and give every public function an L2 `Rules:` block.

**Writing good rules.** Rules must be specific and actionable. Write
`soft-delete via deleted_at — never issue DELETE` rather than a vague line such
as `handle deletes carefully`. Never write vague rules such as `handle errors
gracefully` or `follow best practices`. Use `rules: none` only when a file
genuinely has no domain constraint. Every time you discover a constraint, fix a
bug, or notice a non-obvious behavior, add it to `rules:` immediately. This is
how you communicate with the next agent.

**Writing critical functions.** Give every public function a `Rules:`
annotation that covers its constraints, invariants, and edge cases.

**Editing files.** Re-read `rules:`, the `agent:` history, and the `Rules:` of
the function you are editing. Apply all file-level constraints before writing.
After editing, check `used_by:` targets, especially `[cascade]`-tagged ones.
Never remove `exports:` symbols; they are contracts used by other files. If you
discover a constraint or fix a bug, update `rules:` for the next agent. Append a
new `agent:` line to the module header in the form `model-id | provider |
YYYY-MM-DD | session_id | what you did and what you noticed`. Keep only the last
5 entries; drop the oldest when adding a 6th. Full history is in git.

**Session end protocol.** At the end of every session that modifies files,
record the work in the git commit with the session trailers defined under Git
Workflow; do not keep a separate ledger file.

## Verification

Run the smallest check that proves the change before claiming completion:

- For config or docs edits: syntax checks or targeted grep checks.
- For Python source edits: the relevant `rtk pytest` targets.
- For Go source edits: `rtk go build ./...` and `rtk go vet ./...`.
- For browser-facing work: verify with a real browser when possible.
- Report any check that could not run and why.

## Environment

### Companion surfaces

| File | Role |
|---|---|
| `CLAUDE.md` | Claude Code adapter: per-tool deltas only; inherits everything else from this file |
| `RTK.md` | Token-efficient CLI proxy command reference (installed copy: `~/.claude/RTK.md`) |
| `README.md` | Project bootstrap and layout |
| `.claude/settings.json` | Permissions, hooks, enabled plugins |

### Installed plugins

| Plugin | Scope | Purpose |
|---|---|---|
| `superpowers@claude-plugins-official` | user | Workflow skills (TDD, planning, debugging, parallel, verification) |

Use the Skill tool when a Superpowers skill matches the task; otherwise read
the tracked `SKILL.md` for project guidance.

### Context window management

Avoid the last 20% of the context window for large-scale refactoring, feature
implementation spanning multiple files, and debugging complex interactions.
Lower-sensitivity tasks (single edits, docs, simple fixes) tolerate higher
utilization.

### Knowledge capture

Put captured knowledge in the right place:

- Personal debugging notes, preferences, temporary context → memory
- Team/project knowledge (architecture decisions, API changes, runbooks) → the
  project's existing docs structure
- If an existing doc already captures the information, do not duplicate it
- If no obvious location exists, ask before creating a new top-level file

## Source Repositories

| Source | Purpose |
|---|---|
| `https://github.com/rtk-ai/rtk` | RTK CLI and command reference |
| `https://github.com/obra/superpowers` | Superpowers plugin |
| `https://github.com/jbarbier/CLAUDE.md` | Operating-contract influence merged into this file |
| `https://github.com/multica-ai/andrej-karpathy-skills` | Karpathy behavioral guidelines |
| `https://github.com/affaan-m/ECC` | Rule-pack influence for coding style, security, testing, git workflow, code review, development workflow |
