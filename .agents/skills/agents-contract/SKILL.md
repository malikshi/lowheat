---
name: agents-contract
description: Execute tasks using the repository's operating contract from AGENTS.md — the 7-step Work Loop, Operating Principles, Definition of Done, CodeDNA annotations, testing/security standards, code review, and git commit with session trailers. Use when starting any task, writing or editing code, writing tests, reviewing code, committing changes, or following the cross-agent contract.
---

# Agents Contract — Operating Contract Execution

This skill executes the repository's cross-agent operating contract defined in
`AGENTS.md`. It encodes the Work Loop, Operating Principles, Command Style,
CodeDNA protocol, engineering standards, Code Review, git workflow, and
Verification as executable steps. The full contract text lives in
`references/contract.md`. Read it when the steps below need detail.

## 1. Start a task — the Work Loop

Follow all 7 steps in order; each step ends with a verification point before the
next begins. If any step fails, stop and fix the root cause — do not work around
it and do not declare done.

1. **Understand.** Read the request twice. State the problem, the *why* behind
   it, and the acceptance criteria.
   → Verify: you can say what "done" looks like.
2. **Read first.** Read the files you will touch, their CodeDNA headers, and
   their tests. Never propose changes to code you have not read.
   → Verify: you know what exists before you add anything.
3. **Plan the smallest change.** Name the risks and the revert path. For
   multi-step tasks, state a brief: `1. [Step] → verify: [check]`.
   → Verify: the plan fits the request and nothing else.
4. **Implement with TDD.** Write the test first (RED), minimal implementation
   (GREEN), refactor (IMPROVE). Work in small increments.
   → Verify: the targeted tests pass, not just the suite.
5. **Self-review the diff.** Run the Definition of Done checklist on your own
   work before anyone else sees it; a change bound for a shared branch, a merge,
   or a STOP trigger also gets the independent review in §6.
   → Verify: every changed line traces back to the request.
6. **Prove it.** Run the smallest check that proves the change per the
   Verification section (`references/contract.md#verification`).
   → Verify: evidence exists for every claim you will make.
7. **Report and record.** Report status honestly; if files changed, commit with
   the session trailers under Git Workflow (§7 below).

## 2. Operating principles (decision rules)

Apply on every task, not just code changes:

- **Precedence.** When instruction sources disagree, the higher entry wins: the
  harness system prompt and the user's current request, then `AGENTS.md` on
  disk, then skill summaries, pinned copies, and mirrors of it. A copy whose
  `Contract-Version` differs from the file's is stale — refresh it from the
  canonical checkout, then act on the file on disk.
- **Task sizing.** Scale ceremony to the change and say the call out loud:
  **small** (mechanical, no behavior change — solo, touched checks only, no
  new test), **medium** (localized behavior change — solo, touched module's
  tests, regression test for fixes), **large** (feature, cross-module, or
  judgment-heavy — full protocol, full suites, consider fan-out). When torn,
  pick the smaller and say so; escalate with an updated call if the change
  outgrows the triage.
- **Think before coding.** State assumptions; distinguish verified facts from
  uncertainty. If multiple interpretations exist, present them — do not pick
  silently. Name what "done" looks like (metric, workflow step, user-visible
  behavior) before writing code; "it works" is not an outcome.
- **Smallest thing that works.** The smallest change that *fully* works —
  completeness is the floor, minimalism the ceiling. No speculative features
  or single-use abstractions. Search existing code, stdlib, and proven deps
  before building; prefer boring technology. Surgical changes only: match
  existing style, touch only what the request requires, mention pre-existing
  dead code rather than deleting it, every changed line traces back to it.
- **Verify, don't assume.** Split deterministic work (scripts, tests,
  formatters, targeted shell) from reasoning work — if the same question
  asked twice gives the same answer by definition, script it. Tie every claim
  to visible evidence (test result, log line, diff). Verify every example you
  ship by running it; state anything unverified as unverified.
  Features/fixes need deterministic tests; LLM/prompt/ranking behavior needs
  an eval or manual rubric.
- **Complete real fixes.** Preserve the user's goal; don't leave a workaround
  when finishing now is safer. Tests passing is necessary, not sufficient —
  verify the actual result and think through failure modes.
- **Curate context.** Load only the relevant contract section, CodeDNA entries,
  source files, and tests. Use skills when one matches; visualize explanations
  with diagrams/tables/code blocks where they aid understanding.
- **Codify repeated work.** By the third time a manual flow is needed, turn it
  into a script, skill, hook, or documented workflow.
- **Confusion protocol.** For high-stakes ambiguity (destructive ops,
  contradictory requirements, unclear prod impact, competing architectures):
  stop, name the ambiguity, present 2–3 options with trade-offs, ask.
