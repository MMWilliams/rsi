# Post-query feedback evaluator transfer

Status: **the candidate-level feedback edit failed fresh promotion.** The new sensor-conditioned post-query model tied the existing E0 order when every shifted-AST task received one exact output query. Its small four-call advantage was uncertain. This result is evaluator evidence, not a parent-to-child improver result.

## Why this edit was tested

The first audited shifted-AST stress test had 19/96 tasks that remained wrong even though a final-correct program in the old top 20 survived the actual output probe. A post-query candidate model was therefore trained on 8,681 verified surviving-candidate labels from 1,152 previously opened tasks. The matched plain model used public candidate features; the sensor model also used E0 probability/rank, surviving-score gap, survivor fractions and predicted-output agreement. Both used the same model class and source labels. On opened development panels, the sensor model scored 27 versus E0's 23 one-query choices on 96 shifted tasks, and 448 versus 438 on 576 familiar tasks. Their restricted-call gains were only +2 and +1 respectively, with intervals touching or crossing zero. These opened observations motivated the fresh test but did not validate the edit.

## Frozen test and result

The [frozen protocol](EXPERIMENT-post-query-feedback-transfer.md) specified 24 new shifted-AST banks, seeds 903100-903123, eight tasks per bank. All three policies saw identical widened V67/V73 candidate pools, the same old AST ranker, E0's top-20 candidate scores, and the same fixed output probe. The one true probe output was supplied by the external interpreter. Candidate choices and the cheap four-call allocation were frozen before final correctness labels were evaluated. The source models and their hashes were fixed. A query-free task used E0's top choice for all three policies.

| Outcome | E0 | Plain post-query | Sensor-conditioned post-query |
| --- | ---: | ---: | ---: |
| No call, shared E0 choice | 16/192 | 16/192 | 16/192 |
| One call on each task, 192 calls | **47/192** | 46/192 | **47/192** |
| Four calls per bank, 96 calls | 33/192 | 32/192 | **35/192** |

Sensor minus E0 at one call each was **0**, with two winning banks, one losing bank and a paired bank interval of **[-5,+4]**. Sensor minus plain was +1, interval [-5,+7]. With 96 fixed call locations, sensor minus E0 was +2 on two banks and tied the other 22, interval [0,+5]. The preregistered evaluator, sensor-feature and integrated-seed gates all failed. The four-call difference is a small observed edge, not evidence for promotion.

The widened pool contained a final-correct program for **112/192** tasks, but the old top 20 contained one for only **53/192**. An opened diagnostic rechecked all 93,840 labels: top-50, top-100 and top-200 recall rose to **75, 91 and 104** tasks respectively. Every one of the 112 full-pool reachable tasks retained a final-correct candidate after the probe. E0 solved 47 with one call per task, including some programs below the old top 20; 14 tasks still had a surviving correct top-20 program but were missed. The fixed top-20 post-query model had a narrow ceiling while at least 59 reachable tasks lay beyond its action set. The next action should expand recall into the post-query candidate set and test ranking there at equal pool and query cost. A top-50 model tested on opened panels improved one-query outcomes but regressed without calls and did not improve the restricted-call package; it is not yet an admitted solution. See `analysis/post-query-shortlist-diagnostic-20260918.json`.

## Cost and interpretation

The new test generated 25,962 base candidates plus 67,878 extra AST candidates, predicted 750,720 candidate/probe output cells, made 3,840 E0 candidate scores and 1,554 scores for each post-query model. Preparation took 185.2 seconds wall time, including 868.3 summed parallel candidate-generation seconds. The source acquisition involved 8,681 verified survivor labels, in addition to historical E0 and candidate-pool acquisition. The final research oracle checked 93,840 candidate labels; deployed one-query and restricted policies would buy 192 and 96 exact output calls respectively.

The independent replay audit passed. It regenerated all 192 tasks and pools, rechecked 750,720 predicted output cells and 1,554 post-query candidate scores per model, reproduced frozen choices and allocations, and re-evaluated all 93,840 final candidate labels. The audit result is `runs/post-query-feedback-transfer-20260918/audit.json`.

The preliminary opened-panel gain did not transfer to these new instances. This does not show that sensor-conditioned ranking cannot work; it shows this specific fixed-top-20 model and training set did not pass a fresh, paired test. It also cannot establish recursive intelligence growth: no later improver used feedback to design a better child improver from the same base and budget.

## Subsequent opened wider-shortlist screen

After the fresh result was opened, a separate development screen trained top-50 survivor models on 19,789 verified labels from the same 1,152 historical source tasks. It preserved E0's no-query choice and changed only the post-query choice. On the now-opened 192-task panel, the top-50 plain and sensor models scored 46 and 47 with one call per task versus E0 47; under the fixed 96 calls, they scored 33 and 35 versus E0 33. On the opened familiar 576-task panel, the sensor model scored 453 versus E0 438 with one call each, but only 381 versus 380 under 96 calls. It did not show a useful restricted-call package gain on changed arithmetic and does not warrant a new transfer test yet. This screen is recorded in `analysis/wide-post-query-development-20260918.json` and is **not fresh validation**.

Run artifacts: `runs/post-query-feedback-transfer-20260918/`; runner: `post_query_feedback_transfer.py`; opened screen: `analysis/post-query-candidate-development-20260918.json`.
