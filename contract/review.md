# Code Review and Independent Review

This companion owns the executable detail behind `AGENTS.md` → Code Review
Standards. The thin contract keeps the gates; this file explains how to run
them. It distils the cores of two review skills: one reads code for defects,
one decides whether a change is allowed to ship. They are separate passes.
A defect-reading pass never clears a change; only a fresh independent round
does.

## Dimensions and selection

State the selected dimensions, scope and comparison baseline before
investigating. Omitted or bare "review this" defaults to correctness only (plus
security automatically whenever a STOP trigger surface is touched); "full",
"all" or "audit" selects correctness, performance and security. Only ask about
an explicitly named unknown dimension when ambiguous and risky — never stall an
unattended review on an omitted selection. Review working changes when present,
else the repository. Follow dependencies beyond changed lines and separate
defects introduced from ones merely revealed. Review and report; apply fixes
only when asked.

| Dimension | Anchor |
|---|---|
| Correctness (core) | Agreements between participants across a boundary |
| Performance | Workload → resource demand → growth or contention → consequence |
| Security | Source → trust boundary → sink, with an attacker controlling the source |

One flow map serves all dimensions. Enter performance from the workload: what
work each request or operation triggers, how demand grows with input or load,
where contention or unbounded growth appears, and what observable consequence
follows. Static reasoning is not a measurement: settle layout and performance
claims on the running build in either direction, with a baseline built from
`HEAD` in its own worktree. Report one root cause once, with both impacts when
it spans correctness and security. Keep the tests separate per dimension.

## Two passes, two jobs

| Pass | Author | Question | Owner |
|---|---|---|---|
| Self-review | writer of the change | "What is wrong with this code?" | the author |
| Independent review | fresh subagent that never saw the build | "Would this break or block what ships?" | a non-author |

Self-review fixes defects before anyone else sees the diff. Independent review
owns the verdict; the writer never clears their own work. A one-line change
that ships gets a short round, never no round. A review that only finds faults
and a round that only approves both fail their job.

## Self-review: the agreement engine

Review consequential agreements, not isolated files. The defects worth finding
are disagreements between participants that each look reasonable alone:
caller and callee, producer and consumer, writer and later reader, branches
that must end in the same state, validator and sink.

**Map one flow** — inputs, execution paths, state owners, external
dependencies, observable effects. For each agreement, note its participants,
the value or effect exchanged, who decides the real answer (the authority),
its identity and lifetime, the required relationship, the evidence for that
relationship, and the order in which transitions happen.

**Establish an obligation** from a specification, documented contract,
language or protocol semantics, a test, or a necessary producer/consumer
relationship — never from one participant's implementation alone. A consumer
being written one way does not prove the consumer is right.

**Start where agreements break** — transformed or negotiated values,
reassigned identities, asynchronous work, persisted and reloaded state,
effects that must agree. Then inspect local arithmetic, boundaries and error
branches. Two probes earn explicit attention because they are usually missed:
- *Authority reconciliation:* force a requested value apart from the accepted
  or committed value, then find what still reads the request.
- *Identity correlation:* vary keys under overlap, reordering, removal and
  reuse; run two operations and complete them out of order.

**Force a violating execution** before calling a suspicion a finding: make
values differ, vary completion order, change identity between observation and
use, inject failure between effects, and exercise empty, exact-boundary and
adjacent-boundary inputs. Confirm each case is reachable. Absorption is not
prevention — a cache that usually holds or a retry that usually succeeds
hides a defect, it does not remove it. Timing that usually resolves correctly
is a race. Rare still means real: say who meets the trigger and how often.

### Diagnostic lenses

Overlapping detection tells, not a classification scheme or quota. Lenses 1 and
2 are the ones read-throughs miss most, because both sides look reasonable
alone; force those probes explicitly.

1. **Authority reconciliation** — a requested value is not an applied value.
   Follow validation, normalisation, negotiation and commit. Force the
   effective answer to differ from the request, then find stored state, UI,
   later calls and logs still carrying the request. Reconcile before the first
   consequential use.
2. **Identity and correlation** — check the correlation key's uniqueness,
   stability and lifetime under overlap, reordering, removal and reuse. Run two
   operations and complete them out of order; remove one mid-flight and reuse
   its slot.
3. **Freshness and generations** — mark values captured before a yield, await,
   callback, timer or lock release. Ask what can change before use and whether
   the stale result is ignored, applied, or applied silently.
4. **Lifecycle and derived state** — compare every construction, replacement,
   restoration, reset, failure and termination path. Two paths that should end
   in equivalent state are an agreement.
5. **Atomicity and partial failure** — split multi-effect operations at each
   failure and cancellation point. Check partial state is recoverable and
   success is not reported before effects are durable.
