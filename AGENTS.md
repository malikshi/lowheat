# Agent Instructions

This repository operates as a multi-agent workspace. This file is the **cross-agent
source of truth**. Agent-specific files (`CLAUDE.md`, `CODEX.md`, `GEMINI.md`)
are adapters — they add tool-specific deltas but must not
duplicate the tables below.

Read these companion surfaces when relevant:

| File | Role |
|---|---|
| `CLAUDE.md` | Claude Code adapter: hook scripts, plugins, skill paths, agent-style import |
| `GEMINI.md` | Gemini adapter: fallbacks for tools unavailable outside Claude Code |
| `CODEX.md` | Codex adapter: CodeDNA/RTK contract mirror |
| `COMMANDCODE.md` | CommandCode adapter: RTK manual-prefix contract |
| `RTK.md` | Token-efficient CLI proxy command reference |
| `.codedna` | Source map and session ledger (always read before editing source) |
| `.claude/settings.json` | Permissions, hooks, enabled plugins |
| `.mcp.json` or `.claude/mcp.json` | MCP server definitions (two servers expose `codegraph_*` family: `codegraph`, `caveman-shrink` — equivalent) |
| `.agent-style/` | Pinned prose rules imported by Claude Code |

## Operating Contract

This contract adapts guidance from `https://github.com/jbarbier/CLAUDE.md` (an
influence, not a live bootstrap dependency), plus Karpathy behavioral guidelines
from `https://github.com/multica-ai/andrej-karpathy-skills`. Bias toward caution;
use judgment on trivial tasks.

- **Complete real fixes** that are in reach. Don't leave work with a workaround,
  loose plan, or follow-up note when finishing now is safer and practical.
- **Search before building.** Check existing project code, standard libraries, and
  proven dependencies before creating a new abstraction or helper.
- **Split deterministic work from reasoning work.** Use scripts, tests, formatters,
  schema checks, targeted shell commands, repeatable facts, file lookups, parsing,
  counting, transformations, validation.
- **Curate context deliberately.** Load the relevant contract, CodeDNA entry, source
  files, tests, examples. Do not dump unrelated files into context.
- **Use skills when the task matches an installed skill.** If a repo-local skill is
  unavailable through the current tool surface, read its tracked `SKILL.md` for
  project guidance.
- **Codify repeated work.** By the third time a manual flow is needed, turn it into a
  script, skill, hook, or documented workflow.
- **Tie changes to visible evidence:** test result, config check, log line, metric,
  diff inspection, or other concrete validation proving the claim.
- **Report final status honestly** as one of `DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`,
  or `NEEDS_CONTEXT`, with evidence supporting the status.
- **Think before coding** (Karpathy §1). State assumptions explicitly. If multiple
  interpretations exist, present them — don't pick silently. If a simpler approach
  exists, say so. If unclear, stop and ask.
- **Simplicity first** (Karpathy §2). No speculative features, no abstractions for
  single-use code, no error handling for impossible scenarios. If 200 lines could be
  50, rewrite. Ask: "Would a senior engineer call this overcomplicated?"
- **Surgical changes** (Karpathy §3). Touch only what you must. Don't "improve" adjacent
  code. Match existing style. Remove only orphans your changes created — don't touch
  pre-existing dead code. Test: every changed line traces back to the user's request.
- **Goal-driven execution** (Karpathy §4). Define verifiable success criteria.
  "Add validation" → "write tests with invalid inputs, then make them pass." For
  multi-step tasks, state a brief: `1. [Step] → verify: [check]`. Strong criteria let
  you loop independently; weak criteria ("make it work") require constant
  clarification.

### How to use this file with a new agent

1. Read `AGENTS.md` first to understand the contract, CodeGraph, CodeDNA, and the
   hook-ledger protocol.
2. Read the matching adapter: `CLAUDE.md` for Claude Code, `CODEX.md` for Codex,
   `GEMINI.md` for Gemini.
3. Use RTK for shell commands per the Command Style section.
4. Use CodeGraph tools for structural code questions when available, or the
   `rg`/`find` fallbacks named in `GEMINI.md` when not.

### Programming-style notes

Some guidance comes from the upstream Claude Code template and was
intentionally adapted:

- `AGENTS.md` remains the source of truth. `CLAUDE.md`, `GEMINI.md`, `CODEX.md`
  stay as adapters rather than symlinks — each tool has different capabilities
  and fallbacks.
