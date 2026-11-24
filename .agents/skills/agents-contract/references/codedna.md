# CodeDNA

Normative summary: `AGENTS.md` → Engineering Standards → CodeDNA. This file is the full convention.

CodeDNA is a source-annotation convention adapted from
`https://github.com/Larens94/codedna`. This repository uses the convention only.
It uses no upstream `codedna` binary, validator, or git hook, and no `.codedna`
ledger file; the agents-contract skill ships its own read-only checker. Git is
the authoritative audit log. Agents apply and maintain these annotations by hand
while reading and editing code.

**CodeDNA is the only comment content.** No comment content outside CodeDNA may
exist in source files — no explanatory prose, no commented-out code, no
`TODO`/`FIXME` markers, no section dividers. The complete permitted set is a
single-line summary of what the file or function does, the L1 fields, L2
`Rules:` blocks, and inline `Rules:`/`message:`; in Python the summary line and
the `Rules:` block live in the docstring. Constraints go in `rules:`/`Rules:`;
open items go in `message:`. Delete every non-CodeDNA comment in the functions
or blocks you edit — this is the one exception to the Surgical-changes rule and
the trace-back requirement.
Tool directives and license headers (`//go:build`, linter pragmas, type-ignore
comments, SPDX lines) are exempt — they are code, not comments. User-visible
documentation strings are exempt on the same footing: CLI help text, API and
OpenAPI descriptions, and public-library docstrings are product surface. Keep
them short and factual; constraints still belong in `rules:`/`Rules:`.

## Scope

Apply CodeDNA annotations to every source file in the project whose language
supports comments. The checker covers Python, Go, JavaScript/JSX/mjs/cjs,
TypeScript/TSX, Rust, shell (sh/bash/zsh), CSS, HTML/htm, C, C++, Objective-C,
Objective-C++, C#, Java, Kotlin, Scala, Groovy, Swift, Ruby, PHP, Perl, Lua,
Haskell, Elixir, Erlang, Clojure, Dart, SQL, PowerShell, batch, VB, F#, OCaml,
R, Julia, Zig, Nim, Crystal, D, Solidity, HCL/Terraform, Fortran, Elm,
Vue/Svelte/Astro, and the template families Blade, Jinja2/Twig/Volt, ERB/EJS,
Handlebars/Mustache, and Razor, with a safe generic fallback for any other
commented source language. A compound suffix wins over its last component, so
`page.blade.php` is scanned as Blade, not PHP. Do not annotate documentation,
plain text, or commentless data formats: `.md`, `.tex`, `.rst`, `.txt`,
`.json`, and similar.

## Module header (L1)

Every source file begins with a module header written in the file's native
comment syntax, after any mandatory declaration the language requires above it
(`package`, `namespace`, `using`, `<?php`) and after a license banner. Python
uses the module docstring; Go, JavaScript, TypeScript,
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
that do not exist, `exports:` names absent from the file body — judged against
the Python AST when the file parses — agent-entry shape and the 5-entry cap)
AND comment content (prose, commented-out code, TODO
markers outside `Rules:`/`message:`), across the language set above (C, C++,
Objective-C, C#, Java, Kotlin, Scala, Groovy, Swift, Ruby, PHP, Perl, Lua,
Haskell, Elixir, Erlang, Clojure, Dart, SQL, PowerShell, batch, VB, F#, OCaml,
R, Julia, Zig, Nim, Crystal, D, Solidity, HCL/Terraform, Fortran, Elm,
Vue/Svelte/Astro, the template families above, and the earlier suffix set), with
line numbers on every
finding.
`--skip-content` limits it to the header checks. It is line-based and errs toward
reporting; a false positive is a signal that the comment belongs under
`Rules:`/`message:`. A Python `used_by:` consumer is also proven against the
import graph: a consumer that never imports the module is reported, and so is an
importer the header omits — a consumer that loads the module by path with
`importlib` is exempt from the proof. When the scanned paths hold an `AGENTS.md`,
it also lints
that document's Python examples against these rules.

**Session end protocol.** At the end of every session that modifies files,
record the work in the git commit with the session trailers defined under Git
Workflow; do not keep a separate ledger file. A project `RULES.md` of current
cross-file invariants is a rulebook, not a session ledger.

## Comment audit

The ban above is already enforced: `codedna_check.py` reports prose, commented-out
code, and mid-stream `TODO` markers. Do not build a second detector — it would
disagree with the first. What the ban cannot measure is the **permitted** annotation
surface, which is legal by construction and grows without limit unless something
counts it. That is what a comment audit is for.

Grade every comment, then take exactly one action:

| Category | Test | Action |
|---|---|---|
| **Tautology** | Delete it and read the code — did any information vanish? | Delete |
| **Excuse** | Does it exist only to justify a shortcut the code should not have taken? | Delete, then add a row to `docs/comment-debt.md` |
| **Stale** | Does it name code, a file, an API, or a behavior that no longer exists? | Delete |
| **Decision Record** | Does it carry *why* — an ordering, compatibility, or rejected-alternative constraint? | Delete, then write `docs/adr/NNNN-slug.md` |

A CodeDNA annotation is not automatically safe. An `exports:` line written as a
sales pitch, a `rules:` that restates the signature, an `agent:` note describing a
change the diff already shows, and a `message:` whose issue has since closed are all
Tautology or Stale. The four required L1 fields stay: removing one fails the
checker.

Two homes hold what deletion must not destroy. Reasoning goes to `docs/adr/`, one
decision per file, moved in the same change that deletes the comment — never copied
verbatim, always rewritten as Context / Decision / Consequences. An excused hack goes
to `docs/comment-debt.md`, one row with the fix it was avoiding; the ledger is the
tracker, so no issue tracker or network access is involved, and the file is deleted
once the table is empty.

**Ratchet.** Not every comment dies in one change, so the total may only fall.
`comment_budget.py` counts two numbers over the same tree the ban covers:

```bash
python3 <skill-dir>/scripts/comment_budget.py . \
  --baseline docs/comment-budget.json            # exit 1 if either number grew
python3 <skill-dir>/scripts/comment_budget.py . --update
```

`<skill-dir>` is where the harness reports the `agents-contract` skill, as above.

`comments` counts permitted annotation lines; `open_notes` counts `message:` lines,
the genuinely unresolved items. In a project with no baseline yet,
`--bootstrap --template-dir <lowheat-checkout>/docs` creates one seeded with the
current counts plus the ADR and debt templates. It never overwrites an existing
file; `--update` still never creates one, so creating a baseline stays a separate,
visible action and the ratchet is unchanged. `--update` refuses to raise either
number without `--force`, and it refuses a baseline it cannot read rather than
creating one — an unreadable file must never become a free reset. CI
also compares the checked-in baseline against the base commit with `--against`,
so editing the JSON upward fails the run even without `--update`. `--force` is a
deliberate, reviewed exception and belongs in the pull request body. The
`delete-comment` skill runs the whole pass end to end. Every skill that ships
beside this contract is installed into each harness, so it is available wherever
the contract is.