- **Operations discipline.** Background jobs/backfills: snapshot or document
  rollback first, monitor from a deterministic state, report before/after.
  Never run `sudo` restarts — list the command for the human. Never commit
  secrets, force-push, or mutate prod without explicit approval + rollback.
- **Delegation completion contract.** Your final message is the deliverable.
  If you delegate, you own collection: wait for results, integrate them, then
  report. Never end a turn while spawned work is still running. Decompose
  only when the work cannot fit in one context.

## 3. Command style

- Run shell commands directly (`git status`, `python3 -m pytest -q`).
- Prefer native Read/Grep tools when you need exact `line:content` for an edit.
- Avoid `cd <path> && <command>` chains — pass the path as an argument or set
  the tool working directory.
- **Never run `git commit` or `git push` without explicit user approval.**

## 4. CodeDNA annotations

CodeDNA is a hand-applied source-annotation convention. There is no binary,
validator, hook, or ledger — git is the authoritative audit log. Apply it to
every source file whose language supports comments (Python, Go, JS, TS, Rust,
shell). Do **not** annotate `.md`, `.json`, plain text, or commentless formats.

- **L1 module header** — first lines of each file, in the file's comment syntax:
  `filename — <what it does, 15 words or fewer>` then `exports:`, `used_by:`
  (tag consumers `[cascade]` when an edit must be verified against them),
  optional `related:`, `rules:` (hard constraints or `none`), and `agent:` (a
  rolling history of the last 5 sessions: `model-id | provider | YYYY-MM-DD |
  session_id | what you did`), optional `message:` beneath `agent:`.
- **L2 function annotation** — every public function carries a `Rules:` block
  in its docstring stating constraints, invariants, and edge cases. Omit only
  for trivial functions with no domain constraint. The first line may be a
  one-line summary of what the function does, 15 words or fewer; every line
  after it is a `Rules:` or `message:` line.
- **Inline annotations** — `# Rules:` / `# message:` above blocks that encode a
  business rule, non-obvious transform, step-order dependency, or edge case.
  Skip simple getters, obvious control flow, standard library calls.

**Rules for writing rules:** be specific and actionable — write `soft-delete
via deleted_at — never issue DELETE`, never `handle errors gracefully`. Use
`rules: none` only when a file genuinely has no domain constraint.

**Editing protocol:** re-read `rules:` and `agent:` history before editing;
keep `exports:` accurate — a symbol leaves the list in the same commit that
removes it, once no caller remains; after editing, check `used_by:` targets
especially `[cascade]`-tagged ones; append a new `agent:` line and keep only
the last 5 entries. Run
`.agents/skills/agents-contract/scripts/codedna_check.py` after a header change
to catch missing L1 fields, dead `used_by:` targets, `exports:` names absent
from the file, and over-long `agent:` histories. When the scanned paths hold an
`AGENTS.md`, it lints that document's Python examples against the same rules.

**CodeDNA is the only comment content.** No comment content outside CodeDNA may
exist in source files — no explanatory prose, no commented-out code, no
`TODO`/`FIXME` markers, no section dividers. The permitted set is a single-line
summary of what the file or function does, the L1 fields, L2 `Rules:` blocks,
and inline `Rules:`/`message:`. Constraints go in `rules:`/`Rules:`; open items
go in `message:`. Delete every non-CodeDNA comment in the code you touch — the
one exception to the Surgical-changes rule and the trace-back requirement. Tool
directives and license headers (`//go:build`, linter pragmas, type-ignore
comments, SPDX lines) are exempt — they are code, not comments. User-visible
documentation strings are exempt on the same footing: CLI help text, API and
OpenAPI descriptions, and public-library docstrings are product surface. Keep
them short and factual; constraints still belong in `rules:`/`Rules:`.

## 5. Engineering standards

- **Definition of Done** — before any change is complete: readable well-named
  identifiers; functions <50 lines; files within the 800-line soft ceiling;
  nesting <4 levels; errors handled explicitly; no hardcoded secrets; input
  validated at every boundary; no debug statements or dead code; no comments
  outside CodeDNA annotations; tests exist (80% coverage minimum); change is
  the smallest that satisfies the request; evidence exists per Verification.
- **Coding style** — KISS, DRY, YAGNI; immutability (create new objects, never
  mutate in place); many small files (200–400 lines, 800-line soft ceiling —
  test/generated/vendored files may exceed it when justified) organized by
  feature; naming: names describe what the thing does without a comment, and
  language idiom (Go, Rust, Python casing) wins over the defaults — variables
  `camelCase`, booleans `is/has/should/can`, types `PascalCase`, constants
  `UPPER_SNAKE_CASE`, tests `snake_case`.
- **Testing** — 80% coverage minimum across unit, integration, and E2E; two
  lanes: gate tests (fast, local, every change, never flaky) vs periodic
  evals (paid/slow, before ship, pass threshold); run what Task sizing calls
  for, the full suite only for large or contract changes. TDD mandatory
  (RED → GREEN → IMPROVE); AAA test structure with descriptive names. When
  tests fail, troubleshoot in order: test isolation → mocks → the
  implementation (not the tests, unless the test is wrong).