- Automatic commit and push are **disabled**. The upstream template recommends it,
  but this repository requires explicit approval before `git commit` or `git push`.

## Behavior Contract Details

- **Understand before declaring work complete.** Tests passing is necessary evidence
  for code changes, but it isn't sufficient — think about failure modes, what would
  break if the assumption is wrong.
- **Use the smallest verification that proves the change.** Features and bug fixes
  need deterministic tests where the repository has a viable test surface. LLM,
  prompt, and ranking behavior need an eval or documented manual rubric. Config and
  docs changes need syntax, diff, link, and marker checks.
- **Name the outcome before broad work.** For features, identify the metric,
  workflow step, user-visible behavior, or operational trace that should improve.
  If you can't state it, stop and clarify the requirement.
- **Prefer boring technology.** Use standard-library features, existing project
  helpers, and established dependencies before adding new tools. Add a new
  dependency only when it is clearly better than the existing path.
- **Keep architecture parallel-friendly** without forcing a `services/` rewrite. New
  subsystems should have clear ownership, contracts, tests, and docs. Follow the
  current repository layout unless the task explicitly includes restructuring.
- **Fan out independent work only when boundaries are clear.** Use isolated sessions,
  worktrees, or subagents for independent units; coordinate through contracts and
  avoid overlapping write sets.
- **Apply the confusion protocol for high-stakes ambiguity.** Stop, name the
  ambiguity, present two or three real options with trade-offs, and ask before
  proceeding. This applies to destructive operations, contradictory requirements,
  unclear production impact, and competing architectures.
- **Treat background jobs and backfills as operations, not fire-and-forget tasks.**
  For data-changing jobs, snapshot or document the rollback path first, monitor
  progress from a deterministic state, and produce a before/after report with file
  paths and metrics. Ask before snapshotting if data volume is large or production
  impact is unclear.
- **Report restart needs as changes.** If a service, bot, daemon, shell session, or
  browser needs a restart, list the exact command for the human to run. Never run
  `sudo` restarts yourself unless explicitly authorized.
- **Preserve safety boundaries.** Never commit secrets, destructive commands,
  production mutations, force pushes, hook bypasses, binaries, or model weights
  without explicit approval and a rollback plan.

## Command Style

- Wrap shell commands through **RTK**. RTK supports `git`, `go`, `pytest`, `ruff`,
  `npm`, `cargo`, `docker`, `kubectl`, `psql`, `curl`, `ls`, `tree`, `find`, `grep`,
  `read`, `wc`, `json`, `env`, `deps`, `log`, and many more. Run `rtk --help` to
  confirm support before reaching for a raw command.
- The mapping is transparent: `git status` becomes `rtk git status`, `cat file.py`
  becomes `rtk read file.py`, `python3 -m pytest -q` becomes `rtk pytest -q`. Treat any
  command missing from `rtk --help` as unsupported.
- Fall back to raw commands only when RTK is not installed, the subcommand is
  unsupported, or output must be machine-parsed without compression. See `RTK.md` for
  the full command catalogue or `rtk discover` for missed-savings hints.
- **PreToolUse is behavior, not a broken wrapper.** The PreToolUse hook rewrites a
  raw Bash `grep` into `rtk grep`, so a raw shell `grep` returns compressed output.
  That is expected; use the `Grep` tool instead when you need exact `line:content`
  for an edit.
- Avoid compound `cd <path> && <command>` chains. Use `git -C <path> ...`, pass the
  target path as an argument, or set the tool working directory.
- **Never run `git commit` or `git push` without explicit user approval.** This
  repository rule overrides any upstream templates that suggest automatic commit and
  push behavior.

## CodeGraph

This project runs a CodeGraph MCP server (`codegraph_*` tools) — a tree-sitter-parsed
knowledge graph of symbols, edges, and files. Use CodeGraph for structural questions:

| Question | Tool | Notes |
|---|---|---|
| Where is `X` defined? | `codegraph_search` | Quick symbol → file:line lookup |
| What calls `Y`? | `codegraph_callers` | Upstream dependency trail |
| What does `Y` call? | `codegraph_callees` | Downstream call graph |
| What would break if `Z` changed? | `codegraph_impact` | Breadth/depth-aware affected set |
| Show signature + source for `Y` | `codegraph_node` | Full body, includeCode=true |
| Show several related symbols | `codegraph_explore` | Read-equivalent; best first call for "how does this work" |
| List indexed files | `codegraph_files` | Filter/pattern/group |
| Check index health | `codegraph_status` | Files/nodes/edges counts |

