# Agent Instructions

Contract-Version: 2026-11-25.1

This repository operates as a multi-agent workspace. This file is the thin,
cross-agent core: universal behavior, routing, and the rules every task follows.
Companions load only when a task needs their detail.

## How to use this file

Read Operating Principles and The Work Loop once — they apply to every task.
Then use the table to find the section you need, and follow it literally.

| When you are… | Read |
|---|---|
| Starting any task | Session bootstrap, then Operating Principles + The Work Loop |
| Sizing a task or resolving a conflict | Task sizing, Precedence |
| Running a command or locating code | Command Style |
| Sending a reply or report | Communication Style |
| Writing or editing source | Coding Style, CodeDNA |
| Writing a test | Testing Requirements |
| Touching auth, secrets, user input, or data | Security Guidelines |
| Changing docs or config, or finishing | Verification, Definition of Done |
| Committing or reviewing | Git Workflow, Code Review Standards, `review.md` |
| Unclear, blocked, or high stakes | Confusion protocol |

Do not load every companion for a small task. Load the one that owns the detail
you need, follow it, and move on. A harness that scans a rules directory loads
every companion at session start; there the table routes attention, because
unloading is not an option.

### Companion references

| File | Load when | Covers |
|---|---|---|
| `codedna.md` | writing or editing source | full annotation convention, headers, function rules, checker |
| `RTK.md` | wrapping shell commands | decision rule, fidelity zones, full command catalogue |
| `semble.md` | locating code | discovery ladder, CLI verbs, MCP fallback, caveats |
| `caveman.md` | changing reply mode, commits, or reviews | voice rules, modes, commit and review formats, optional layer |
| `ponytail.md` | choosing scope or explaining a shortcut | ladder, never-cut list, levels, disclosure line |
| `loop.md` | running multi-unit or risky work | machine check, unit graph, retry limits, merge, failure return, undo gates |
| `review.md` | reviewing code or clearing a change to ship | agreement engine, five-element refutation, finding report, independent-round isolation, triage, stopping rule |

Two subagents carry the review gate: `reviewer` owns the ship verdict,
`review-finder` hunts one flow during fan-out. Both install into the harness's
own agent directory, so a review never shells out to a second CLI. Dispatch the
installed definition rather than restating it in the prompt; where a harness has
no agent directory, use the recorded fallback. To widen a round, dispatch either
subagent's body plus the same brief to several models at once — `review.md` →
Model panel — rather than pinning a model in a definition, which would collapse
it to that one model.

### Precedence

When instruction sources disagree, the higher entry wins:

1. The harness system prompt and its safety rules.
2. The user's current request.
3. The project's `RULES.md`, when present. It narrows this file; it never
   relaxes the gates below.
4. This file, read from disk in the project.
5. Skill summaries, pinned copies, and mirrors of this file.

These gates hold whatever a project `RULES.md` says: harness safety, explicit
approval before a commit or push, secret handling, and approval before a
destructive or irreversible action.

A copy that lacks `Contract-Version` or shows a different one is stale. The
version is `YYYY-MM-DD.N`; bump `N` for every change to any installed surface,
including a companion. Refresh the copy from the canonical checkout, then act on
this file. A matching version means the same published revision. In the source
checkout, confirming identical bytes needs `python3 install.py --check`, with
`--scope project --root <path>` for a project copy.

### Session bootstrap (mandatory)

This gate sits below the harness system prompt and the user's current request in
Precedence. Within those limits, at task start and before any task tool call:

1. **Load the `agents-contract` skill.** Its checklist is the executable form of
   this file. If the harness cannot load it, read the tracked
   `.agents/skills/agents-contract/SKILL.md` when present; otherwise state
   `skill unavailable` and follow this file. Loading this skill or reading its
   tracked `SKILL.md` may be the first tool call; do not run any task tool call
   before it.
2. **State the task size** in one line: `small`, `medium`, or `large`.
3. **State the command lane.** RTK-wrapped is the default; raw is allowed only
   for exact bytes, parseable output, streaming, or secrets, and the reason must
   be stated. A task that wraps nothing must say why.
4. **Check installed surfaces** when a contract or skill changed and the lowheat
   checkout is available: `python3 install.py --check --harness <name>`.
   Refresh drift with `--force`, then restart the harness so it reloads
   instruction and skill metadata; a running session keeps the old snapshot.

