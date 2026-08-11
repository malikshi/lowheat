---
name: agents-contract
description: Execute tasks using the repository's operating contract from AGENTS.md — the 7-step Work Loop, Definition of Done, CodeDNA annotations, testing/security standards, and git commit with session trailers. Use when starting any task, writing or editing code, writing tests, committing changes, wrapping shell commands through RTK, or following the cross-agent contract.
---

# Agents Contract — Operating Contract Execution

This skill executes the repository's cross-agent operating contract defined in
`AGENTS.md`. It encodes the Operating Principles, the Work Loop, engineering
standards, CodeDNA protocol, and git workflow as executable steps. The full
contract text lives in `references/contract.md`; the RTK command catalogue
lives in `references/commands.md`. Read them when the steps below need detail.

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
   work before anyone else sees it.
   → Verify: every changed line traces back to the request.
6. **Prove it.** Run the smallest check that proves the change per the
   Verification section (`references/contract.md#verification`).
   → Verify: evidence exists for every claim you will make.
7. **Report and record.** Report status honestly; if files changed, commit with
   the session trailers under Git Workflow (step 4 below).

## 2. CodeDNA annotations

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
  for trivial functions with no domain constraint.
- **Inline annotations** — `# Rules:` / `# message:` above blocks that encode a
  business rule, non-obvious transform, step-order dependency, or edge case.
  Skip simple getters, obvious control flow, standard library calls.

**Rules for writing rules:** be specific and actionable — write `soft-delete
via deleted_at — never issue DELETE`, never `handle errors gracefully`. Use
`rules: none` only when a file genuinely has no domain constraint.

**Editing protocol:** re-read `rules:` and `agent:` history before editing;
never remove `exports:` symbols (they are contracts); after editing, check
`used_by:` targets especially `[cascade]`-tagged ones; append a new `agent:`
line and keep only the last 5 entries.

## 3. Engineering standards

- **Definition of Done** — before any change is complete: readable well-named
  identifiers; functions <50 lines; files <800 lines; nesting <4 levels; errors
  handled explicitly; no hardcoded secrets; input validated at every boundary;
  no debug statements or dead code; tests exist (80% coverage minimum); change
  is the smallest that satisfies the request; evidence exists per Verification.
- **Coding style** — KISS, DRY, YAGNI; immutability (create new objects, never
  mutate in place); many small files (200–400 lines, 800 max) organized by
  feature; naming: `camelCase` variables, `is/has/should/can` booleans,
  `PascalCase` types, `UPPER_SNAKE_CASE` constants, `snake_case` tests.
- **Testing** — 80% coverage minimum across unit, integration, and E2E; TDD
  mandatory (RED → GREEN → IMPROVE); AAA test structure with descriptive names.
  When tests fail, troubleshoot in order: test isolation → mocks → the
  implementation (not the tests, unless the test is wrong).
- **Security** — before any commit: no hardcoded secrets, input validation,
  SQLi/XSS/CSRF protection, auth verified, rate limiting, no sensitive data in
  error messages. On exposure: stop, identify, fix, rotate, review.

## 4. Git workflow with session trailers

- **Never run `git commit` or `git push` without explicit user approval.** This
  repo rule overrides any upstream template suggesting automatic commit.
- **Commit format:** `<type>: <description>` where type is `feat`, `fix`,
  `refactor`, `docs`, `test`, `chore`, `perf`, or `ci`.
- **Session trailers** — at the end of every session that modified files, add
  these trailers to the commit:

  ```
  AI-Agent:    <model-id>
  AI-Provider: <provider>
  AI-Session:  <session_id>
  AI-Visited:  <comma-separated list of files read>
  AI-Message:  <one-line summary of what was found or left open>
  ```

- **Git is the authoritative audit log** — do not keep a separate ledger file.
- **Pull requests:** analyze full commit history, diff against base,
  comprehensive summary, test plan with TODOs, push with `-u` on new branches.

## 5. Verification

Run the smallest check that proves the change before claiming completion:

- Config/docs edits: syntax checks or targeted grep checks.
- Python: the relevant `rtk pytest` targets.
- Go: `rtk go build ./...` and `rtk go vet ./...`.
- Browser/user-facing work: test observable behavior, verify with the real
  interface when possible.
- Report any check that could not run and why. Report final status honestly as
  `DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`, or `NEEDS_CONTEXT` with evidence.

## Worked example

Task: "add a `get_config()` helper to src/config.py".

1. **Understand** — acceptance: lazy env loading, no import-time reads.
2. **Read first** — read `src/config.py`, its module header, and tests.
3. **Plan** — `1. Write failing test → verify: test fails for right reason.
   2. Implement lazy load → verify: targeted tests pass. 3. Annotate →
   verify: header + Rules present.`
4. **Implement with TDD** — test first (RED), minimal impl (GREEN), refactor.
5. **Self-review** — run the DoD checklist (size, errors, secrets, coverage).
6. **Prove it** — `rtk pytest src/config_test.py`.
7. **Report and record** — status + commit with session trailers (approval
   first).
