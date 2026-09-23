# Feedback-trained shifted-survivor evaluator

Status: **a scoped evaluator component passed fresh transfer; incremental improvement from the second feedback batch did not pass its separate gate.** No growing child improver was demonstrated.

## Frozen test

The [protocol](EXPERIMENT-shifted-survivor-evaluator-transfer.md) froze 24 new shifted-AST banks, seeds 903300-903323 (192 tasks). The candidate pools, old AST ranker, E0 zero-call choice, fixed probe, protected cheap four-call locations and final hidden examples were identical across policies. Each post-query evaluator selected a candidate consistent with the one exact output observed on a queried task. All tasks, pools, probe predictions, candidate choices, call locations and model files were hashed before final correctness labels opened.

The first shifted model was a plain-feature top-100 survivor ranker trained on **1,527 verified survivors from 96 earlier shifted tasks**. The later checkpoint used 4,862 verified survivors from 288 shifted tasks under the same model class and fitting rule. Task-wise scrambled added labels, duplicated earlier data, and an equal-label sensor-feature model were controls. A familiar-trained plain top-50 ranker was the predeclared cross-domain control.

| Policy after a call | Correct / 192 at 96 frozen calls | Correct / 192 with 192 calls |
| --- | ---: | ---: |
| E0 | 44 | 56 |
| Familiar-trained plain top-50 | 44 | 54 |
| Shifted 96-task plain top-100 | **61** | 80 |
| Shifted 288-task plain top-100 | **67** | **87** |
| 288-task scrambled-added plain top-100 | 57 | 77 |
| Duplicated-earlier plain top-100 | 60 | 78 |
| 288-task sensor-feature top-100 | 62 | 80 |

The 96-task checkpoint gained **+17** over both E0 and the familiar top-50 model at 96 calls. It won 15 of 24 banks and lost one against each; paired bank interval **[+10,+24]**. It passed the declared component gate. All policies used the same 96 calls and E0 choice without a call, so this is a gain in evaluating surviving candidates on the fixed pool. The output-call cost is matched; source acquisition and model-scoring costs are not.

The later 288-task checkpoint gained **+6** over the earlier one at 96 calls, interval **[+1,+12]**, with no losing banks, and beat scrambled by +10 and duplicate by +7 with positive interval lower endpoints. But only **four** of 24 banks improved, below the predeclared eight-bank requirement. Its *incremental feedback gate failed*. It is a promising higher-scoring checkpoint in this sample, not a promoted claim of stable incremental growth. The sensor-feature model scored **five fewer** than the matched-label plain model, interval **[-9,-1]**; its feature claim failed.

Pool reachability was **109/192**; old top-20, top-50 and top-100 recall was **68, 80 and 96**. The later model selected 87 correct programs with one call per task, leaving nine top-100 reachable tasks unresolved. Search and shortlist limits remain measurable even with the stronger evaluator.

## Matched-width attribution after the test

After opening the frozen result, a separate development diagnostic trained the same plain top-100 model class on **35,291 verified survivors from 1,152 familiar tasks**. On these already opened shifted target banks, it scored **45/192** at the same 96 calls, one more than E0 and **16 fewer** than the 96-task shifted model; the matched-width difference favored shifted training with paired interval **[+9,+23]**. This diagnostic was not part of the preregistered gate, but it shows that widening the action shortlist and using the same model class alone did not explain the gain. Relevant shifted-task feedback was essential on this panel. See `analysis/familiar-top100-survivor-diagnostic-20260918.json`.

## Cost, audit and scope

The fresh test generated 26,476 base candidates plus 67,208 extra AST candidates, predicted 749,472 candidate/probe output cells, made 3,840 E0 candidate scores, and had 3,264 surviving top-100 rows available to each shifted model. A single shifted model would score those 3,264 rows when all 192 tasks are queried; its deployed 96-call scoring cost depends on which tasks receive calls. The historical feedback acquisition was 1,527 survivor labels for the first checkpoint or 4,862 for the later one, beyond E0's earlier source training. The final research oracle rechecked **93,684 candidate labels**; each budgeted policy bought **96 exact outputs**.

The independent replay passed. It regenerated all 192 tasks and pools, rechecked 4,862 source survivor labels, 749,472 output predictions, every frozen candidate choice and 93,684 final candidate labels. See `runs/shifted-survivor-evaluator-transfer-20260918/audit.json`.

This confirms a **feedback-trained evaluator improvement for new instances of the same shifted-AST generator**. The models, update rule and test were researcher-authored; a positive feedback loop in the improver still requires a later improver to produce a stronger child improver from the same base and resource budget on a further untouched bank.

An opened familiar-AST check then showed why the specialist cannot replace E0 globally. On 96 familiar AST tasks with one identical output call each, E0 solved **36**, the 96-task shifted specialist **25** and the 288-task specialist **24**. The first specialist minus E0 was **-11**, interval **[-20,-2]**. The AST Unicode cue is shared across both task generators, so a simple family route cannot distinguish them. A broader seed must learn a public-evidence applicability rule and verify it on mixed fresh banks before deploying the specialist. See `analysis/shifted-specialist-familiar-diagnostic-20260918.json`.

Run: `runs/shifted-survivor-evaluator-transfer-20260918/`. Runner: `shifted_survivor_evaluator_transfer.py`.
