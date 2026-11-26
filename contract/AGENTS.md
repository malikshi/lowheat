# Agent Instructions

Contract-Version: 2026-11-26.1

Thin cross-agent operating core; companions load on demand only when needed.

## How to use this file

Read Operating Principles and The Work Loop once; route detail via the tables:

| When you are… | Read |
|---|---|
| Starting any task | Session bootstrap, Operating Principles, The Work Loop |
| Sizing or resolving conflict | Task sizing, Precedence |
| Running commands / locating code | Command Style (`RTK.md`, `semble.md`) |
| Replying, committing, or reviewing | Communication Style (`caveman.md`), Git Workflow, Code Review (`review.md`) |
| Writing or editing source | Coding Style, CodeDNA (`codedna.md`) |
| Writing tests or touching boundaries | Testing Requirements, Security Guidelines |
| Choosing scope or running units | `ponytail.md`, `loop.md` |
| Unclear or blocked | Confusion protocol |

A harness scanning a rules directory loads every companion at startup; use the
table to route attention, not loading.

### Companion references

| File | Load when | Covers |
|---|---|---|
| `codedna.md` | writing or editing source | annotations, headers, function rules, checker, comment audit |
| `RTK.md` | wrapping shell commands | intent rule, fidelity zones, CLI catalogue |
| `semble.md` | locating code | discovery ladder, CLI verbs, MCP fallback, caveats |
| `caveman.md` | changing reply, commit, or review format | voice rules, modes, commit/review shapes, layer |
| `ponytail.md` | choosing scope or disclosing skips | ladder, never-cut floor, levels, disclosure line |
| `loop.md` | running multi-unit or risky work | machine check, unit cards, retries, merge, undo gates |
| `review.md` | reviewing code or clearing a change | agreement engine, refutation, isolated rounds, panel, triage |

`reviewer` owns the ship verdict; `review-finder` hunts one flow during fan-out.
Both install into the harness agent directory (no second CLI). Dispatch the
installed definition, or the runtime/recorded fallback where no agent directory
exists. For a Model panel, dispatch either
subagent's body plus the same brief across models rather than pinning `model`.

### Precedence

Higher wins:

1. Harness system prompt and safety rules.
2. User's current request.
3. The project's `RULES.md`, when present. It narrows this file; it never
   relaxes the gates below.
4. This file on disk.
5. Skill summaries, pinned copies, and mirrors.

These gates hold whatever a project `RULES.md` says: harness safety, explicit
approval before a commit or push (which may appear in the request itself, never
assumed from silence), secret handling, and approval before a destructive or
irreversible action.

A copy lacking `Contract-Version` or showing a different one is stale. Format
is `YYYY-MM-DD.N`; bump `N` for every change to any installed surface,
companions included, refresh from canonical checkout, then act on disk. Check
identical bytes via `python3 install.py --check` (`--scope project --root
<path>` for project scope).

### Session bootstrap (mandatory)

Below system prompt and user request in Precedence, before any task tool call:

1. **Load `agents-contract`.** If unavailable, read tracked
   `.agents/skills/agents-contract/SKILL.md`; else state `skill unavailable` and
   follow this file. Loading or reading it may be the first tool call.
2. **State task size** (`small`, `medium`, or `large`) and **command lane**
   (RTK-wrapped default; raw only for exact bytes, parseable output, streaming,
   or secrets, stating why). Do not end Turn 1 after stating these — proceed
   directly into The Work Loop.
3. **Check installed surfaces** when contract/skill changed and checkout is
   present: `python3 install.py --check --harness <name>` (use `/usr/bin/python3`
   or `.venv/bin/python` if a `python3` shim on `PATH` fails). Refresh missing
   or installer-owned links without `--force`; use `--force` only after
   verifying a differing target is an older lowheat copy, never user-owned.
   If user-scope config paths are read-only in a sandbox, sync repo mirrors via
   `python3 -c 'import install; install.sync_contract_mirror(install.CONTRACT_DIR, install.SKILL_DIR)'`
   and read canonical files from disk instead of requesting sandbox escalation.
   Re-read updated files from disk in-session; never block waiting for a human
   harness restart (note the refresh for future sessions in the final report).

## Operating Principles

Adapts CLAUDE.md, Karpathy guidelines, and ECC rule packs.

### Autonomous execution & task sizing

Execute end-to-end without pausing for plan approval, step confirmation,
test/fix permission, or reversible implementation choices unless asked. Scale
ceremony to the change and state the size once:

