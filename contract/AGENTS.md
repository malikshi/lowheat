# Agent Instructions

Contract-Version: 2026-11-05

This repository operates as a multi-agent workspace. This file is the thin,
cross-agent core: universal behavior, routing, and the rules every task follows.
Detailed references load only when a task needs them.

## How to use this file

Read the Operating Principles and the Work Loop once — they apply to every task.
Then use the table to find the section you need, and follow it literally.

| When you are… | Read |
|---|---|
| Starting any task | Session bootstrap, then Operating Principles + The Work Loop |
| Resolving conflicting instructions | How to use this file → Precedence |
| Sizing a task | Operating Principles → Task sizing |
| Deciding how much to build | Operating Principles → Do the smallest thing that works |
| Running a command | Execution & Delivery → Command Style |
| Sending a reply or report | Execution & Delivery → Communication Style |
| Writing or editing code | Engineering Standards → Coding Style + CodeDNA, then `codedna.md` |
| Writing a test | Engineering Standards → Testing Requirements |
| Touching auth, secrets, user input, or data | Engineering Standards → Security Guidelines |
| About to commit | Execution & Delivery → Git Workflow |
| Reviewing or merging code | Execution & Delivery → Code Review Standards |
| Changing docs or config | Engineering Standards → Verification |
| Done with a change | Engineering Standards → Definition of Done → Verification |
| Unclear, blocked, or ambiguous | Operating Principles → Confusion protocol |

Do not load every companion for a small task. Load the one that owns the detail
you need, follow it, and move on.

### Companion references

| File | Load when | Covers |
|---|---|---|
| `codedna.md` | writing or editing source | full annotation convention, headers, function rules, checker |
| `RTK.md` | wrapping shell commands | decision rule, fidelity zones, full command catalogue |
| `semble.md` | locating code | discovery ladder, CLI verbs, MCP fallback, caveats |
| `caveman.md` | changing reply mode, commits, or reviews | voice rules, modes, commit and review formats, optional layer |
| `ponytail.md` | choosing scope or explaining a shortcut | ladder, never-cut list, levels, disclosure line |

### Precedence

When instruction sources disagree, the higher entry wins:

1. The harness system prompt and its safety rules.
2. The user's current request.
3. This file, read from disk in the project.
4. Skill summaries, pinned copies, and mirrors of this file.

A copy that lacks this file's `Contract-Version` line, or shows a different one,
is stale. Refresh the copy from the canonical checkout, then act on this file.

### Session bootstrap (mandatory)

This gate sits below the harness system prompt and the user's current request in
Precedence. Within those limits, before the first tool call of any task:

1. **Load the `agents-contract` skill.** Its checklist is the executable form of
   this file. If the harness cannot load it, read the tracked
   `.agents/skills/agents-contract/SKILL.md` when present; otherwise state
   `skill unavailable` and follow this file. Do not begin with a tool call and
   load it later.
2. **State the task size** in one line: `small`, `medium`, or `large`.
3. **State the command lane.** RTK-wrapped is the default; raw is allowed only
   for exact bytes, parseable output, streaming, or secrets, and the reason must
   be stated. A task that wraps nothing must say why.
4. **Check installed surfaces** when the contract or skill changed and the
   lowheat checkout is available: `python3 install.py --check --harness <name>`
   from that checkout. Refresh a stale copy with `--force`, then restart the
   harness or session so it reloads instruction and skill metadata. A running
   session keeps the old snapshot. Without the checkout, compare
   `Contract-Version` and refresh from the source.

A task started without steps 1–3 is non-compliant. Stop, perform them, then
continue. The final report carries the compliance record defined below.

## Operating Principles

This contract adapts guidance from `https://github.com/jbarbier/CLAUDE.md` (an
influence, not a live bootstrap dependency), Karpathy behavioral guidelines
from `https://github.com/multica-ai/andrej-karpathy-skills`, and ECC rule packs
from `https://github.com/affaan-m/ECC`. Bias toward caution; use judgment on
trivial tasks.

### Task sizing

Scale the ceremony to the change, and say the call out loud. State the size in
one line when starting any non-trivial task; a wrong mode is only correctable
if the choice is visible.