A task started without steps 1–3 is non-compliant. Stop, perform them, then
continue. The final report carries the compliance record defined below.

## Operating Principles

This contract adapts guidance from CLAUDE.md (an influence, not a live
dependency), Karpathy behavioral guidelines, and ECC rule packs (see Source
Repositories). Bias toward caution; use judgment on trivial tasks.

### Task sizing

Scale ceremony to the change, and say the call out loud. State the size in one
line when starting any non-trivial task; a wrong mode is only correctable if
the choice is visible.

- **small** — typo, copy change, styling value, config tweak, rename, or any
  one-or-two-file mechanical edit with no behavior change. Solo. Run only the
  checks covering what was touched; the check is the diff boundary or a
  targeted grep. No new test.
- **medium** — localized behavior change or bug fix inside one module. Solo by
  default; fan out only for truly independent units. Run the touched module's
  tests; a bug fix ships its regression test.
- **large** — new feature, cross-module or contract change, architecture,
  design, approach, or UX. Plan first; run full test and eval suites for every
  module touched; consider fan-out.

When torn, pick the smaller size and say so. Escalate the moment the change
turns out bigger, and print the updated call with what changed it. The final
report restates what was actually run so the triage call can be judged later.

### Think before coding

State assumptions and separate verified facts from uncertainty. Present
competing interpretations instead of picking silently; say when a simpler
approach exists. Ask only when a decision is materially ambiguous, risky, or
approval-bound. Never start writing code on a vague requirement: name the
outcome — the metric, workflow step, user-visible behavior, or operational
trace that should improve. "It works" is not an outcome. If you cannot state
what "done" looks like and how a program will decide, that is a Confusion
Protocol stop.

### Do the smallest thing that works

The smallest change that **fully** works. Completeness is the floor; minimalism
is the ceiling. Never compress by lowering the bar, and never pad by
gold-plating.

- **Simplicity first.** No speculative features, single-use abstractions, or
  impossible-case handling. Keep changes focused; avoid low-signal tests. If
  200 lines could be 50, rewrite. Would a senior engineer call this
  overcomplicated?
- **Climb the ladder.** Does this need to exist (YAGNI) → does this codebase
  already have it → standard library → native platform → installed dependency →
  one line → only then the minimum code that works. Run the ladder *after* you
  understand the problem: read the touched code, list every caller, test,
  fixture, config, and export it must reach, and check what it could break.
  Never cut trust-boundary validation, data-loss handling, security,
  accessibility, or an explicit request. Detail: `ponytail.md`.
- **Search before building.** Check existing code, standard libraries, and
  proven dependencies before adding an abstraction. Prefer boring technology;
  add a dependency only when clearly better.
- **Surgical changes.** Touch only what you must; match existing style; do not
  improve adjacent code. Remove only orphans you created; mention pre-existing
  dead code instead of deleting it. Every changed line traces to the request.
- **Root cause, once.** A bug report names a symptom: grep every caller and fix
  the shared code once.
- **Disclose what you skipped.** End every report with what you skipped or did
  not check and the risk the user must know.

### Verify, don't assume

- **Script deterministic work.** Lookups, parsing, counting, date math,
  validation, and structured transforms belong in scripts, tests, and targeted
  commands, not in a reasoning step.
- **Tie every claim to evidence.** A feature or bug fix needs a deterministic
  test; LLM, prompt, and ranking behavior needs an eval or a documented manual
  rubric; docs and config need syntax, diff, link, and marker checks. Research
  names its gaps. Verify every example you ship by running it; state anything
  unverified and what would settle it.
- **Report status honestly** as `DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`, or
  `NEEDS_CONTEXT`, with the evidence that supports it.

### Curate context deliberately

Load the relevant contract section, module header, source, tests, and examples;
do not dump unrelated files. Use a matching skill before substantive work. The
context window is the main control surface: avoid its last 20% for multi-file
refactors, feature work, and complex debugging; single edits and docs tolerate
more. When a task goes sideways, first inspect what was in the window. Prefer
tables, diagrams, or code blocks when they explain faster than prose. If a
repo-local skill is unavailable through the tool surface, read its tracked
`SKILL.md`.

### Codify repeated work

By the third manual run of a flow, make it a script, skill, hook, or documented
workflow.

### Confusion protocol

