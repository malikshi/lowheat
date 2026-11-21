---
name: delete-comment
description: Repeatable comment audit for this repository — inventory every comment, grade it Tautology / Excuse / Stale / Decision Record, delete or relocate it, then lower the annotation budget. Use when asked to audit comments, delete comments, clean up comment debris, or shrink the comment budget.
---

# Delete Comment

Run this pass over a path. It is idempotent: running it on a clean tree changes
nothing and reports `0`.

Read `contract/codedna.md` → **Comment audit** first. This skill is the executable
form of that section.

## 0. Establish the baseline

```bash
python3 .agents/skills/agents-contract/scripts/comment_budget.py <paths> \
  --baseline docs/comment-budget.json
```

Both numbers must already pass. If `comments` or `open_notes` exceeds the baseline,
stop: the tree is failing CI for a reason unrelated to this audit and a later
subtraction would hide it.

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
python3 .agents/skills/agents-contract/scripts/comment_budget.py <paths> \
  --baseline docs/comment-budget.json --update
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
python3 .agents/skills/agents-contract/scripts/codedna_check.py <paths>    # exit 0
python3 .agents/skills/agents-contract/scripts/comment_budget.py <paths> \
  --baseline docs/comment-budget.json                                      # exit 0
python3 -m pytest tests -q --cov                                           # exit 0, 80% floor
```

Report three numbers — comments deleted, ADRs written, debt rows filed — and the
baseline before and after. A pass that reports zero deletions on a tree this clean
is the expected result, not a failed audit.

## Grading examples

| Comment | Label | Why |
|---|---|---|
| `# increment the counter` above `counter += 1` | Tautology | The code says it. |
| `# retry twice; the upstream 502s on cold start` | Decision Record | Non-obvious *why*, survives from the code. |
| `# skip validation for internal calls` | Excuse | It excuses a missing trust-boundary check. |
| `# see UserService.validate (removed in v2)` | Stale | The named symbol is gone. |
| `rules: check the amount` on `def charge(amount_cents)` | Tautology | Restates the signature, no constraint. |
| `message: waiting on #412 to land` with #412 closed | Stale | The open item resolved. |