- **small** — typo, copy change, styling value, config tweak, rename, any
  one-or-two-file mechanical edit with no behavior change. Solo. Run only the
  checks that cover what was touched. A non-behavioral change needs no new
  test.
- **medium** — localized behavior change or bug fix inside one module. Solo by
  default; fan out only if the work splits into truly independent units. Run
  the touched module's tests. Bug fixes ship the regression test.
- **large** — new feature, cross-module or contract change, architecture work,
  anything judgment-heavy (design, approach, UX). Full protocol: plan first,
  full test + eval suites for every module touched, consider fan-out.

When torn between two sizes, pick the smaller one and say so. Escalate the
moment the change turns out bigger than triaged, and print the updated call
with what changed it. The final report restates what was actually run so the
triage call can be judged after the fact.

### Think before coding

State assumptions explicitly and distinguish verified facts from uncertainty.
If multiple interpretations exist, present them — do not pick silently. If a
simpler approach exists, say so. Challenge weak assumptions candidly. Ask
questions only when a decision is materially ambiguous or risky, or requires
approval. Never start writing code when the requirement is vague; name the
outcome first: the metric, workflow step, user-visible behavior, or operational
trace that should improve. "It works" is not an outcome — if you cannot state
what gets measurably better and how you will see it, that is a Confusion
Protocol stop. If you cannot state what "done" looks like, you are not ready
to start.

### Do the smallest thing that works

The smallest change that **fully** works. Completeness is the floor;
minimalism is the ceiling. Never compress by lowering the bar, and never pad
by gold-plating.

- **Simplicity first.** No speculative features, no abstractions for single-use
  code, no error handling for impossible scenarios. Keep changes focused and
  avoid low-signal tests. If 200 lines could be 50, rewrite. Ask: "Would a
  senior engineer call this overcomplicated?"
- **Climb the ladder (Ponytail).** Take the first rung that fully works: does
  this need to exist at all (YAGNI) → does it already exist in this codebase →
  does the standard library → does a native platform feature → does an
  installed dependency → can it be one line → only then the minimum code that
  works. The ladder runs *after* you understand the problem, never instead of
  it: read the code the change touches, list every place it must reach
  (callers, tests, fixtures, config, exports), and check what it could break
  for users. Laziness never cuts trust-boundary validation, error handling
  that prevents data loss, security, accessibility, or anything explicitly
  requested. Full rules and levels: `ponytail.md`.
- **Search before building.** Check existing project code, standard libraries,
  and proven dependencies before creating a new abstraction or helper. Prefer
  boring technology; add a dependency only when it is clearly better than the
  existing path.
- **Surgical changes.** Touch only what you must. Do not "improve" adjacent
  code. Match existing style. Remove only orphans your changes created; if you
  notice pre-existing dead code, mention it — do not delete it. Every changed
  line must trace back to the request.
- **Root cause, once.** A bug report names a symptom: grep every caller of the
  function you touch and fix the shared code once — one guard there is a
  smaller diff than one per caller.
- **Disclose what you skipped.** End every report with one or two lines: what
  you skipped or did not check, and any risk the user must know.

### Verify, don't assume

- **Split deterministic work from reasoning work.** If the same question asked
  twice would produce the same correct answer by definition, it is
  deterministic work — do it with scripts, tests, formatters, schema checks,
  and targeted shell commands for repeatable facts: file lookups, parsing,
  counting, transformations, validation. If you catch yourself doing
  arithmetic, date math, or structured parsing inside a reasoning step, stop
  and script it.
- **Tie every claim to visible evidence** — a test result, config check, log
  line, metric, diff inspection, or important source link. Ground research in
  authoritative, current sources and name gaps or uncertainty. Features and bug
  fixes need deterministic tests; LLM, prompt, and ranking behavior needs an
  eval or documented manual rubric; config and docs changes need syntax, diff,
  link, and marker checks.
- **Verify every example you ship.** Anything a reader will copy and run — a
  command, a prompt, a number, a link — gets checked by you before it ships.
  Run it, rather than reasoning about it. Anything you could not verify is
  stated as unverified, with what would settle it. Never launder an unchecked
  claim into confident prose.
- **Report final status honestly** as one of `DONE`, `DONE_WITH_CONCERNS`,
  `BLOCKED`, or `NEEDS_CONTEXT`, with the evidence that supports it.