Rules:

- For architecture and "how does this work" questions, start with `codegraph_explore`
  when source bodies are needed.
- For specific symbol lookups, start with `codegraph_search`.
- Do not grep first for symbols or call relationships. Use grep only for literal
  strings, log messages, comments, or when the specific file is already known.
- If CodeGraph reports a pending sync on edited files, read the files directly.

**Tool availability note.** Two MCP servers expose the `codegraph_*` family: `codegraph`
(the direct binary) and `caveman-shrink` (an `npx` wrapper around the same binary).
**They are equivalent** — use whichever prefix your agent surface exposes. If neither
is available, fall back to `rg`/`find` per the Gemini search table in `GEMINI.md`.

## Installed Plugins (Claude Code)

The following Claude Code plugins are installed and enabled. These are specific to
the Claude Code agent surface; treat them as context for other agents.

| Plugin | Scope | Purpose |
|---|---|---|
| `caveman@caveman` | user | Compressed communication, cavecrew agents, commit/review/stats skills |
| `codedna@codedna` | user | Source map annotations, session ledger, `codedna` CLI |
| `superpowers@claude-plugins-official` | user | Workflow skills (TDD, planning, debugging, parallel, verification) |
| `agent-skills@addy-agent-skills` | user | Addy Osmani engineering workflow skills |
| `code-review@claude-plugins-official` | project | Structured code review flows |
| `claude-md-management@claude-plugins-official` | project | CLAUDE.md file operations |

### Plugin Boundaries

- **CodeDNA**: annotation and session-ledger protocol. Use `/codedna:init` for
  first-time annotation, `/codedna:check` for coverage reports, `/codedna:impact <file>`
  for dependency chains.
- **Caveman**: compressed agent communication. Use when token efficiency matters and is
  explicitly triggered. Cavecrew agents (`builder`, `investigator`, `reviewer`)
  available via `.claude/skills/cavecrew`.
- **Superpowers**: workflow skills for structured development. Use when the request
  matches a Superpowers skill pattern (planning, TDD, debugging, parallel work,
  verification).
- **Agent Skills**: engineering workflow skills installed via
  `agent-skills@addy-agent-skills`. Use the Skill tool if the current surface exposes
  them; otherwise read the tracked `.agents/skills/<name>/SKILL.md` file as project
  guidance.
- **code-review**: structured review flows for diffs and PRs.
- **claude-md-management**: CLAUDE.md file operations and maintenance.

## Context Window Management

Avoid last 20% of context window for:
- Large-scale refactoring
- Feature implementation spanning multiple files
- Debugging complex interactions

Lower sensitivity tasks (single edits, docs, simple fixes) tolerate higher utilization.

## Workflow and Knowledge Capture

- **Workflow Surface Policy** — `skills/` is canonical. `commands/` is legacy.
  New workflow contributions land in `skills/` first. `commands/` only for
  migration shims or cross-harness parity.
- **Knowledge Capture** — Put captured knowledge in the right place:
  - Personal debugging notes, preferences, temporary context → memory
  - Team/project knowledge (architecture decisions, API changes, runbooks) →
    the project's existing docs structure
  - If an existing doc already captures the information, do not duplicate it
  - If no obvious location exists, ask before creating a new top-level file

## Coding Style

### Immutability (CRITICAL)

Create new objects; never mutate in place — `update(orig, field, val)` returns a new copy; `modify(...)` in-place is rejected. Immutable data prevents hidden side effects, simplifies debugging, enables safe concurrency.

### Core Principles

- **KISS** — simplest solution that works; clarity over cleverness.
- **DRY** — extract repeated logic; introduce abstractions only when repetition is real.
- **YAGNI** — no speculative features; start simple, refactor when pressure is real.

### File Organization

Many small files over few large files: 200–400 lines typical, 800 max, high cohesion, low coupling, organized by feature/domain not by type.

### Error Handling

Handle errors explicitly at every level. User-facing messages in UI code. Detailed context server-side. **Never** silently swallow.

### Input Validation

