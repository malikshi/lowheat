# Code Review and Independent Review

This companion owns the executable detail behind `AGENTS.md` → Code Review
Standards. The thin contract keeps the gates; this file explains how to run
them. It distils the cores of two review skills: one reads code for defects,
one decides whether a change is allowed to ship. They are separate passes.
A defect-reading pass never clears a change; only a fresh independent round
does.

## Dimensions and selection

State the selected dimensions, scope and comparison baseline before
investigating. Bare "review this" means correctness only; an explicit list
selects correctness, performance, security or a combination; an unknown or
empty selection gets asked about, never reinterpreted. Review working changes
when present, else the repository. Follow dependencies beyond changed lines
and separate defects introduced from ones merely revealed. Review and report;
apply fixes only when asked.

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
unchanged at the end. Workers that split one flow share one model, named, so
their reports stay comparable; a model panel is the opposite axis and is
described below.

## Independent review: the ship gate

**Selection and isolation.** The reviewer is a subagent of the harness you are
already running, dispatched from the installed `reviewer` definition: no second
CLI, no external process, no provider key. A fresh subagent session never saw the
build, so it is independent; it shares more blind spots than another model
family, and a round that runs beats one skipped. The repository ranks its
reviewers; it cannot rule out a review. When no agent runner is available, use
the recorded fallback without asking — then a fresh session of the builder's
family. Name the actual reviewer and why it replaced the named one. "Never
review another family's work" means prefer another family, never skip.

Fresh means never a resume, a fork or the builder's own context: the subagent
must not inherit the builder's beliefs. Dispatch it with no edit, write, or
commit capability, memory off, project and user instructions off where the
harness allows, and the brief below as its whole prompt. The installed `reviewer`
grounds this in the harness's own controls as far as they go: no edit tool in any
rendered shape, Codex's read-only sandbox, OpenCode and Kilo's `edit: deny`, Grok's
`readonly`. The reviewer still needs shell for `git log` and `git diff`, and that
shell is not sandboxed on those harnesses; Factory Droid carries no field at all.
So the remaining control is the definition's instruction, and a round says which
of its controls were enforced and which were instruction only. Name whatever
cannot be switched off in the report. Give the reviewer only the mechanical
range and the usage model, not suspected defects.

### Model panel

A panel is the cheapest way to buy coverage of blind spots: the same brief and
the same subject dispatched to several models at once, so their different tells
surface on one subject instead of one model's view standing in for review.

**Dispatch.** Hold `reviewer` itself back. Name `reviewer` in a subagent file
only when you are happy with one fixed model; pin `model` there and the panel
collapses to that model, because a per-run override is the only way to vary it.
For a panel, dispatch three generic subagent calls in one turn on a provider that
offers at least three models. Each member's prompt is the full `reviewer`
definition body — read the installed agent file and use it verbatim — with the
five-part brief appended beneath it. The brief alone is only the subject; without
the body a member has no method, no five-element refutation and no report shape,
and the three reports stop being comparable. Keep both parts byte-identical
across members: a variant prompt measures the prompt, not the model.

**Independence.** Members never see each other's report and never share a
session, a resume, or a fork of the builder. Run them in that one turn, collect
all three results, then triage; showing one member another's findings turns the
panel into a single reviewer with extra steps. Name every model actually used,
and say which one was the fallback if fewer members ran than you asked for.

**Reading the spread.** Treat agreement as strength and disagreement as the
lead. A finding several members reach independently earns triage first; a
finding only one member reaches is not weaker — a single member is often the
one who saw it — so give it the same five-element check, never a pass because
the majority was silent. Where two members contradict each other, say so
plainly and settle it from the code, not by counting votes. A model that
returns nothing usable is a failed member, not a silent approval: report it by
name and rerun on another model rather than reading three as two.

**Cost.** A panel is one round, not three. It covers a subject once with three
views, so it consumes one round number and one set of findings; triage
outcomes, fixes and reruns follow the stopping rule unchanged. Run a panel when
the subject is large, security-scoped, or bound for a release; a one-line
change still gets a single short round.

**Write the brief in five parts, in this order, to avoid steering:** what the
product is in two sentences, naming binding spec files and trust boundaries;
the git-computed subject; the usage model — who uses which surface, when, and
what stays serious however exotic the trigger; the question "what would block
or break this release", requiring every finding labelled INTRODUCED or
PRE-EXISTING with a literal triggering sequence; and a terse ranked list of
claim, `file:line` evidence and what to change. Omit earlier findings,
suspected files and approval requests — a reviewer asked whether it approves
will say it approves.

**When.** Before every release, however green the tests; before any push that
deploys; again after every fix a round found. A fix is unreviewed code and
produces the worst defects; never report readiness from a round followed by a
fix. Review the completed phase; test stages as they land. State the phase
split, review cadence and rough builder-hour estimate before building. Run
phase reviews after the coordinator's gate, visual and docs checks. An
advisory stage round clears nothing. Run the full applicable gate before
reviewing a finished standalone change, and rerun it if a fix followed its
last full run.

**Subject.** Compute it from git, not prose: the unreleased range
(`git log --oneline $RELEASED..HEAD`, `git diff $RELEASED...HEAD --stat`,
`git status --porcelain -uall`), including uncommitted and untracked files.
`$RELEASED` is the production branch, release tag or deployed commit. Read the
status for what does not belong; generated or scratch files are subject noise,
so ignore them or ask the owner before the round. Before the first release,
review the whole history with `--subject HEAD`, including the first commit, and
mark every finding INTRODUCED. Later rounds cover only commits since the
previous round, with the rest as context. Never narrow a range by hand to make
it fit: split an oversized subject by commits when history falls into stages,
or by surface when it does not. Split by contiguous commits or by complete
area; together the rounds cover every changed file. Keep coordinator notes and
suspected defects out of the subject until the series closes; they steer a
fresh reviewer. Scope the subject by what a reviewer must read, not file count;
give generated docs as context, not subject.

**Run and verify the round.** Give the reviewer the mechanical range and the
usage model, not a list of suspected defects. A short clean round is a failed
round: require it to say what it read, what it expected and why the result
holds. A round that could not read the subject is failed however long it is.
Require a round that reports the files and ranges it examined, and check those
against the subject yourself. Findings and severity labels are claims. Verify
each against the code by hand, including whether the trigger is reachable in
the usage model. Keep notes, brief and report outside the repository; review in
a still checkout, and treat a pushing deploy as closing that round.

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