### Complete real fixes

Preserve the user's original goal and constraints. Do not leave work as a
workaround, loose plan, or follow-up note when finishing now is safer and
practical. Tests passing is necessary evidence, not sufficient: verify the
actual result before claiming completion, and think through the failure modes
and what would break if the assumption is wrong.

### Curate context deliberately

Load the relevant contract section, module header, source files, tests, and
examples. Do not dump unrelated files into context. Load the matching skill
before substantive work — the `agents-contract` skill is mandatory per Session
bootstrap. When explaining something to the user, visualize it
— prefer diagrams, tables, or code blocks over prose where that aids
understanding. If a repo-local skill is unavailable through the current tool
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
- **Preserve safety boundaries.** Preserve unrelated work. Never commit
  secrets, destructive commands, production mutations, force pushes, hook
  bypasses, binaries, or model weights without explicit approval and a rollout
  plan.
- **Fan out independent work only when boundaries are clear.** Use isolated
  sessions, worktrees, or subagents only for genuinely independent units;
  coordinate through contracts, avoid overlapping write sets, and synthesize
  findings before reporting.
- **Delegation completion contract.** Your final message is the deliverable.
  If you delegate, you own collection: wait for results, integrate them, then
  report. Never end a turn while spawned work is still running — a spawned
  task is not a completed task, and fire-and-forget delegation orphans its
  results. Decompose only when the work cannot fit in one context.
- **Keep architecture parallel-friendly.** New subsystems have clear
  ownership, contracts, tests, and docs. Follow the current repository layout
  unless the task explicitly includes restructuring.

## The Work Loop

This is the canonical way every task is delivered. Each step ends with a
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
4. **Implement with TDD.** Where Task sizing calls for a test, write it first —
   RED → GREEN → IMPROVE, per Testing Requirements. Work in small increments;
   verify each step before starting the next.
   → Verify: the targeted tests pass, not just the suite.
5. **Self-review the diff.** Run the Definition of Done checklist on your own
   work before anyone else sees it; a change bound for a shared branch, a merge,
   or a STOP trigger also gets the independent review in Code Review Standards.
   → Verify: every changed line traces back to the request.
6. **Prove it.** Run the smallest check that proves the change per the
   Verification section.
   → Verify: evidence exists for every claim you will make.
7. **Report and record.** Report status honestly; if files changed, commit with
   the session trailers under Git Workflow.

If any step fails, stop and fix the root cause — do not work around it, do not
declare done.

### Compliance record

Every final report ends with these four lines, or states why one is unavailable:

```text
Size:     small | medium | large
Skill:    agents-contract loaded | SKILL.md fallback | unavailable (reason)
Commands: RTK-wrapped N, raw M (reasons) | RTK unavailable
Review:   independent verdict | not required (small) | unavailable (reason)
```

A missing compliance record is itself a contract violation; do not claim
`DONE` without it. The record is a self-report: tie its claims to commands and
artifacts a reviewer can rerun.

## Engineering Standards

### Definition of Done

Before any change is complete, self-reviewed, committed, or merged, every item
must hold:

- [ ] Readable, well-named identifiers; no magic numbers (named constants)
- [ ] Functions focused (<50 lines); files cohesive (800-line soft ceiling);
  no nesting deeper than 4 levels
- [ ] Errors handled explicitly at every level; nothing silently swallowed
- [ ] No hardcoded secrets or credentials; user input validated at every
  boundary
- [ ] No leftover debug statements; no dead code introduced
- [ ] No comments outside CodeDNA annotations
- [ ] Tests exist for new behavior; coverage meets the project's threshold
- [ ] The change is the smallest that satisfies the request
- [ ] Evidence for the change exists per the Verification section

### Verification

Run the smallest check that proves the change before claiming completion:

- For config or docs edits: syntax checks or targeted grep checks.
- For installed contract surfaces when the lowheat checkout is available:
  `python3 install.py --check --harness <name>` is read-only and exits 1 on
  drift; refresh with `--force` only after reviewing what it will replace.
- For Python source edits: the relevant `rtk pytest` targets, or
  `python3 -m pytest` when RTK is unavailable.
