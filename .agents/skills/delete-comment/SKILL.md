---
name: delete-comment
description: Repeatable comment audit for any project — inventory every comment, grade it Tautology / Excuse / Stale / Decision Record, delete or relocate it, then lower the annotation budget. Use when asked to audit comments, delete comments, clean up comment debris, or shrink the comment budget.
---

# Delete Comment

Run this pass over a path. It is idempotent: running it on a clean tree changes
nothing and reports `0`.

Resolve the checker path from the harness skill directory the agent was given —
do not guess a repo-relative path and never search the filesystem for it. Call it
`CHECKER` below, e.g.
`~/.claude/skills/agents-contract/scripts/comment_budget.py` for Claude Code or
`.agents/skills/agents-contract/` for the central fallback. For an installed
skill, the docs templates live at `SKILL_DIR/../docs` (the lowheat checkout's
`docs/` directory), because user scope links the skill into each harness.

Read `contract/codedna.md` → **Comment audit** when that file exists. Outside
lowheat it will not; the four categories below are the complete rule, so continue
without it.

## 0. Establish the baseline

```bash
python3 "$CHECKER" <paths> --baseline docs/comment-budget.json
```

**First run in a project without `docs/`, or with no readable baseline:** bootstrap
explicitly, then continue. This is the only command allowed to create a baseline.

```bash
python3 "$CHECKER" <paths> --bootstrap \
  --template-dir <lowheat-checkout>/docs \
  --baseline docs/comment-budget.json
```

It creates `docs/comment-budget.json` seeded with the *current* counts,
`docs/adr/0000-template.md`, `docs/adr/README.md`, and `docs/comment-debt.md`.
It never overwrites an existing file, and it refuses to touch an unreadable
baseline — a corrupt file may hold a real ceiling. Re-running it reports
`bootstrap already complete`. If `<lowheat-checkout>/docs` is not available,
create those four files by hand with the same names and seed the JSON with
`{"version": 1, "comments": <count>, "open_notes": <count>}`.

On every later run the baseline must already exist and both numbers must pass.
If `comments` or `open_notes` exceeds it, stop: the tree is over budget and a
later subtraction would hide that.

## 1. Inventory

```bash
python3 .agents/skills/agents-contract/scripts/comment_budget.py <paths>   # no --quiet
```

`codedna_check.py` is the ban and already reports non-CodeDNA content; it is not
the inventory. The inventory is the **permitted** annotation surface, which no
detector flags because it is legal by construction. Enumerate it with the reader
for the dialect:

- Python: `ast.get_docstring` per module, class, and function, plus the
  `codedna_masking._python_scan_inputs` comment bodies.
- Other dialects: `codedna_masking._comment_bodies(profile, text, spans)`.

Skip directive bodies, shebangs, and bare separators — they carry no prose and cost
nothing to keep. The counter applies that exemption in every dialect, so a
`# type: ignore`, a `# shellcheck` pragma, and a first-line `#!` never move the
number. A bare `#` separator line does count, because it is a line someone chose to
keep.

## 2. Grade each comment

Exactly one label per comment. When two fit, choose the earlier one.

| Label | Test | Action |
|---|---|---|
| **Tautology** | Delete it, read the code — did any information vanish? | Delete |
| **Excuse** | Does it exist to justify a shortcut the code should not have taken? | Delete, then add a row to `docs/comment-debt.md` |
| **Stale** | Does it name code, a file, an API, or a behavior that no longer exists? | Delete |
| **Decision Record** | Does it carry *why* — an ordering, compatibility, or rejected-alternative constraint? | Delete, then write `docs/adr/NNNN-slug.md` |

A CodeDNA annotation is not automatically safe: sales-pitch `exports:` lines, a
`rules:` that restates the signature, an `agent:` note that describes a fix the
diff already shows, and a `message:` whose issue closed are all Tautology or Stale
and go like any other comment. The four **required** L1 fields stay — removing one
fails `codedna_check.py`.

## 3. Act

- **Tautology / Stale:** delete the line. In a docstring, delete the line and keep
  the surrounding block well-formed (first line stays the summary).
- **Excuse:** delete it, then append one row to `docs/comment-debt.md` —
  `id | file:line | hack the comment excused | fix | owner`. The row carries the fix
  the comment was avoiding. Do not file a tracker issue from the skill; the ledger
  is the tracker, and it needs no network or auth.
- **Decision Record:** delete it, then write the ADR from `docs/adr/0000-template.md`
  with the next free number, and add the row to `docs/adr/README.md`. Never copy the
  comment verbatim — write the Context, Decision, and Consequences.

Delete the comment in the **same** change that adds the ADR or the debt row. A
comment that is gone with the reasoning unrecorded is the one failure mode of this
skill.

## 4. Lower the budget

```bash
python3 "$CHECKER" <paths> --baseline docs/comment-budget.json --update
```

`--update` writes the new, lower numbers. It refuses to raise either number; if it
refuses, an edit added comments or docstring lines rather than removing them — revert
that edit instead of reaching for `--force`. It also refuses a baseline it cannot
read, so a damaged file cannot become a free reset. `--force` is for a deliberate,
reviewed exception and belongs in the PR description. CI additionally compares the
baseline against the base commit (`--against`), so editing the JSON upward fails
even without `--update`.

## 5. Verify

```bash
BAN_CHECKER="$(dirname "$CHECKER")/codedna_check.py"
python3 "$BAN_CHECKER" <paths>                                              # exit 0
python3 "$CHECKER" <paths> --baseline docs/comment-budget.json             # exit 0
```

Run the project's own test command with its own coverage floor, if it has one;
the `pytest tests -q --cov` line in lowheat's CI is not portable to project A.

`codedna_check.py` reports missing L1 headers too. A project that never adopted
CodeDNA will fail that check on every source file; this audit does not fix that.
Report the count as a pre-existing condition and leave the headers alone unless
the user asked to adopt CodeDNA. The budget check passing is the gate for this
skill's own change.

Report three numbers — comments deleted, ADRs written, debt rows filed — and the
baseline before and after. A first run that only bootstraps and deletes nothing is
the expected result, not a failed audit.

## Grading examples

| Comment | Label | Why |
|---|---|---|
| `# increment the counter` above `counter += 1` | Tautology | The code says it. |
| `# retry twice; the upstream 502s on cold start` | Decision Record | Non-obvious *why*, survives from the code. |
| `# skip validation for internal calls` | Excuse | It excuses a missing trust-boundary check. |
| `# see UserService.validate (removed in v2)` | Stale | The named symbol is gone. |
| `rules: check the amount` on `def charge(amount_cents)` | Tautology | Restates the signature, no constraint. |
| `message: waiting on #412 to land` with #412 closed | Stale | The open item resolved. |
