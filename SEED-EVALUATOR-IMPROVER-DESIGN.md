# Evaluator, improver and integration design criteria

These are operational design criteria for the seed search. They are not claims that the current implementation satisfies the research goal.

| Component | Useful capability | Failure to measure separately |
| --- | --- | --- |
| Evaluator | Distinguishes behaviorally different candidates using evidence relevant to the task | More confident scores without better choices |
| Evaluator | Predicts uncertainty and asks for informative, affordable feedback | Spending extra oracle queries and calling the extra information intelligence growth |
| Evaluator | Transfers judgment to new public examples and changed mechanisms | Remembering a recurring benchmark template |
| Improver | Predicts which intervention helps from the current state, including harms and costs | Treating a global mean edit effect as universally useful |
| Improver | Produces a better evaluator from an identical seed under the same budget | Starting later improvers with an already improved evaluator |
| Improver | Retains transferable evidence about effects, with support and provenance | Repeatedly counting correlated evidence as independent support |
| Integration | Admits useful changes while preserving working capabilities | Replacing a useful incumbent on an inconclusive score |
| Integration | Lets the retained evaluator guide the next feedback step | Testing gates after fixing the entire acquisition trajectory |

## Seed components under comparison

1. Judgment: lexical regression; structure-sensitive regression; verified behavioral memory; their ensemble; an incumbent-favoring score.
2. Feedback acquisition: uniform sampling; uncertainty; cross-evaluator disagreement; behavioral novelty; disagreement plus novelty.
3. Improvement memory: empty; source-round-2 effects; source-round-4 effects; scrambled effects; and an inherited table updated online.
4. Integration: unconditional replacement; strict admission improvement; and improvement with no regression across observed alphabet groups.

The behavioral evaluator executes candidate predicates on unlabeled probes. It does not know the correct probe outputs. Verified source outcomes teach the relation between those signatures and correctness. Its memory can transfer within recurring mechanisms; changed-mechanism performance must be tested independently.

The learned feedback controller maps public evaluation state to expected utility of an acquisition tactic. It selects which source feedback to buy, then the target evaluator updates from those verified outcomes. A distinct admission bank judges the update. The retained evaluator drives the next query. This closes the operational feedback loop while preserving a separate final bank for measurement.

## Required dissection

- Freeze candidate pools to measure judgment improvement independently of generator coverage.
- Reset bootstrap evaluator, feedback reservoir, budget and admission bank when comparing improver states.
- Compare each learned controller with empty and scrambled knowledge, every fixed tactic and the strongest static source-selected tactic.
- Include the best initial evaluator component as a no-update control even when another component was selected for active learning.
- Report raw evaluator choices and conservative deployment choices separately.
- Plot/record learning curves; distinguish a single useful update from repeated improvements and from a plateau.
- Record oracle label counts and acquisition cost; report any mismatch alongside accuracy.
- Treat all source/admission findings as selection evidence. Confirmation and replication must use new banks, with visible-example deduplication and mechanism-shift results shown separately.

The source search already shows why the strong static control matters: the initial lexical evaluator achieved 18/18 on its small admission bank, while the selected ensemble/uncertainty controller grew from 17/18 to 18/18. That is a gain over the ensemble's starting point, not superiority over every initial evaluator. Fresh confirmation decides whether the learned recipe has broader value.
