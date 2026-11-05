---
name: agents-contract
description: MANDATORY bootstrap for every task under the repository's AGENTS.md operating contract — load before the first tool call; covers the 7-step Work Loop, task sizing, CodeDNA annotations, testing and security gates, code review, and git session trailers.
---

# Agents Contract — execution checklist

The canonical contract is `references/contract.md`, byte-identical to
`AGENTS.md`. This file is the executable checklist; load the reference section
when a step needs detail.

- `references/codedna.md` — full CodeDNA convention and checker behaviour.
- `references/commands.md` — full RTK catalogue, byte-identical to `RTK.md`.
- Companions `caveman.md`, `ponytail.md`, `semble.md`, and `loop.md` sit beside
  the `AGENTS.md` the harness loaded, or in its rules directory for Grok; this
  skill does not duplicate them.

## 0. Startup gate (before any tool call)

This file is the executable checklist; do not treat it as optional reading.
Subject to harness-precedence and the user's current request:

1. **Load this skill.** If you are acting on the contract without it, load it
   now. If the harness cannot load it, read the tracked
   `.agents/skills/agents-contract/SKILL.md` when present; otherwise state
   `skill unavailable` in the compliance record and follow the contract.
2. **State the task size**: `small`, `medium`, or `large`, with the one-line
   reason when the call is not obvious.
3. **State the command lane**: RTK-wrapped by default; raw only for exact
   bytes, parseable output, streaming, or secrets, with the reason.
4. **Check installed surfaces** after any contract/skill edit when the lowheat
   checkout is available: `python3 install.py --check --harness <name>`
   (read-only; exit 1 on drift). After a refresh, restart the harness or session
   so it reloads instruction and skill metadata; a running session keeps the old
   snapshot.

Starting a task with a tool call before steps 1–3 is non-compliant. Stop,
perform them, then continue.

## 1. Work Loop

Follow all 7 steps; each ends with a verification gate. Detailed unit mechanics
are in the `loop.md` companion beside `AGENTS.md`. If a step fails, fix the root
cause and do not declare done.

1. **Understand and define the check.** Read the request twice. State the
   problem, the *why*, and acceptance criteria. Write the pass condition as a
   command/exit code, schema, diff boundary, or eval threshold; confidence never
   passes.
   → Verify: you can say what "done" looks like and how a program decides.
2. **Read first.** Read the files you will touch, their CodeDNA headers, and
   their tests. Never propose changes to unread code.
   → Verify: you know what exists before adding anything.
3. **Plan the smallest unit graph.** Name risks and the revert path. For
   multi-unit work, give each unit a job, input, output, check, failure state,
   and write set; edge only real data dependencies; parallel only disjoint
   writes.
   → Verify: the plan fits the request and no unit writes another's files.
4. **Implement with TDD, one unit at a time.** Change, run the fixed check, keep
   or revert. Cap a behavior unit at three attempts; after three, stop and
   report the plan wrong. Revert only your own edits.
   → Verify: the targeted tests pass.
5. **Merge, then review.** Merge/dedupe/sort/compare with code; failed units
   return `UNIT`, `VERDICT`, `REASON`, `EVIDENCE`, `SCOPE`; never redo a passed
   unit. Run the Definition of Done; shared branches, merges, and STOP triggers
   also need independent review (§6).
   → Verify: every changed line traces to a unit and its check.
6. **Prove it and gate by undo cost.** Run the smallest check (§8). Cheap,
   contained changes may proceed; reversible, wide changes need evidence and a
   rollback; irreversible changes stop for approval.
   → Verify: evidence exists for every claim.
7. **Report, learn, and record.** Stop on a passing check, two rounds with no
   new evidence, or the budget. Report changed/checked/rejected/approval/
   unverified; write the learned rule into CodeDNA or the contract, not a second
   ledger; commit with the session trailers in §7.
   → Verify: a reviewer can rerun every claimed check.

## 2. Decision rules

- **Precedence.** Harness system prompt and safety rules, then the user's
  current request, then `AGENTS.md` on disk, then skill summaries and mirrors.
  A copy with a different `Contract-Version` is stale; refresh it, then act on
  the file on disk.
- **Task sizing.** Say the size out loud.
  **small** — mechanical, no behavior change; solo, touched checks only, no new
  test. **medium** — localized behavior change or bug fix; solo, touched module
  tests, regression test for fixes. **large** — feature, cross-module, contract,
  or judgment-heavy; full protocol, full suites, consider fan-out.
  When torn, pick smaller and say so; escalate with the new call.
- **Think first.** State assumptions; separate verified facts from uncertainty;
  present competing interpretations instead of picking silently. Ask only when
  materially ambiguous, risky, or approval-bound. Name the outcome and what
  "done" looks like before coding.