Validate at every system boundary. Schema-based where available. Fast fail with clear messages. All external data is untrusted.

### Naming Conventions

- Variables/functions: `camelCase` with descriptive names.
- Booleans: `is`/`has`/`should`/`can` prefix.
- Interfaces/types/components: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.
- Tests: snake_case describing the behavior under test.

### Code Smells to Avoid

- **Deep nesting** — prefer early returns once conditions stack.
- **Magic numbers** — named constants for thresholds, delays, limits.
- **Long functions** — split at 50 lines; each piece gets one responsibility.

### Quality Checklist

Before marking work complete:
- [ ] Readable, well-named identifiers.
- [ ] Functions focused (<50 lines).
- [ ] Files cohesive (<800 lines).
- [ ] No deeper than 4 nesting levels.
- [ ] Errors handled explicitly.
- [ ] No hardcoded values; use constants or config.
- [ ] Immutable patterns enforced.

## Security Guidelines

### Mandatory Security Checks

Before any commit:
- [ ] No hardcoded secrets (API keys, passwords, tokens).
- [ ] All user inputs validated.
- [ ] SQL injection prevention (parameterized queries).
- [ ] XSS prevention (sanitized HTML).
- [ ] CSRF protection enabled.
- [ ] Authentication/authorization verified.
- [ ] Rate limiting on appropriate surfaces.
- [ ] Error messages do not leak sensitive data.

### Secret Management

- **Never** hardcode secrets.
- Environment variables or a secret manager.
- Validate required secrets at startup.
- Rotate any exposed secrets.

### Security Review Triggers

Stop and invoke **security-reviewer** when touching: authentication or authorization code, user input, database queries, file-system operations, external API calls, cryptographic operations, payment or financial code.

### Security Response Protocol

1. Stop immediately.
2. Invoke **security-reviewer** agent.
3. Fix CRITICAL issues before continuing.
4. Rotate any exposed secrets.
5. Review the codebase for similar issues.

## Testing Requirements

### Minimum Test Coverage: 80%

Test types (all required):
1. **Unit tests** — individual functions, utilities, components.
2. **Integration tests** — API endpoints, database operations.
3. **E2E tests** — critical user flows (framework chosen per language).

### Test-Driven Development (Mandatory)

1. Write test first (RED) — must fail.
2. Write minimal implementation (GREEN) — must pass.
3. Refactor (IMPROVE).
4. Verify coverage (80%+).

### Troubleshooting Failures

1. Invoke **tdd-guide** agent.
2. Test isolation check.
3. Verify mocks.
4. Fix the implementation — not the tests, unless the test is wrong.

### Test Structure (AAA Pattern)

Arrange / Act / Assert. Use descriptive names explaining the behavior under test.

## Git Workflow

### Commit Message Format

```
<type>: <description>

<optional body>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`. Attribution disabled globally via `~/.claude/settings.json`.

### Pull Request Workflow

When creating PRs:
1. Analyze full commit history — not just the latest commit.
2. Use `git diff [base-branch]...HEAD` to see all changes.
3. Draft a comprehensive PR summary.
4. Include a test plan with TODOs.
5. Push with `-u` flag if on a new branch.

## Code Review Standards

### When to Review

Mandatory triggers:
- After writing or modifying code.
- Before any commit to shared branches.
- When security-sensitive code is changed.
- When architectural changes are made.
- Before merging pull requests.

Pre-review requirements:
- All automated checks (CI/CD) passing.
- Merge conflicts resolved.
- Branch up to date with target branch.

### Review Checklist

Before marking code complete:
- [ ] Readable and well-named.
- [ ] Functions focused (<50 lines).
- [ ] Files cohesive (<800 lines).
- [ ] No deep nesting (>4 levels).
- [ ] Errors handled explicitly.
- [ ] No hardcoded secrets or credentials.
- [ ] No leftover debug statements.
- [ ] Tests exist for new functionality.
- [ ] Test coverage meets 80% minimum.

### Review Severity Levels

| Level    | Meaning                                  | Action                   |
|----------|------------------------------------------|--------------------------|
| CRITICAL | Security vulnerability or data loss risk | BLOCK — must fix first.  |
| HIGH     | Bug or significant quality issue         | WARN — should fix first. |
| MEDIUM   | Maintainability concern                  | INFO — consider fixing.  |
| LOW      | Style or minor suggestion                | NOTE — optional.         |

