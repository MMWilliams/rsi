# Incremental shifted-feedback evaluator transfer

Status: **the preregistered feedback update did not transfer.** It changed the evaluator's query-value estimates but did not improve the protected fixed-budget E0 seed. A wider post-query action showed an exploratory gain, and the run identified the remaining call-placement and action-selection headroom.

## Frozen comparison

The [protocol](EXPERIMENT-shifted-feedback-value-transfer.md) froze 24 new shifted-AST banks (192 tasks, seeds 903200-903223). All policies shared the widened V67/V73 pools, old AST replay ranker, E0 candidate reranker, exact output probe and four output calls per eight-task bank. Candidate programs and probe outputs were generated first; all value models, candidate choices and 96-call locations were frozen before final correctness labels opened. The primary pooled model added 96 verified shifted-task effects to 1,152 familiar query-effect records, using the development-selected 12-fold shifted weighting. Scrambled-shifted and duplicated-familiar controls used the same fitting rule. Candidate-model acquisition and any extra post-query scoring are separate costs.

| Four-call policy | Correct / 192 |
| --- | ---: |
| Protected cheap E0 | **46** |
| Familiar-only prior E0 | 44 |
| Pooled shifted-feedback E0, primary | 44 |
| Shifted-only E0 | 44 |
| Scrambled shifted-feedback E0 | 43 |
| Duplicated familiar-feedback E0 | 42 |
| Hash-selected E0 calls | 42 |
| Joint pooled route across E0/plain/sensor | 48 |
| Joint shifted-only route, secondary | 51 |

The primary pooled update was **-2 versus cheap E0**, with one winning and three losing banks and a paired bank interval of **[-6,+2]**. It exceeded scrambled by only one and duplicate by two, with both intervals crossing zero. The preregistered evaluator gate failed. The preregistered joint pooled route was +2 versus cheap, four wins and three losses, interval [-4,+8]; its gate also failed. The secondary shifted-only route reached 51, +5 versus cheap, five wins and one loss, interval [0,+11]. It was not the declared primary route and does not establish promotion.

Without calls, E0 selected 26/192. A call on every task would select 55 under E0 or 60 under the wider sensor model. The full pool was reachable on **113** tasks; the old top 20 on **64**. Unavailable oracle placement of four E0 calls per bank reached 55, and unavailable selection of both call location and post-query candidate action reached 66. Those are upper bounds that use final labels, not deployable policies.

## What caused the observed gains

An opened, fixed-location decomposition showed that keeping the protected cheap call locations and changing only the post-query choice to the **plain top-50 survivor model** scored 50, versus cheap E0's 46. That +4 occurred on four banks without a loss, interval [+1,+8], but it was selected after viewing this result. The sensor variant scored 48. The secondary shifted-only route scored 51 and selected the plain action on 75 of its 96 calls; it exceeded fixed cheap-plus-plain by just one, interval [-4,+6]. Thus most of the route's observed benefit came from candidate choice, not learned call placement.

The shifted feedback also failed to improve the E0 query-gain forecast on these tasks. Mean squared forecast error was 0.1287 for familiar-only prior, 0.1325 for pooled shifted, and 0.1331 for shifted-only. A duplicated-familiar control had 0.1277. This is further evidence against interpreting model movement or more verified labels as intelligence growth.

## Cost and audit

The run generated 26,008 base candidates plus 67,422 extra AST candidates, predicted 747,440 candidate/probe output cells, scored 3,840 E0 candidate rows, 1,258 top-20 post-query model rows total, and 2,984 top-50 model rows total. The source update checked 4,992 candidate-choice labels, including 96 additional shifted-task effect records. Each budgeted policy used 96 exact output calls; one-query-each references used 192. The final research oracle checked 93,430 candidate labels.

The independent replay passed. It rebuilt all 192 tasks and pools, 747,440 predicted output cells, the source models and frozen decisions, 4,992 source choices and all 93,430 final candidate labels. See `runs/shifted-feedback-value-transfer-20260918/audit.json`.

The supported seed remains protected cheap E0 for this contract. The next improver test should use task-level paired effects for both **call placement and post-query candidate edits**, compare earlier and later edit-effect checkpoints on the same frozen base, and require a later child to beat the strongest fixed cheap-plus-plain schedule on an untouched panel. The present update is researcher-authored and failed its fresh gate; it is not a recursively improving improver.

## Opened later-checkpoint diagnostic

After this panel's labels opened, an edit-effect learner was updated from **96 to 288 verified shifted tasks** while keeping the same fixed candidate models and four-call budget. On this already opened 192-task panel, its routed policy tied the earlier checkpoint at **51**. The scrambled-added-feedback route scored 48 and duplicated-old-feedback route 50, but the later-minus-earlier route interval was **[-6,+6]**, with five winning and five losing banks. The E0-only call allocator rose 44 to 46, matching protected cheap E0 and a duplicated-feedback control, with a later-minus-earlier interval **[0,+6]**. This is development evidence, not a fresh child-improver test; it gives no basis to promote an I1 improver. See `analysis/incremental-joint-improver-development-20260918.json`.

Run: `runs/shifted-feedback-value-transfer-20260918/`. Diagnostic: `analysis/shifted-feedback-effect-diagnostic-20260918.json`. Runner: `shifted_feedback_value_transfer.py`.