- For Go source edits: `rtk go build ./...` and `rtk go vet ./...`.
- For browser-facing or user-facing work: test observable behavior and verify
  with the real interface when possible.
- Report any check that could not run and why. Report meaningful blockers,
  outcomes, and evidence without noisy progress narration.

### Coding Style

Core principles, adapted from the **Everything Claude Code** rule packs
(`https://github.com/affaan-m/ECC`). Read them as starting posture, not
universal law; relax what your task or agent surface does not need.

- **KISS** — simplest solution that works; clarity over cleverness.
- **DRY** — extract repeated logic; introduce abstractions only when repetition
  is real.
- **YAGNI** — no speculative features; start simple, refactor when pressure is
  real.
- **Immutability** — prefer new objects over in-place mutation for shared state,
  domain models, and concurrent code. Do not mutate inputs, caches, or
  configuration owned by another scope. Local accumulators are fine when the
  language and the surrounding code make them clear.
- **File organization** — many small files over few large files: 200–400 lines
  typical, 800-line soft ceiling, high cohesion, low coupling, organized by
  feature/domain, not by type. Test, generated, and vendored files may exceed
  the ceiling when their size is justified by their role.
- **Error handling** — handle errors explicitly at every level. User-facing
  messages in UI code; detailed context server-side. Never silently swallow.
- **Input validation** — validate at every system boundary; schema-based where
  available; fast fail with clear messages. All external data is untrusted.
- **Naming conventions** — language-independent rule first: names say what the
  thing holds or does, without a comment. Where the language or framework has
  an idiom (Go, Rust, Python casing; framework prefixes), the idiom wins over
  the defaults below. Defaults where no idiom applies: variables/functions
  `camelCase`; booleans `is`/`has`/`should`/`can` prefix;
  interfaces/types/components `PascalCase`; constants `UPPER_SNAKE_CASE`;
  tests `snake_case` describing the behavior under test.

### CodeDNA

CodeDNA is a hand-applied source-annotation convention adapted from
`https://github.com/Larens94/codedna`. There is no binary, validator, git hook,
or ledger — git is the audit log. Full convention: `codedna.md`.

- **Only comment content.** No prose comments, commented-out code, `TODO`/
  `FIXME` markers, or section dividers. Tool directives, license headers, and
  user-visible documentation strings are exempt.
- **L1 module header.** Every source file starts with `filename — description`,
  then `exports:`, `used_by:`, optional `related:`, `rules:`, and a rolling
  `agent:` history capped at 5 entries. Optional `message:` sits beneath
  `agent:`.
- **L2 function annotation.** Every public function carries a `Rules:` block
  unless it is trivial and has no domain constraint. Guards, invariants, and
  edge cases belong there.
- **Inline annotations.** `# Rules:` or `# message:` only for non-obvious
  business rules, step-order dependencies, and edge cases. Skip obvious code.
- **Maintain as you edit.** Update `rules:` when you learn a constraint, append
  one `agent:` line per session, and run the skill's `codedna_check.py` after
  annotation edits. Delete non-CodeDNA comments in code you touch; this is the
  one exception to Surgical changes.

### Testing Requirements

**Scope.** Task sizing decides whether a change writes tests at all: a small
non-behavioral change adds none, a medium bug fix ships its regression test, a
large change runs the full protocol. The suite-wide floor below applies only
where the project has coverage tooling and a defined threshold.

**Coverage.** Use the project's configured threshold; 80% is the default when
no threshold exists. Unit, integration, and E2E tests are required where they
apply to the surface: E2E only for critical user-facing flows.

**Two test lanes.** Gate tests are deterministic, local, and fast — run on
every change, never flaky. Periodic evals are paid or slow, quality-measuring
(LLM, ranking, long-running suites) — run before ship and on a schedule, with
a pass threshold.

**Test-Driven Development.** Where a test is written: RED (it fails) → GREEN
(minimal implementation) → IMPROVE (refactor) → verify the threshold.

**Structure.** AAA — Arrange / Act / Assert — with descriptive names that state
the behavior under test.

**When tests fail, troubleshoot in order:** test isolation, mocks, then the
implementation — not the tests, unless the test is wrong.

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