### Agents

Use **code-reviewer** for general quality, **security-reviewer** for OWASP Top 10, plus per-language reviewers (`python-reviewer`, `go-reviewer`, `rust-reviewer`, `typescript-reviewer`, …).

### Approval Criteria

- **Approve**: no CRITICAL or HIGH issues.
- **Warning**: only HIGH issues remain.
- **Block**: CRITICAL issues found.

## Development Workflow

### Feature Implementation Workflow

0. **Research & Reuse** — mandatory first:
   - GitHub code search (`gh search repos`, `gh search code`).
   - Library docs via Context7 or vendor sources.
   - Exa only when the first two are insufficient.
   - Search package registries (npm, PyPI, crates.io, …).
   - Prefer forking portable solutions over hand-rolled code.
1. **Plan First** — invoke **planner** agent; identify dependencies and risks; break into phases.
2. **TDD Approach** — invoke **tdd-guide** agent; RED → GREEN → IMPROVE; verify 80%+ coverage.
3. **Code Review** — invoke **code-reviewer** agent; address CRITICAL and HIGH; fix MEDIUM when practical.
4. **Commit & Push** — conventional-commits format; comprehensive PR summary. This repository requires **explicit user approval** before `git commit` or `git push`.
5. **Pre-Review Checks** — CI/CD green, no merge conflicts, branch up to date.

## Project Skills

### Claude Code Skills (`.claude/skills/`)

Skills in `.claude/skills/` are symlinks into `.agents/skills/`:

| Skill | Purpose |
|---|---|
| `agent-rules-books` | Book-derived architecture, refactoring, legacy-code, reliability, DDD, enterprise-pattern guidance |
| `cavecrew` | Multi-agent crew (`builder`, `investigator`, `reviewer`) |
| `caveman` | Core compressed communication skill |
| `caveman-commit` | Token-efficient commit workflow |
| `caveman-compress` | Token-efficient output compression |
| `caveman-help` | Caveman usage reference |
| `caveman-review` | Token-efficient review workflow |
| `caveman-stats` | Token savings analytics |

### Addy Osmani Engineering Skills (`.agents/skills/`)

Installed via `agent-skills@addy-agent-skills`:

- `api-and-interface-design` — API design patterns
- `browser-testing-with-devtools` — DevTools-based browser testing
- `ci-cd-and-automation` — CI/CD pipeline patterns
- `code-review-and-quality` — Code review practices
- `code-simplification` — Simplifying complex code
- `context-engineering` — Context window optimization
- `debugging-and-error-recovery` — Systematic debugging
- `deprecation-and-migration` — Deprecation and migration workflows
- `documentation-and-adrs` — Documentation and architecture decision records
- `doubt-driven-development` — Questioning assumptions before implementing
- `frontend-ui-engineering` — Frontend UI work
- `git-workflow-and-versioning` — Git workflow guidance
- `idea-refine` — Refining ideas into implementation
- `incremental-implementation` — Step-by-step implementation
- `interview-me` — Interview-style requirement gathering
- `performance-optimization` — Performance profiling and optimization
- `planning-and-task-breakdown` — Planning and task decomposition
- `security-and-hardening` — Security review and hardening
- `shipping-and-launch` — Release and launch workflows
- `source-driven-development` — Working from source code
- `spec-driven-development` — Working from specifications
- `test-driven-development` — TDD workflow
- `using-agent-skills` — How to discover and use agent skills

### Superpowers Workflow Skills (`.agents/skills/superpowers-*`)

Provided by `superpowers@claude-plugins-official`, tracked in `.agents/skills/`:

- `superpowers-brainstorming` — Design exploration and implementation
- `superpowers-dispatching-parallel-agents` — Parallel independent tasks
- `superpowers-executing-plans` — Execute written plans with review checkpoints
- `superpowers-finishing-a-development-branch` — Merge/PR/cleanup decisions
- `superpowers-receiving-code-review` — Handle review feedback rigorously
- `superpowers-requesting-code-review` — Request structured review
- `superpowers-subagent-driven-development` — Subagent orchestration
- `superpowers-systematic-debugging` — Root-cause analysis
- `superpowers-test-driven-development` — TDD workflow
- `superpowers-using-git-worktrees` — Git worktree workflows
- `superpowers-using-superpowers` — Meta-skill
- `superpowers-verification-before-completion` — Verify before claiming done
- `superpowers-writing-plans` — Plan authoring
- `superpowers-writing-skills` — Create/edit skills