- **Smallest complete change.** Completeness is the floor, minimalism the
  ceiling. No speculative features, single-use abstractions, or impossible-case
  handling. Read the touched code, list callers/tests/fixtures/config/exports,
  then climb: YAGNI → existing code → standard library → native platform →
  installed dependency → one line → minimum code. Search before building.
  Surgical changes; fix a bug once at the shared root. Never cut trust-boundary
  validation, data-loss handling, security, accessibility, or explicit requests.
  End every report with what you skipped and the remaining risk.
- **Verify, don't assume.** Script deterministic work: lookups, parsing,
  counting, date math, validation. Tie every claim to evidence: test result,
  config check, log line, metric, diff. Test features and fixes; eval LLM,
  prompt, and ranking behavior; syntax/diff/link/marker-check docs and config.
  Never ship an unverified example. Status is `DONE`, `DONE_WITH_CONCERNS`,
  `BLOCKED`, or `NEEDS_CONTEXT`, with evidence.
- **Context.** Load the relevant contract section, module header, source,
  tests, and examples only. Use a matching skill. Prefer tables or code blocks
  when they explain faster than prose.
- **Codify repeated work** by the third manual run.
- **Confusion protocol.** For destructive, contradictory, production-impacting,
  or architectural ambiguity: stop, name it, present 2–3 options with
  trade-offs, ask.
- **Operations.** Document rollback before background jobs or backfills;
  monitor from a deterministic state; report before/after with paths and
  metrics. List exact restart commands for the human; never `sudo` restart
  unless authorized. Never commit secrets, destructive commands, production
  mutations, force pushes, hook bypasses, binaries, or model weights without
  approval and a rollback plan. Preserve unrelated work.
- **Delegation.** Your final message is the deliverable. Wait for subagents,
  integrate results, then report; never end a turn with work still running.
  Fan out only for independent units with disjoint write sets. Keep new
  subsystems ownership-, contract-, test-, and docs-clear.

## 3. Command style

- Instruction-only: no hook rewrites or refuses commands; invoke RTK and the
  discovery ladder yourself.
- Discovery ladder: semble MCP (`mcp__semble__search` on Claude Code and
  Command Code, `semble__search` on Grok) → semble CLI → `rtk grep` → native
  Grep/Glob. Native is the fallback for every-occurrence or exact
  `line:content`; reads stay native (`rtk read` equals `cat`).
- Wrap shell commands through RTK by default (`rtk git status`,
  `rtk pytest -q`). Run raw for exact bytes, parseable output, streaming, and
  secrets. Re-run raw once if a wrapped view hid something, then stop wrapping
  that command.
- **RTK gate:** attempt RTK first on every shell command. Raw needs a stated
  fidelity reason; a session with no wrapped command must explain why RTK was
  unusable or unsupported. One read-compressor per command: RTK; if RTK cannot
  wrap it, `caveman shrink` when installed; otherwise raw. `caveman browse`
  covers pages.
- Avoid `cd <path> && <command>`; pass the path or set the working directory.
- **Never run `git commit` or `git push` without explicit user approval.**

## 4. CodeDNA annotations

Apply to every source file whose language supports comments; do not annotate
`.md`, `.tex`, `.rst`, `.txt`, `.json`, or other commentless formats. No
comment content exists outside CodeDNA: no prose, commented-out code,
`TODO`/`FIXME`, or dividers. Tool directives, license headers, and user-visible
documentation strings are exempt.

- **L1 header** — `filename — description` (≤15 words), `exports:`,
  `used_by:` (`[cascade]` when edits must be verified there), optional
  `related:`, `rules:` (hard constraints or `none`), `agent:` (last 5 sessions,
  oldest first: `model-id | provider | YYYY-MM-DD | session_id | what changed`),
  optional `message:` beneath `agent:`.
- **L2 function** — every public function carries a `Rules:` block unless it is
  trivial and has no domain constraint. Auth, data, money, and external
  boundaries list every invariant and edge case.
- **Inline** — `# Rules:` / `# message:` only above non-obvious business rules,
  step-order dependencies, or edge cases. Skip simple getters and obvious code.

Read headers first: `exports:` as rename/removal guards, `used_by:`/`related:`
for scope, `rules:` as constraints, `agent:` as history. On edit, keep
`exports:` accurate, append one `agent:` line, drop the oldest beyond five, and
run this skill's `scripts/codedna_check.py` after annotation changes. In user
scope the skill is linked at `~/.claude/skills`, `~/.commandcode/skills`, or
`~/.grok/skills`; in the lowheat checkout it is
`.agents/skills/agents-contract/scripts/codedna_check.py`. Never `find /` for
it. Skip the run when the install ships no script.

## 5. Engineering standards

- **Definition of Done.** Named identifiers, no magic numbers; functions <50
  lines; cohesive files within the 800-line soft ceiling; nesting <4 levels;
  explicit error handling; no secrets; boundary validation; no debug or dead
  code; no non-CodeDNA comments; tests for new behavior and the project's
  coverage threshold; smallest change; evidence per §8.
