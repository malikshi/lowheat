# The Loop

Companion to `AGENTS.md` → The Work Loop. This file is the unit-level method
for multi-unit, risky, or long-running work. `AGENTS.md` stays authoritative,
including Precedence, approval gates, and the Commit rule.

Adapted from the Karpathy-style loop gist: make one change, measure it against a
fixed check, keep it if it passes, revert it if it does not. This version keeps
the graph, bounded retries, failure return, and a current project `RULES.md`
rulebook for cross-file invariants. Git is the audit log; attempts are reported,
not kept as a second ledger.

## Contract with the user

- **The check decides, not confidence.** "Looks good", "I'm confident", and a
  green-looking diff never count as passing.
- **Everything before the final report is self-verified.** The user is asked to
  approve only what `AGENTS.md` says needs approval — irreversible actions,
  destructive operations, production mutations, a commit, or a push. Do not
  defer a required approval to the end, and do not treat "approve only the final
  step" as permission to do irreversible work earlier. Nothing here waives the
  Confusion protocol or independent review.
- **Preserve user work.** Revert only the current unit's own edits. Never reset,
  checkout over, or delete unrelated changes. Use an isolated worktree or branch
  for an experiment that may need to be discarded.

## Step 0 — Write the check first

Before changing code, write the pass condition as something a program can
evaluate:

- a command and its expected exit code;
- a schema or fixture comparison;
- a diff boundary that names the allowed paths;
- a lint, format, type, or contract check;
- for judgment work, an eval or a documented rubric with a pass threshold.

For behavior work this is the failing test (RED). For a docs or config change it
is a syntax, link, marker, or diff check. If no check can be written, stop and
report `NEEDS_CONTEXT` or name the manual evidence that will settle it.

Record the check in the plan. A check that cannot fail is not a check.

## Step 1 — Split into units

Cut the task into the smallest independent units. Every unit carries one card:

```text
UNIT:    what this unit delivers
INPUT:   files, data, or decisions it reads
OUTPUT:  the artifact or observable result it produces
CHECK:   the fixed command or rubric that proves the output
FAILURE: the named state that means this unit did not pass
WRITES:  the paths this unit may change
```

- One job per unit. If a unit needs two checks, it is usually two units.
- Draw an edge only when one unit reads another unit's output.
- Run units in parallel only when their write sets are disjoint and their checks
  are independent. "No shared variable" is not enough: shared files, generated
  artifacts, caches, and external state are edges too.
- A small task is one unit. Do not manufacture a graph for ceremony.
- Reuse existing code before adding a unit.
- Use an isolated context or worktree only for a unit that is independent and
  has a disjoint write set; never isolate a unit that shares files or state.

## Step 2 — Run one unit

For each unit: make one change, run its fixed check, keep it if it passes, revert
it if it does not.

- Keep the change inside the unit's write set. If it reaches another unit, stop
  and fix the split.
- Revert only this unit's change; preserve user work and other units.
- **Three attempts maximum per behavior unit.** Count one attempt each time a
  newly changed hypothesis fails the same check. After the third failure, stop:
  report `UNIT`, `VERDICT`, `REASON`, `EVIDENCE`, and the proposed new plan. Do
  not retry the same hypothesis.
- Mechanical docs or formatting units normally need one pass. They also cap at
  three attempts; after three, report the plan wrong.
- Record rejected attempts in the final report and in the `AI-Rejected:` commit
  trailer. Do not create a separate attempt ledger.

## Step 3 — Merge with code

Merge and compare with scripts, not with model judgment. Spend reasoning only on
steps that judge or decide.

- Re-run the integration check after the merge, not just each unit's check.
- Never redo a unit that already passed.
- Send a failed unit back with this exact shape:

```text
UNIT:    ...
VERDICT: FAIL
REASON:  the check that failed and why
EVIDENCE: command, exit code, output, or line reference
SCOPE:   this unit's files only
NEXT:    one concrete changed hypothesis, or a plan change
```

- Keep passed units untouched. If the merge exposes a new dependency, add an
  edge and a unit; do not silently widen an old one.

## Step 4 — Review the merged result

Run the self-review in `AGENTS.md` → Definition of Done. A shared branch, a
merge, or a STOP trigger also gets the independent review. Review against the
unit cards and the check, not against the model's confidence.

## Step 5 — Gate by cost to undo

Sort every remaining change by what it costs to undo:

| Cost | Examples | Action |
|---|---|---|
| Cheap and contained | local test, docs, a single reversible edit | Keep after the check passes |
| Reversible but wide | shared files, generated artifacts, schema-compatible changes | Require hard evidence and a written rollback path |
| Irreversible | migrations, deletes, production data, money, force pushes | Stop and wait for explicit user approval |

"Ship" here means keep in the working tree after the check passes, not commit or
push. Commit and push need the approval `AGENTS.md` already requires. Confidence
never overrides an irreversible gate.

## Step 6 — Learn one rule

When a fix passes, write its cause in the right home:

- CodeDNA `rules:` for a constraint that governs one file;
- a project-owned `RULES.md` for a cross-file invariant: one that affects two
  or more files or a workflow/security boundary. It narrows the contract and
  never relaxes an approval gate;
- an `agent:` entry for session history;
- a test or script when the rule can be enforced mechanically.

The contract and companions are read-only in an installed project; write there
only when contributing to lowheat itself. `RULES.md` is a current rulebook, not
a ledger: one line per invariant with an owning path or test, no dates or
attempts. Keep the rule in one home; a file may state its local consequence but
must not repeat the global text. For example, `RULES.md` says "writes go through
`repository/`"; a model file's `rules:` says "never import the DB driver." That
is a local consequence, not a copy. Remove a line in the same commit that makes
it false. Git remains the audit log; rejected attempts go in the final report and
the `AI-Rejected:` trailer.

## Step 7 — Stop and report

Stop when the check passes, after two consecutive rounds with no new evidence,
or when the agreed time, token, or tool-call budget runs out. A round is one full
pass over the remaining units; "no new evidence" means the same checks fail for
the same reason and no new hypothesis was tested. Then report once:

```text
Changed:    files and behavior
Checked:    command, exit code, and result
Rejected:   failed attempts and why they were reverted
Approval:   irreversible or shared actions still waiting
Unverified: what remains, and what would settle it
```

Do not claim `DONE` while the check is unrun, failing, or unverified. Carry the
compliance record from `AGENTS.md` in the same report.

## Mapping to the Work Loop steps

| Work Loop step | This companion |
|---|---|
| 1 Understand | Step 0: machine-evaluable pass condition |
| 2 Read first | Step 1: INPUT and WRITES cards require reading the touched files first |
| 3 Plan | Step 1: unit cards, edges, parallel boundaries |
| 4 Implement with TDD | Step 2: change → check → keep/revert, three attempts |
| 5 Self-review | Steps 3–4: deterministic merge, failure return, review |
| 6 Prove it | Step 5: check plus undo-cost gate |
| 7 Report and record | Steps 6–7: learned rule, stop conditions, final report |

## Anti-patterns

- Retrying the same failed hypothesis a fourth time.
- Running units in parallel because they share no variable, while they write the
  same file.
- Merging with "looks right" instead of a script.
- Redoing a passed unit because the merge failed elsewhere.
- Sending a failure without a check, evidence, or bounded scope.
- Writing a second history or attempt ledger beside CodeDNA and git; a current
  project rulebook is not a ledger.
- Treating "approve the final step" as permission for an irreversible step now.
- Calling a task done because the model is confident, not because the check
  passed.
