# Seed-improver work checkpoint

The active goal remains open. Stable improver transfer, growth of child improvers, and a supported best seed have not been established.

## Full mixed AST sensor integration passed budgeted system gate

- On six fresh 48-task mixed banks, the prior fixed temperature map scored 140/288 with zero oracle outputs. Widened AST pools plus replay ranker scored 150 with zero outputs; adding one AST output query per task scored 156 with 48 total calls. Paired gains over the zero-query map were positive in all six banks, interval +11 to +20. AST reachability rose 11 to 26/48; the one-query sensor selected 16 of 26. The 288-task audit regenerated pools, 196,016 predicted output cells and 76,630 candidate labels, and passed.
- At 48 calls, fixed minimax scored 157, top-20/random 156, learned allocator 158. Learned-minus-minimax interval −2 to +4 failed improver promotion. This is a supported budgeted fixed sensor component, not a self-improving seed. See `FULL-MIXED-AST-SENSOR-RESULTS-2026-09-18.md`.

## Fixed-total query allocator did not transfer

- A 12-feature ridge model trained on 96 verified query-effect tasks was evaluated on twelve fresh eight-task AST banks at exactly eight oracle outputs per bank. It tied one query per task, 31/96; random and scrambled scored 29, high entropy two-on-four 28, high disagreement two-on-four 24. Learned-minus-static interval −3 to +3 and only one positive bank failed the gate. The 96-task audit rechecked 47,346 candidates, 378,768 predicted output cells, allocations and outcomes, and passed.
- A hindsight allocation ceiling was 40/96, while marginal-value correlations were only 0.18 and 0.11. The current learner reduces some wasted calls but cannot reliably convert them into better choices. See `AST-QUERY-ALLOCATION-RESULTS-2026-09-18.md`.

## Output-query AST sensor: large feedback gain, policy gate failed

- On twelve fresh eight-task AST banks, widened-pool reachability was 57/96. The frozen ranker selected 12 without an oracle output, top-20 entropy selected 36 with one output per task and 46 with two. The one-query gain was positive in every bank; a second query added ten at 96 more oracle calls. The 96-task audit regenerated 386,368 predicted candidate outputs and 48,296 final candidate labels, and passed.
- At equal one-query cost, top-20 entropy 36 versus minimax 29 had only five bank wins, one loss and a 0 to +14 interval, so its method-selection gate failed. This is an effective external feedback sensor with cost, not retained evaluator or improver growth. See `AST-OUTPUT-SENSOR-RESULTS-2026-09-18.md`.

## Full mixed integration of replay specialist failed promotion

- A second full six-mechanism test on six fresh 48-task banks raised reachability 240 to 250/288 with wider AST pools. The fixed temperature map scored 152/288; adding the replay AST specialist scored 155, with gains in only two banks and a 0 to +7 bank interval. The first and replay specialists tied at three AST correct choices each. Global replay specialist use regressed to 122/288. The declared integration gate failed.
- The 288-task audit regenerated pools, 576 choice sets and 118,892 candidate outcomes and passed. Keep the fixed map as the strongest supported zero-query whole-system control; do not promote the specialist gate. See `GATED-AST-REPLAY-INTEGRATION-RESULTS-2026-09-17.md`.

## Verified AST feedback replay improved a second evaluator checkpoint

- A 40-epoch incremental update on 48,596 verified candidate labels from two inspected AST transfer streams raised fresh fixed-pool selection from 7 to 13/96 versus the preceding specialist and zero for the original parent. It gained on five of twelve banks, tied seven, lost none; exact bank-resampling interval +2 to +11. Gains were +3 in each of AST-only and mixed AST streams. Reachability was 49/96. The 96-task/47,546-candidate reconstruction audit passed.
- This is a scoped evaluator update after substantial extra feedback, not an automatically improving improver. The new specialist needs fresh whole-system routing and a matched-cost parent/child improver test. Report `AST-REPLAY-FEEDBACK-RESULTS-2026-09-17.md`; protocol `EXPERIMENT-ast-feedback-replay-update.md`; data `runs/ast-feedback-replay-transfer-20260917/`.

## Fresh mixed-bank gate failed

