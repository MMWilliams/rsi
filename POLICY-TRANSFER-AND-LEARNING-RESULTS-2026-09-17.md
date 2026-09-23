# Policy transfer and learning-capability results

## What was tested

Two independently audited synthetic task lanes were tested. On the semantic string-transformation lane, a seven-feature AST ranking genome plus four source weights evolved on 12 development tasks, passed or failed a 12-task admission gate, and was frozen before transfer labels were opened on three new 12-task banks. Candidate pools combined V67, V70, V72 and V73 with eight visible examples and 13 hidden examples per task. The corrected sealed run is `runs/policy-transfer-20260917b`; its independent audit regenerated 240 candidate-source calls over 60 tasks, recomputed 65 policy modes and checked 89 sealed artifacts. The earlier `runs/policy-transfer-20260917` has the same scores but graded transfer candidates before the policy freeze. It is exploratory only; the corrected run is the reported result.

On the encoded stack-task lane, the retained V86 lineage library was replayed on two new 24-task banks, seeds 203215 and 203216. Each task had 40 visible and 13 hidden examples. The second bank tested a router declared after seeing the first bank: choose direct V73 grammar when it has a visible-fitting candidate; otherwise choose the V86 encoding-adaptive lineage. Both archives passed independent candidate and oracle replay (72 source calls and 90 sealed artifacts each). The policy is researcher-designed and the four encoding hypotheses are fixed.

## V67 + V73, with an evolving ranker

Counts below pool the three new transfer banks. Each bank had two tasks from each of six synthetic families; totals are descriptive.

| Semantic candidate set | Frozen ranker | Evolved/selected ranker | Oracle-reachable tasks |
| --- | ---: | ---: | ---: |
| V67 alone | 16/36 | 13/36 | 19/36 |
| V73 alone | 21/36 | 21/36 | 21/36 |
| V67 + V73 | **30/36** | 29/36 | 33/36 |
| V70 + V72 (representation group) | 10/36 | 11/36 | 13/36 |
| V67 + V70 + V72 + V73 | 21/36 | 29/36 | 33/36 |

The V67+V73 learned ranker passed admission at 11/12 versus the frozen ranker's 10/12, yet transferred at 29/36 versus 30/36. On paired transfer tasks it gained two and lost three. V67 alone also regressed, 16 to 13. Thus **candidate complementarity transferred; the improved ranking policy did not**. The union beat the stronger single arm V73 by eight tasks, but it generated candidates from both sources. Across all 60 source and transfer tasks, V67 generation consumed 200.6 seconds and V73 3.5 seconds, so the union was roughly as expensive as V67 and far more expensive than V73. These are sequential process timings, not a controlled hardware cost study.

The union's 33/36 reachability leaves four mistakes to ranking and three tasks with no correct candidate. V67 alone could reach every AST-family task (6/6) but its selected ranker solved none; the union selected 2/6. That is a concrete ranking bottleneck. V73 covered mutation and self-edit tasks (6/6 each), while V67 covered transform tasks (6/6); the two generated different useful programs.

## Top-five policy and improvement types

The top-five set from the previous ranking was V67, V70, V72, V73 and V86. `unified_top5_policy.py` provides one typed visible-only dispatcher: it uses the four compatible sources and their learned weights frozen before transfer for semantic tasks, and V73 direct grammar plus V86 adaptive lineage for encoded tasks. `validate_unified_top5.py` replayed its choices against 36 audited semantic and 24 audited encoded decisions, then regenerated one live task in each lane. Task lane must be supplied by the caller. Accuracy is reported by lane because the two grammars, task generators and compute budgets differ.

Adding V70 and V72 to the semantic pair raised the frozen ranker's score from 21/36 to 29/36 when the top-four ranker evolved, but the final 29/36 exactly tied the evolved V67+V73 pair on every task. The four-source pool had the same 33/36 oracle reachability as the pair, so the representation group supplied no new reachable solution on these banks. The two extra sources consumed another 49.8 seconds of candidate generation across all 60 tasks. A top-five integration was implemented and tested; no incremental semantic gain was established over the narrower pair.

The compatible selection/grammar group (V67+V73) scored 29/36 with evolved ranking; the representation group (V70+V72) scored 11/36. This comparison is confounded by task families and unequal computation; it ranks these bundles on this bank, not a general superiority of one improvement type. The best measured semantic score was the **frozen V67+V73 ranker, 30/36**. A subsequent policy should gate the additional sources and ranking edits with stronger transfer evidence before promotion.

## Explicit learning and representation expansion

| Mechanism | Independent observation | What it establishes |
| --- | --- | --- |
| V67 ranking-weight evolution | Development improved 6/12 to 7/12, but transfer fell 16/36 to 13/36 | The system can modify ranking weights; this edit did not transfer here. |
| V73 editable grammar | 21/36 selected and reachable on the semantic transfer banks | Strong candidate generation in the fixed SAFE_OPS grammar; no new primitive was invented in this test. |
| V70+V72 stack/mutation representation | 11/36 selected, 13/36 reachable | Some distinct programs, but no added reachability beyond V67+V73 in the four-source pool. |
| V86 encoding hypotheses, fresh seed 203215 | Identity lineage 7/24; adaptive lineage 14/24; direct grammar 17/24 | Visible-example adaptation recovered seven bit-splice tasks, while direct grammar handled ten fold-parity tasks. |
| V86 encoding hypotheses, fresh seed 203216 | Identity 5/24; adaptive 17/24; direct 12/24; fixed combined router **24/24** | The two sources have complementary coverage and a visible-only availability rule transfers to a new bank. |

On seed 203215, adaptive solved all 7/7 `bit_splice` tasks and direct grammar solved all 10/10 `fold_parity` tasks. On the prospectively routed seed 203216, the combined policy chose direct grammar on 12 tasks and adaptive lineage on 12; both groups were 12/12. The combined proposer spent about 21.6 seconds generating those two sources, versus 18.0 seconds for adaptive alone and 3.6 for direct alone. This is a small closed synthetic domain; the 24/24 ceiling cannot support extrapolation beyond it.

“Learning something new” is operationally limited here to changed scoring weights or a better choice among already authored representations and grammar operations. No experiment measured awareness, subjective experience, general intelligence growth, autonomous language acquisition, or invention of a primitive outside the fixed catalogs. The strongest improvement seen in this study is **composition of complementary candidate generators**, followed by a simple source-availability selector on the encoded lane. It is a useful systems result, not evidence of open-ended recursive self-improvement.

## Next discriminating test

Freeze the best measured semantic pair as the control. On fresh banks, train a ranker on candidate behavior and task-visible features, require a strict admission improvement over that pair, and compare at matched generation time. For the encoded branch, test an encoding absent from the four-hypothesis catalog; a gain there would distinguish representation invention from choosing among known transforms. Keep the hidden oracle outside the writer's access and re-audit every candidate and policy decision.

## Archives and checks

- `runs/policy-transfer-20260917b/`: corrected semantic run; audit passed, 89 artifacts, 240 candidate-source replays.
- `runs/encoding-transfer-20260917/`: fresh V86 transfer; audit passed, 90 artifacts, 72 candidate-source replays.
- `runs/encoding-combination-20260917/`: prospectively tested fixed aggregation rule; audit passed, 90 artifacts, 72 candidate-source replays.
- `validate_unified_top5.py`: passed 36 semantic and 24 encoded policy-decision replays, plus one live task per lane.