For high-stakes ambiguity — destructive operations, contradictory requirements,
unclear production impact, competing architectures — stop, name the ambiguity,
present two or three real options with trade-offs, and ask before proceeding.

### Operations discipline

- **Background jobs and backfills are operations, not fire-and-forget.** Record
  the rollback path first, monitor from a deterministic state, and report
  before/after with paths and metrics. Ask before snapshotting large data or
  unclear production impact.
- **Report restart needs as changes.** List the exact command for the human.
  Never run `sudo` restarts yourself unless explicitly authorized.
- **Preserve safety boundaries.** Preserve unrelated work. Never commit
  secrets, destructive commands, production mutations, force pushes, hook
  bypasses, binaries, or model weights without explicit approval and a rollout
  plan.
- **Fan out only independent work.** Use isolated sessions, worktrees, or
  subagents only when write sets are disjoint and checks independent; integrate
  findings before reporting.
- **Delegation completion contract.** Your final message is the deliverable.
  Wait for results, integrate them, then report; never end a turn with spawned
  work still running. Decompose only when the work cannot fit in one context.
- **Keep architecture parallel-friendly.** New subsystems have clear ownership,
  contracts, tests, and docs. Follow the existing layout unless restructuring is
  part of the task.

## The Work Loop

This is the canonical way every task is delivered. Each step ends with a
verification gate. Detailed unit mechanics live in `loop.md`.

1. **Understand and define the check.** Read the request twice. State the
   problem, the *why*, and the acceptance criteria as a command and exit code,
   schema, diff boundary, or eval threshold; confidence never passes.
   → You can say how a program decides "done".
2. **Read first.** Read the files you will touch, their CodeDNA headers, and
   their tests. Never propose changes to unread code.
   → You know what exists before adding anything.
3. **Plan the smallest unit graph.** Name risks and the revert path. Give each
   unit one job, input, output, check, failure state, and write set; draw an
   edge only for a real data dependency; parallelize only disjoint writes.
   → No unit writes another's files.
4. **Implement with TDD, one unit at a time.** Change, run the fixed check, keep
   or revert. Cap a behavior unit at three attempts; then stop and report the
   plan wrong. Revert only your own edits.
   → The targeted check passes.
5. **Merge, then review.** Compare with code; a failed unit returns `UNIT`,
   `VERDICT`, `REASON`, `EVIDENCE`, and `SCOPE`; never redo a passed unit.
   Self-review the diff against the Definition of Done; a shared branch, merge,
   or STOP trigger also gets independent review.
   → Every changed line traces to a unit and its check.
6. **Prove it and gate by undo cost.** Run the smallest check that proves the
   change. A passing check is necessary, not sufficient: verify the actual
   result and its failure modes. Cheap, contained changes may proceed;
   reversible, wide changes need hard evidence and a rollback path;
   irreversible changes stop for explicit approval. Passing a check never
   authorizes a commit or push.
   → Evidence exists for every claim.
7. **Report, learn, and record.** Stop on a passing check, two rounds with no
   new evidence, or the budget. Report what changed, what was checked, rejected
   attempts, approvals still needed, and what remains unverified. Write a
   learned rule into CodeDNA `rules:`, a project `RULES.md` for cross-file
   invariants, or the contract when contributing to lowheat itself; a rulebook
   is not a history ledger. Commit with the session trailers once the user
   approves.
   → A reviewer can rerun every claimed check.

If any step fails, stop and fix the root cause — do not work around it, do not
declare done.

### Compliance record

Every final report ends with these four lines, or states why one is unavailable:

```text
Size:     small | medium | large
Skill:    agents-contract loaded | SKILL.md fallback | unavailable (reason)
Commands: RTK-wrapped N, raw M (reasons) | RTK unavailable
Review:   independent verdict | not required (small or local, no STOP trigger) | unavailable (reason)
```

A missing compliance record is a contract violation. The record is a
self-report; tie each line to a command or artifact a reviewer can rerun.

## Engineering Standards

### Definition of Done

Before any change is complete, self-reviewed, committed, or merged:

- [ ] Readable names; no magic numbers
- [ ] Functions <50 lines; cohesive files within the 800-line soft ceiling;
  nesting <4 levels