6. **Replay and effect cardinality** — follow retries, duplicate delivery and
   re-entry; compare guaranteed effects with required effects, especially for
   money, messages and shared totals. Check deduplication scope and lifetime.
7. **Composition and precedence** — trace pieces through merge, reduction,
   ordering and dispatch; compare real overwrite and selection rules with the
   intended authority, including transformations applied after the merge.
8. **Bounds, units and accounting** — follow counts, lengths, offsets and
   totals through every transformation. Check empty, boundary and overflow
   cases and whether measurement and consumption use the same unit.
9. **Framing and incremental processing** — compare logical item boundaries
   with read, write, iterator and callback boundaries. Test split items,
   combined items, partial writes and the last item.
10. **Representation and information loss** — compare what a producer can emit
    with the distinctions a consumer relies on; trace round-trips. This is the
    highest-frequency class: probe the nullish family (pending, absent, empty,
    zero, false, failed), field-set drift (a producer stops emitting a field
    and consumers degrade silently), and Unresolved values stored as resolved
    ones. A cast, `any`, non-null assertion or suppressed warning at a boundary
    is a candidate, not a refutation.
11. **Ownership, completion and progress** — trace who may mutate, release,
    cancel and complete. Inspect exceptional exits and competing terminal paths
    for premature release, missing completion, deadlock and use after ownership
    changed hands.
12. **Decisions and dispatch** — enumerate meaningful states and inputs for
    consequential predicates; check overlapping, inverted and missing branches
    and the language or framework default when nothing is specified. Ask
    whether each branch is reachable and whether anything starts each handler.
13. **Verification and observability** — follow each step's failure. Look for
    checks that cannot fail, oracles measuring the wrong thing, exceptions
    swallowed into success, gates skipping their subject, and effects whose
    absence nothing detects. If no observation would break, the guarantee is
    decorative.

Deduplicate by violated agreement and root cause, never by file. Passing tests,
unfamiliar code, a suspicious name and a missing test warrant investigation;
none is a finding or a refutation. Zero supported findings is valid.

### Refutation: the five elements

Promote a candidate only when all five hold:

1. **Expectation** — required behaviour, with the evidence for it.
2. **Trigger** — a feasible execution: inputs, state and ordering the system permits.
3. **Defect** — the concrete violated relationship, with source locations for every participant.
4. **Impact** — an observable consequence and its affected scope.
5. **Refutation** — the strongest mechanism that would prevent or repair it, checked and found insufficient.

Hunt the refutation: an enclosing guarantee, synchronisation excluding the
interleaving, reconciliation before any consequential read, an intentional
contract, an excluding precondition, a different responsible owner. Drop on
evidence that defeats execution, obligation or consequence; an essential
unknown goes in a separate "Unexamined areas and essential unknowns" list.
No quota: zero supported findings is valid; never call that "bug-free".

Security uses the same engine with a changed anchor — source → trust boundary
→ sink, with an attacker controlling the source — and one inverted rule:
drop a finding whose only victim is the attacker on their own machine,
account, tenant or data, unless it crosses a shared boundary. A finding
dropped as security may still stand as correctness. Static findings are not
confirmed exploits.

### Finding report

```
Review scope:
Comparison baseline:
Selected dimensions:

[Severity] [Dimension] Concrete consequence
  Expectation:  required behaviour, and the evidence for it
  Trigger:      feasible preconditions and execution
  Defect:       the violated relationship
  Evidence:     source locations for EVERY participant
  Impact:       observable consequence and affected scope
  Refutation:   strongest counterargument checked, and why it fails
  Remedy:       minimal correction to the violated relationship
  Verification: what was executed versus established from source

Coverage:
Unexamined areas and essential unknowns:
```

Chat findings use the terse `caveman.md` one-line shape; the fields above are
the content, not optional decoration. Cite both sides of a cross-boundary
defect. Report coverage as work performed: examined with/without findings,
not applicable with a reason, or not examined with a reason. State what is
well built and the limits of static review.

Fan-out, when used, partitions complete flows, never files or taxonomy
classes. Dispatch one `review-finder` subagent per flow; each reads both sides
of its agreements and never edits the tree, so confirm the worktree is
unchanged at the end. A finder that splits a flow across several workers uses
one model, named, for that flow, so their reports stay comparable. Widening to
several models is the other axis: it goes to every flow through the panel
described below, never to half a flow, because two models covering different
halves of one flow produce reports nobody can compare.

## Independent review: the ship gate

**Selection and isolation.** The reviewer is a subagent of the harness you are
already running, no second CLI, no external process, no provider key. Dispatch
along this ladder without asking the user:

1. Installed `reviewer` (and `review-finder` per flow on multi-flow subjects)
   where the harness loads an agent directory.