- A fixed public-block gate preserved the parent on five non-AST mechanisms and used the AST specialist on widened AST pools. Across six new 48-task banks, candidate reachability rose 229 to 245/288, but the gate tied the parent at 135/288; the prior fixed temperature map scored 139. The AST specialist selected zero of 26 reachable AST solutions, versus six on the preceding AST-only transfer. Its positive evaluator result did not replicate in this mixed stream.
- The 288-task audit regenerated every task/pool, 576 choice sets and 118,228 candidate outcomes, and passed. The gate is unpromoted. Diagnose ranking on widened pools and require protected admission and parent/child improver transfer. See `GATED-AST-FEEDBACK-RESULTS-2026-09-17.md`.

## AST feedback edit: scoped evaluator gain, global retention loss

- Widening V67/V73 from cap 128 to 512 raised fresh AST reachability 12 to 26/48. A 60-epoch update on 23,686 verified AST candidate labels then raised zero-query selection on the same wide pools from 0 to 6/48. Five of six fresh banks gained, one tied; exact bank-resampling interval +3 to +9. The 48-task/30,876-label reconstruction audit passed.
- Applying that AST update globally regressed an already inspected stack/mutation/self-edit bank from 143 to 125/192. Retain the parent and test a separately gated specialist on fresh mixed banks. This was a researcher-authored evaluator edit, not improver growth. See `AST-FEEDBACK-GROWTH-RESULTS-2026-09-17.md`.

## Contextual temperature inheritance: failed child-growth gate

- Six fresh six-family parent/child episode pairs compared empty, inherited, scrambled family-conditioned loss-edit tables and fixed controls. Child final scores: empty72/144, inherited73, scrambled71, fixed prior family map74, fixed 0.25=71. Inherited-minus-empty child deltas 0,0,0,+1,0,0 and interval 0 to +3 failed the declared gate. Parent inherited66 vs empty64 and fixed family map68.
- Child final candidate reachability was 119/144; AST reachability 6/24 and all policies scored zero. The 576-task audit regenerated 97,460 candidate programs, 2,304 model choices, all table updates and outcomes, and passed. Report `CONTEXTUAL-LOSS-INHERITANCE-RESULTS-2026-09-17.md`; protocol `EXPERIMENT-contextual-loss-inheritance.md`; data `runs/contextual-loss-inheritance-20260917/`.
- Temperature selection alone offers too little new headroom. Expand the AST candidate set and representation as distinct edit types, with reachability and ranking evaluated separately before another child-improver trial.

## Withheld mechanisms expose contextual edit effects and AST bottleneck

- A no-query frozen transfer over 288 tasks (six banks, six mechanisms) tested temperature 0.25 versus 1.0 and controls. On 144 trained-family tasks, 0.25 scored 105 versus 95; on 144 withheld-family tasks it scored 32 versus 33 for 1.0 and 37 for 0.5. The withheld bank-level interval for 0.25 minus 1.0 was −6 to +4, so the transfer gate failed. Transformation favored 0.5 (22/48) over 0.25 (14); novel operator favored 0.25 (18) over 1.0 (12). AST reachability was 14/48 and every evaluator scored zero.
- The 288-task audit regenerated all pools, 1,728 choices and all outcomes, and passed. Report `TEMPERATURE-WITHHELD-FAMILIES-RESULTS-2026-09-17.md`; protocol `EXPERIMENT-temperature-withheld-families.md`; data `runs/temperature-withheld-families-20260917/`.
- A single global 0.25 evaluator is not the best evidenced seed across all mechanisms. Next test inherited **family-specific** edit effects against empty/scrambled parent improvers on untouched parent and child banks. Track AST candidate reachability separately; temperature selection cannot solve it.

## Incremental query-value feedback failed fresh transfer

- A fixed 18-feature ridge query allocator was retrained from 192 to 384 verified query-effect tasks, with a same-size scrambled-update and duplicated-prior control. On six untouched banks at exactly 95 live oracle output queries per arm, no query scored 155/192, previous learned 175, updated 173, duplicated prior 174, scrambled 171, and fixed top disagreement 174. Updated-minus-previous bank deltas 0,0,0,0,0,-2 and interval −6 to 0 failed the predeclared gate. Candidate reachability 190/192.
- The 192-task audit regenerated every pool, public model choice and updated prediction, query allocation and final outcome; it passed. Report `QUERY-FEEDBACK-UPDATE-RESULTS-2026-09-17.md`; protocol `EXPERIMENT-query-feedback-update-transfer.md`; data `runs/query-feedback-update-transfer-20260917/`.
- The new feedback shifted queries toward mutation tasks, but the next bank's baseline mutation accuracy rose from 34/66 to 49/66. This suggests a need for within-bank adaptation and protected rollback, not just accumulation of global query-effect labels.

