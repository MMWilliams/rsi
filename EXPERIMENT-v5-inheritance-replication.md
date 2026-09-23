# V5: fresh replication of balanced table inheritance

Declared 2026-09-16 before generating the study banks or scoring any v5 task.
This follows the small, inconsistent v4 gain. It retains the complete RSI goal;
this study isolates one required component rather than establishing full RSI.

## Fixed method and changes from v4

Use the same twelve numerical edit types, selector, common ancestor, macro
library, six generations, 128 search expansions, and 16 development/admission
tasks per generation. Source calibration tries all twelve edits; transfer tries
two. Transplant g0/g3/g6, scrambled g6, and random selection into BASE_CONFIG.
No model inference, weight training, new context features or selection rule.

Six new source seeds: 101, 113, 127, 139, 151, 163. Bank seed: 9162605. Each
source has disjoint 96-task source development/admission and 96-task transfer
development/admission banks. Five paired transfer conditions share that source's
transfer banks. A fresh 256-task final bank is shared across all sources and
conditions. Exclude all earlier literal-scrubbed reference templates, including
v4. This shifts the remaining task distribution; it is a fresh-bank replication,
not an IID claim about an unchanged infinite task population.

All 36 optimization trajectories must close before final scoring. Run this
configuration once, preserve failures, and do not change budgets or seeds after
seeing results. Larger source count and final bank are declared for more evidence,
not derived from a claimed power calculation.

## Logging intervention, verified to preserve selection behavior

Enable optional selection traces: available/excluded names, effect-table hash,
RNG state hashes before/after, each beta draw and its parameters, mean immediate
and descendant effects, combined scores, chosen name and tie rule. Random arms
record the uniform choice and RNG hashes. Recording consumes no extra draws.
Regression tests compare choices and final RNG states against the archived v4
selector. The auditor independently reconstructs the stream from the recorded
seed and table history; it does not invoke the selector to validate itself.

The trace explains the implemented selection rule, not the underlying causal
reason why an edit helped. That distinction remains explicit in reporting.

## Prespecified report

Primary contrasts remain g6−g0, g6−g3, g6−scrambled and g6−random, averaged across
six paired sources. Report all six differences, per-source paired-task bootstrap
intervals, accepted edits, source informativeness and acquisition/downstream
costs. Do not treat six evaluations on shared final tasks as six independent
task banks or pool v4/v5 absolute solve rates. No optional stopping, seed removal
or promotion based only on a favorable aggregate.

An encouraging replication requires all four mean contrasts positive and g6
strictly beating both g0 and scrambled in a majority of sources. This is a
screen for the next experiment, not a statistical certification or a full RSI
criterion. Failure of that screen redirects work to better effect prediction or
the edit space. Even a pass requires acquisition-inclusive compute controls,
broader tasks and neural coverage before integrating a claimed better improver.

Archive/audit requirements are unchanged from v4, with selection reconstruction
added. Logical cost charges and measured elapsed times remain separate; neither
equal proposal counts nor acquiring a table once makes total compute matched.

## Research context

[S3Gym](https://arxiv.org/abs/2608.31100), abstract inspected 2026-09-16,
distinguishes self-testing, judging and improvement and reports task-dependent
benefits and negative transfer. It supports measuring downstream transfer
separately from feedback accuracy; it does not validate our selector.
[MetaRSI](https://arxiv.org/abs/2609.06396), abstract inspected, composes data,
harness and model updates and changes their scheduling. This is relevant prior
art against claiming that our system-level composition alone is novel. Detailed
methods/code review remains open. Neither paper's results are reproduced here.
