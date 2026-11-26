# Architecture Decision Records

One decision per file, named `NNNN-slug.md`, numbered in order of acceptance. A
Decision Record comment found during a comment audit moves here in the same pull
request that deletes it: the record is the durable form, the comment was the
scattered copy.

A comment is a **Decision Record** when it explains *why* a non-obvious choice was
made — an ordering constraint, a compatibility constraint, a rejected alternative —
and that reasoning would be lost from the code itself.

- `0000-template.md` — copy this to start a new record.
- `0001-comments-are-codedna-only.md` — comment content, the four audit categories,
  and the shrinking budget (superseded by `0002`).
- `0002-comment-audit-is-prose-in-codedna.md` — comment audit lives as prose in
  `codedna.md` without a separate skill or budget script.

Keep the `Status:` line current (`accepted`, `superseded by NNNN`, `deprecated`).
Never rewrite an accepted record's Context or Decision; a reversal is a new record
that supersedes it.