2. Runtime or generic read-only subagent (`define_subagent`, `research`, or a
   read-only worker) when the harness exposes subagent tools without an agent
   directory or in project scope — pass the installed agent body if readable,
   else this file's five-element method, report shape and read-only rule
   verbatim plus the brief.
3. The repository's recorded fallback, then a fresh session of the builder's
   family (`"Never review another family's work"` means prefer another family,
   never skip).
4. Single-session harnesses with zero subagent tools run the full five-element
   + STOP-trigger audit inline and report `Review: unavailable (no subagent
   runner; inline five-element review completed)` without faking independence.

A fresh subagent session never saw the build, so it is independent; it shares
more blind spots than another model family, and a round that runs beats one
skipped. The repository ranks its reviewers; it cannot rule out a review. Name the actual reviewer and why it replaced the named one.

Fresh means never a resume, a fork or the builder's own context: the subagent
must not inherit the builder's beliefs. Dispatch it with no edit, write, or
commit capability, memory off, project and user instructions off where the
harness allows, and the brief below as its whole prompt. An installed `reviewer`
enforces no edit tool; Codex adds a read-only sandbox, OpenCode and Kilo set
`edit: deny`, Grok sets `readonly`. Shell for `git log`/`git diff` is unsandboxed
elsewhere and Factory Droid has no tool field, so name which controls were
enforced vs instruction-only. Give only the mechanical range and usage model,
not suspected defects.

### Model panel

A panel is the cheapest way to buy coverage of blind spots: the same brief and
the same subject dispatched to several models at once, so their different tells
surface on one subject instead of one model's view standing in for review. It
applies to both subagents. On `reviewer` it widens the ship verdict on one
subject; on `review-finder` it widens each flow, so every flow still gets every
model — a panel applied to some flows and not others is not a panel.

**Naming the models.** Read model IDs from the harness catalog (the harness's
model picker or its own `models` command).
Pick one provider that the session can already reach and take three of its
models that differ. Do not hard-code a provider in the shipped text: whatever
the catalog prints is dispatchable.

Where the catalog serves them, prefer `opus-model`, `sonnet-model`, and
`haiku-model` as the default pick. That is a default, not a privilege, and it is
one maintainer's default rather than a vendor naming scheme: a name the catalog
does not serve is not a member, a catalog serving other ids still runs a panel
from what it serves, and the dispatch rules below decide how each name is
written. They are three sizes of one family, so where the same provider also
serves another family, swap one member out and say the panel spans two families.

Name each id as the catalog prints it: prefix included when it prints one, the
bare alias when it prints bare, because a bare alias resolves while exactly one
provider serves that name and becomes ambiguous only when two do. When two
providers print the same bare name, qualify it with the provider prefix or drop
that member and say which. When the subagent tool constrains `Model` to fixed
tier enums (`pro`, `flash`, `flash_lite`, `inherit`) rather than catalog
strings, widen across distinct schema tiers instead of passing an invalid
string. If a member fails to launch, report it and how many ran. If the provider
serves fewer than three ids, widen on what it serves rather than crossing
endpoints, and state the panel size and every name dispatched.

**Dispatch.** Keep `model` unpinned in `reviewer` and `review-finder` (pinning
collapses the panel to one model). For a panel, dispatch three generic subagent
calls in one turn. Each member's prompt is that agent's full
definition body — read the installed file verbatim, or use this file's
five-element method, report block and read-only rule when no file exists on disk
— with the brief appended beneath it. For `reviewer`
the brief is the five parts below; for `review-finder` it names the flow, the
baseline and the dimension. Without the body a member lacks method and report
shape; keep both parts byte-identical across members and flows so differences
measure the model, not the prompt.

**Independence.** Members never see each other's reports and never share a
session, resume, or builder fork. Run all three in one turn, collect, then
triage; name every model used and any fallback.

**Reading the spread.** Agreement earns triage first; disagreement is a lead.
Give a lone member's finding the full five-element check, never a pass because
the majority was silent. Settle contradictions from code, not by counting votes. A model that
returns nothing usable is a failed member, not silent approval: name it and
rerun on another model.

**Cost.** A panel is one round, not three — one round number and one triage/fix
cycle. Run a panel for large, security-scoped, or release subjects; a one-line
change still gets a single short round.

**Brief in five parts (in order, no steering):** two-sentence product summary
naming specs and trust boundaries; git-computed subject; usage model (who uses
which surface, when, and what stays serious however exotic the trigger); the
question "what would block or break this release" requiring INTRODUCED or
PRE-EXISTING plus a literal triggering sequence; and ranked findings (`file:line`,
claim, minimal change). Omit prior findings, suspected files, and approval
requests — asking if it approves biases toward yes.