- **small** — mechanical 1–2 file edit, no behavior change. Solo; check diff
  boundary or targeted grep; no new test.
- **medium** — localized behavior change or bug fix in one module. Solo by
  default; run module tests; bug fixes ship a regression test.
- **large** — feature, cross-module/contract change, architecture, or UX. Plan
  first; run full module test/eval suites; fan out only disjoint work.

When torn, pick smaller and say so; escalate immediately if scope grows.

### Think before coding

Name the outcome (metric, workflow step, behavior, or trace) before editing.
Resolve ambiguity from code, tests, types, git history, and `RULES.md` first.
When multiple reversible paths fit, pick the smallest convention-matching one,
verify it, and disclose the assumption at the end. Stop under Confusion
protocol **only** when codebase evidence cannot settle it AND a wrong choice
risks data loss, security exposure, production impact, or breaking an external
contract.

### Smallest complete change

Completeness is the floor; minimalism is the ceiling.

- **Simplicity & ladder.** No speculative abstractions or unrequested options.
  Read touched code, callers, tests, fixtures, config, and exports first, then
  climb: YAGNI → existing code → stdlib → platform → installed dep → one line →
  minimal new code (`ponytail.md`). Never cut trust-boundary validation,
  data-loss guards, security, accessibility, or explicit requests.
- **Surgical changes.** Touch only what the task requires; preserve unrelated
  work; mention pre-existing dead code instead of deleting it. Fix a bug once
  at its shared root.
- **Disclose skips.** End every report with what was skipped and residual risk.

### Verify, don't assume

Script lookups, parsing, counting, date math, and validation. Every claim
needs evidence: tests for features/fixes, evals or rubrics for LLM/prompt
behavior, syntax/diff/link/marker checks for docs/config. Never ship an
unverified example. Report status honestly: `DONE`, `DONE_WITH_CONCERNS`,
`BLOCKED`, or `NEEDS_CONTEXT`.

### Context & operations discipline

- Load only relevant sections, headers, source, tests, and examples; avoid the
  last 20% of context on multi-file refactors.
- **Confusion protocol:** for destructive, contradictory, production-impacting,
  or external-contract ambiguity that code cannot resolve, stop, name it, give
  2–3 options with trade-offs, and ask.
- **Operations:** record rollback before background jobs/backfills; report exact
  human restart commands (never `sudo` restart unasked); never commit secrets,
  destructive commands, production mutations, force pushes, hook bypasses,
  binaries, or model weights without approval and rollback.
- **Delegation:** wait for subagents, integrate results, and never end a turn
  with spawned work still running.

## The Work Loop

Each step ends with a verify gate (unit mechanics in `loop.md`):

1. **Define the check.** State problem, *why*, and program-verifiable pass
   criteria (exit code, schema, diff boundary, or eval threshold).
2. **Read first.** Read touched files, CodeDNA headers, and tests.
3. **Plan smallest unit graph.** One job, input, output, check, failure state,
   and write set per unit; parallelize only disjoint write sets.
4. **Implement with TDD.** Edit, run fixed check, keep or revert (your edits
   only; cap behavior units at 3 attempts before re-planning).
5. **Merge, then review.** Compare with code; failed units return `UNIT`,
   `VERDICT`, `REASON`, `EVIDENCE`, `SCOPE`. Self-review against Definition of
   Done; shared branches, merges, releases, and STOP triggers get independent
   review.
6. **Prove & gate by undo cost.** Verify actual behavior and failure modes.
   Cheap/contained → keep; reversible/wide → hard evidence + rollback path;
   irreversible → stop for explicit approval. Passing checks never authorize
   commit or push.
7. **Report, learn, record.** Stop on passing check, two rounds without new
   evidence, or budget cap. Report changed, checked, rejected, approvals
   needed, and unverified. Capture learned rules in CodeDNA `rules:`, project
   `RULES.md`, or lowheat contract itself. Commit with trailers only with
   explicit approval.

Fix root causes on failure; never work around or declare done.

### Compliance record

End every final report with these four lines (or why one is unavailable):

```text
Size:     small | medium | large
Skill:    agents-contract loaded | SKILL.md fallback | unavailable (reason)
Commands: RTK-wrapped N, raw M (reasons) | RTK unavailable
Review:   independent verdict | not required (small or local, no STOP trigger) | unavailable (reason)
```