## Learned query-value evaluator: small lead, failed growth gate

- At exactly 95 external output queries on six untouched banks, the frozen temperature-0.25 ranker scored 138/192 without queries, random allocation 156, fixed uncertainty 161, fixed top disagreement 169, and a learned 18-feature query-value allocator 172. Learned minus strongest fixed by bank was 0,+1,+1,-1,+1,+1, with six-bank interval −1 to +6; the predeclared growth gate failed. Candidate reachability was 190/192.
- The 192-task audit regenerated pools, public plans, allocations and every oracle-conditioned final result. Report `SHARP-QUERY-VALUE-TRANSFER-RESULTS-2026-09-17.md`; protocol `EXPERIMENT-sharp-query-value-transfer.md`; data `runs/sharp-query-value-transfer-20260917/`. Fixed top disagreement is the supported cost-aware query component; learned allocation is unpromoted.
- On inspected development tasks, a plain sharp/context score blend regressed, while a two-model disagreement probe gained from 143 to 161 using 95 queries and full-pool reranking reached 166. Fixed top disagreement reached 172 at the same budget, so the model-pair arbitrator was not promoted. Development data: `analysis/sharp-context-integration-development.json`, `analysis/sharp-query-allocation-development.json`.

## Fixed-catalog inheritance trial: parent benefit, child failure

- Six fresh 32-task parent/32-task child episode pairs compared an empty loss-edit table, a 64-effective-task inherited table, a scrambled table, and fixed temperature controls. Parent final scores: empty64/96, inherited71, scrambled66, fixed 0.25=71. Child final: empty70/96, inherited69, scrambled64, fixed 0.25=69. Inherited-minus-empty child deltas were 0,0,0,0,-1,0, so the predeclared child-improver gate failed. Prior-weight/decay development replay never exceeded 70/96 child.
- The 384-task audit regenerated all pools, recomputed 1,152 model selections, replayed all policy tables and final outcomes, and passed. Protocol `EXPERIMENT-loss-catalog-inheritance.md`; report `LOSS-CATALOG-INHERITANCE-RESULTS-2026-09-17.md`; data `runs/loss-catalog-inheritance-20260917/`.
- The inherited table offered initial label efficiency but merely reproduced the fixed 0.25 choice; the empty policy caught up after one verified bank. The next seed needs contextual effect prediction or new edit creation, not more tuning of this global prior.

## Sharper listwise loss: confirmed evaluator edit

- Changing only listwise loss temperature from 1.0 to 0.25, with the same 31,500 verified source labels and 120 epochs, scored **143/192** on six untouched banks versus the original listwise evaluator **130/192**, temperature 0.5 **137/192**, and E192 **98/192**. The 0.25 edit won five banks and tied one against the original; six-bank resampling interval **+6 to +19**. Gains occurred in stack, mutation, and self-edit mechanisms. Candidate reachability was 190/192.
- Full 192-task reconstruction audit passed: all pools regenerated, 768 temperature decisions and all outcomes recomputed. Protocol `EXPERIMENT-temperature-ranker-transfer.md`; report `TEMPERATURE-RANKER-TRANSFER-RESULTS-2026-09-17.md`; data `runs/temperature-ranker-transfer-20260917/`.
- This is a supported researcher-authored **evaluator edit**. It does not show the improver learned to propose, select, or transmit better edits. The seed-improver catalog should include training-objective changes and compare inherited edit knowledge with an empty/scrambled policy under matched feedback, then test child improvers.
- A source-only two-fold edit selector chose temperature 0.25 but tied 0.5 at 125/192 held-out tasks and beat temperature 1.0 by just one; ten fits cost 425 seconds. Sharper generated temperature edits 0.1875, 0.125, and 0.0625 increased source fit but regressed on inspected transfer tasks. See `LOSS-CATALOG-IMPROVER-DEVELOPMENT-RESULTS-2026-09-17.md`. This motivates a cost-aware inherited effect table and protected admission, not unbounded sharpening.

## Direct feedback update pilot

- Six development-only one-bank-to-next-bank updates of the frozen listwise-120 ranker tested four learning rates/epoch scopes, scrambled feedback, and continued source training. Fixed base scored 130/192 transfer tasks; a ten-epoch update tied, other verified-feedback updates scored 126–129, scrambled labels tied, and continued source training scored 131. The extra 30,676 candidate labels did not create a transferable gain. See `INCREMENTAL-RANKER-FEEDBACK-DEVELOPMENT-RESULTS-2026-09-17.md` and `analysis/incremental-ranker-feedback-development.json`.
- Next test a source-cross-validated edit search over training objectives or model architectures with protected admission and matched optimization cost. A later improver parent must then produce a better child improver, not only a stronger fixed evaluator.