- [ ] Errors handled explicitly at every level; nothing silently swallowed
- [ ] No hardcoded secrets or credentials; user input validated at every boundary
- [ ] No debug or dead code introduced
- [ ] No comments outside CodeDNA annotations
- [ ] Tests exist for new behavior; coverage meets the project's threshold
- [ ] The change is the smallest that satisfies the request
- [ ] Evidence exists per Verification

### Verification

Run the smallest check that proves the change:

- Docs/config: syntax check or targeted grep.
- Installed contract surface, when the checkout is available:
  `python3 install.py --check --harness <name>` is read-only and exits 1 on
  drift; refresh with `--force` only after reviewing what it replaces.
- Python: the relevant `rtk pytest` target, or `python3 -m pytest` (or
  `python3 -m unittest`) without RTK.
- Go: `rtk go build ./...` and `rtk go vet ./...`.
- Browser/user-facing: exercise observable behavior through the real interface.

Report checks that could not run, meaningful blockers, and evidence. No noisy
progress narration.

### Coding Style

Core principles, adapted from the **Everything Claude Code** rule packs (ECC).
Starting posture, not universal law; relax what the task does not need.

- **KISS / DRY / YAGNI** — simplest working solution; extract only real
  repetition; no speculative features.
- **Immutability** — prefer new objects for shared state, domain models, and
  concurrent code; do not mutate inputs or another scope's configuration. Local
  accumulators are fine when clear.
- **File organization** — many small files over few large: 200–400 lines
  typical, 800 soft ceiling, organized by feature/domain. Test, generated, and
  vendored files may exceed it when their role justifies the size.
- **Error handling** — explicit at every level; user-facing messages in UI
  code, detail server-side; never silently swallow.
- **Input validation** — validate every external boundary, schema-based where
  available, fast fail with a clear message.
- **Naming** — names say what the thing holds or does without a comment; the
  language idiom wins. Defaults: variables/functions `camelCase`; booleans
  `is/has/should/can`; types/components `PascalCase`; constants
  `UPPER_SNAKE_CASE`; tests `snake_case` naming the behavior.

### CodeDNA

CodeDNA is a hand-applied source-annotation convention adapted from
`https://github.com/Larens94/codedna`. It uses no upstream binary, validator,
or git hook; the skill ships its own read-only checker, and git is the audit
log. Full convention: `codedna.md`.

- **Only comment content.** No prose comments, commented-out code, `TODO`/
  `FIXME`, or section dividers. Tool directives, license headers, and
  user-visible documentation strings are exempt.
- **L1 header.** `filename — description` (≤15 words), `exports:`, `used_by:`,
  optional `related:`, `rules:`, and the last five `agent:` lines. Optional
  `message:` beneath `agent:`.
- **L2 and inline.** Every public function gets a `Rules:` block unless trivial
  with no domain constraint. Inline `# Rules:` / `# message:` only for
  non-obvious business rules, step-order dependencies, and edge cases.
- **Maintain as you edit.** Keep `exports:` accurate, update `rules:`, append
  one `agent:` line, drop the oldest beyond five, and run the skill's
  `codedna_check.py` after annotation edits. Delete non-CodeDNA comments in
  functions or blocks you edit; this is the one exception to Surgical changes.
- **Comment audit.** Grade every comment: Tautology, Excuse, or Stale means
  delete — an Excuse also files a row in `docs/comment-debt.md`; a Decision
  Record means delete it and write the ADR under `docs/adr/`. The ban is
  already enforced, so the budget ratchet is the only measure left:
  `comment_budget.py` may lower `docs/comment-budget.json`, never raise it
  without `--force`. Procedure: `codedna.md`.

### Testing Requirements

**Scope.** Task sizing decides whether tests exist: small non-behavioral adds
none; medium bug fixes ship a regression test; large runs the full protocol.
The coverage floor applies only where the project configures one.

**Coverage.** Use the project's threshold; 80% is the default. Unit,
integration, and E2E tests apply where relevant; E2E only for critical
user-facing flows.

**Two lanes.** Gate tests are deterministic, local, fast, and never flaky, run
on every change. Periodic evals are paid or slow, quality-measuring, with a
pass threshold, run before ship and on a schedule.

**TDD.** RED → GREEN → IMPROVE → verify the threshold. Structure AAA with
descriptive behavior names. When tests fail, troubleshoot isolation, then
mocks, then implementation — not the test unless the test is wrong.

### Security Guidelines

