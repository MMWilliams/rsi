# Candidate-consensus evaluator and typed edit effects

## Decision

**Retain the public-context ranker, AST search branch and exact-output sensor as the provisional seed; do not promote the richer query-value model or its bounded improver yet.** The source-selected richer model looked useful in inspected development, but the prospective transfer failed both the evaluator-feature and recursive-child gates. The protected admission rule rejected the later parent and correctly deployed the initial child.

On twelve untouched 48-task mixed transfer banks, each active policy used **96 true output calls**:

| Policy | Correct / 576 |
| --- | ---: |
| No query | 286 |
| Strongest fixed eight-call schedule, transformation only | 320 |
| Initial rich-feature child | **339** |
| Later rich-feature child | 335 |
| Later frozen parent | 337 |
| Scrambled-history child | 336 |
| Duplicate-history child | 338 |
| Fixed rich ridge-10 / ridge-100 on later child's rows | 335 / **339** |
| Fixed base-feature ridge-10 / ridge-100 on later child's rows | 333 / 334 |
| Protected deployment after admission rejection | **339** |

The later-minus-initial child difference was positive in one of twelve banks, with an exact bank-bootstrap 95% interval of **-9 to +1** for its total. The later child exceeded the best base-feature rule by only one choice; that paired interval was **-4 to +6** with four positive banks. Reachability was **489/576**, leaving substantial room in candidate coverage and selection, but these results do not show that the richer value model reliably uses it.

## Development signal and why it was insufficient

The new features describe the evaluator's candidate consensus before it buys an output: score-weighted support for the leading answer, how quickly rival outputs appear in the ranked list, agreement across eight predicted probes, source diversity and candidate complexity. They are computable from public inputs, candidate programs and predicted outputs. They do not use the true probe output or final correctness label at inference. On 864 opened source tasks, the selected rich interaction ridge-10 model scored **523** correct choices under leave-one-bank-out eight-call allocation versus **516** for the best base-feature model. On a separate, already opened 576-task development set, it scored **355 versus 345**, with a **-1 to +20** paired interval. These observations justified a new frozen experiment; they were not promotion evidence.

The initial parent used 864 verified task effects; the later parent inherited 576 more. Both selected rich interaction ridge-10. After the same new 288-task admission update, the initial child selected ridge-100 while the later child selected ridge-10 on a source-CV tie. On admission, the later parent scored 173/288 versus initial 170 and the strongest fixed schedule 170, but won only three of six banks against that fixed schedule. The declared four-bank protection requirement therefore rejected the later parent. Both raw children were still tested on two transfer panels that had been frozen before either panel's final labels were opened. The later child scored 167 versus 169 on panel A and 168 versus 170 on panel B. Fixed rich ridge-100 on its **own** 1,728 training rows scored 339 overall, four above the selected child. The method selector added no advantage over choosing that fixed rule.

Historical acquisition is unequal: the initial and later parents began with 864 and 1,440 task effects, and their children had 1,152 and 1,728 rows after the shared admission update. Acquiring each first-query effect requires a true output plus external final-correctness labels and candidate work. Matched 96-call transfer budgets therefore do **not** imply matched total resources. The feature extractor also predicts eight outputs for every candidate; fixed schedules can avoid some of this inference.

## Typed component effects from opened banks

The separate typed ledger reconstructs **1,440 opened tasks** from the earlier meta-improver and incumbent-aware runs, with the same candidate and final-label definitions. It records verified effect and cost vectors for search widening, temperature sharpening, replay ranking and two first-probe selectors:

| Component edit on common tasks | Gains | Harms | Net final choices |
| --- | ---: | ---: | ---: |
| AST widening under the old fixed ranker | 0 | 0 | 0 |
| Global sharp ranker versus public-context fixed route | 11 | 27 | -16 |
| AST replay ranker versus fixed route | 25 | 0 | +25 |
| One top-20 output query versus replay/no-query | 300 | 0 | +300 at 1,440 calls |
| One minimax output query versus replay/no-query | 288 | 0 | +288 at 1,440 calls |

AST widening raised reachability from **1,177 to 1,233** across the full 1,440-task stream: **56** newly reachable AST tasks. The fixed ranker selected none of them correctly. After the replay ranker and top-20 sensor, **32** of those newly reachable tasks were solved, showing a genuine search/ranker/sensor interaction. Top-20 beat minimax on 45 tasks and lost on 33, so the net advantage of 12 is not a universal per-task ordering. These effects are *development diagnostics*, not a fresh comparison of a learned cross-component improver.

Across the 30 opened banks, the replay-ranker edit gained in 16 banks, lost in none, and had a descriptive bank-bootstrap interval of **+15 to +35** for its +25 total. Global sharpening's -16 total had interval **-29 to -4**. A first top-20 query gained in all 30 banks when purchased for every task, at 1,440 calls. These intervals describe the fixed components on opened banks; they are not a transfer test of a policy that learned when to apply each edit.

A deeper sensor action is a poor first priority at this call budget. Across the same 1,440 opened tasks, a second query helped 96 task choices if bought for everyone, with two harms. Under eight calls per bank, even an unavailable oracle choosing zero, one or two calls could score only **994**, versus **989** for an oracle restricted to zero or one. That five-choice upper-bound gain across 30 banks is much smaller than the unfilled first-query allocation opportunity. The ledger and two-query records are in `analysis/typed-edit-effects-*.json` and `analysis/two-query-effects-*.json`.

## Verification and next test

The prospective experiment froze source model hashes, then admission choices, then both transfer panels' pools, candidate-predicted outputs, rank scores, public features and every eight-call allocation before scoring transfer. Its runner evaluated **205,076 candidate final labels** and produced **1,640,608 candidate-predicted output cells** over admission and transfer; generation/preparation took **422.0 seconds wall time** across the three stages. The **independent audit passed**: it retrained four parents and ten child/control states, regenerated all 864 tasks, pools, 1,640,608 predictions and public features, rechecked 264 bank-policy allocations, and re-evaluated all 205,076 final candidate labels and their bank scores. Its record is `runs/rich-query-improver-transfer-20260918/audit.json`.

The next seed-improver experiment should target **first-query allocation and package selection**, not another weak method tie-break or a second-query catalog expansion. Keep distinct effect fields for reachability, ranker recovery, probe recovery, harm, candidate-generation cost, prediction cost and true-output calls. A child must improve a common frozen base on disjoint banks after shared new feedback, beating its parent, scrambled/duplicated history and the strongest fixed package. Test altered or misleading public mechanism cues before claiming transfer beyond these six synthetic string families. No current result establishes an optimal general RSI seed or self-generated edit vocabulary.

Protocol: `EXPERIMENT-rich-query-improver-transfer.md`. Runner: `rich_query_improver_transfer.py`. Auditor: `audit_rich_query_improver_transfer.py`. Development: `rich_query_feature_extraction.py`, `rich_query_value_development.py`, `typed_edit_effect_development.py`, `reconstruct_typed_edit_effects.py`, `two_query_effect_development.py`.