## Confirmed nonlinear evaluator upgrade, pending improver integration

- A task-level 175→32→1 listwise ranker trained on E192's same 31,500 verified source labels scored **130/192** on six untouched banks versus E192 **105/192**, the strongest tested context blend **117/192**, and a pairwise combination **115/192**. It beat E192 on all six banks; the exact six-bank resampling interval for the total difference was **+17 to +33**. Checkpoints 40/80/120 scored 108/126/130, so most of the incremental gain arose by epoch 80. The gain concentrated in self-edit transition (49/60 versus E192 24/60); stack and mutation were approximately tied.
- The 192-task audit regenerated every candidate pool, recomputed 576 listwise choices, and verified every final result. Source label count matched E192. A same-machine timing rerun took 25.8 seconds for 120 GPU epochs plus source checkpoint scoring versus 1.57 seconds for an E192 logistic fit. Protocol `EXPERIMENT-listwise-evaluator-transfer.md`; report `LISTWISE-EVALUATOR-TRANSFER-RESULTS-2026-09-17.md`; data `runs/listwise-evaluator-transfer-20260917/`.
- This is a supported **evaluator** component, not evidence that an improver learned to choose or create better edits. The next test must cross this fixed ranker with protected edit-admission feedback and then compare parent improver checkpoints on an identical base and a second untouched bank.
- A leave-one-bank-out development selector used prior verified outcomes plus 16 admission tasks to switch between listwise-120 and the context blend by family. Four admission weights all scored 61/96 final tasks versus 68/96 for fixed listwise. It was rejected before fresh confirmation. See `analysis/listwise-selector-development.json` and the listwise report.
- A within-task score blend yielded at most +3/192 on the inspected bank; leave-one-bank-out family-weight selection tied listwise at 130/192. Neither edit supports a fresh improver gain. Also, listwise's +13 aggregate over the context blend has a bank-resampling interval from 0 to +26, so its clear transfer claim is against E192, not a statistically settled win over the strongest context control.

## Closed-catalog seed-improver pilot

- On 12 already inspected 16-admission/16-final episodes, fixed context expert and blend each scored 108/192 final tasks; an admission-gated chooser over six evaluator states scored 105 at margin 1, 104 at margin 2, and 99 at margin 3. The per-episode hindsight best was 115. This development pilot did not show an improver gain and was not promoted to a fresh trial.
- Report `CATALOG-GATE-DEVELOPMENT-RESULTS-2026-09-17.md`; data `analysis/catalog-gate-development.json`. Next expand the edit vocabulary to produce materially different evaluators, then retest selection at matched compute. E192 remains the confirmed control.

## Top-choice edits and context experts

- A global update targeting E192's 89 highest-ranked false positives regressed on source and two inspected target sets at every tested anchor strength. Three public-context expert models trained on the same labels showed mixed development results. Their 50/50 blend scored 110/192 on six fresh banks versus E192 101, but its bank-level interval included zero and it tied the pure experts; the predeclared promotion gate failed. All 192 frozen decisions passed reconstruction audit.
- Report `TOP-CHOICE-EDIT-RESULTS-2026-09-17.md`; protocol `EXPERIMENT-context-expert-transfer.md`; data `runs/context-expert-transfer-20260917/`. E192 stays the confirmed evaluator control. The blend is an unpromoted edit candidate; neither result proves improver growth.

## Edit-effect and two-evaluator integration

- Exact one-task training-edit effects were measured across two inspected source-target episodes. Public-feature predictors and direct prior-bank replay transferred Brier or AUC effects, but not top-choice correctness effects. A 7,000-label policy using inherited Brier effects scored 87/192 on inspected targets versus 97/192 for source order. A sensor-gated development pilot kept E192 and tied its 48/96 final score while hindsight best gained one.
- A random-pairwise evaluator had better candidate AUC but nearly tied E192 top-choice accuracy. The two components were complementary, with an oracle union of 237/384 on inspected tasks. A router trained on their verified disagreements reached 102/192 on six fresh banks versus E192 95 and equal-weight combination 101, but won only four banks; the predeclared growth gate failed. Its 192-case audit passed.
- Report `EDIT-EFFECT-AND-ROUTER-RESULTS-2026-09-17.md`; router protocol `EXPERIMENT-evaluator-router-transfer.md`; data `runs/evaluator-router-transfer-20260917/`. E192 remains the confirmed evaluator component; router is unpromoted. Need a top-choice-focused edit and later-parent-to-better-child-improver test.

