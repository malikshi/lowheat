---
name: delete-comment
description: Repeatable comment audit for any project — inventory every comment, grade it Tautology / Excuse / Stale / Decision Record, delete or relocate it, then lower the annotation budget. Use when asked to audit comments, delete comments, clean up comment debris, or shrink the comment budget.
---

# Delete Comment

Run this pass over a path. It is idempotent: a clean tree changes nothing and
reports `0`.

Resolve the checker path from the harness skill directory you were given — do
not guess a repo-relative path or search the filesystem. Call it `CHECKER`
below, e.g. `~/.claude/skills/agents-contract/scripts/comment_budget.py` for
Claude Code or `.agents/skills/agents-contract/` for the central fallback. The
bootstrap templates live in the checkout's `docs/`. A user-scope install links
the skill into the harness, so resolve the link first and climb three levels
from the `agents-contract` directory:

```bash
SKILL_DIR=$(dirname "$(dirname "$(realpath "$CHECKER")")")
TEMPLATE_DIR="$SKILL_DIR/../../../docs"   # lowheat checkout's docs/
```

A copied skill (fx) and a project-scope install carry no docs tree, so create
the four files by hand as described in step 0.

Read `codedna.md` → **Comment audit** when it sits beside the installed
`AGENTS.md`. Outside lowheat it does; the four categories below are the
complete rule either way, so continue if it is absent.

## 0. Establish the baseline

```bash
python3 "$CHECKER" <paths> --baseline docs/comment-budget.json
```

**First run without `docs/` or a readable baseline:** bootstrap explicitly,
then continue. This is the only command allowed to create a baseline.

```bash
python3 "$CHECKER" <paths> --bootstrap \
  --template-dir "$TEMPLATE_DIR" \
  --baseline docs/comment-budget.json
```

It creates `docs/comment-budget.json` seeded with current counts,
`docs/adr/0000-template.md`, `docs/adr/README.md`, and `docs/comment-debt.md`.
It never overwrites an existing file and refuses an unreadable baseline, which
may hold a real ceiling. A re-run reports `bootstrap already complete`. An
unreadable baseline is repaired by hand — restore the last committed JSON, or
write it with the numbers from the last green run; neither `--update --force`
nor `--bootstrap` will replace it, because a corrupt file may hide a real
ceiling. Without the checkout, create those four files by hand and seed the JSON
with `{"version": 1, "comments": <count>, "open_notes": <count>}`.

On later runs the baseline must exist and both numbers must pass. If `comments`
or `open_notes` exceeds it, stop: the tree is over budget, and a later
subtraction would hide that.

## 1. Inventory

```bash
python3 "$CHECKER" <paths>   # no --quiet
```

`codedna_check.py` is the ban and already reports non-CodeDNA content; it is not
the inventory. The inventory is the **permitted** annotation surface, which no
detector flags because it is legal by construction. Enumerate it with the
reader for the dialect:

- Python: `ast.get_docstring` per module, class, and function, plus
  `codedna_masking._python_scan_inputs` comment bodies.
- Other dialects: `codedna_content._comment_bodies(profile, text, spans)`.

Skip directive bodies, shebangs, and empty bodies — they cost nothing to keep,
and the counter exempts them in every dialect (`# type: ignore`, `# shellcheck`,
a first-line `#!`, a bare `#` separator). Every `agent:` line counts like any
other annotation. A file at the five-entry cap stays flat by dropping its oldest
entry as it appends the newest; a file below the cap pays one unit, so delete a
Tautology or Stale annotation in the same change to hold the budget.

## 2. Grade each comment

Exactly one label per comment. When two fit, choose the earlier one.

| Label | Test | Action |
|---|---|---|
| **Tautology** | Delete it, read the code — did any information vanish? | Delete |
| **Excuse** | Does it justify a shortcut the code should not take? | Delete, then add a row to `docs/comment-debt.md` |
| **Stale** | Does it name code, a file, an API, or a behavior that no longer exists? | Delete |
| **Decision Record** | Does it carry *why* — an ordering, compatibility, or rejected-alternative constraint? | Delete, then write `docs/adr/NNNN-slug.md` |

A CodeDNA annotation is not automatically safe: sales-pitch `exports:`, a
`rules:` that restates the signature, an `agent:` note the diff already shows,
and a `message:` whose issue closed are Tautology or Stale and go like any
other comment. The four **required** L1 fields stay — removing one fails
`codedna_check.py`.

## 3. Act

- **Tautology / Stale:** delete the line; keep a docstring well-formed.
- **Excuse:** delete it, then append one row to `docs/comment-debt.md` —
  `id | file:line | hack the comment excused | fix | owner`. The ledger is the
  tracker; do not file an external issue.
- **Decision Record:** delete it, then write the ADR from
  `docs/adr/0000-template.md` with the next free number and add the row to
  `docs/adr/README.md`. Write Context, Decision, and Consequences; never copy
  the comment verbatim.

Delete the comment in the **same** change that adds the ADR or debt row. A
comment gone with its reasoning unrecorded is this skill's one failure mode.

## 4. Lower the budget

```bash
python3 "$CHECKER" <paths> --baseline docs/comment-budget.json --update
```

`--update` writes the lower numbers and refuses to raise either. If it refuses,
an edit added comments or docstring lines — revert that edit instead of reaching
for `--force`. It also refuses an unreadable baseline, so damage cannot become a
free reset. `--force` is for a deliberate, reviewed exception and belongs in the
PR description. CI compares the baseline against the base commit (`--against`),
so editing the JSON upward fails even without `--update`.

## 5. Verify

```bash
BAN_CHECKER="$(dirname "$CHECKER")/codedna_check.py"
python3 "$BAN_CHECKER" <paths>                                  # exit 0
python3 "$CHECKER" <paths> --baseline docs/comment-budget.json  # exit 0
```

Run the project's own test command and coverage floor if it has one; lowheat's
CI line is not portable.

`codedna_check.py` also reports missing L1 headers. A project that never adopted
CodeDNA fails that on every source file; this audit does not fix it. Report the
count as pre-existing and leave headers alone unless the user asked to adopt
CodeDNA. The budget check passing is the gate for this skill's own change.

Report three numbers — comments deleted, ADRs written, debt rows filed — and the
baseline before and after. A first run that only bootstraps and deletes nothing
is the expected result, not a failed audit.

## Grading examples

| Comment | Label | Why |
|---|---|---|
| `# increment the counter` above `counter += 1` | Tautology | The code says it. |
| `# retry twice; the upstream 502s on cold start` | Decision Record | Non-obvious *why* that survives from the code. |
| `# skip validation for internal calls` | Excuse | It excuses a missing trust-boundary check. |
| `# see UserService.validate (removed in v2)` | Stale | The named symbol is gone. |
| `rules: check the amount` on `def charge(amount_cents)` | Tautology | Restates the signature, no constraint. |
