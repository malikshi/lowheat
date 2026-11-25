---
name: agents-contract
description: MANDATORY bootstrap for every task under the repository's AGENTS.md operating contract — load before any task tool call; covers the 7-step Work Loop, task sizing, CodeDNA annotations, testing and security gates, code review, and git session trailers.
---

# Agents Contract — execution checklist

Canonical detail: `references/contract.md`, byte-identical to `AGENTS.md`.
`references/codedna.md` covers annotations and `references/commands.md` the RTK
catalogue. Companions `caveman.md`, `ponytail.md`, `semble.md`, `loop.md`, and `review.md`
sit beside `AGENTS.md`; this skill does not duplicate them. The review gate
dispatches the installed `reviewer` and `review-finder` subagents.

## 0. Startup gate (before any task tool call)

1. **Load this skill.** If the harness cannot load it, read the tracked
   `.agents/skills/agents-contract/SKILL.md` when present; otherwise state
   `skill unavailable` and follow `AGENTS.md`.
2. **State the task size** (`small`, `medium`, or `large`) and **command lane**
   (RTK-wrapped default; raw only for exact bytes, parseable output, streaming,
   or secrets, stating why). Do not end Turn 1 after stating these — proceed
   directly into the Work Loop.
3. **Check installed surfaces** when a contract or skill changed and the
   lowheat checkout is available: `python3 install.py --check --harness <name>`
   (use `/usr/bin/python3` or `.venv/bin/python` if a `python3` shim on `PATH`
   fails). Refresh missing or installer-owned links without `--force`; use
   `--force` only after confirming a differing target is an older lowheat copy,
   never a user-owned file. If user-scope config paths are read-only inside a
   sandbox, sync repo mirrors via
   `python3 -c 'import install; install.sync_contract_mirror(install.CONTRACT_DIR, install.SKILL_DIR)'`
   and read canonical `contract/` files from disk instead of asking for sandbox
   escalation. Re-read updated files from disk in-session;
   never block waiting for a human harness restart (note the refresh for
   future sessions in the final report).

Starting task work before steps 1–2 is non-compliant. Stop, perform them, then
continue.

## 1. Work Loop

Each step ends with its gate. Unit mechanics: `loop.md`.

1. **Define the check.** State the problem, the *why*, and acceptance criteria
   as a command/exit code, schema, diff boundary, or eval threshold. Gate: a
   program can decide "done".
2. **Read first.** Read touched files, their CodeDNA headers, and their tests.
   Gate: know what exists before adding anything.
3. **Plan the smallest unit graph.** One job, input, output, check, failure
   state, and write set per unit; edges only for real data dependencies;
   parallel only disjoint writes. Gate: no unit writes another's files.
4. **Implement with TDD, one unit at a time.** Change, run the fixed check,
   keep or revert. Cap a behavior unit at three attempts, then report the plan
   wrong. Revert only your own edits. Gate: the targeted check passes.
5. **Merge, then review.** Compare with code. A failed unit returns `UNIT`,
   `VERDICT`, `REASON`, `EVIDENCE`, and `SCOPE`; never redo a passed unit.
   Self-review against the Definition of Done; a shared branch, merge, release,
   or STOP trigger also gets independent review. Gate: every changed line traces
   to a unit and its check.
6. **Prove it and gate by undo cost.** Run the smallest proving check. Cheap
   contained changes may proceed; reversible wide changes need evidence and a
   rollback path; irreversible changes stop for approval. A passing check never
   authorizes a commit or push. Gate: evidence for every claim.
7. **Report, learn, and record.** Stop on a passing check, two rounds with no
   new evidence, or the budget. Report changed/checked/rejected/approval/
   unverified; write the learned rule into CodeDNA `rules:`, a project
   `RULES.md` for cross-file invariants, or the contract when contributing to
   lowheat. Gate: a reviewer can rerun every claimed check.

If a step fails, fix the root cause; do not work around it or declare done.

## 2. Decision rules

- **Precedence.** Harness system prompt and safety rules, then the user's
  current request, then the project's `RULES.md` (it narrows the contract and
  never relaxes the approval gates), then `AGENTS.md` on disk, then skill
  summaries and mirrors. A different `Contract-Version` is stale; refresh it,
  then act on the file on disk.
- **Task sizing.** **small** — mechanical, no behavior change; solo, touched
  checks only, no new test; the check is the diff boundary or a targeted grep.
  **medium** — localized behavior change or bug fix; solo, touched module
  tests, regression test for fixes. **large** — feature, cross-module,
  contract, or judgment-heavy; plan first, full suites, consider fan-out. When
  torn, pick smaller and say so; escalate with the new call.
- **Think first.** Name the outcome and what "done" looks like before coding.
  Resolve ambiguity from existing code, tests, types, git history, and
  `RULES.md` first. Execute end-to-end without pausing for plan or step
  confirmations unless asked; when multiple reversible paths fit, pick the
  smallest convention-matching one, verify it, and disclose the assumption.
  Explicit commit/push approval may come in the user prompt or after the report.