## Same-base 7,000-label improver test

- A fresh 192-source-task / six-bank 192-target-task comparison froze six acquisition rules at exactly 7,000 candidate labels each. Source order produced a child evaluator scoring 95/192, random 96, low-confidence 83, uncertainty 82, small-pool 89, and three-stage low-confidence 97. The development-favored low-confidence rule regressed by 12 versus order and failed its predeclared transfer gate. The iterative rule exceeded order by two and random by one, with an interval including zero.
- E192 scored 102 on the same target but used 31,500 earlier labels, so it is a reference rather than a matched-cost winner. The 192-source/192-target reconstruction audit passed. Protocol `EXPERIMENT-improver-acquisition-transfer.md`; report `IMPROVER-ACQUISITION-TRANSFER-RESULTS-2026-09-17.md`; data `runs/improver-acquisition-transfer-20260917/`.
- Next estimate source-task marginal value for future candidate ranking from disjoint development cases. Test the resulting acquisition policy at matched labels on new source-target episodes. Parent-to-child improver growth remains unmeasured.

## Supported evaluator checkpoint, pending improver integration

- Six fresh 32-task banks across stack, mutation, and self-edit mechanisms confirmed retained structural-evaluator growth on fixed pools: E0 36/192, E48 90, E96 89, E192 99, versus within-task label-scrambled 72. E192 beat E0 in all six banks; the predeclared bank-level growth screen passed. One common output query raised E192 to 160/192 versus E0 115. Candidate Brier error fell from 0.549 to 0.175.
- The 192-case reconstruction audit passed. Protocol `EXPERIMENT-mixed-evaluator-checkpoint-transfer.md`; report `MIXED-EVALUATOR-CHECKPOINT-RESULTS-2026-09-17.md`; data `runs/mixed-evaluator-transfer-20260917/`.
- E192 is a supported evaluator component for this synthetic three-family distribution. It is not a proven seed improver. Next compare improvers on an identical base and test whether a later improver creates a better child improver on new banks while charging source-label cost.

## Cost-aware sequential evaluator transfer

- Six fresh 64-task AST banks tested a learned decision to buy a second oracle output after seeing the first. At 480 output queries per policy, learned scored 269/384, fixed entropy allocation 261, and fixed top-disagreement 270. The learned rule won only three banks over entropy and failed its predeclared interval and bank-win screen. It also trailed the strongest fixed control by one task.
- One query per task scored 239/384, while two on every task scored 293/384 at 768 queries; candidate reachability was 338. All 384 allocation decisions and final outcomes passed reconstruction audit. The next priority is prospective mechanism variation, then same-base improver and child-improver tests.
- Protocol `EXPERIMENT-sequential-evaluator-budget.md`; report `SEQUENTIAL-EVALUATOR-BUDGET-RESULTS-2026-09-17.md`; data `runs/sequential-budget-transfer-20260917/`.

## Active evaluator transfer check

- On six fresh 64-task AST banks, the initial evaluator solved 179/384. At one oracle output query per task, the learned pairwise probe policy solved 252/384 and fixed minimax solved 256/384. The learned policy lost or tied on every bank, so its small 384-task development gain did not transfer.
- A fixed sequential weighted-entropy policy using two output queries solved 301/384. Candidate reachability was 353/384. This is a measured within-task feedback gain at higher oracle cost, not retained evaluator or improver growth.
- All 384 decisions and outcomes passed a reconstruction audit. Protocol: `EXPERIMENT-active-evaluator-transfer.md`; report: `ACTIVE-EVALUATOR-TRANSFER-RESULTS-2026-09-17.md`; data: `runs/active-evaluator-transfer-20260917/`.
- Next measure learned allocation/stopping of sequential queries against fixed controls at matched total queries on untouched banks. Then resume same-base and child-improver comparisons.

## New low-budget control test