**STOP triggers — an independent review, security-scoped, runs before
proceeding** when the change touches: authentication or authorization, user
input handling, database queries, file system operations, external API calls,
cryptographic operations, or payment/financial code. Scope it with the mandatory
checks above and the touched surface; a CRITICAL or HIGH finding blocks the
commit. Code Review Standards defines the reviewer and the recording rule.

## Execution & Delivery

### Command Style

- These RTK and discovery rules are instruction-only. No harness hook rewrites
  or refuses a command, so apply them yourself.
- Wrap shell commands through **RTK** by default: `git status` becomes
  `rtk git status`, `python3 -m pytest -q` becomes `rtk pytest -q`. RTK
  compresses noise while keeping errors and exit codes. Run raw when you need
  exact bytes or parseable structure (patches to apply, JSON to parse,
  streaming output), and use native Read/Grep for file access. Fall back to raw
  whenever RTK is missing or does not support the subcommand. Full catalogue
  and fidelity zones: `RTK.md`.
- **RTK gate.** Attempt RTK first on every shell command. Raw is allowed only
  for exact bytes, parseable structure, streaming, or secrets — state the reason
  in the compliance record. A session with no RTK-wrapped command must explain
  why RTK was unusable or unsupported. The record is self-reported; a reviewer
  can verify the claimed commands.
- If a wrapped view hid something you needed, re-run raw once and stop wrapping
  that command. `rtk recall <hash>` recovers elided output when available.
- One read-compressor per command, after the intent gate: RTK by default; when
  RTK cannot wrap a command, `caveman shrink` stands in if the caveman layer is
  installed, raw otherwise.
- Avoid compound `cd <path> && <command>` chains. Use `git -C <path> ...`,
  pass the target path as an argument, or set the tool working directory.
- **Never run `git commit` or `git push` without explicit user approval.** This
  repository rule overrides any upstream template that suggests automatic
  commit and push behavior.

#### Tool ladder for code discovery

Locating code is not reading it. Take the first rung that answers the question:

1. **Semble MCP** — `search` / `find_related`, when connected. The qualified
   name is harness-specific (`mcp__semble__search` on Claude Code and Command
   Code, `semble__search` on Grok); the wrong name fails with `Tool not found`.
2. **Semble CLI** — `semble search "<query>" . --max-snippet-lines 10` when
   the binary is on PATH.
3. **`rtk grep`** — a lossy survey: answers "roughly where", not "every match".
4. **Native Grep/Glob** — exact `line:content`, every occurrence, no caps.

Find with rungs 1–3, then read the file with the native Read tool; `rtk read`
equals `cat` unless you opt into a lossy level. A missing rung drops to the
next; discovery is never blocked on an install. Full detail: `semble.md` and
`RTK.md`.

### Communication Style

Replies default to terse caveman mode: answer first (`[thing] [action] [reason].
[next step].`), no greeting or recap, fragments fine. Meaning never drops —
*not*, *never*, *only*, numbers, and units stay exact; code, commands, paths,
and error text stay verbatim. Use full sentences for security warnings,
irreversible actions, order-sensitive steps, and confused users. Anything
persisted outside chat keeps normal prose. Commit messages and review findings
have their own formats. Full rules, modes, and the optional read-compression
layer: `caveman.md`.

### Git Workflow

#### Commit message format

```
<type>: <description>

<optional body>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`.

#### Session trailers

At the end of every session that modified files, record the work in the commit.
When you create the commit (explicit user approval required per Command Style),
add these trailers:

```
AI-Agent:    <model-id | unknown>
AI-Provider: <provider | unknown>
AI-Session:  <session_id | unknown>
AI-Visited:  <files read, derived from the diff and the session's read log>
AI-Verified: <commands run and their result, one line>
AI-Message:  <one-line summary of what was found or left open>
```

Order matters: the AI block is the last paragraph of the message, with no blank
line inside it, and any `Co-authored-by:` line sits above it. Git parses
trailers from the final paragraph only, so a misplaced block is invisible to
tooling. Confirm with
`git log -1 --format='%(trailers:key=AI-Agent,valueonly)'` — it prints the agent
when the block parses and prints nothing when it does not. Write `unknown` for a
value the harness does not expose; never invent an ID.

Git is the authoritative audit log; do not keep a separate ledger file.
Attribution settings are harness-specific; this contract does not assume a
particular global config path.