- **Coding style.** KISS, DRY, YAGNI. Prefer new objects for shared state,
  domain models, and concurrent code; local accumulators are fine. Organize by
  feature/domain (200–400 lines typical, 800 soft ceiling; test/generated/
  vendored files may exceed it). Handle errors at every level, never swallow.
  Validate external input at boundaries, schema-based where available, fast
  fail with clear messages. Names describe the thing; language idiom wins over
  defaults (variables `camelCase`, booleans `is/has/should/can`, types
  `PascalCase`, constants `UPPER_SNAKE_CASE`, tests `snake_case`).
- **Testing.** Task sizing decides whether tests exist; the suite-wide coverage
  floor uses the project's threshold, defaulting to 80% only when none exists.
  Unit, integration, and E2E apply where relevant; E2E only for critical
  user-facing flows. Gate tests are fast, local, every change, never flaky;
  periodic evals are paid/slow, before ship, with a pass threshold. TDD where a
  test is written; AAA structure; descriptive names. On failure: isolation →
  mocks → implementation, not the test unless the test is wrong.
- **Security.** Before commit: no hardcoded secrets; validate input; prevent
  SQLi (parameterized queries) and XSS (sanitize HTML); enable CSRF; verify
  authn/authz; rate-limit appropriate surfaces; never leak sensitive data in
  errors. On exposure: stop, identify, fix, rotate, review. STOP triggers
  require an independent security-scoped review before proceeding: auth, user
  input, database queries, file operations, external APIs, crypto, payments. A
  CRITICAL or HIGH finding blocks the commit.

## 6. Code review

- **Self-review** — author runs the Definition of Done and severity table, and
  fixes CRITICAL/HIGH before anyone else sees the diff. Every change.
- **Independent review** — a non-author owns the verdict, using a reviewer
  subagent or a human. Required for shared branches, merges, and every STOP
  trigger. Record verdict, covered scope, and open risk in the PR body or
  commit message.
- Pre-review: CI passing, no conflicts, branch current with target.
- CRITICAL = BLOCK; HIGH = WARN; MEDIUM = INFO (including an unexplained file
  over the 800-line ceiling); LOW = NOTE. MEDIUM findings are fixed or recorded
  with a reason; LOW may be skipped. Approve only with no CRITICAL/HIGH; a
  security review also blocks on HIGH.

## 7. Git workflow

- Commit format: `<type>: <description>` with `feat`, `fix`, `refactor`,
  `docs`, `test`, `chore`, `perf`, or `ci`.
- Session trailers go in the final paragraph, no blank lines inside, after any
  `Co-authored-by:` line:

  ```
  AI-Agent:    <model-id | unknown>
  AI-Provider: <provider | unknown>
  AI-Session:  <session_id | unknown>
  AI-Visited:  <files read, derived from the diff and the session's read log>
  AI-Verified: <commands run and their result, one line>
  AI-Message:  <one-line summary of what was found or left open>
  ```

  Confirm with `git log -1 --format='%(trailers:key=AI-Agent,valueonly)'`.
  Write `unknown` when the harness exposes no value; never invent an ID. Git is
  the audit log; no separate ledger.
- Pull requests: analyze full history, diff against base, write a comprehensive
  summary and test plan, push with `-u` on new branches.

## 8. Verification

Run the smallest check that proves the change:

- docs/config: syntax check or targeted grep;
- installed contract surface when the lowheat checkout is available:
  `python3 install.py --check --harness <name>` (read-only; `--force` refresh
  only after reviewing replacements);
- Python: the relevant `rtk pytest` target, or `python3 -m pytest` without RTK;
- Go: `rtk go build ./...` and `rtk go vet ./...`;
- browser/user-facing: exercise observable behavior.

Report checks that could not run, meaningful blockers, outcomes, and evidence.
No noisy progress narration.

## 9. Environment

- Use a matching superpowers skill when available; otherwise read the tracked
  `SKILL.md` for project guidance.
- Treat context as an input. Avoid the last 20% of the window for multi-file
  refactors or complex debugging; single edits and docs tolerate more. When a
  task goes sideways, inspect what was in the window first.
- Personal notes → memory; team/project knowledge → existing docs. Do not
  duplicate an existing doc; ask before adding a top-level file.

## 10. Compliance record

End every final report with these four lines, or state why one is unavailable:

```text
Size:     small | medium | large
Skill:    agents-contract loaded | SKILL.md fallback | unavailable (reason)
Commands: RTK-wrapped N, raw M (reasons) | RTK unavailable
Review:   independent verdict | not required (small) | unavailable (reason)
```

A missing record is a contract violation. Do not claim `DONE` without it. The
record is a self-report; tie each line to a command or artifact a reviewer can
rerun.