**When.** Before releases, deploying pushes, and after any fix a round found
(a fix is unreviewed code). Review completed phases and test stages as they
land; state phase split, review cadence, task size and unit count before
building. Run phase reviews after coordinator gates and docs checks. Advisory
rounds clear nothing. Run full applicable gates before final review, and rerun
after fixes.

**Subject.** Compute deterministically from git: resolve `RELEASED` first
(explicit release tag/ref → `git merge-base HEAD @{upstream}` → `origin/HEAD` /
`origin/main` / `origin/master` merge-base). Never run an unset
`$RELEASED..HEAD` (git parses `..HEAD` as empty `HEAD..HEAD`). Run
`git log --oneline "$RELEASED..HEAD"`, `git diff "$RELEASED...HEAD" --stat`, and
`git status --porcelain -uall` (if `HEAD` equals `RELEASED`, review `git diff
HEAD` + untracked files). Exclude generated/scratch noise and list exclusions
under `Coverage:`. Before the first release (no base ref), review full history
from git's empty tree (`git log --oneline HEAD`, `git diff --stat $(git
hash-object -t tree /dev/null)..HEAD`), marking all findings INTRODUCED. Later
rounds cover commits since the prior round with earlier commits as context.
Never narrow by hand: split oversized subjects into stages by commits, or
by surface when it does not. Split by contiguous commits or by complete
area covering every changed file. Keep suspected defects out of the brief;
give generated docs as context, not subject.

**Run and verify the round.** Supply only the mechanical range and usage model.
Short clean rounds and unreadable-subject rounds fail: require examined files
and ranges, expected behavior, and why it holds, then verify against the
subject yourself. Findings and severity labels are claims; verify triggers in
code and usage model. Keep briefs/reports outside the repo in a still checkout;
a deploying push closes the round.

### Triage — mandatory before acting

**Question zero, in one sentence: what actually goes wrong for the person?**
If it does not sound bad read aloud, there is nothing to fix. The reviewer's
label is part of its claim. Weigh frequency before fixing: a rare precondition
is Low, except when it crosses a line the person cares about — another tenant's
data, private data on a public surface, disappearing work, a lost write, an
irreversible external write the person did not approve or had stopped, or
anonymous access to a member capability. A stated limit that stops loudly and
leaves visible, repairable state is safe; a silent wrong result is not.
Record each finding's harm, who meets it, how often, and the line it crosses;
rank by what it costs this product, not by list position or reviewer label.
When findings cluster, look for one false premise underneath before fixing any.

1. **Exact sequence** — literal steps, not "an attacker could".
2. **Permitted execution** — does this system actually allow the sequence?
3. **Actor and motive** — who does it, and why? Someone already holding the
   owner's session on the owner's screen already had the screen.

An attacker finding must grant a capability they lack in that position; a
mechanism granting nothing new is a description, not a vulnerability.
Layout and performance claims settle on the running build, not by re-reading
code in either direction; build the baseline from `HEAD` in its own worktree.
Accepting a finding is legitimate. A fix that did not need to happen is itself
a defect: run its regression test on the tree before the fix; if it passes,
revert the fix and keep the assertion. Prefer removing the rare case to
supporting it. Check whether the fix replaces a mechanism or adds one, and
write each stated limit where the product keeps its assumptions. When a repair
writes who decided, scope it by participant and item, never by current row
state. Search every doc when a state they all describe changes; repair a
drifted pair by copying the right sentence, never writing a third version.

### Stopping rule and recording

Stop at **no INTRODUCED finding above Low and no High or Critical of any
age** — severity after triage, not the reviewer's label. Fix High and
Critical regardless of age. An introduced Low goes to the owner's list with
its round number, opens no round, and gets fixed only when already in a batch
that needs one; that fix then opens a round.

If one mechanism draws findings two rounds running, stop patching: cut it,
or redesign it once in writing and only if the redesign removes machinery.
No third design; take the choice to the owner as cut or pause. Budget a
fix commit's own round in ingest, queue and concurrency code.

Rerun the tests a fix touches yourself after every fix. Verify each finding
and its INTRODUCED label against the released text. Record every round's
finding count and outcome — confirmed, disproved, fixed, accepted with
reason — in the PR body or commit message. Record pre-existing findings with
a deferral reason *and* a revisit trigger. Number rounds in one sequence per
repository and cite the number wherever the outcome lands. A clean round
came from a fresh reviewer given only the mechanical range, with nothing
fixed after it.

## Compliance record

The contract's four-line record reports `Review:` as an independent verdict
only after this gate holds. Otherwise it says why: not required for a small
or local change with no STOP trigger, or unavailable with the reason. Never
report a verdict from a round whose findings or fixes you did not verify.