### Book-Derived Guidance (`.agents/skills/agent-rules-books/`)

Sourced from `ciembor/agent-rules-books`. For architecture, refactoring, legacy-code,
domain-driven (DDD), data-intensive design, enterprise patterns, or code-quality
decisions that need stronger design rules. Load only the relevant book guidance:

1. `references/mini/<rule-set>.mini.md` first
2. `references/nano/<rule-set>.nano.md` only under tight context
3. `references/full/<rule-set>.md` only when mini is insufficient

Do not load all full book files globally.

## Hooks (Claude Code)

Project hooks are defined in `.claude/settings.json`. Hook scripts live under `tools/`.

| Hook | Script | Purpose |
|---|---|---|
| `SessionStart` | `tools/claude_hook_session_start.sh` | Session banner; reads `.codedna` module count; emits RTK reminder |
| `PreToolUse` (Bash) | `rtk hook claude` | Rewrites raw shell commands into RTK equivalents |
| `PreToolUse` (Write\|Edit) | `tools/claude_hook_pretooluse.sh` | Reminds agent to check CodeDNA annotations before editing source |
| `PostToolUse` (Write\|Edit) | `tools/claude_hook_codedna.sh` | Validates CodeDNA headers after writes; emits L2 Rules: reminders |
| `Stop` | `tools/claude_hook_stop.sh` | Blocks completion until `.codedna` has an `agent_sessions` entry when tracked or untracked project files changed |

### Hook script details

**`claude_hook_session_start.sh`** — emits a JSON banner with project name and module
count so the agent reads `.codedna` before editing source files.

### CodeDNA reading protocol

1. Read the **module docstring** at the top of every Python file before reading any code.
2. Parse `exports:` — these are symbols you **must never rename or remove** without explicit instruction.
3. Parse `used_by:` — callers that depend on this file. Filter: "does this caller's domain intersect with my current task?" Only explore callers relevant to the specific change.
4. Parse `related:` — files sharing the same logic without importing each other. Same filter applies.
5. Parse `rules:` — hard constraints for every edit in this file; read **before writing any logic**.
6. Parse `agent:` — session history written by previous agents; read to understand *why* the current state exists.
7. For any function with a `Rules:` docstring, read and respect those before writing logic.

### CodeDNA editing protocol

1. **First step:** re-read `rules:`, the `agent:` history, and the `Rules:` of the function you are editing.
2. Apply all file-level constraints before writing.
3. After editing, check `used_by:` targets (especially `[cascade]`-tagged ones).
4. Never remove `exports:` symbols — they are contracts used by other files.
5. If you discover a constraint or fix a bug, **update `rules:` for the next agent**.
6. **Append a new `agent:` line** to the module docstring after editing: `model-id | provider | YYYY-MM-DD | session_id | what you did and what you noticed`. Keep only the last 5 entries — drop the oldest when adding a 6th. Full history is in git and `.codedna`.

### New-file mandate

Every new Python source file **must begin** with a CodeDNA module docstring (see header format below). This is a hard requirement for this repository.

### Session-start history

At session start, read the last 3 `agent_sessions:` entries in `.codedna` to understand recent project history. Also emits an RTK
reminder when `rtk` is on PATH.

**`claude_hook_pretooluse.sh`** — inspects the Write/Edit payload's `file_path`. If it
matches a source extension (`.py .ts .tsx .js .go .rs .java .kt .swift .rb .cs .php`),
emits a reminder to read the docstring and verify CodeDNA annotations before editing.

**`claude_hook_codedna.sh`** — runs `tools/validate_manifests.py` against the written
file. Skips `__init__.py`, `conftest.py`, `.agents/skills/*`, `.claude/skills/*`,
`.codex/*`, `migrations/`, `experiments/runs/`, `node_modules/`, `venv/`, `.venv/`.
Emits L2 reminders for public Python functions missing `Rules:` in their docstring.
Mode-aware: `agent` mode enforces inline `# Rules:` / `# message:` on non-trivial
logic; `semi` mode only reminds on business-logic changes.