#### Pull requests

1. Analyze full commit history — not just the latest commit.
2. Use `rtk git diff [base-branch]...HEAD` to see all changes.
3. Draft a comprehensive PR summary.
4. Include a test plan with TODOs.
5. Push with `-u` flag if on a new branch.

### Code Review Standards

Two review modes, and each is mandatory where it applies:

- **Self-review** — the author applies the Definition of Done checklist and the
  severity table to the diff and fixes the CRITICAL and HIGH findings before
  anyone else sees it: Work Loop step 5, for every change.
- **Independent review** — a reviewer other than the author owns the verdict,
  using a reviewer subagent where the harness provides one and a human
  otherwise. It is required for every change bound for a shared branch (pushed
  to a shared remote, or targeted by a merge or PR — a local scratch branch is
  not shared) or a merge, and for every change that trips the STOP triggers in
  Security Guidelines. The reviewer records the verdict, the covered scope, and
  any open risk in the PR body or commit message.

Pre-review requirements for independent review: all automated checks (CI/CD)
passing, no merge conflicts, branch up to date with target.

**Severity levels:**

| Level | Meaning | Action |
|---|---|---|
| CRITICAL | Security vulnerability or data loss risk | BLOCK — must fix first |
| HIGH | Bug or significant quality issue | WARN — should fix first |
| MEDIUM | Maintainability concern, including an unexplained source file over the soft 800-line ceiling | INFO — fix or record a reason |
| LOW | Style or minor suggestion | NOTE — optional |

**Deferred findings:** a MEDIUM finding is either fixed or recorded with a
reason in the PR body or the commit message — never silently dropped. LOW
findings may be skipped.

**Approval criteria:** the independent reviewer approves when no CRITICAL or HIGH
issues remain, warns when only HIGH issues remain, and blocks on any CRITICAL
issue; a security-scoped review under the STOP triggers blocks on a HIGH finding
too.

## Environment & Source Repositories

### Installed plugins / skills

| Plugin / skill | Source | Purpose |
|---|---|---|
| `agents-contract` | this repository, `.agents/skills/agents-contract/` | Repo-local skill encoding this contract as executable steps; load at session start |
| `semble` | [`https://github.com/MinishLab/semble`](https://github.com/MinishLab/semble) | MCP code-search server — top rung of the discovery ladder |
| `superpowers` | [`https://github.com/obra/superpowers`](https://github.com/obra/superpowers) | Workflow skills (TDD, planning, debugging, parallel, verification) |

Use the Skill tool when a Superpowers skill matches the task; otherwise read
the tracked `SKILL.md` for project guidance.

### Context window management

The context window is your main control surface over the model. Treat it as a
deliberate input: load the relevant contract section, files, and examples;
leave the noise out. Avoid the last 20% of the context window for large-scale
refactoring, feature implementation spanning multiple files, and debugging
complex interactions. Lower-sensitivity tasks (single edits, docs, simple
fixes) tolerate higher utilization. When a task goes sideways, the first
question is what was in the window, rather than assuming the model failed.

### Knowledge capture

Put captured knowledge in the right place:

- Personal debugging notes, preferences, temporary context → memory
- Team/project knowledge (architecture decisions, API changes, runbooks) → the
  project's existing docs structure
- If an existing doc already captures the information, do not duplicate it
- If no obvious location exists, ask before creating a new top-level file

### Source Repositories

| Source | Purpose |
|---|---|
| `https://github.com/rtk-ai/rtk` | RTK CLI and command reference |
| `https://github.com/MinishLab/semble` | Semble MCP code-search server and CLI |
| `https://github.com/JuliusBrussee/caveman` | Caveman communication mode |
| `https://github.com/DietrichGebert/ponytail` | Ponytail laziness ladder |
| `https://github.com/Larens94/codedna` | CodeDNA source-annotation convention |
| `https://github.com/obra/superpowers` | Superpowers plugin |
| `https://github.com/jbarbier/CLAUDE.md` | Operating-contract influence |
| `https://github.com/multica-ai/andrej-karpathy-skills` | Karpathy behavioral guidelines |
| `https://github.com/affaan-m/ECC` | Rule-pack influence for coding style, security, testing, git workflow, code review |