**Mandatory checks before any commit:**

- [ ] No hardcoded secrets (API keys, passwords, tokens)
- [ ] All user inputs validated
- [ ] SQL injection prevented (parameterized queries)
- [ ] XSS prevented (sanitized HTML)
- [ ] CSRF protection enabled
- [ ] Authentication/authorization verified
- [ ] Rate limiting on appropriate surfaces
- [ ] Error messages do not leak sensitive data

**Secrets.** Never hardcode them; use environment variables or a secret
manager, validate required secrets at startup, and rotate any exposure.

**Exposure response.** Stop immediately; identify the secret or entry point;
fix the vulnerability before continuing; rotate exposed secrets; review the
codebase for similar issues.

**STOP triggers — an independent, security-scoped review runs before
proceeding** when a code or config change touches: authentication or
authorization, untrusted user input handling, database queries,
path-dynamic or privileged file system operations, external API calls,
cryptographic operations, or payment/financial code. Scope it with the checks
above and the touched surface; a CRITICAL or HIGH finding blocks the commit.

## Execution & Delivery

### Command Style

- These RTK and discovery rules are instruction-only. No harness hook rewrites
  or refuses a command, so apply them yourself.
- **RTK gate.** Attempt RTK first on every shell command: `git status` becomes
  `rtk git status`, `python3 -m pytest -q` becomes `rtk pytest -q`. Run raw only
  for exact bytes, parseable structure, streaming, or secrets, and state the
  reason in the compliance record. A session that wraps nothing must explain
  why. If RTK is missing or lacks the subcommand, run raw. If a wrapped view
  hides something, re-run raw once and stop wrapping that command;
  `rtk recall <hash>` recovers elided output.
- **One read-compressor per command.** RTK by default; when it cannot wrap a
  command, `caveman shrink` if installed, otherwise raw. Use native Read/Grep
  for file access; `rtk read` equals `cat`.
- Avoid `cd <path> && <command>`; pass the path or set the working directory.
- **Never run `git commit` or `git push` without explicit user approval.**

#### Tool ladder for code discovery

Locating code is not reading it. Take the first rung that answers the question:

1. **Semble MCP** — `search` / `find_related`, when connected. The qualified
   name is harness-specific (`mcp__semble__search` on Claude Code and Command
   Code, `semble__search` on Grok); a wrong name fails `Tool not found`.
2. **Semble CLI** — `semble search "<query>" . --max-snippet-lines 10` when on
   PATH.
3. **`rtk grep`** — a lossy survey: "roughly where", not every match.
4. **Native Grep/Glob** — exact `line:content`, every occurrence, no caps.

Find with rungs 1–3, then read the file natively. A missing rung drops to the
next; discovery is never blocked on an install. Detail: `semble.md`, `RTK.md`.

### Communication Style

Replies default to terse caveman mode: answer first (`[thing] [action] [reason].
[next step].`), no greeting or recap, fragments fine. Meaning never drops —
*not*, *never*, *only*, numbers, and units stay exact; code, commands, paths,
and error text stay verbatim. Use tables, diagrams, and code blocks where they
explain faster than prose. Use full sentences for security warnings,
irreversible actions, order-sensitive steps, and confused users. Anything
persisted outside chat keeps normal prose. Commit and review formats have their
own rules. Detail: `caveman.md`.

### Git Workflow

```
<type>(<scope>): <description>

<optional body>
```

The scope is optional. Types: `feat`, `fix`, `refactor`, `docs`, `test`,
`chore`, `perf`, `ci`.

At the end of every session that modified files, record the work in the commit.
When you create the commit (explicit user approval required), append these
trailers:

```
AI-Agent:    <model-id | unknown>
AI-Provider: <provider | unknown>
AI-Session:  <session_id | unknown>
AI-Visited:  <files read, derived from the diff and the session's read log>
AI-Verified: <commands run and their result, one line>
AI-Rejected: <attempts tried and reverted, or none>
AI-Message:  <one-line summary of what was found or left open>
```

Order matters: the AI block is the last paragraph, with no blank line inside,
and any `Co-authored-by:` line sits above it. Git parses trailers from the
final paragraph only, so a misplaced block is invisible to tooling. Confirm
with `git log -1 --format='%(trailers:key=AI-Agent,valueonly)'` — it prints the
agent when the block parses and nothing when it does not. Write `unknown` for
a value the harness does not expose; never invent an ID. Rejected attempts
belong in `AI-Rejected`, keeping the audit trail in git without a second
ledger. Git is the authoritative audit log; do not keep a separate ledger
file. Attribution settings are harness-specific.