**`claude_hook_stop.sh`** — collects changed files via `git diff --name-only HEAD`,
`git diff --cached --name-only`, and `git ls-files --others --exclude-standard`. If
tracked project files changed but `.codedna` has no new `session_id:` line in the diff,
blocks completion with the list of changed files and the required `agent_sessions`
fields. On success, prints an RTK session savings summary.

## CodeDNA

- Treat `.codedna` as the repo-local source map and session ledger.
- When tracked or untracked project files are changed, `.codedna` must include a
  matching `agent_sessions` entry in the diff. The Stop hook blocks completion
  otherwise.
- Before editing source files, check the nearest CodeDNA header for module purpose,
  exports, `used_by`, rules, and agent notes.
- After source changes, keep CodeDNA annotations current. Add or update module
  headers and public-function `Rules:` docstrings for behavior, constraints, and
  edge cases that changed.
- After editing, adding, deleting, or staging Python source, run
  `codedna init <path> --no-llm` or `codedna update <path>` on the touched path
  before commit validation.
- At session end, append an `agent_sessions` entry to `.codedna` with: `agent`,
  `provider`, `date`, `session_id`, `task`, `changed`, `visited`, `message`.

### CodeDNA header format (Python)

```python
"""filename.py — purpose ≤15 words.

exports: function(arg) -> type
used_by: caller.py → caller_fn
rules:   constraint the agent must respect
agent:   model-id | provider | YYYY-MM-DD | session_id | what you implemented and what you noticed
         message: "<open hypothesis or observation for the next agent>"
"""
```

### CodeDNA L2 function annotations (Python)

```python
def my_function():
    """Short description.

    Rules:   constraint the agent must respect
    message: model-id | YYYY-MM-DD | observation for next agent
    """
```

### CodeDNA modes

| Mode | Behavior |
|---|---|
| `agent` | Full enforcement: module headers + inline `# Rules:` / `# message:` on non-trivial logic + semantic naming (`type_shape_domain_origin`) |
| `semi` | Module headers + inline Rules: on new/edited code + semantic naming on new variables |
| `human` | Module headers only; L2 enforcement skipped |

## RTK

RTK is a token-optimized CLI proxy. Prefix shell commands with `rtk` for 60–90% token
savings on dev operations. Full reference: `rtk --help` or `~/.claude/RTK.md`.

### Rule

Always prefer RTK-wrapped commands. Bypass only when raw output is required, RTK is
unavailable, or RTK cannot run the command.

### Grep is lossy by design

`rtk grep` and `rtk rg` group matches by file, strip whitespace, and truncate lines.
That is correct for surveys ("which files mention X", rough counts), but it loses
exact `line:content`. When you need a precise line number or the full matching line
(for example, to feed an edit), use the `Grep` tool instead.

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

### JavaScript and Frontend Development

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

### Rust, Ruby, .NET, and Android

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

### Cloud, Containers, and Databases

```bash
rtk aws sts get-caller-identity # AWS CLI with compact JSON output
rtk docker ps                  # Docker with compact output
rtk kubectl get pods           # Kubectl with compact output
rtk psql -c "select 1"         # PostgreSQL output with compact tables
rtk curl https://example.com   # Curl with auto-JSON detection
rtk wget <url>                 # Download with compact progress output
```

### Testing and Linting

```bash
rtk test <cmd>                 # Run tests, show only failures
rtk err <cmd>                  # Run command, show only errors/warnings
rtk lint <cmd>                 # ESLint with grouped rule violations
rtk log <file-or-cmd>          # Filter and deduplicate log output
rtk summary <cmd>              # Run command and show heuristic summary
```

### Data and Config

```bash
rtk json <file>                # Show JSON (compact values)
rtk json --keys-only <file>    # Show JSON keys only
rtk deps                       # Summarize project dependencies
rtk env                        # Show environment variables (filtered, sensitive masked)
rtk pipe                       # Read stdin, apply an RTK filter, print filtered output
```

### Meta Commands

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

### Hook Integration

```bash
rtk hook claude                # Hook processors for Claude Code (rewrites Bash tool)
rtk rewrite <cmd>              # Rewrite a raw command to its RTK equivalent
rtk hook-audit                 # Show hook rewrite audit metrics
rtk init                       # Initialize RTK instructions for assistant CLI usage
rtk trust                      # Trust project-local TOML filters in current directory
rtk untrust                    # Revoke trust for project-local TOML filters
rtk verify                     # Verify hook integrity and TOML filter tests
```

