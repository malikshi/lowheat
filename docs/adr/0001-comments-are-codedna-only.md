# 0001 — Comment content is CodeDNA only, and the budget only shrinks

- Status: superseded by 0002
- Date: 2026-11-21

## Context

Agent-written source accumulates comment debris: lines that restate the code,
"temporary" notes that excuse a shortcut and then outlive it, and references that
drifted stale three refactors ago. The debris is not neutral — a stale comment is
worse than no comment, because the next agent trusts it over the code.

This repository had already made the boldest version of the decision: `codedna.md`
states that CodeDNA annotations are the only permitted comment content, and
`codedna_check.py` enforces it in CI, reporting prose, commented-out code, and
mid-stream `TODO` markers with line numbers.

An audit of the whole tree found what that enforcement implies: of 6,679 tracked
Python lines, there are **no** tautology, stale, or excuse comments left. Deleting
every comment would therefore delete obligations, not prose.

The remaining question was the opposite one: what keeps the annotation layer
itself from growing without limit?

## Decision

We keep the ban, and we add three things around it rather than a third detector.

1. **Four categories, four actions.** Every comment is judged Tautology (delete),
   Excuse (delete, and record the hack in `docs/comment-debt.md`), Stale (delete),
   or Decision Record (delete, and move the reasoning into `docs/adr/`).
2. **A budget that may only fall.** `comment_budget.py` counts two repo-wide
   numbers — `comments` and `open_notes` — against `docs/comment-budget.json`.
   `--update` writes a new baseline but refuses to raise either number without
   `--force`. A pull request may lower or hold the budget; raising it takes a
   deliberate, visible flag.
3. **Process, not prose.** The audit lives in the `delete-comment` skill so the
   pass can be repeated — and `install.py` ships every skill under
   `.agents/skills` to each harness, so it reaches any agent that has the
   contract. The four categories are stated once in `codedna.md` so the contract
   and the skill cannot drift.

A third detector was rejected: `codedna_check.py` already detects exactly the class
of comment this rule bans, and a second scanner would disagree with the first.

## Consequences

- The comment surface can only shrink. Lowering the baseline is the success state;
  hitting it exactly is not.
- A genuine need for a longer explanation has one pre-approved home — an ADR — and
  the comment that carried it is deleted rather than duplicated in both places.
- `--force` exists and is the single escape hatch. Raising the budget without it is
  a failing CI run, and CI also diffs the checked-in baseline against the base
  commit (`--against`), so editing the JSON upward is caught even though the
  baseline is a file in the repository.
- Enforced by `.github/workflows/ci.yml`: `codedna_check.py . contract` for the ban,
  `comment_budget.py . --baseline docs/comment-budget.json` for the ratchet, and
  `--against` against the base commit for baseline growth.