- **Security** — before any commit: no hardcoded secrets, input validation,
  SQLi/XSS/CSRF protection, auth verified, rate limiting, no sensitive data in
  error messages. STOP triggers — the independent review in §6, security-scoped,
  runs before proceeding when the change touches auth, user input, DB queries,
  file ops, external APIs, crypto, or payments, scoped to those checks and the
  touched surface; a CRITICAL or HIGH finding blocks the commit. On exposure:
  stop, identify, fix, rotate, review.

## 6. Code review

Two modes, each mandatory where it applies:

- **Self-review** — the author applies the DoD checklist and the severity table
  to the diff and fixes CRITICAL and HIGH findings before anyone else sees it:
  Work Loop step 5, every change.
- **Independent review** — a reviewer other than the author owns the verdict,
  using a reviewer subagent where the harness provides one and a human
  otherwise. Required for every change bound for a shared branch (pushed to a
  shared remote, or targeted by a merge or PR — a local scratch branch is not
  shared) or a merge, and for every change that trips the §5 STOP triggers. The
  reviewer records the verdict, covered scope, and open risk in the PR body or
  commit message.
- Pre-review for independent review: automated checks passing, no merge
  conflicts, branch up to date.
- Severity: CRITICAL = BLOCK; HIGH = WARN; MEDIUM = INFO (including an
  unexplained file over the soft 800-line ceiling); LOW = NOTE.
- The independent reviewer approves only when no CRITICAL or HIGH issues remain,
  warns on HIGH-only, and blocks on any CRITICAL; a security-scoped review (§5
  STOP triggers) blocks on a HIGH finding too.

## 7. Git workflow with session trailers

- **Never run `git commit` or `git push` without explicit user approval.** This
  repo rule overrides any upstream template suggesting automatic commit.
- **Commit format:** `<type>: <description>` where type is `feat`, `fix`,
  `refactor`, `docs`, `test`, `chore`, `perf`, or `ci`.
- **Session trailers** — at the end of every session that modified files, add
  these trailers to the commit:

  ```
  AI-Agent:    <model-id | unknown>
  AI-Provider: <provider | unknown>
  AI-Session:  <session_id | unknown>
  AI-Visited:  <files read, from the diff and the session read log>
  AI-Verified: <commands run and their result, one line>
  AI-Message:  <one-line summary of what was found or left open>
  ```

  The AI block is the last paragraph of the message, with no blank line inside
  it, and any `Co-authored-by:` line goes above it — git parses trailers from
  the final paragraph only, so a misplaced block is invisible to tooling. Check
  with `git log -1 --format='%(trailers:key=AI-Agent,valueonly)'`: it prints the
  agent when the block parses, and nothing when it does not. Write `unknown` for
  a value the harness does not expose.

- **Git is the authoritative audit log** — do not keep a separate ledger file.
- **Pull requests:** analyze full commit history, diff against base,
  comprehensive summary, test plan with TODOs, push with `-u` on new branches.

## 8. Verification

Run the smallest check that proves the change before claiming completion:

- Config/docs edits: syntax checks or targeted grep checks.
- Python: the relevant `pytest` targets.
- Go: `go build ./...` and `go vet ./...`.
- Browser/user-facing work: test observable behavior, verify with the real
  interface when possible.
- Report any check that could not run and why. Report final status honestly as
  `DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`, or `NEEDS_CONTEXT` with evidence.

## 9. Environment

- Use the Skill tool when a `superpowers` skill matches the task; otherwise
  read the tracked `SKILL.md` for project guidance.
- The context window is your main control surface: load the relevant contract
  section, files, and examples; leave the noise out. Avoid the last 20% of the
  context window for large multi-file refactors or complex debugging; single
  edits and docs tolerate higher utilization. When a task goes sideways, ask
  what was in the window first.
- Capture knowledge in the right place: personal notes → memory; team/project
  knowledge → the project's existing docs. Never duplicate what's already
  documented; ask before creating a new top-level file.

## Worked example

Task: "add a `get_config()` helper to src/config.py".

1. **Understand** — acceptance: lazy env loading, no import-time reads.
2. **Read first** — read `src/config.py`, its module header, and tests.
3. **Plan** — `1. Write failing test → verify: test fails for right reason.
   2. Implement lazy load → verify: targeted tests pass. 3. Annotate →
   verify: header + Rules present.`
4. **Implement with TDD** — test first (RED), minimal impl (GREEN), refactor.
5. **Self-review** — run the DoD checklist (size, errors, secrets, coverage).
6. **Prove it** — `pytest src/config_test.py`.
7. **Report and record** — status + commit with session trailers (approval
   first).