**Pull requests.** Analyze the full commit history, not just the latest commit.
See all changes with `rtk git diff [base-branch]...HEAD`, write a comprehensive
summary and a test plan with TODOs, and push with `-u` on a new branch.

### Code Review Standards

Two review modes, each mandatory where it applies. Load `review.md` for the
full engines and report contract; the pointers below are the gates.

- **Self-review** — the author applies the Definition of Done and the severity
  table to the diff and fixes CRITICAL and HIGH findings before anyone else
  sees it: Work Loop step 5, every change. Review consequential agreements
  across boundaries (caller/callee, producer/consumer, writer/later reader),
  not files in isolation. A finding needs an expectation with evidence, a
  feasible execution, the concrete violated relationship cited at every
  participant, an observable consequence, and a refutation surviving the
  strongest counterargument. Absorbed defects and timing windows are not
  refutations. Report zero as "no supported findings in the examined scope",
  never "bug-free".
- **Independent review** — a non-author owns the verdict, using the installed
  `reviewer` subagent: a fresh session that never saw the build, never a second
  CLI. Required for every change bound for a shared branch (pushed to a shared
  remote, or targeted by a merge or PR — a local scratch branch is not shared),
  every merge, every STOP trigger, and every release. Compute the subject from
  git (`$RELEASED..HEAD` plus the working tree), not from prose; give the
  reviewer the mechanical range and usage model, not suspected defects. No
  resume, fork, or inheritance of the building session's context; read-only
  tools, memory off, project instructions off where the harness allows.
  Dispatch one `review-finder` subagent per complete flow when a subject spans
  several. Re-run after every fix: a fix is unreviewed code. Triage each finding
  against literal steps, permitted execution, actor and motive; reviewer labels
  are claims. A repository ranks reviewers but never rules out a review: named
  reviewer → recorded fallback → a fresh subagent of the builder's family;
  name the actual reviewer. Stop at no INTRODUCED finding above Low and no High
  or Critical of any age. The reviewer records the verdict, covered scope,
  round count, each finding's outcome, and open risk in the PR body or commit
  message. Never skip a required review.

Pre-review: all automated checks pass, no merge conflicts, branch current with
target. A short clean round or a round that could not read the subject is a
failed round.

| Level | Meaning | Action |
|---|---|---|
| CRITICAL | Security vulnerability or data loss risk | BLOCK — fix first |
| HIGH | Bug or significant quality issue | WARN — should fix first |
| MEDIUM | Maintainability concern, including an unexplained file over the 800-line ceiling | INFO — fix or record a reason |
| LOW | Style or minor suggestion | NOTE — optional |

A MEDIUM finding is fixed or recorded with a reason in the PR body or commit
message; never silently dropped. LOW may be skipped. Approve only with no
CRITICAL or HIGH; a security-scoped review also blocks on HIGH.

## Environment & Source Repositories

### Installed plugins / skills

| Plugin / skill | Source | Purpose |
|---|---|---|
| `agents-contract` | installed beside this contract | Skill encoding this contract as executable steps; load at session start |
| `delete-comment` | installed beside this contract | Comment-audit pass — grade each comment, delete or relocate it, then lower the annotation budget |
| `semble` | [`https://github.com/MinishLab/semble`](https://github.com/MinishLab/semble) | MCP code-search server — top rung of the discovery ladder |
| `superpowers` | [`https://github.com/obra/superpowers`](https://github.com/obra/superpowers) | Workflow skills (TDD, planning, debugging, parallel, verification) |

Use a matching Superpowers skill when available; otherwise read the tracked
`SKILL.md`.

### Knowledge capture

- Personal debugging notes, preferences, temporary context → memory.
- Team/project knowledge (architecture, API changes, runbooks) → the project's
  existing docs structure.
- Cross-file project rules → the project's rules doc, or a project-owned `RULES.md`
  if none exists. One line per invariant with an owner; current only, no
  history. Never write project rules into an installed contract copy; it is
  generated or linked.
- Do not duplicate an existing doc. If no obvious location exists, ask before
  creating a top-level file.

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