- Six episodes `runs/seed-low-9000` through `runs/seed-low-14000` completed, with all six audits passed (268 candidate-source calls, ten arms, five checkpoints each, exactly 64 improvement labels per arm). One older-bank end-to-end contract test passed.
- I0 matched the fixed disagreement/disagreement/uncertainty/combined schedule in **all actions and final predictions**, scoring 241/288. I4 matched fixed uncertainty in all actions and final predictions, scoring 244/288. Thus the apparent learned-policy gains are explained by fixed tactic choices in this case distribution.
- Full I0 utility scramble scored 240/288; balanced-table B0 scored 242/288. Neither passed the declared I0 comparison screen. B0 reduced first-edit regret but worsened mean absolute utility prediction error and did not transfer to a consistent final gain.
- Initial behavioral memory scored 243/288; candidate reachability was 247/288. Changed arithmetic was reachable on only 36/72 tasks. No adaptive improver or seed is promoted.
- Protocol `EXPERIMENT-seed-low-budget-control.md`; report `SEED-LOW-BUDGET-RESULTS-2026-09-17.md`; machine summary `analysis/seed-low-budget-summary.json`. All preparation/run/audit processes returned exit 0; no process remains live.

## New same-base improver test

- Six cold-start transfer episodes `runs/seed-transfer-3000` through `runs/seed-transfer-8000` completed. All six replay audits passed (268 candidate-source calls, 12 arms, five checkpoints each). One end-to-end same-base contract test passed.
- Declared I4 versus I0 screen **failed**: paired final differences 0, -1, 0, 0, 0, 0; I4 241/288, I0 242/288; I4 won zero of six episodes.
- Feedback improved I0's evaluator from 226 to 242/288. Initial behavioral-only evaluator scored 236; candidate reachability was 243/288. The changed-arithmetic panel reached only 36/72.
- I0 exceeded empty (232) and every fixed single-tactic control, but the difference from empty was concentrated in two episodes. Frozen I4 and scrambled appended knowledge both scored 241; online I4 scored 240. I0 is only an unpromoted observed candidate, not a proven optimal seed.
- Protocol `EXPERIMENT-seed-improver-transfer.md`; detailed report `SEED-IMPROVER-TRANSFER-RESULTS-2026-09-17.md`; machine summary `analysis/seed-transfer-summary.json`.
- The six preparation, six run and six audit commands returned exit 0. No transfer process is running; use the saved artifacts rather than restarting any episode.

## Completed and verified

- Source search audit passed: 144 candidate-source calls, 15 trajectories, 75 checkpoints.
- First confirmation audit passed: 240 candidate-source calls, ten controller arms, five checkpoints. Evaluator gains 43 to 47/48 were blocked by a separate deployment margin; oracle-label budgets differed.
- V2 fixes admission/deployment consistency and matches 48 new candidate labels per round, four rounds. Six focused contract tests passed.
- Original v2 and both independent whole-episode replications completed; all three audits passed, each replaying 276 candidate-source calls, 32 policies and five checkpoints.
- Primary aggregate: 136 to 142/144; per-episode gains 0, +6, 0.
- Best observed inherited policies: 143/144, versus initial behavioral evaluator 139/144 and best fixed feedback policy 142/144. Online and frozen inherited controllers tie at final. Observed winner is exploratory and unpromoted.
- Original plus replications have 143 reachable tasks of 144. The third episode begins at its reachable ceiling.
- No processes from this experiment remain running. Sessions 55361, 71651, 85978, 53800, 70002, 20231 and 64362 returned exit 0; do not restart them.

## Current report and data

- `SEED-FEEDBACK-REPLICATION-RESULTS-2026-09-17.md`
- `analysis/seed-replication-summary.json`, rebuilt by `summarize_seed_replications.py`
- `runs/seed-integration-v2-20260917`
- `runs/seed-v2-replica-1`
- `runs/seed-v2-replica-2`

Preserve archived source and run artifacts. The exported `output/seed-improver-candidate/state.json` remains the earlier source candidate, not a silently promoted post-hoc winner.

## Next necessary work

1. Design cases with prospectively varied task mechanisms and enough reachable but evaluation-ambiguous candidates; test whether the best feedback tactic actually changes by context. Reuse matched first-edit observations to train a budget-specific edit evaluator, then transfer it to untouched mechanisms.
2. Raise candidate coverage on new mechanisms, with an independently declared generator change and separate generator/evaluator endpoints. Avoid filtering tasks by observed final correctness.
3. Test later-parent-to-better-child-improver performance separately from better child solvers/evaluators.
4. Confirm any newly selected seed on fresh independent episodes before promotion. Preserve the null and negative comparisons.

Keep accepted updates, useful updates, task losses and costs separate. Probability-error gains or more accepted changes alone are not intelligence growth.
