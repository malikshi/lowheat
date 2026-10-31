# CodeDNA

Normative summary: `AGENTS.md` → Engineering Standards → CodeDNA. This file is the full convention.

CodeDNA is a source-annotation convention adapted from
`https://github.com/Larens94/codedna`. This repository uses the convention only.
It does not use the `codedna` binary, a validator, git hooks, or a `.codedna`
ledger file. Git is the authoritative audit log. Agents apply and maintain
these annotations by hand while reading and editing code.

**CodeDNA is the only comment content.** No comment content outside CodeDNA may
exist in source files — no explanatory prose, no commented-out code, no
`TODO`/`FIXME` markers, no section dividers. The complete permitted set is a
single-line summary of what the file or function does, the L1 fields, L2
`Rules:` blocks, and inline `Rules:`/`message:`; in Python the summary line and
the `Rules:` block live in the docstring. Constraints go in `rules:`/`Rules:`;
open items go in `message:`. Delete every non-CodeDNA comment in the code you
touch — this is the one exception to the Surgical-changes rule and the
trace-back requirement.
Tool directives and license headers (`//go:build`, linter pragmas, type-ignore
comments, SPDX lines) are exempt — they are code, not comments. User-visible
documentation strings are exempt on the same footing: CLI help text, API and
OpenAPI descriptions, and public-library docstrings are product surface. Keep
them short and factual; constraints still belong in `rules:`/`Rules:`.

## Scope

Apply CodeDNA annotations to every source file in the project whose language
supports comments: Python, Go, JavaScript, TypeScript, Rust, shell, and any
other commented source language. Do not annotate documentation, plain text, or
commentless data formats: `.md`, `.tex`, `.rst`, `.txt`, `.json`, and similar.

## Module header (L1)

Every source file begins with a module header written in the file's native
comment syntax. Python uses the module docstring; Go, JavaScript, TypeScript,
and Rust use leading `//` lines; shell uses leading `#` lines. Fields appear in
this order:

- First line: `filename — <what it does, 15 words or fewer>`.
- `exports:` public symbols this file provides, separated by ` | `. Use `->`
  for a return type.
- `used_by:` consumer files that depend on this file, one per line as
  `consumer_file → symbol(s)`. Tag a consumer `[cascade]` when an edit here must
  be verified against it.
- `related:` (optional) files that share the same pattern or logic without an
  import link.
- `rules:` the hard constraint agents must never violate, or `none`.
- `agent:` a rolling history of the last 5 sessions, oldest first, newest
  appended last: `model-id | provider | YYYY-MM-DD | session_id | what you did
  and what you noticed`.
- `message:` (optional) an open hypothesis or observation for the next agent,
  indented beneath `agent:`.

Python module docstring:

```python
"""src/config.py — Bot configuration with lazy environment loading.

exports: class Config | get_config()
used_by: manager/src/admin/menu.py → DB_FILE, logger [cascade]
rules:   Never read os.environ at import time; load lazily in get_config().
agent:   claude-fable-5 | anthropic | 2026-07-24 | s_example | tightened lazy load
"""
```

Go, TypeScript, JavaScript, or Rust leading comments:

```go
// auth.go — API-key middleware for the ZiVPN HTTP surface.
//
// exports: Middleware
// used_by: ZiVPN/cmd/zivpn-api/main.go → Middleware
// rules:   none
// agent:   claude-fable-5 | anthropic | 2026-07-24 | s_example | reviewed guard
```

## Function annotation (L2)

Every public function carries a `Rules:` block in its docstring or leading
comment stating what the agent must or must not do there. Omit it only for
trivial functions with no domain constraint. The first line may be a one-line
summary of what the function does, 15 words or fewer like the module header;
every line after it is a `Rules:` or `message:` line.

```python
def charge(amount_cents: int) -> None:
    """Charge the customer for a completed order.

    Rules:   amount_cents is in cents, not euros; divide by 100 before display.
    """
```

## Inline annotations on complex logic

Place a `# Rules:` or `# message:` comment (native comment syntax) directly
above a block when the block encodes a business rule, filters or transforms in a
non-obvious way, depends on step order, or works around an edge case. Skip
simple getters and setters, obvious control flow, and standard library calls.

```python
# Rules: skip cancelled orders — status=4 means cancelled in the legacy DB.
```

## Agent protocols

**Reading files.** Read the module header before any code. Parse `exports:`,
the symbols you must never rename or remove without explicit instruction. Parse
`used_by:` and `related:`, then follow only the callers whose domain intersects
your current task, not all of them blindly. Parse `rules:`, the hard constraints
for every edit in this file. Parse `agent:`, the session history that explains
why the current state exists. Read the `Rules:` block of any function before
writing logic in it.

**Writing new files.** Begin every new source file with a complete L1 module
header; public functions carry the L2 block described above.

**Writing good rules.** Rules must be specific and actionable. Write
`soft-delete via deleted_at — never issue DELETE` rather than a vague line such
as `handle deletes carefully`. Never write vague rules such as `handle errors
gracefully` or `follow best practices`. Use `rules: none` only when a file
genuinely has no domain constraint. Every time you discover a constraint, fix a
bug, or notice a non-obvious behavior, add it to `rules:` immediately. This is
how you communicate with the next agent.

**Writing critical functions.** For a function that guards auth, data, money, or
an external boundary, the `Rules:` block carries each constraint, invariant, and
edge case rather than the headline rule alone.

**Editing files.** Re-read `rules:`, the `agent:` history, and the `Rules:` of
the function you are editing. Apply all file-level constraints before writing.
After editing, check `used_by:` targets, especially `[cascade]`-tagged ones.
Keep `exports:` accurate: a symbol leaves the list in the same commit that
removes it, once no caller remains. If you discover a constraint or fix a bug,
update `rules:` for the next agent. Append a
new `agent:` line to the module header in the form `model-id | provider |
YYYY-MM-DD | session_id | what you did and what you noticed`. Keep only the last
5 entries; drop the oldest when adding a 6th. Full history is in git. Run the
checker the agents-contract skill ships after any annotation edit:
`scripts/codedna_check.py` beside that skill's `SKILL.md`. Resolve the path from
the skill directory the harness reports and never search the filesystem for it —
a `find /` sweep for this script is slow enough to be killed. In user scope the
skill is linked into each harness config directory, so the path is under that
harness's `skills/agents-contract/scripts/codedna_check.py` (for example
`~/.claude`, `~/.codex`, `~/.commandcode`, `~/.grok`, or `~/.agents`); in the
lowheat checkout it is `.agents/skills/agents-contract/scripts/codedna_check.py`.
Skip the run when an install ships no script. With no flags it
checks L1 headers (missing
files/fields, `filename — description` form, field order, `used_by:` targets
that do not exist, `exports:` names absent from the file body, agent-entry
shape and the 5-entry cap) AND comment content (prose, commented-out code, TODO
markers outside `Rules:`/`message:`), across Python, Go, JavaScript/JSX/mjs/cjs,
TypeScript/TSX, Rust, shell, CSS, and HTML, with line numbers on every finding.
`--skip-content` limits it to the header checks. It is line-based and errs toward
reporting; a false positive is a signal that the comment belongs under
`Rules:`/`message:`. When the scanned paths hold an `AGENTS.md`, it also lints
that document's Python examples against these rules.

**Session end protocol.** At the end of every session that modifies files,
record the work in the git commit with the session trailers defined under Git
Workflow; do not keep a separate ledger file.