## Engineering Standards

### Definition of Done

- [ ] Readable names; no magic numbers
- [ ] Functions <50 lines; files ≤800 lines; nesting <4 levels
- [ ] Explicit error handling at every boundary; user input validated
- [ ] No hardcoded secrets, debug leftovers, or dead code
- [ ] No comments outside CodeDNA annotations
- [ ] Tests cover new behavior and meet project coverage threshold
- [ ] Smallest change meeting the request, backed by Verification evidence

### Verification

Run the smallest proving check:

- Docs/config: syntax, marker, or targeted grep.
- Checkout surfaces: `python3 install.py --check --harness <name>`.
- Python: `rtk pytest` (or raw `python3 -m pytest` / `unittest`).
- Go: `rtk go build ./...` and `rtk go vet ./...`.
- UI/user-facing: exercise observable behavior through the real interface.

### Coding Style

KISS, DRY, YAGNI. Prefer immutable/new objects for shared state and concurrent
code. Organize by domain (200–400 lines typical, 800 ceiling). Fail fast on
invalid boundary input; detail errors server-side. Use language-idiomatic naming
(`camelCase` vars/fns, `is/has/should/can` booleans, `PascalCase` types,
`UPPER_SNAKE_CASE` constants, `snake_case` behavioral test names).

### CodeDNA

Hand-applied annotation convention (`codedna.md`); no upstream binary or hook —
the skill ships its own read-only checker and git is the audit log.

- **Only comment content.** No prose comments, commented-out code, `TODO`/
  `FIXME`, or section dividers. Tool directives, license headers, and
  user-visible docstrings are exempt.
- **L1 header.** `filename — description` (≤15 words), `exports:`, `used_by:`,
  optional `related:`, `rules:`, and ≤5 `agent:` lines (+ optional `message:`).
- **L2 & inline.** Public functions carry `Rules:` unless trivial with no domain
  constraint; inline `# Rules:` / `# message:` only for non-obvious invariants.
- **Maintain on edit.** Update `exports:` and `rules:`, append one `agent:`
  line (drop oldest >5), delete non-CodeDNA comments in functions or blocks you edit,
  and run `codedna_check.py`.
- **Comment audit.** Grade every comment (including CodeDNA annotations;
  earlier label wins): Tautology (delete), Excuse (delete + row in
  `docs/comment-debt.md`), Stale (delete), Decision Record (delete + ADR in
  `docs/adr/`) in the same change.

### Testing Requirements

Task sizing governs test scope (80% default coverage floor when unconfigured).
Gate tests are deterministic, local, and fast; evals measure LLM/prompt
quality on schedule or pre-ship. TDD (RED → GREEN → IMPROVE), AAA structure;
on failure check isolation → mocks → implementation.

### Security Guidelines

Check before commit: no hardcoded secrets; input validated; parameterized SQL;
sanitized HTML (XSS); CSRF; authn/authz; rate limiting; non-leaking errors.
On secret exposure: stop, identify, fix, rotate, review codebase.

**STOP triggers — independent security-scoped review required** when touching
authn/authz, untrusted user input, database queries,
path-dynamic or privileged file system operations, external APIs, crypto, or
payments. CRITICAL or HIGH blocks the commit.

## Execution & Delivery

### Command Style

Instruction-only (no harness hook rewrites/refuses commands).

- **RTK gate.** Attempt `rtk <cmd>` first when skimming (`rtk git status`,
  `rtk pytest -q`). Run raw only for exact bytes, parseable output, streaming,
  or secrets (state reason in Compliance record). If RTK hides needed output,
  recover with `rtk recall <hash>` or re-run raw once and stop wrapping that
  command. If RTK is missing or unsupported, run raw.
- **One compressor per command.** RTK default, else `caveman shrink`, else raw.
  Use native Read/Grep for exact file work (`rtk read` equals `cat`).
- Avoid `cd <path> && <command>`; pass paths or set working directory.
- **Never run `git commit` or `git push` without explicit user approval.**

#### Discovery ladder

Take the first available rung, then read natively (`semble.md`, `RTK.md`):

1. **Semble MCP** — harness-qualified `search` / `find_related`
   (`mcp__semble__search` on Claude/Command Code, `semble__search` on Grok).
2. **Semble CLI** — `semble search "<query>" . --max-snippet-lines 10`.
3. **`rtk grep`** — lossy survey ("roughly where", not exhaustive).
4. **Native Grep/Glob** — exact `line:content`, every occurrence.