- **Smallest complete change.** Completeness is the floor, minimalism the
  ceiling. Read touched code, list callers/tests/fixtures/config/exports, then
  climb: YAGNI → existing code → standard library → native platform →
  installed dependency → one line → minimum code. Fix a bug once at the shared
  root. Never cut trust-boundary validation, data-loss handling, security,
  accessibility, or explicit requests. End every report with what you skipped
  and the remaining risk.
- **Verify, don't assume.** Script deterministic work. Tie every claim to a
  test, config check, log, metric, or diff. Test features and fixes; eval LLM,
  prompt, and ranking behavior; syntax/diff/link/marker-check docs and config.
  Never ship an unverified example. Status: `DONE`, `DONE_WITH_CONCERNS`,
  `BLOCKED`, or `NEEDS_CONTEXT`, with evidence.
- **Context.** Load the relevant section, header, source, tests, and examples
  only. Avoid the last 20% of the window for multi-file refactors or complex
  debugging; when a task goes sideways, inspect what was in the window first.
- **Confusion protocol.** Trigger only when codebase evidence cannot settle
  ambiguity AND a wrong choice risks destructive/irreversible actions, data
  loss, security exposure, production impact, or breaking an external contract:
  stop, name it, present 2–3 options with trade-offs, ask.
- **Operations.** Document rollback before background jobs or backfills;
  report before/after with paths and metrics. List exact restart commands for
  the human; never `sudo` restart unless authorized. Never commit secrets,
  destructive commands, production mutations, force pushes, hook bypasses,
  binaries, or model weights without approval and a rollback plan. Preserve
  unrelated work.
- **Delegation.** Your final message is the deliverable. Wait for subagents,
  integrate results, then report; never end a turn with work still running.
  Fan out only for independent units with disjoint write sets.

## 3. Command style

- Instruction-only: no hook rewrites or refuses commands; apply the ladder
  yourself.
- **Discovery ladder:** semble MCP (`search`/`find_related`) → semble CLI →
  `rtk grep` (lossy survey) → native Grep/Glob (exact `line:content`). Reads
  stay native; `rtk read` equals `cat`. A missing rung drops to the next.
- **RTK gate.** Attempt RTK first on every shell command (`rtk git status`,
  `rtk pytest -q`). Raw needs a stated fidelity reason; a session with no
  wrapped command says why. Re-run raw once if a wrapped view hid something,
  then stop wrapping that command.
- Avoid `cd <path> && <command>`; pass the path or set the working directory.
- **Never run `git commit` or `git push` without explicit user approval.**

## 4. CodeDNA annotations

Apply to every source file whose language supports comments; never annotate
`.md`, `.tex`, `.rst`, `.txt`, `.json`, or other commentless formats.

- **L1 header** — `filename — description` (≤15 words), `exports:`, `used_by:`
  (`[cascade]` when edits must be verified there), optional `related:`,
  `rules:`, and the last five `agent:` lines. Optional `message:` beneath
  `agent:`.
- **L2 function** — every public function carries a `Rules:` block unless
  trivial with no domain constraint. Auth, data, money, and external
  boundaries list every invariant and edge case.
- **Inline** — `# Rules:` / `# message:` only above non-obvious business
  rules, step-order dependencies, or edge cases.
- **On edit** — keep `exports:` accurate, update `rules:`, append one `agent:`
  line, drop the oldest beyond five, delete non-CodeDNA comments in functions
  or blocks you edit, and run `scripts/codedna_check.py` after annotation
  changes (skip when no script ships). If `docs/comment-budget.json` exists,
  also run `scripts/comment_budget.py . --baseline docs/comment-budget.json`,
  and offset `<5`-entry `agent:` appends by deleting a Tautology or Stale line
  in the same edit.

## 5. Engineering standards

- **Definition of Done.** Named identifiers, no magic numbers; functions <50
  lines; cohesive files within the 800-line soft ceiling; nesting <4 levels;
  explicit error handling; no secrets; boundary validation; no debug or dead
  code; no non-CodeDNA comments; tests for new behavior and the project's
  coverage threshold; smallest change; evidence per Verification.
- **Coding style.** KISS, DRY, YAGNI. Prefer new objects for shared state,
  domain models, and concurrent code; local accumulators are fine. Organize by
  feature/domain (200–400 lines typical, 800 soft ceiling). Handle errors at
  every level; validate external input at boundaries; names say what the thing
  holds without a comment, language idiom first.
- **Testing.** Task sizing decides whether tests exist; the coverage floor uses
  the project's threshold, defaulting to 80% only when none exists. Unit,
  integration, and E2E apply where relevant; E2E only for critical flows. Gate
  tests are fast, local, every change, never flaky; periodic evals are paid or
  slow, before ship, with a pass threshold. TDD where a test is written; AAA;
  descriptive names. On failure: isolation → mocks → implementation, not the
  test unless the test is wrong.