### Options

```bash
-v, --verbose        # Verbosity level (-v, -vv, -vvv)
--ultra-compact      # Ultra-compact mode: ASCII icons, inline format
--skip-env           # Set SKIP_ENV_VALIDATION=1 for child processes
```

## Agent Style

This repository uses `agent-style` `v0.3.5` from
`https://github.com/yzhao062/agent-style` for technical prose. Full rule bodies are
pinned in `.agent-style/RULES.md`. When asked "is agent-style active?" or "what
writing rules apply here?", answer:

> agent-style v0.3.5 active: 21 rules (RULE-01..12 canonical + RULE-A..I
> field-observed); full bodies at .agent-style/RULES.md.

Apply agent-style to `.md`, `.tex`, `.rst`, `.txt`, PR descriptions, and API docs.
Do not apply it to code comments, log output, or other machine-oriented text.

### The 21 Rules (Names)

Canonical (Strunk & White 1959, Orwell 1946, Pinker 2014, Gopen & Swan 1990):

- RULE-01: Curse of knowledge.
- RULE-02: Passive voice.
- RULE-03: Abstract vs concrete language.
- RULE-04: Needless words.
- RULE-05: Dying metaphors.
- RULE-06: Avoidable jargon.
- RULE-07: Affirmative form.
- RULE-08: Claim calibration.
- RULE-09: Parallel structure.
- RULE-10: Related words together.
- RULE-11: Stress position.
- RULE-12: Long sentences, varied length.

Field-observed (maintainer observation of LLM output, 2022–2026):

- RULE-A: Bullet-point overuse.
- RULE-B: Em and en dashes as casual punctuation.
- RULE-C: Consecutive same-starts.
- RULE-D: Transition-word overuse.
- RULE-E: Paragraph-closing summary sentences.
- RULE-F: Inconsistent terms / abbreviation redefinition.
- RULE-G: Sentence-case section headings.
- **RULE-H: Handwavy claims and fabricated citations (critical).**
- RULE-I: Contractions in formal technical prose.

### Writing Defaults

- Use clear, scientifically accessible language.
- Keep meaningful technical detail and factual accuracy.
- Preserve Markdown, LaTeX, and reStructuredText formats unless asked otherwise.
- Do not convert prose into bullet points unless the content is a real list.
- Prefer full forms such as `it is` and `he would` in technical prose.
- Avoid casual em dashes and en dashes. Prefer commas, semicolons, colons, or
  parentheses.
- Keep terms consistent. Define an abbreviation once, then use it consistently.
- Break long or nested sentences into shorter sentences.
- Do not overuse transition words such as "Additionally", "Furthermore", or
  "Moreover".

### Escape Hatch

> "Break any of these rules sooner than say anything outright barbarous." — George
> Orwell, "Politics and the English Language" (1946), Rule 6. Rules are guides to
> clarity, not ends in themselves.

## Verification

Before claiming completion, run the smallest checks that prove the change:

- For config or docs edits, run syntax checks or targeted grep checks.
- For Python source edits, run CodeDNA validation and the relevant `rtk pytest`
  targets.
- For Go source edits, run `rtk go build ./...` and `rtk go vet ./...`.
- For browser-facing work, verify with a real browser when possible.
- Report any check that could not run and why.

## Source Repositories

| Source | Purpose |
|---|---|
| `https://github.com/rtk-ai/rtk` | RTK CLI and command reference |
| `https://github.com/JuliusBrussee/caveman` | Caveman plugin and cavecrew skills |
| `https://github.com/Larens94/codedna` | CodeDNA source map tool |
| `https://github.com/colbymchenry/codegraph` | CodeGraph MCP server |
| `https://github.com/obra/superpowers` | Superpowers plugin |
| `https://github.com/addyosmani/agent-skills` | Addy Osmani engineering skills |
| `https://github.com/ciembor/agent-rules-books` | Book-derived engineering rules |
| `https://github.com/jbarbier/CLAUDE.md` | Operating-contract influence merged into `AGENTS.md` |
| `https://github.com/multica-ai/andrej-karpathy-skills` | Karpathy behavioral guidelines |
| `https://github.com/yzhao062/agent-style` | Pinned prose rules in `.agent-style/` |
