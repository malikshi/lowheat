---
name: agents-contract
description: MANDATORY bootstrap for every task under the repository's AGENTS.md operating contract — load before any task tool call; covers the 7-step Work Loop, task sizing, CodeDNA annotations, testing and security gates, code review, and git session trailers.
---

# Agents Contract — execution checklist

Canonical detail: `references/contract.md`, byte-identical to `AGENTS.md`.
`references/codedna.md` covers annotations and `references/commands.md` the RTK
catalogue. Companions `caveman.md`, `ponytail.md`, `semble.md`, `loop.md` sit
beside `AGENTS.md`; this skill does not duplicate them.

## 0. Startup gate (before any task tool call)

1. **Load this skill.** If the harness cannot load it, read the tracked
   `.agents/skills/agents-contract/SKILL.md` when present; otherwise state
   `skill unavailable` and follow `AGENTS.md`.
2. **State the task size**: `small`, `medium`, or `large`.
3. **State the command lane**: RTK-wrapped by default; raw only for exact
   bytes, parseable output, streaming, or secrets, with the reason.
4. **Check installed surfaces** after a contract or skill edit when the lowheat
   checkout is available: `python3 install.py --check --harness <name>`
   (read-only; exit 1 on drift). Refresh with `--force`, then restart the
   session so it reloads instruction and skill metadata.

Starting task work before steps 1–3 is non-compliant. Stop, perform them, then
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
   Self-review against the Definition of Done; a shared branch, merge, or STOP
   trigger also gets independent review. Gate: every changed line traces to a
   unit and its check.
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
- **Think first.** State assumptions; separate facts from uncertainty; present
  competing interpretations. Ask only when materially ambiguous, risky, or
  approval-bound. Name the outcome and what "done" looks like before coding.
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
- **Confusion protocol.** For destructive, contradictory,
  production-impacting, or architectural ambiguity: stop, name it, present
  2–3 options with trade-offs, ask.
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
  or blocks you edit, and run the skill's `scripts/codedna_check.py` after
  annotation changes. Skip when the install ships no script.

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

- **Self-review** — the author applies the Definition of Done and severity
  table and fixes CRITICAL/HIGH before anyone else sees the diff. Every change.
- **Independent review** — a non-author owns the verdict (reviewer subagent or
  human). Required for shared branches, merges, and every STOP trigger. Record
  verdict, covered scope, and open risk in the PR body or commit message.
- Pre-review: checks pass, no conflicts, branch current with target.
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
- Installed contract surface: `python3 install.py --check --harness <name>`
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
