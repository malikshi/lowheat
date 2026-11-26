# 0002 — Comment audit is prose in codedna.md without a separate skill or budget script

- Status: accepted
- Date: 2026-11-26

## Context

`0001` added a second skill (`delete-comment`), a comment-budget ratchet script
(`comment_budget.py`), a checked-in baseline (`docs/comment-budget.json`), and
bootstrap machinery on top of `codedna_check.py`. Maintaining the script, JSON
baseline, and extra skill directory added churn without expanding automated
enforcement beyond what `codedna_check.py` already checks.

## Decision

We remove the `delete-comment` skill, `comment_budget.py`,
`docs/comment-budget.json`, and their tests, and keep the comment-audit essence
as pure prose in `contract/codedna.md` (with summaries in `contract/AGENTS.md`
and `agents-contract/SKILL.md`): every comment — including CodeDNA annotations —
is graded `Tautology`, `Excuse`, `Stale`, or `Decision Record` (earlier label
wins), with `Excuse` rows moving to `docs/comment-debt.md` and `Decision Record`
reasoning moving to `docs/adr/NNNN-slug.md` in the same change that deletes the
comment.

## Consequences

- `codedna_check.py` remains the sole automated comment and header check.
- Comment auditing requires no extra skill, script, JSON baseline, or bootstrap
  step.
- `contract/AGENTS.md`, `contract/codedna.md`, and every companion remain under
  the 24,000-byte per-file rule cap.
