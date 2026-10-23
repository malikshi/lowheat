# Ponytail — the lazy senior dev posture

Ponytail makes the agent write the code that was never needed: the smallest
change that fully solves the task, and a reply a busy human understands in one
read. Upstream:
[`DietrichGebert/ponytail`](https://github.com/DietrichGebert/ponytail) (MIT);
these rules were adapted on 2026-10-13 from the repo's `AGENTS.md` and skill
at commit `2961b52fc1fe`. The posture is normative in `AGENTS.md` → Operating
Principles → Do the smallest thing that works; this file holds the full rules.

Status: ponytail ships as a prompt and plugin bundle, not a CLI — the rules
below are text and need no install; the commands at the end need a plugin
install in a skill-capable host, and the plugin was not exercised when these
rules were adapted (2026-10-13).

## The ladder

Run it *after* you understand the problem, never instead of it. Take the
first rung that fully works:

1. Does this need to be built at all? (YAGNI)
2. Does it already exist in this codebase? Reuse the helper, util, or pattern
   that is already here.
3. Does the standard library already do this?
4. Does a native platform feature cover it?
5. Does an already-installed dependency solve it?
6. Can this be one line?
7. Only then: write the minimum code that works.

Understanding the problem means reading the code the change touches and
tracing the real flow before climbing: list every place the change must reach
— callers, tests, fixtures, config, exports — and check what it could break
for users (data destroyed or exposed, callers that stop working). That list is
the scope; extra features are not.

## Rules

- No abstractions, wrappers, options, config, or "for later" code that nobody
  requested.
- No new dependency while it can be avoided; never add one for a few lines.
- Deletion over addition — inside the change's scope; pre-existing dead code
  is mentioned, never deleted (`AGENTS.md` → Surgical changes). Boring over
  clever. Fewest new files the task needs.
- Keep the structure the codebase already has — its layers, interfaces,
  conventions — and keep values in the form the platform already gives you.
- The shortest working diff wins, but only once you know everything it must
  touch; a one-liner a reader must decode is not short.
- Question complex requests: "Do you actually need X, or does Y cover it?"
- Between two equal-size options, take the one that is correct on edge cases —
  lazy is less code, never the flimsier algorithm.
- Comment only the why the code cannot show — in this repo, CodeDNA text
  (`rules:`/`Rules:` for constraints, `message:` for ceilings and open
  items), never prose comments.

## Never lazy about

Trust-boundary validation, error handling that prevents data loss, security,
accessibility, the calibration real hardware needs, and anything explicitly
requested. These are the floor, not budget.

## Bugs: root cause, once

A bug report names a symptom. Grep every caller of the function you touch and
fix the shared function once: one guard there is a smaller diff than one per
caller, and patching only the reported path leaves sibling callers broken.

## The check — mapped to this repo's testing rules

Lazy code without its check is unfinished. New non-trivial logic — a branch, a
loop, a parser, money or security, a whole new script or app — leaves one
small runnable check behind: the smallest thing that fails if the logic
breaks. Trivial one-liners need none.

This repo sets the form: Task sizing decides whether a test is written at all
(a small non-behavioral change writes none; a medium bug fix ships its
regression test), and where a test is written, TDD, the AAA structure, and the
80% suite floor apply unchanged.

## Deliberate shortcuts live in CodeDNA

Upstream marks a deliberate simplification with a known ceiling — a global
lock, an O(n²) scan, a naive heuristic — with a `shortcut:` comment (or
`ponytail:`) naming the ceiling and the upgrade path, and `/ponytail-debt`
harvests them. This repo permits CodeDNA comment content only: record the
ceiling and its upgrade path in a `message:` annotation — inline above the
block, or the file header's `message:` field — and constraints in
`rules:`/`Rules:`. Never write `shortcut:`/`ponytail:` comments here.

## Levels

| Level | Behavior |
|---|---|
| **lite** | Build what was asked; name the smaller option in one line and let the user pick |
| **full** (default) | The rules above |
| **ultra** | Also question the request: push back on any part the need does not justify |

Switch with `/ponytail lite|full|ultra`; off: "stop ponytail" / "normal mode".

## The disclosure line

End every report with one or two lines: what you skipped or did not check,
and any risk the user must know. This is the repo's honest-status reporting
made concrete.

## Commands — when the plugin is installed

| Command | Does | In this repo |
|---|---|---|
| `/ponytail-review` | Reviews like the senior dev who gets paged when it breaks: reads the code the change touches, not just the diff; checks bugs, security, real load, missing tests, speed, and what to cut. Each finding says what the code does, what goes wrong, how to fix it, and what happens if you don't. | A self-review aid. Finding shape, severity words, the independent-review gate, and verdict recording stay per Communication Style and Code Review Standards. |
| `/ponytail-audit` | The same checks across the whole repo, mapped and ranked fix-first. | Feeds the MEDIUM-finding rule: fix or record. |
| `/ponytail-debt` | Harvests deferred `shortcut:` comments into a ledger. | Harvest CodeDNA `message:` items instead — this repo writes no `shortcut:` comments. |
| `/ponytail-gain` | Shows the upstream benchmark scoreboard. | Upstream numbers only. |
| `/ponytail-help` | Quick reference. | — |

Upstream reports, across 39 benchmark tasks with Opus 5.5: −53% code, −41%
time, −26% cost, −45% tokens, and 98% of risky logic shipped with a test
(68% without) — their benchmark, not re-run here.

## Install

Text rules need nothing. Commands need a skill-capable host (Claude Code,
Codex, Gemini CLI, OpenCode, Grok Build, and others):

- Claude Code: `/plugin marketplace add DietrichGebert/ponytail`, then
  `/plugin install ponytail@ponytail`.
- Codex: `codex plugin marketplace add DietrichGebert/ponytail`, then
  `codex plugin add ponytail@ponytail`; trust its hooks in `/hooks`.
- Any other agent: copy upstream `AGENTS.md`, or install
  `skills/ponytail/SKILL.md` as a skill.
- Optional default level: `~/.config/ponytail/config.json` or the
  `PONYTAIL_DEFAULT_MODE` environment variable.
- Install only from the upstream repo or the `@dietrichgebert/ponytail` npm
  package: upstream never ships `.exe` or `.dll` files, and a copy that does
  is not theirs. The npm package name was verified to exist on 2026-10-13;
  the install flow itself was not run here.
