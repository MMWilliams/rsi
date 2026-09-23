# Programme target: growth in the capacity to learn

Adopted 2026-09-21 in response to the third external review. This document
records what is adopted, what the review omits, what was done immediately, and
what requires a decision before it can proceed.

## 1. The reframing, accepted

The programme measured selection accuracy on fixed candidate pools in one
synthetic benchmark. That is not intelligence growth under any general
definition. The review's operational definition is adopted as the target:

> Intelligence growth is a persistent improvement in the ability to solve
> unfamiliar problems and acquire unfamiliar skills, across a specified range of
> environments, under controlled resources and prior information.

Four objects are measured separately and none is allowed to stand in for the
others:

| object | what it measures | current status in this repository |
| --- | --- | --- |
| intelligence | novel-family learning curves at frozen experience levels and budgets | not measured; one benchmark, instance-level transfer only |
| improvement productivity | independently validated intelligence gain per matched research resource | not measured; every improver result was dominated by a capacity-matched pooled model |
| evaluation reliability | selection regret on identical candidate pools, calibration, robustness under optimization | partly measured; the fixed-pool test is retained as this diagnostic |
| forecasting accuracy | proper-scored predictions committed before each experiment | not measured; no forecast was ever committed |

The existing fixed-pool benchmark is kept as the evaluator-selection
diagnostic. It answers "does this evaluator make better use of the same
available solutions" and nothing broader.

## 2. Specific points accepted

- Separate new instances, new compositions and new mechanisms. Every transfer
  result so far is instance-level.
- The selection-regret decomposition, selected gain equals best available
  candidate gain minus evaluator regret, with the 2-epsilon bound stated as a
  uniform bound over the candidates an optimizer actually produces.
- Do not call the maximum of noisy observed scores an oracle. Every per-task
  oracle in this repository is a max over final labels and is an upper bound
  with unquantified optimism.
- Three item collections, development, linking and sealed audit, with the
  scoring specification frozen within a confirmatory study.
- The two-by-two factorial with an evaluator-evolves arm, the three replay
  probes, and charging evaluator construction to the arms that use it.
- Forecasts committed before execution, scored with proper rules against
  no-change, constant-gain, budget-only and saturating baselines, with whole
  lineages and intervention families held out and a prespecified randomized
  exploration fraction.
- Four levels of conclusion, intelligence growth, improver growth, recursive
  growth and compounding growth, with no ratio of near-zero denominators.

## 3. What the review omits, and it is the thing that ended every claim today

The review does not engage with the day's decisive finding: every improver
result in this programme was measured against a default with less model
capacity than the improver's output, and one larger pooled model on the same
labels beat all of them. Nothing in the proposed battery, measurement model or
factorial design guards against the same artifact at larger scale.

The programme therefore adds one requirement to every layer of the review's
design:

- **Every arm and every reference population must include "one larger model on
  the same labels" at several sizes.** It is a zero-knowledge default and it is
  free. A constructor, curriculum, abstraction or evaluator counts as an
  improvement only over the largest such model that the budget permits.
- **The item response reference population must contain capacity-scaled
  single models**, so that a capability dimension cannot be an artifact of
  capacity that the reference population never spanned.
- **Any constructor language must be able to express "fit one larger model."**
  Otherwise it can win by adding capacity in a form the baseline was denied.

## 4. Stage 1, repair and instrument the current experiment: complete

| item | status |
| --- | --- |
| out-of-fold router audit | done; leakage inflated one replication by +14 |
| E3 as a single estimand with its own interval | done; replication two touches zero |
| capacity-matched pooled baseline | done; dominates every built system |
| feature-augmented pooled baseline | done; does not explain the gap |
| combined capacity-and-feature-matched baseline | done; features add nothing at 60 or 120 leaves in either replication (+0 and -3 at 60, -1 and +5 at 120, all intervals crossing zero) |
| complete cost records | label counts and wall time recorded; CPU time, peak memory and failed-run counts were not, and are required from the next run onward |
| preserve the experiment as an evaluator-selection diagnostic | done |

## 5. Stage 2, the first split: mechanism holdout on the surviving claim

The only claim standing is verifier growth: a larger model on more verified
labels is a better evaluator. It has been shown on fresh instances of the same
six generators. `mechanism_holdout_verifier.py` trains the 60-leaf pooled model
on five families and scores it on the sixth, paired over 36 banks per family,
against E0 and against an in-distribution model. If the held-out gain over E0
collapses, verifier growth here is family-specific and the reviewer's warning
that fresh seeds establish only instance transfer applies to the last standing
result too.

**Result: collapsed.** Held out, the evaluator is worse than E0 on every family
(716 against 1020 over six families, every interval negative; self-edit 111
against 241). In distribution it beats E0 by +174; the transfer gap is +478. The
improvement is familiarity with the six generators. Under the adopted definition
the programme has demonstrated no intelligence growth. Record in
`MECHANISM-HOLDOUT-VERIFIER-2026-09-21.md`. The capacity follow-up at 15, 60 and
120 leaves (`mechanism_holdout_capacity.py`) answers yes: in-distribution
totals 1000, 1194, 1230; held-out totals 762, 716, 706; transfer gap +238,
+478, +524. Larger evaluators overfit families more. The held-out-mechanism
gate must therefore be run at the deployed capacity, and the Stage 2 battery
must report every capability at more than one evaluator capacity.

## 6. Stages 2 to 4 require a decision

The remainder of the review is a research programme, not an experiment:

- four procedurally generated domains with independently checkable outcomes,
  each with instance, composition and mechanism splits, whose diversity must be
  demonstrated rather than assumed;
- a multidimensional item response model calibrated against a reference
  population of architectures, heuristics, memory configurations and search
  budgets, with linking items preserved across generations;
- a research forecaster with prospectively committed, proper-scored predictions
  over held-out lineages;
- a five-arm factorial over independent lineages for about six generations,
  with common-state replay, evaluator swap and inheritance-reset probes.

On this machine one twelve-bank frozen replication with audit costs one to two
hours. Lineage-level replication across five arms and six generations, on four
domains, is weeks of compute before any battery is built, and three of the four
domains do not exist yet. That is a decision about investment, not a step I
should take on my own. What can be done without that decision is what sections
4 and 5 describe, and it is being done.

## 7. Literature

The review cites Chollet, tinyBenchmarks, the emergent-abilities mirage paper,
observational scaling laws, proper scoring rules, LAPS, GROOVE, TRACED,
ProcessBench, reward-model overoptimization and the Red Queen Gödel Machine.
None is cited in this repository's own claims and none will be until read
directly; the reviews' summaries of them are not a substitute.