- **Security.** No hardcoded secrets; validate input; prevent SQLi
  (parameterized queries) and XSS (sanitize HTML); enable CSRF; verify
  authn/authz; rate-limit appropriate surfaces; no sensitive data in errors.
  On exposure: stop, identify, fix, rotate, review. **STOP triggers** require
  an independent security-scoped review when a change touches auth, untrusted
  input, database queries, path-dynamic or privileged file system operations,
  external APIs, crypto, or payments. A CRITICAL or HIGH finding blocks the
  commit.

## 6. Code review

- Load `review.md` for both engines; the gates below stay in the thin core.
- **Self-review** — the author applies the Definition of Done and severity
  table, fixes CRITICAL/HIGH before anyone sees the diff, every change. Review
  agreements across boundaries, not files. Every finding needs an
  evidence-backed expectation, a feasible execution, the violated
  relationship cited at every participant, an observable consequence, and a
  refutation that survives the strongest counterargument; drop on a real
  preventing mechanism, not on "usually works". Zero supported findings is
  valid — never say "bug-free".
- **Independent review** — a non-author owns the verdict, required for shared
  branches, merges, STOP triggers, and every release. Dispatch ladder:
  installed `reviewer` (plus `review-finder` per flow on multi-flow subjects) →
  fresh runtime/generic read-only subagent (`define_subagent`, `research`, or
  read-only worker) carrying `review.md`'s method + brief where no agent
  directory exists or in project scope → `RULES.md` recorded fallback → fresh
  builder-family subagent → inline five-element + STOP-trigger audit on
  single-session harnesses with zero subagent tools (`Review: unavailable (no
  subagent runner; inline five-element review completed)`). Never resume, fork,
  or inherit the builder's context; read-only tools, no suspected defects in
  brief. Compute the subject deterministically from git (resolve `RELEASED` or
  empty tree first — never run an unset `$RELEASED..HEAD`, which evaluates as
  empty `HEAD..HEAD`). Re-run after every fix. Stop at no INTRODUCED finding
  above Low and no High or Critical of any age. The author/coordinator triages
  findings and records verdict, scope, round count, finding outcomes, and open
  risk in the final report, PR body, or commit message.
- Pre-review: checks pass, no conflicts, branch current with target. A short
  clean round or a round that could not read the subject is a failed round.
- **Model panel** — to widen one round, dispatch the `reviewer` or
  `review-finder` body plus the same brief (using `review.md`'s method + report
  block when no agent file exists on disk) to three models in one turn with
  per-run model overrides (or distinct tier enum values when the tool schema
  rejects catalog strings), never by pinning `model` in the installed
  definition. Members stay isolated; a lone member's finding gets the full five
  elements, not a majority vote; a panel is one round, not three. Fan-out
  applies it to every flow or not at all, never to some flows.
- CRITICAL = BLOCK; HIGH = WARN; MEDIUM = INFO (including an unexplained file
  over the 800-line ceiling); LOW = NOTE. MEDIUM is fixed or recorded with a
  reason; LOW may be skipped. Approve only with no CRITICAL/HIGH; a security
  review also blocks on HIGH.

## 7. Git workflow

- Format: `<type>(<scope>): <description>`, where the scope is optional; types
  are `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`.
- Session trailers go in the final paragraph, no blank lines inside, after any
  `Co-authored-by:` line:

```text
AI-Agent:    <model-id | unknown>
AI-Provider: <provider | unknown>
AI-Session:  <session_id | unknown>
AI-Visited:  <files read, derived from the diff and the session's read log>
AI-Verified: <commands run and their result, one line>
AI-Rejected: <attempts tried and reverted, or none>
AI-Message:  <one-line summary of what was found or left open>
```

Confirm with `git log -1 --format='%(trailers:key=AI-Agent,valueonly)'`; write
`unknown` when the harness exposes no value. Git is the audit log; keep no
separate ledger.
- Pull requests: full history, diff against base, comprehensive summary and
  test plan, push with `-u` on a new branch.

## 8. Verification

- Docs/config: syntax check or targeted grep.
- Installed contract surface, in the source checkout:
  `python3 install.py --check --harness <name>`
  (read-only; `--force` refresh only after reviewing replacements).
- Python: the relevant `rtk pytest` target, or `python3 -m pytest` (or
  `python3 -m unittest`) without RTK.
- Go: `rtk go build ./...` and `rtk go vet ./...`.
- Browser/user-facing: exercise observable behavior.

Report checks that could not run, blockers, outcomes, and evidence.

## 9. Compliance record

End every final report with these four lines, or state why one is unavailable:

```text
Size:     small | medium | large
Skill:    agents-contract loaded | SKILL.md fallback | unavailable (reason)
Commands: RTK-wrapped N, raw M (reasons) | RTK unavailable
Review:   independent verdict | not required (small or local, no STOP trigger) | unavailable (reason)
```

A missing record is a contract violation. Tie each line to a command or
artifact a reviewer can rerun.