### Communication Style

Default terse caveman mode (`caveman.md`): answer first (`[thing] [action]
[reason]. [next step].`), no greeting/recap, fragments fine, negations/numbers/
code/paths/errors verbatim. Full sentences for security warnings, irreversible
actions, order-sensitive steps, and confused users; normal prose outside chat.

### Git Workflow

`<type>(<scope>): <description>` (The scope is optional; types: `feat`, `fix`,
`refactor`, `docs`, `test`, `chore`, `perf`, `ci`).

With explicit approval (from prompt or after report), commit modified sessions
with these trailers in the final paragraph (no blank lines inside, after any
`Co-authored-by:`):

```text
AI-Agent:    <model-id | unknown>
AI-Provider: <provider | unknown>
AI-Session:  <session_id | unknown>
AI-Visited:  <files read, derived from diff and session read log>
AI-Verified: <commands run and result, one line>
AI-Rejected: <attempts tried and reverted, or none>
AI-Message:  <one-line summary of what was found or left open>
```

Verify via `git log -1 --format='%(trailers:key=AI-Agent,valueonly)'`; write
`unknown` if unexposed; never invent IDs or keep a separate ledger. Without
approval, stop after reporting and provide the ready-to-run commit block.

**Pull requests:** analyze full branch history (`rtk git diff [base]...HEAD`),
write summary + test plan, push `-u` on a new branch (with approval).

### Code Review Standards

Load `review.md` for full engines and report contract.

- **Self-review** (Work Loop step 5, every change): check Definition of Done and
  cross-boundary agreements; fix CRITICAL/HIGH before handoff. Candidates need
  evidence-backed expectation, feasible execution, concrete violated
  relationship at every participant, observable consequence, and strongest
  refutation checked. Zero findings is "no supported findings in the examined
  scope", never "bug-free".
- **Independent review** — non-author verdict, required for shared branches,
  merges, STOP triggers, and releases (Never skip). Dispatch ladder: installed
  `reviewer` (plus `review-finder` per flow on multi-flow changes) → fresh
  runtime/generic read-only subagent carrying `review.md`'s method + brief where
  no agent directory or in project scope → `RULES.md` recorded fallback →
  fresh builder-family subagent → inline five-element audit if zero subagent
  tools exist (`Review: unavailable (...)`). Name the actual reviewer. Never
  resume/fork builder context; read-only tools, no suspected defects in brief.
  Compute subject deterministically from git (never an unset `$RELEASED..HEAD`
  yielding empty diff). Re-run after every fix. Stop at no INTRODUCED finding
  above Low and no High/Critical of any age. The author/coordinator triages
  findings and records verdict, scope, round count, outcomes, and open risk in
  the final report, PR body, or commit message.

Pre-review: checks pass, no conflicts, branch current. Short clean rounds or
unreadable subjects fail the round.

| Level | Meaning | Action |
|---|---|---|
| CRITICAL | Security or data loss risk | BLOCK — fix first |
| HIGH | Bug or significant quality issue | WARN — fix first |
| MEDIUM | Maintainability / >800-line file | INFO — fix or record reason |
| LOW | Style or minor suggestion | NOTE — optional |

Approve only with no CRITICAL/HIGH (security review also blocks HIGH).

## Environment & Source Repositories

### Installed plugins / skills

| Plugin / skill | Source | Purpose |
|---|---|---|
| `agents-contract` | installed beside this contract | Executable contract bootstrap; load at session start |
| `semble` | `https://github.com/MinishLab/semble` | MCP/CLI code search — top discovery rung |
| `superpowers` | `https://github.com/obra/superpowers` | Workflow skills (TDD, debugging, planning, verification) |

### Knowledge capture

- Personal/temporary notes → memory; architecture/runbooks → existing `docs/`.
- Cross-file invariants → project-owned `RULES.md` (one line per invariant +
  owner, no history). Never write project rules into an installed contract copy.
- Place new docs in existing folders (`docs/`, `docs/adr/`); avoid unrequested
  top-level files.

### Source Repositories

`rtk-ai/rtk`, `MinishLab/semble`, `JuliusBrussee/caveman`,
`DietrichGebert/ponytail`, `Larens94/codedna`, `obra/superpowers`,
`jbarbier/CLAUDE.md`, `multica-ai/andrej-karpathy-skills`, `affaan-m/ECC`.
