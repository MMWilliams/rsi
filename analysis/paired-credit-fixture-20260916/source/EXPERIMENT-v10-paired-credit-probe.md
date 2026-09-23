# V10 source probe: paired effects on later improvement

Declared before new task generation. This is a CPU source-mechanism probe, not
the full inherited-improver comparison proposed in NEXT-IMPROVER-CREDIT-STUDY.md.
It tests whether that comparison has measurable signal worth estimating.
The live v9b neural experiment and its source files remain unchanged.

## Frozen setup

Use corrected partial-empty search with exact cost reopening, BASE_CONFIG,
the v7 common macro library, expansion ceiling 128 and max four atoms. No neural
inference or weight updates. Initial interventions are all twelve existing
numeric edit operators; each is installed as an experimental intervention even
if it would not pass an improvement gate. No intervention is declared beneficial
merely because it was installed.

Six source groups, seeds 347, 359, 373, 389, 401, 419. Bank seed 9162611. For each
group generate development=16, admission=16 and measurement=16 tasks, with three
visible and thirteen hidden examples. The first two splits divide into two
eight-task rounds. Exclude prior protected-bank reference templates, including
v9b and implementation fixtures. New splits exclude preceding splits. All pairs
within a group share its tasks and baseline, so they are dependent observations.

For each group, a fixed random schedule draws two distinct operator names from
the twelve-entry catalog in each of two rounds, using Random(source_seed +
126000). Freeze it before any branch is evaluated. The no-edit branch and all
twelve edited branches receive the same schedule. At each round evaluate the
parent and both candidates on development tasks, choosing maximum signed gain
with lexical operator-name tie breaking. Evaluate that candidate and parent on
admission tasks even for nonpositive development gain. Retain it only if
development gain is positive and admission gain is nonnegative.

This is a fixed downstream improver. It adapts acceptance to observed outcomes;
its proposal schedule, scoring rule and budget do not learn during this probe.

## Deferred measurement and quantities

Close all 78 branch optimizations before evaluating any source-measurement
task. Then measure starting and terminal states on the group's common measurement
bank. Measurement is source data for possible future memory learning, not the
final holdout of a subsequent inheritance test.

For edit e versus no-edit control b, report exact solved-task counts and:

- Immediate effect: Q(e_start) - Q(b_start).
- Total descendant effect: Q(e_terminal) - Q(b_terminal).
- Change in later improvement: [Q(e_terminal) - Q(e_start)] -
  [Q(b_terminal) - Q(b_start)].

Report all 72 pairs, signs, paired counts and group summaries. The last quantity
is not the initial edit's benefit and can have a different sign from total
effect. Record which descendant edits were accepted in each branch.

This pilot does not promote a memory policy or test statistical significance.
Proceed to designing an estimator only if at least one measured paired effect
on later improvement is nonzero; that is a headroom check, not evidence of
generalization or RSI. A zero result argues for changing the tested edit/policy
space rather than fitting this signal. Sample counts are a bounded pilot choice,
not a power calculation for a headline result.

A smaller implementation fixture may test the runner and auditor with distinct
seeds and task counts. Its outcomes have no research status and do not select
the full study's thresholds, tasks or operators.

## Logging, replay and audit

Journal branch initial/terminal configurations, complete schedules, every
development/admission decision and exact request references. Search sees only
public examples. Every unique task/config search executes twice with exact
replay comparison; grade using independent and published interpreters. Cached
reuse requires an exact full request and explicit provenance. Record physical
search and replay costs separately from logical evaluation reuse; a shared
baseline is not free in a hypothetical standalone pair.

Snapshot source/config/protocol/input hashes, preserve failures, and refuse run
overwrites. Independently regenerate banks, reconstruct schedules and every
branch, rerun all unique searches, regrade outcomes, and recompute every effect.
Require audit before interpretation. Audit computation is additional overhead.
The finite task oracle is not an all-input proof, and local hashes do not
authenticate against the host. This human-designed probe supplies neither
autonomous edit invention nor an improved recursive improver.
