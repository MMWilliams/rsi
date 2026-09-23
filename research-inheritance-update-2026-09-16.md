# Inheritance experiment: current research check

Checked primary sources on 2026-09-16 before the v4 study. This is a targeted
update, not an exhaustive priority search or confirmation of novelty.

## RSIAgent (14 September)

[RSIAgent](https://arxiv.org/html/2609.15364v1), abstract, section 4.6 and
appendix 8.3 inspected. It uses exploration to construct memory, then freezes
memory for downstream evaluation without weight updates. Its failure analysis
describes incomplete verification and unreliable consolidation. This is relevant
prior work for transferable learned knowledge; explicit memory alone is not a
novelty claim. Our inference: a frozen-memory task gain does not by itself answer
whether a later improver is better from the same ancestor. V4 keeps that separate
comparison. We have not reproduced its results or audited its code.

## Huxley–Gödel Machine

[HGM](https://arxiv.org/html/2510.21614), abstract and section 4.1 located during
this check; earlier review covered its introductory algorithm description.
Its distinction between task performance and improvement potential motivates
the common-ancestor test. V4's simple descendant-effect sum is not HGM's clade
estimator and should not be described as a reproduction of it.

## Principle-guided language-model research

[Data-Efficient Language Modeling](https://arxiv.org/html/2609.10702v1), abstract
and reported continuation comparison inspected. It reports two continuations
from a shared parent and a small increase across model generations. This is
relevant to measuring research interventions, but those scores do not establish
our table-inheritance hypothesis. Full methods/code inspection remains open.

## Decision

Keep the predeclared v4 comparison. It tests whether more balanced source
evidence improves table-only transfer, before adding a new selector or edit
language. Preserve failures, reconstruct decisions independently, and account
separately for acquiring the table. Any result remains a component finding;
neural coverage, broader application outcomes and full recursive improvement
need further experiments.

## Follow-up during v5 replication

[MetaRSI-v1](https://arxiv.org/html/2609.06396v1), sections 4.5 and 5.4 now
inspected: its outer policy rewrites a scheduler, and its improver comparison
forks the same starting system under equal downstream budgets. Thus neither
system-level composition nor the common-start comparison is novel by itself.
Its outermost meta-policy remains fixed. The paper is a direct comparator;
reported gains have not been reproduced or its implementation audited here.

[S3Gym](https://arxiv.org/html/2608.31100v1), sections 6.2–6.3 inspected:
the reported association between local judgment agreement and subsequent gains
is near zero. Benefits from summary memory vary with task structure. Our
inference is to retain raw, state-specific edit records rather than assuming
an unconditional aggregate preserves all useful information. That does not
establish that context conditioning will improve our DSL selector.

V5 remains a fixed-method replication. These findings refine the comparison and
next hypothesis; they do not change the active run's protocol or selector.

## V6 context diagnostic, after v5 completed

[Hutter et al., Algorithm Runtime Prediction](https://arxiv.org/abs/1211.0906),
abstract checked: empirical performance models use task features and algorithm
parameters, with applications to selection and configuration. Our coverage-change
target is different, but context-conditioned prediction itself is established
prior art. The S3Gym abstract was rechecked: effects of memory/training depend on
task structure, and translating feedback into transferable decisions remains a
separate problem. Neither source validates our proposed model.

V6 now tests that proposal using source data alone: contextual ridge slightly
improved squared prediction error but failed the declared edit-ranking screen.
Do not promote it or infer that all contextual approaches fail. Plan and full
result: `EXPERIMENT-v6-context-diagnostic.md` and
`context-diagnostic-results-2026-09-16.md`. The next intervention will need fresh
banks and a stronger fixed-pair control discovered in this exploratory analysis.
