# Measuring growth in the evaluator and improver

## Root cause of the improver-growth failures, 2026-09-20

**The improver-growth gates in this file were run on an environment that cannot
express the result they test for.** Banks are drawn i.i.d. from a fixed family
mix, so the optimal action is a constant. Measured on the audited
region-acquisition transfer, fixed regret, the entire value available to a
perfectly context-conditioned policy over the best constant policy, is **+6 and
+12 per 576 tasks**, and a policy fitted on eleven banks beats one fitted on a
single bank by **+1 and -3**. Against a twelve-bank interval half-width near 9,
no learner can demonstrate growth at any action space, and larger banks would
shrink the residual noise that fixed regret is made of, making the result *less*
measurable rather than more. See `ACTION-SPACE-STATIONARITY-2026-09-20.md`.

This does not retract any evaluator result. Evaluator growth passed again on
fresh banks (+49/576, twelve of twelve banks, interval +37 to +62) and does not
require non-stationarity: building better components is orthogonal to whether
the best component varies by instance.

It does mean the roughly forty recorded improver-growth failures below are
**weak evidence about improver intelligence** and strong evidence about
experimental design. They are retained unchanged as the record of how the
diagnosis was reached.

Two preconditions now gate every future improver experiment, defined in
`TECHNICAL-DESIGN-EXPERIMENTATION-2026-09-20.md`:

- **P2, power.** Oracle headroom over the strongest fixed control must exceed
  +20 per 576 tasks on opened development.
- **P2b, non-stationarity.** Measured fixed regret must exceed +20 per 576
  tasks, and the dependence must be predictable from public instance features.
  Fixed regret is cheap and is computed for every candidate environment before
  any improver is built for it.

**Update, 2026-09-21 (later): the construction claim below is WITHDRAWN.** An out-of-fold and capacity-matched audit on both frozen replications found a single 60-leaf pooled model beats the built system by 50 and 36 at 24 banks, and in-sample router fitting inflated replication one by +14. E3 crosses zero or is negative against every baseline; only E2 ("more data helps") survives. See the withdrawal section of `CONSTRUCTION-IMPROVER-RESULTS-2026-09-21.md`. The original text follows for the record.

**Original, superseded:**
The routing result below tested an improver choosing among specialists trained
outside the experiment. A second, stronger experiment removed that: the improver
receives verified history banks and nothing else, computes the latent complexity
partition from its own labels, trains every specialist and the pooled model,
fits its own router, and deploys. Nothing is inherited.

Against the strongest free alternative, one pooled model on exactly the same
history: **E1 +29 and +26** (intervals +12 to +50, +5 to +46); **E2 +45 and +49**,
twelve of twelve banks in both; **E3**, the gate that separates a better improver
from simply more data, **45 against pooled 21** and **49 against pooled 29**,
margins **+24 and +20**. Both independent audits passed with zero failures,
reconstructing 3,456 tasks and 323,184 labels and verifying the cached feature
matrices. A five-fold rotation on opened panels passed both development gates in
5 of 5 folds. See `CONSTRUCTION-IMPROVER-RESULTS-2026-09-21.md`.

Two results are explicitly *not* claimed. **E4, monotonicity, failed in
replication two**: built dips from 362.7 at sixteen banks to 358.0 at
twenty-four, and the rotation agreed at four of five folds. Growth is real and
replicated in aggregate and is **not strictly monotone in history size**.
**Recursive child-improver growth failed** and its cause was screened: a parent
transmitting a partition scheme buys +1 to +13, below the +20 bar, so no parent
can grow through that state. See `RECURSIVE-GROWTH-2026-09-21.md`.

The remaining purity gap is that the partition *rule*, bin edges on
first-correct rank, is researcher written; the improver computes the partition
and trains every model but did not invent the rule.

**Update, 2026-09-21 (last): verifier growth is within-distribution only.** Under leave-one-family-out the 60-leaf pooled evaluator is worse than E0 on every held-out mechanism (716 against 1020 over six families, every interval negative); its in-distribution gain, +174, is smaller than its transfer gap, +478. Every transfer number in this file is instance-level. Under the definition of intelligence growth adopted in `PROGRAMME-TARGET-INTELLIGENCE-GROWTH-2026-09-21.md`, no growth of any kind is demonstrated. Any future evaluator claim must report held-out-mechanism performance beside in-distribution performance and must not regress below the base on the held-out mechanism. See `MECHANISM-HOLDOUT-VERIFIER-2026-09-21.md`.

**Update, 2026-09-21 (final): the routing claim below holds as stated and is DOMINATED.** A single 60-leaf pooled model on the same 24 history banks beats the routed system by 35 and 29, and by 62 and 37 with the specialists' source labels, every interval negative (`runs/complexity-improver-confirmation*/capacity_check.json`). The complexity-partition environment fails P2d against a 120-leaf pooled default (`analysis/partition-rescreen-capacity-20260921.json`). With model capacity in the adversarial default set, **no RSI-relevant improver growth is demonstrated in any form**; verifier growth is strengthened. The original text follows for the record.

**Original, superseded:**
Two frozen replications of `EXPERIMENT-complexity-improver-confirmation.md`, on
banks generated after the protocol was hashed, both pass both gates. C1, the
large-history router against the zero-knowledge default: **+22** (interval +6 to
+38) and **+23** (interval +4 to +42). C2, large history against the *expected*
small history: **+36** (interval +19 to +51) and **+47** on twelve of twelve
banks (interval +33 to +64). Both learning curves rise strictly with history
size. Both independent audits pass with zero failures, reconstructing 3,456
tasks and 322,844 candidate labels and reproducing every curve point exactly.
See `COMPLEXITY-IMPROVER-RESULTS-2026-09-21.md`.

The environment that made it measurable partitions specialists by **latent
solution complexity** rather than by visible mechanism family. It is the first
action space to clear P2c and P2d together: default regret +123, +101 and +89
against the most-confident rule, with a held-out selector beating that rule by
+19. Scope: this is improver **routing** over frozen specialists, not specialist
**construction**, and recursive child-improver growth remains untested.

**Superseded finding, retained for the record: the nine-space infeasibility
result.** The Beta(0.4, 0.4) generator was
constructed and audited; fixed regret rose to +40 to +67 on generated banks
against +7 to +11 on balanced controls, so P2b was satisfied. Improver growth
still failed, and screening seven action spaces against four preconditions
showed why: two further conditions bind.

**P2c, default regret**: the best *zero-knowledge* rule must be beatable. It is
not here. "Trust whichever specialist is more confident" needs no history and
beat a threshold learned from twelve banks by 4 in one replication while losing
by 2 in the other, both intervals crossing zero.

**P2d, learnability**: the residual must be capturable by a policy fitted on
held-out banks. Two action spaces cleared P2c at +38 to +55 and both failed
here, by -9, -18 and -6.

Nine action spaces failed at least one of the four before a tenth succeeded.
Within those nine the benchmark is structurally hostile: mechanisms partition cleanly, specialists transfer poorly
across them, and more data monotonically helps, so "use the specialist matching
this task's mechanism, trained on the most data" is near-optimal and writable
with zero labels. See `IMPROVER-GROWTH-FEASIBILITY-2026-09-20.md`.

Roughly forty prior improver gates were therefore measuring an environment
property, against baselines weaker than a free hand-written rule. That is now a
set of preconditions rather than a pattern to be rediscovered.

The originally proposed environment, retained here for the record:
varying the familiar/shifted mechanism share *between* banks lifts fixed regret
from **2.9** under the current balanced design to **38 to 83**, because the
shifted model scores +26 on shifted tasks and **-14** on familiar ones, so the
wrong action harms. Family-mix heterogeneity does not qualify (at most 16.8),
because every region specialist helps and none harms. See
`MECHANISM-HETEROGENEITY-ENVIRONMENT-2026-09-20.md`.

---


Owner priority: improvements in the evaluator and improver are the primary research outcomes. Solver accuracy is supporting evidence. This document defines the measurement rules and records scoped experimental updates without revising archived gates.

## Evidence ledger and current seed recommendation

The [evidence ledger](SEED-IMPROVER-EVIDENCE-LEDGER-2026-09-18.md) now ranks the tested components on separate evaluator, action, cost and child-improver axes. The strongest defensible seed is task-level listwise ranking with the dual-specialist lower-cost fallback and exact output checks as optional actions. This is an evaluator seed, not a demonstrated recursive improver. The bounded effect-table parent failed child transfer, so inherited feedback is currently a negative control rather than a promoted memory mechanism.

## Direct parent-to-child improver result, September 18

The [bounded cross-family improver test](CROSS-FAMILY-META-IMPROVER-RESULTS-2026-09-18.md) is the current direct evidence on recursive growth. A later parent passed a six-bank admission test (+10 versus transform/mutation), but its child scored 340/576 on 12 untouched transfer banks versus 342 for the initial child, 341 scrambled, 339 duplicate and 343 for fixed interaction-10. Later-minus-initial had one positive and three losing banks, interval -6 to +2. The complete staged audit passed. This rejects a claim that the admitted later parent produced a stronger improver. The next test needs descendant-aware effect estimates and a wider edit catalog; evaluator component gains remain separate from improver growth.

## Budgeted listwise sensor feedback, September 18

The [new-bank budgeted-sensor simulation](LISTWISE-BUDGETED-SENSOR-RESULTS-2026-09-18.md) crossed the supported listwise evaluator objective with one exact output check and a feedback-trained allocation policy. At 96 equal simulated deployment calls across 192 AST tasks, no-query scored 91, early logistic 97, later logistic 99, fixed entropy 98 and seeded random 100; all-query and hindsight four-per-bank scored 103. All three declared gates failed. The later effect forecaster also lacked a clean forecast advantage: later HGB Brier 0.05889 versus scrambled 0.05826 on the same target. Public-choice/source-model and 95,128-label replay passed. A separate public-only reconstruction proved the frozen choices independent of true outputs, but the host preparation function had read those outputs before freeze, violating literal protocol timing. Treat this as a validated nonleaking simulation, not a strictly sealed prospective query run. The external sensor remains a useful action; additional edit feedback did not make this allocator reliably smarter. Only 12/192 query edits were useful, leaving four useful checks beyond the later policy and three beyond the random control at the same budget.

## Replicated task-level evaluator objective, September 18

The [top-200 listwise study](TASK-LISTWISE-TOP200-RESULTS-2026-09-18.md) compared ranking objectives at identical verified candidate-label counts and top-200 pools. A later task-listwise evaluator scored 96/192 versus matched-data candidate-BCE 89 on a first fresh target, then **185/384 versus 173** on a separate 48-bank replication. The replication's objective gate passed (+12, paired bank interval +4 to +20), and both replay audits passed. This is scoped evidence that optimizing task-level selection can produce a better evaluator than optimizing individual candidate labels on this synthetic AST contract.

The other endpoints remain distinct and failed their gates. Later listwise versus early was +4/192 and +6/384, below the predeclared incremental thresholds; the latter interval touched zero. The replication integration gate missed because later listwise's +15 over the prior stack was one below its required +16, and the listwise arm used 225,384 candidate scores versus 76,236 for the lower-cost dual top-100 seed. No improver parent has yet selected the ranking-objective edit and produced a stronger child improver. The next study must measure edit-effect prediction, protected admission, same-base child-system gain and second-bank child-improver gain separately across ranker, search, shortlist and sensor actions.

## Current candidate-level feedback result, September 18

The [fresh stacked-ranker test](CANDIDATE-STACKING-FEEDBACK-RESULTS-2026-09-18.md) put a richer evaluator edit through the same early/later and corrupted-history comparisons. On 192 untouched mixed AST tasks, the frozen dual-specialist top-100 route scored 64, early stacked 66, later stacked 68, scrambled 63, and duplicate-history 63. Later minus early was +2 with bank interval -2 to +6; later minus dual was +4 with interval -1 to +10. Both frozen gates failed. A combined later-stack/top-200 arm scored 73, at 114,168 candidate scores versus 38,400 for the seed. The target replay rebuilt 98,882 exact candidate labels. Top-200 reachability was 89, leaving 16 ranking misses. An oracle choice among the four tested ranker/width actions also reached only 73, so the next action must alter ranking or generation rather than routing among this fixed menu. The improver-growth and descendant-growth endpoints remain unproved.

## Current incremental result, September 18

The [fresh selective-width test](SELECTIVE-WIDTH-FEEDBACK-RESULTS-2026-09-18.md) separates a useful system action from improver growth. On 192 untouched mixed AST tasks, top-100 dual-specialist evaluation selected 74 correct programs. Widening four tasks per bank selected 77 with either an early feedback selector, a later selector trained on 192 more verified effects, or a fixed shifted-priority rule. Widening every task also selected 77. Later edit-effect MSE descriptively improved from 0.01790 to 0.01732, but the later selector's child gain over the same base was **0 versus early and 0 versus fixed** in all 24 banks; the growth gate failed. All 94,614 final candidate labels and frozen public choices passed replay audit. Only three tasks had a beneficial width edit, which limits this particular action's ability to reveal incremental learning.

For the next feedback cycle, report four distinct curves by checkpoint: (1) solution evaluator choice quality on common pools; (2) edit evaluator forecast error, calibration and decision regret against external verified edit effects; (3) same-base child system gain per acquisition and inference cost; and (4) the child improver's gain when applied to a second untouched base. A rising final solver score alone satisfies none of (2)–(4). Include negative edits and harm, fixed/scrambled/duplicate controls, and source acquisition amortization. The next action catalog must include ranker, shortlist and search edits with enough verified effect headroom to test a growing policy.

## Operational outcome

Within a declared task distribution, intelligence growth means a retained system becomes better at judging candidate solutions and changes, and better at producing useful changes, when applied to the same starting system under the same resource limits. The gain must transfer to fresh task instances and separately to withheld mechanism families. Report these as distinct claims. A score on one synthetic domain measures a scoped capability, not general intelligence.

Keep three roles explicit:

- Solver: produces task solutions.
- Evaluator: predicts correctness, tests candidates, estimates uncertainty, and predicts whether proposed changes will improve future performance. This component is allowed to learn.
- Improver: proposes, selects, and applies changes to the solver, evaluator, or improvement process. Its transferable state includes policies, abstractions, edit vocabulary, and effect estimates.

An external measurement oracle judges outcomes. The learning loop cannot edit its code, labels, or sealed test banks. A learned evaluator's score is never the final evidence of its own improvement. Finite hidden examples provide evidence on those examples; they do not prove universal program correctness.

The immediate experimental priority is **incremental evaluator and improver growth**, not a higher final solver score alone. For every retained feedback checkpoint, measure forecast error for the utility of each available query or edit, oracle utility of the choices made at the same budget, decision regret against hindsight, negative transfers, and the cost of acquiring the feedback. Then test whether the later improver checkpoint creates a better child improver from an identical starting base.

The September 18 eight-call tests illustrate why both comparisons are needed. A focused update reduced correct choices from E0's 345 to 340/576. A pairwise learner rose from P0 335 to P18 339/576, but the paired interval crossed zero and a simpler ridge learner on the same 1,440 rows scored 343. Both experiments independently replayed all task, allocation and oracle records. These results support continued development of query-value prediction; they do not demonstrate retained evaluator growth from the tested updates or any child-improver growth.

The subsequent candidate-level test showed a clear **component** evaluator gain on fixed pools: an E0 top-20 reranker selected 323/576 correct versus the old ranker's 284, winning all twelve fresh banks. Its later E1 checkpoint selected 334; E1 minus E0 was +11 with a positive paired interval, but only seven bank wins against a preregistered eight-win requirement. Under a common eight-call allocation, E1 minus E0 was only +2 with an interval crossing zero. The source and target audit passed. Keep component gain, incremental checkpoint evidence and recursive improver growth as separate claims.

## Primary test A: evaluator growth

Freeze a common pool of solutions and proposed edits for each test bank. Apply evaluator checkpoints E0, E3, and E6 to exactly the same candidates and information at the same evaluation budget. Oracle labels remain inaccessible until evaluator outputs and choices are frozen.

Measure two evaluator abilities separately:

1. Solution evaluation: oracle correctness of the selected candidate; missed correct candidates when one was available; incorrect candidates accepted at a declared coverage; and probabilistic error/calibration if the evaluator emits probabilities. Do not infer calibration from arbitrary ranking scores.
2. Change evaluation: agreement between predicted and realized improvement of proposed edits on disjoint validation tasks; frequency and severity of harmful accepted edits; and realized utility of the chosen edit compared with the best available tested edit. Evaluate edit outcomes with paired baseline and changed systems under the same budget.

The primary evaluator endpoint is the difference in oracle-measured utility of its choices on a fixed candidate/edit pool. Report candidate reachability alongside it so a better generator cannot masquerade as a better evaluator. Test unseen candidate generators and withheld error families as separate transfer conditions.

## Primary test B: improver growth

Clone the same frozen starting system S0 for each improver checkpoint I0, I3, and I6. Allow each the same improvement budget and task-visible information, then measure the changed system on a sealed fresh bank with the external oracle. Reset S0 for every independent trial. Later improvers cannot inherit an already improved solver for this comparison.

Define G(I, S0, B) = U(improve(I, S0, B)) - U(S0), where U is external held-out utility and B is the declared resource budget. The primary improver endpoint is G(It, S0, B) - G(I0, S0, B). Also report the improvement curve across budgets, the cost to reach a declared target, regressions, and unsuccessful edits. Use task correctness as the initial U; application-specific research, cybersecurity, social-good, and policy utilities require separate validated task contracts.

Run the first comparison with a common frozen evaluator to isolate the improver's contribution. Then test the combined system. Improvement over time in the live solver alone cannot establish this endpoint.

## Attribution and recursive growth

At each checkpoint, cross the components: I0/E0, It/E0, I0/Et, and It/Et, all starting from S0. This reveals improver effects, evaluator effects, and their interaction. Positive results need not occur in all four cells.

Transfer learned state to a fresh copy and compare inherited state against empty and scrambled state. For evaluator inheritance, transfer the evaluator parameters or testing policy; for improver inheritance, transfer the edit policy and effect knowledge. Scrambling must preserve state size and resource allowance. Charge the source acquisition cost separately and report when it is amortized.

To test recursive improvement, let checkpoint It modify an identical baseline improver I0. Freeze the resulting child improver and test that child's ability to improve an identical S0 on a second, untouched bank. Compare children produced by different parent checkpoints at equal budgets. A stronger child solver alone does not answer whether the parent created a stronger improver. Keep researcher-written edits and system-generated edits separately identified.

## Experimental gates

- Freeze development, admission, instance-transfer, and withheld-family banks, metrics, budgets, stopping rules, and selection rules before scoring.
- Treat previously inspected banks as development evidence for subsequent designs. Do not use them again as untouched confirmation.
- Keep evaluator/improver checkpoint selection independent of final labels. Open final oracle results only after the relevant choices are committed.
- Report total CPU/GPU time, model tokens, candidate executions, oracle queries, and learning cost. Equal candidate caps do not establish equal compute. Predeclare which resource constrains the experiment and report the remaining resource vector.
- Use paired trials across independently generated source/transfer banks and learning seeds. Report uncertainty at the independent-bank/seed level, not just across correlated candidates. Choose confirmation sample size from pilot variability before the confirmation run.
- Require replicated positive transfer at the declared budget to claim growth in the corresponding component. Report evaluator gain and improver gain separately; do not compress them into an unsupported single intelligence score.

## Interpretation of current evidence

The recent V67+V73 pool reached 33/36 semantic transfer tasks. The evolved ranker selected 29/36, compared with 30/36 for the frozen ranker: no positive evaluator-growth result in that comparison. The two generators' complementary coverage is a solver-system gain.

The encoded V73/V86 router reached 24/24 on a fresh bank, but the availability rule was researcher-designed. It demonstrates integration and representation transfer within a fixed catalog. It did not test an improver checkpoint on the same frozen starting system, nor whether a later improver can produce a better child improver.

Next implementation priority: evaluator checkpoint replay on fixed pools, followed by same-base improver checkpoint trials and the crossed component experiment. Use the current solver bundles as controls and task generators, with fresh confirmation banks.

## Update after the three v2 episodes

The fixed-pool evaluator loop and same-base feedback-policy comparison are now implemented. All three v2 replay audits passed. The predeclared policy improved from 136 to 142/144, with per-episode gains 0, +6, 0. The best exploratory inherited controller reached 143/144, compared with 139/144 for the strongest initial evaluator and 142/144 for the best fixed feedback policy. Online controller learning tied its frozen counterpart at final; stable improver growth remains unproved. These are separate learning episodes in a finite synthetic domain, not evidence of general intelligence. Full results and limitations: `SEED-FEEDBACK-REPLICATION-RESULTS-2026-09-17.md`.

Next isolate transferred improver checkpoints I0/I2/I4 on identical fresh starting evaluators. Also retain the separate requirement to measure edit-utility prediction and later-parent-to-better-child-improver growth; the current candidate-ranking results do not discharge those requirements.

## Update after same-base and lower-budget transfer

The I0/I2/I4 same-base test is complete and audited. Across six 192-label episodes, I0 improved its fresh ensemble from 226 to 242/288 while I4 finished at 241/288 and won no paired episode. A second six-episode test with 64 feedback labels measured the first edit against all five fixed tactics from the same starting evaluator. I0's learned controller exactly replicated a fixed four-tactic sequence in all six episodes (241/288); I4 exactly replicated fixed uncertainty (244/288). The strongest initial behavioral evaluator scored 243/288, so the top final policy gained one task over that control. Balanced first-edit feedback reduced action regret but did not pass the final transfer screen. See `SEED-IMPROVER-TRANSFER-RESULTS-2026-09-17.md` and `SEED-LOW-BUDGET-RESULTS-2026-09-17.md`.

This narrows the next requirement: demonstrate a policy that changes its improvement action with case context and beats its matched static action sequence, then show that a later improver checkpoint creates a stronger child improver on untouched cases. The goal remains active.

## Update after active evaluator transfer

A separate active-query evaluator now exposes a larger feedback effect without conflating it with retained intelligence. Across six fresh 64-task AST banks, the initial ranker solved 179/384, fixed one-query minimax 256/384, and fixed sequential two-query weighted entropy 301/384 (candidate reachability 353). The pairwise learned one-query selector scored 252/384 and did not beat minimax in any bank. Its 237-versus-233 development advantage failed transfer. The active-query reconstruction audit passed. See `ACTIVE-EVALUATOR-TRANSFER-RESULTS-2026-09-17.md`.

Thus oracle feedback during each evaluation materially improves choices, but a learned evaluator checkpoint has not shown transferable growth. The next evaluator endpoint should be correct solutions per *total* oracle-query budget, with the learned policy choosing which tasks merit another query and when to stop. Compare with fixed two-query and fixed allocation rules before a new untouched bank. The separate improver and child-improver endpoints above remain required.

## Update after cost-aware sequential transfer

That matched-query test is complete on six further fresh AST banks. At 480 oracle output queries, a learned second-query allocator scored 269/384, fixed entropy allocation 261, and fixed top-disagreement allocation 270. Learned beat entropy in aggregate but won only three banks; the bank-level interval included zero, and the strongest fixed control still led by one. The predeclared evaluator-growth screen failed. One query on every task scored 239/384 at 384 queries; two queries on every task scored 293/384 at 768. The reconstruction audit passed. See `SEQUENTIAL-EVALUATOR-BUDGET-RESULTS-2026-09-17.md`.

The next evaluator study needs prospective variation in mechanism and candidate generator so contextual feedback can matter beyond static disagreement. Keep the same paired, query-matched gates. The improver must still show it can improve the evaluator policy and transfer that improvement to a fresh base; no such result is established here.

## Update after mixed-mechanism evaluator checkpoint transfer

A new fixed-pool test on stack, mutation, and self-edit mechanisms passed the retained-evaluator growth screen. On six fresh 32-task banks, E0 selected 36/192 correct candidates with no output query, while E192 selected 99/192. Paired gains were positive in all six banks; the six-bank resampling interval for mean gain was 8.5 to 12.5 tasks per bank. A within-task label-scrambled model scored 72/192. At the same one-output-query budget, E192 scored 160/192 versus E0 115/192. Mean task-level candidate Brier error fell from 0.549 to 0.175. The trajectory E48 90, E96 89, E192 99 was not strictly monotonic. See `MIXED-EVALUATOR-CHECKPOINT-RESULTS-2026-09-17.md`.

This establishes a scoped transferable evaluator improvement at equal inference candidate pools. It used up to 31,500 source candidate labels, so net compute efficiency is a separate question. The improver-growth endpoint remains open: a retained improver must choose and integrate a beneficial evaluator edit on an identical base under matched acquisition cost, then produce a stronger child improver on a second untouched bank. E192 becomes a control/component in that test, not proof of a self-improving loop.

## Update after matched acquisition transfer

The first same-base 7,000-candidate-label acquisition test did not identify a growing improver. On six fresh target banks, fixed source order produced a child evaluator scoring 95/192, random 96, development-selected low-confidence 83, and three-stage adaptive low-confidence 97. Low-confidence regressed by 12 against order; the adaptive rule's two-task edge over order had a bank-level interval including zero. All source labels, child weights, and target outcomes passed reconstruction audit. E192 scored 102 but had 31,500 earlier labels and is an unequal-cost reference. See `IMPROVER-ACQUISITION-TRANSFER-RESULTS-2026-09-17.md`.

The next improver model should predict a source task's *effect on future ranking* from public features and prior verified edits, rather than rank tasks by current uncertainty alone. Evaluate that effect predictor on disjoint task banks before allowing it to choose labels. Then compare parent checkpoints by their ability to produce a stronger child improver, separately from a stronger child evaluator.

## Update after direct edit-effect and router tests

That proposed effect predictor was tested on two inspected source-target episodes. Public-feature predictions of a one-task edit's future top-choice gain had correlations -0.009 and -0.046 across episodes. Direct replay on a prior validation bank transferred Brier and AUC effects, but top-choice effect correlations were -0.051 and -0.277. An inherited Brier-effect acquisition policy scored 87/192 on inspected targets versus source order 97. A separate sensor-gated development pilot chose to retain E192; it prevented harmful updates but delivered no final gain. See `EDIT-EFFECT-AND-ROUTER-RESULTS-2026-09-17.md`.

Two evaluator models offered complementary choices. A router learned from verified disagreements scored 102/192 on six fresh banks versus E192 95 and equal-weight combination 101, but its bank-level interval included zero and it won only four of six banks. Its predeclared five-bank growth screen failed; E192 remains the confirmed component. The next edit design should target the highest-ranked false positives directly, measure actual top-choice gains on an external admission bank, and then test whether a later improver checkpoint can create a better child improver from the same base and budget.

## Update after top-choice edit and context-expert test

A direct anchored update on E192's 89 source top-choice false positives regressed even on source tasks and is not admitted. Public-context experts trained on the same verified labels provided a more promising but unstable alternative. A 50/50 global/expert blend scored 110/192 on six fresh banks versus global E192 101; its paired bank interval included zero, it lost one bank, and it tied the pure expert control at 110. The predeclared promotion gate failed, though the reconstruction audit passed. See `TOP-CHOICE-EDIT-RESULTS-2026-09-17.md`.

The supported outcome remains E192's earlier retained evaluator transfer. Context-specialized weights and the two-evaluator router are candidate edits for an improver catalog, not confirmed upgrades. The missing result is still a policy that chooses a beneficial edit on an external admission bank and whose later checkpoint can produce a better child improver on a second untouched bank at matched acquisition cost.

## Update after nonlinear listwise evaluator transfer

The first task-level listwise ranker using exactly E192's 31,500 source candidate labels passed a frozen six-bank evaluator gate: 120 epochs scored 130/192 top choices against E192 105, context blend 117, and pairwise combination 115. It gained on all six banks, with a six-bank resampling interval of +17 to +33 choices per 192 tasks. A 192-task reconstruction audit passed. Checkpoints at 40/80/120 epochs scored 108/126/130, showing substantial incremental learning from the same verified feedback. See `LISTWISE-EVALUATOR-TRANSFER-RESULTS-2026-09-17.md`.

This promotes listwise-120 as another supported evaluator component on the synthetic fixed-pool distribution. Its gain was strongly concentrated in self-edit transition, so withheld mechanisms remain a separate requirement. The output is an uncalibrated ranking logit; it supports top-choice accuracy, not a calibration claim. No edit-selection policy, child improver, or recursive improvement passed a fresh test yet.

## Update after incremental feedback and loss-edit tests

Directly fine-tuning the listwise-120 evaluator on one additional verified bank did not improve six development transfers: fixed 130/192, best verified-feedback update 130, scrambled-label update 130, and continued original-source training 131. Additional labels and weight movement alone therefore did not establish growth. See `INCREMENTAL-RANKER-FEEDBACK-DEVELOPMENT-RESULTS-2026-09-17.md`.

A more consequential edit changed the task-level ranking loss temperature from 1.0 to 0.25 while holding 31,500 source labels, architecture, seed, and 120 epochs fixed. On six untouched banks it scored 143/192 versus 130 for temperature 1.0, improving five banks and tying one; the exact six-bank resampling interval was +6 to +19. The full reconstruction audit passed. Gains appeared in all three tested mechanisms. See `TEMPERATURE-RANKER-TRANSFER-RESULTS-2026-09-17.md`. This is a confirmed evaluator-training edit but remains researcher-authored. The improver-growth test still requires automatic edit selection under matched cost and later-parent-to-better-child transfer.

## Update after fixed-catalog parent/child transfer

The first explicit parent-to-child edit-policy trial did not pass improver growth. Six fresh parent/child episode pairs used the same three trained temperature evaluators and live admission feedback. Inherited prior edit outcomes improved parent final accuracy from 64 to 71/96 versus an empty table, but child final accuracy was 69/96 inherited versus 70 empty and 69 for fixed temperature 0.25. The inherited policy selected 0.25 on every parent and child bank; the empty policy learned enough after its parent bank to match or slightly exceed it. A scrambled table scored 66 parent and 64 child. Full 384-task reconstruction audit passed. See `LOSS-CATALOG-INHERITANCE-RESULTS-2026-09-17.md`.

This distinguishes a useful evaluator edit and initial label efficiency from a growing improver. A seed improver must predict when an edit is useful in context or create useful new edit types; a global table that merely remembers the best fixed temperature does not satisfy the child-improver endpoint.

## Update after matched query-allocation transfer

At a fixed budget of 95 exact oracle output queries on six fresh 32-task banks, temperature 0.25 scored 138/192 without queries; deterministic random allocation scored 156, fixed uncertainty 161, fixed top disagreement 169, and a learned query-value policy 172. Learned minus top disagreement had bank differences 0,+1,+1,-1,+1,+1 and a six-bank resampling interval from −1 to +6. The predeclared learned-policy growth gate failed. The 192-task reconstruction audit passed. See `SHARP-QUERY-VALUE-TRANSFER-RESULTS-2026-09-17.md`.

The 31–34 task gain from buying 95 oracle outputs is a feedback-at-inference gain at extra cost, not evidence that the learned allocation surpassed the fixed control or that the improver grew. Keep fixed top disagreement as the cost-aware sensor component until a learned policy beats it on fresh banks at matched queries and acquisition cost.

## Update after incremental query-effect feedback

The frozen 18-feature query-value model was updated with 192 additional verified query effects, then tested against its previous checkpoint, scrambled new effects, duplicated prior data, and fixed top disagreement. On six new banks at 95 queries each, updated scored 173/192, previous 175, scrambled 171, duplicated prior 174, and fixed top disagreement 174. Updated tied five banks and lost two tasks on one; its bank-resampling interval versus previous was −6 to 0. Candidate reachability was 190/192 and full replay audit passed. See `QUERY-FEEDBACK-UPDATE-RESULTS-2026-09-17.md`.

This is a negative retained-evaluator update and a warning against treating more feedback labels as intelligence growth. The update shifted queries toward mutation tasks based on a prior bank where that family was difficult, but baseline mutation accuracy was much higher on the next bank. A useful improver must evaluate and adapt such allocation changes on protected live feedback, keep a fixed-policy rollback, and prove better child-policy performance under the same oracle budget.

## Update after withheld-mechanism transfer

The temperature-0.25 evaluator's growth did not generalize uniformly to three unseen mechanisms. On six fresh banks, it scored 105/144 versus temperature 1.0's 95 on the three source-training families, but 32/144 versus 33 on the three withheld families; temperature 0.5 scored 37 withheld. The 0.25-minus-1.0 withheld bank interval was −6 to +4, and the declared transfer gate failed. Transformation favored 0.5 by 22 to 14/48; novel operators favored 0.25 by 18 to 12 versus temperature 1.0. AST had only 14/48 reachable pools and every tested ranker selected zero correct programs. Full 288-task audit passed. See `TEMPERATURE-WITHHELD-FAMILIES-RESULTS-2026-09-17.md`.

This limits the confirmed 0.25 evaluator upgrade to its measured source-like distribution. For the broader seed, evaluate contextual edit effects and candidate reachability separately. A parent improver must learn when to select each evaluator and transfer that knowledge to a child; the current global temperature table failed that test.

## Update after contextual parent/child edit transfer

Six fresh six-family parent/child episode pairs tested whether a family-specific inherited edit-effect table could integrate the temperature edits. Inherited child final accuracy was 73/144 versus empty 72, scrambled 71, and a fixed prior family map 74. Inherited-minus-empty episode differences were 0,0,0,+1,0,0, with a six-episode interval from 0 to +3. The declared improver-growth gate failed; all 576 task/pool/model/policy replays passed audit. AST child reachability was 6/24 and all policies selected zero correct there. See `CONTEXTUAL-LOSS-INHERITANCE-RESULTS-2026-09-17.md`.

The evaluator edit effects differ by family, but a fixed mapping captures the measured benefit and the child improver did not surpass it. The next comparison needs edits that expand candidate reachability or representation, with the evaluator tested on identical resulting pools and the improver tested on a second untouched bank at matched cost.

## Update after incremental AST feedback

A new evaluator update passed a narrower fresh-instance transfer gate. Widening V67/V73 pools raised AST reachability 12 to 26/48; on those same pools, an AST-feedback update selected 6/48 correct programs versus zero for its parent, with gains in five of six banks and an exact bank-resampling interval of +3 to +9. The 48-task reconstruction audit passed. This is retained evaluator growth within the same synthetic AST mechanism after 23,686 additional verified source candidate labels. The source and fresh banks share a small generated rule family.

The update regressed an already inspected stack/mutation/self-edit bank from 143 to 125/192 when applied globally. Thus it is a scoped specialist, not a replacement for the existing general evaluator. The next improvement cycle must preserve the parent, route the specialist using public context, and admit that combined change on fresh mixed banks. The cap increase and model update were researcher-authored. No later improver checkpoint has produced a better child improver. See `AST-FEEDBACK-GROWTH-RESULTS-2026-09-17.md`.

## Update after fresh mixed-bank specialist integration

The follow-up public-context gate failed on six new 48-task mixed-mechanism banks. Widening AST sources raised total reachability 229 to 245/288, but the AST specialist selected zero of 26 reachable AST tasks. The gate and global parent tied at 135/288, while the prior fixed temperature map scored 139. All six gate-minus-parent bank differences were zero. The 288-task reconstruction audit passed. Thus the earlier 6/48 AST-only evaluator gain did not replicate in this mixed task stream; the specialist is not promoted to the seed. Correct candidates often remained in its top ten, so the next ranking or active-feedback edit can target selection among nearby candidates. See `GATED-AST-FEEDBACK-RESULTS-2026-09-17.md`.

## Update after verified AST replay feedback

The next checkpoint replayed 48,596 verified candidate labels from the two inspected AST transfer streams, starting from the prior AST specialist. On twelve new eight-task banks split evenly between AST-only and mixed task generation, it selected 13/96 correct programs versus seven for its previous checkpoint and zero for the original parent, all on the same 47,546 candidates. Five banks improved, seven tied, none lost; the exact bank-resampling interval was +2 to +11. Each stream gained three. The complete audit passed. This satisfies the narrow declared evaluator checkpoint gate while leaving 36 of 49 reachable tasks unselected. The update is not yet a safe global or full-system component and was researcher specified. A later improver has still not produced a better child improver. See `AST-REPLAY-FEEDBACK-RESULTS-2026-09-17.md`.

## Update after full mixed replay integration

The replay specialist's advantage did not repeat as a full-system gain. On six new 48-task mixed banks, the prior fixed temperature map scored 152/288 and the map plus replay specialist 155. Only two banks improved and the exact bank interval was 0 to +7, failing the declared integration gate. The first and replay AST specialists tied at 3/48 AST correct choices; global replay specialist use regressed to 122/288. Widening AST pools raised reachability 240 to 250/288, but only three of 23 reachable AST tasks were selected by either specialist. The 288-task audit passed. Keep the fixed map as the current zero-query whole-system control and treat the replay specialist as unpromoted. The evaluator gain in the previous two-stream test remains scoped to that test; no better child improver has been demonstrated. See `GATED-AST-REPLAY-INTEGRATION-RESULTS-2026-09-17.md`.

## Update after matched-query AST sensor transfer

On twelve fresh AST banks, the replay ranker selected 12/96 correct programs without an output query, 36/96 after one top-20 entropy query per task, and 46/96 after two. Candidate reachability was 57/96. One-query gain was positive in every bank; the exact bank interval was +17 to +32 selections at 96 oracle outputs. A second query added ten at another 96 outputs, interval +5 to +15. Full reconstruction audit passed. At the same one-query budget, top-20 scored 36 versus minimax 29, but only five bank wins and an interval 0 to +14 failed the predeclared stronger-policy gate. The effective sensor therefore provides **within-task feedback value**, not evidence that a retained learned evaluator or improver improved. Next compare learned allocation against strong fixed schedules under one fixed total query budget and test parent-to-child policy transfer. See `AST-OUTPUT-SENSOR-RESULTS-2026-09-18.md`.

## Update after fixed-total query allocation transfer

A feedback-trained 12-feature value model selected zero, one or two AST output queries under eight calls per bank, then transferred to twelve fresh banks. It tied the one-per-task fixed schedule at 31/96 with exactly 96 total calls per arm. Its bank differences were 0,0,0,−1,+1,0,0,0,0,0,0,0 and interval −3 to +3, so the allocation-growth gate failed; scrambled state scored 29. The full audit passed. An oracle hindsight allocation would score 40/96 at the same budget, but it is not an available policy. The learner's correlations with actual first- and second-query value were only 0.18 and 0.11. This is evidence of feedback value without reliable retained resource-allocation intelligence. No stronger child improver has been demonstrated. See `AST-QUERY-ALLOCATION-RESULTS-2026-09-18.md`.

## Update after full mixed AST sensor integration

The fixed AST sensor passed a full-system budgeted gain test. On six fresh 48-task mixed banks, the prior zero-query fixed map scored 140/288; widening AST pools and substituting the replay ranker scored 150 without a query; one top-20 AST output query per AST task scored 156 at 48 total calls, with six positive bank gains and interval +11 to +20 versus the zero-query map. The 288-task reconstruction audit passed. At the same 48-call budget, fixed minimax scored 157 and learned allocation 158; learned-minus-minimax interval −2 to +4 failed the improver gate. Thus a fixed combination improves system solving at explicit oracle cost, while the learned improver still has no confirmed positive child-transfer loop. See `FULL-MIXED-AST-SENSOR-RESULTS-2026-09-18.md`.

## Update after incremental AST parent/child feedback

The protected checkpoint test separated historical evaluator differences from incremental improver growth. I0 carried 96 verified query-effect tasks; I1 carried 240. Both received the same 48-task admission update. On twelve untouched transfer banks, I1 child scored 28/96, I0 child 25, and fixed one-query-per-task 26. The I1–I0 difference had four positive banks and a -1 to +7 bank interval, failing the declared gate. Applying each frozen parent to the same transfer pools also gave I1 28 and I0 25, so the common update added zero final choices to either lineage. Scrambled and duplicate child controls scored 27 and 26. The audit reconstructed 72,372 candidate labels and all models and allocations. This does not show a self-improving improver. The next step is better public-context prediction of reachability and marginal query value with a protected fixed-policy fallback. See `INCREMENTAL-AST-IMPROVER-RESULTS-2026-09-18.md`.

## Update after contextual AST value and protected child transfer

Richer public features and an RBF value model scored 113/288 versus fixed one-each at 100 in inspected source cross-validation, but only 27/96 versus fixed 26 on a later inspected panel. A simpler ridge-10 model scored 30/96 there. Both were frozen for six new admission and twelve new transfer banks. At 96 transfer query calls, later ridge child scored 33/96 versus earlier child 31, fixed one-each 31, and scrambled/duplicated history 30. Its two-task child edge had only two positive banks and a -2 to +7 bank interval; later ridge parent already scored 33 on the same transfer pools, so the admission update did not improve it. Later RBF parent and child both scored 32; the protected gate rejected RBF and used the fixed schedule. The full 144-task reconstruction audit passed. Candidate reachability was 54/96 and hindsight allocation at the same call budget could reach 43/96, leaving a large but hard-to-predict allocation gap. These are useful evaluator diagnostics but still no retained positive improver feedback loop. See `CONTEXTUAL-AST-IMPROVER-V2-RESULTS-2026-09-18.md`.

## Update after sequential AST output-feedback transfer

A sequential allocator was trained to reconsider a second query after seeing a purchased first output. On 384 inspected source tasks, leave-one-bank-out development scored conditional sequential 139/384, prior-only sequential 134, static ridge 135 and fixed one-each 126. In six new admission banks, conditional parent scored 20/48 versus one-each 18 and missed its predeclared three-task admission threshold; protected deployment fell back to one-each. On twelve untouched transfer banks, raw later child scored 32/96 versus earlier child 31, prior-only and static ridge 30, and one-each 26 at 96 calls each. Later-child minus earlier-child interval was -2 to +4 with only two positive banks, so recursive growth failed. The conditional edge over prior-only/static was also uncertain. Raw later-child minus one-each had interval +1 to +12 with no losing banks, a scoped evaluator allocation signal that was not promoted because of the admission rule. The audit reconstructed 73,812 candidate labels, 590,496 candidate-predicted outputs, all model states and 720 sequential actions. See `ADAPTIVE-AST-IMPROVER-RESULTS-2026-09-18.md`.

## Update after common-bank cross-component edit transfer

A fresh six-mechanism, six-bank comparison tested the sharper listwise loss, AST ranker, fixed output sensor, and shadow sequential allocation on the same 288 tasks. Global temperature 0.25 regressed the no-query fixed map from 145 to 139/288, with a -11 to -2 paired bank interval; four losses were transformation and two self-edit. The AST replay ranker raised the fixed-map score to 148 without a query. One top-20 output query on each AST task raised it to 159 at 48 calls, with six positive bank gains versus the no-query map and interval +10 to +19. The shadow sequential allocator reached 161 at the same calls, but its +2 over fixed top-20 had interval 0 to +4 and did not pass the predeclared promotion gate. The audit reconstructed 288 tasks, 76,542 candidate labels, 200,256 predicted AST outputs and all 48 adaptive actions. These outcomes show context-sensitive evaluator edits and a replicated fixed system gain, not a growing improver. Transformation and mutation pools were each reachable on 48/48 tasks but the fixed map selected only 21 and 23; cross-family output feedback is the next candidate edit. See `CROSS-COMPONENT-MIXED-TRANSFER-RESULTS-2026-09-18.md`.

## Update after cross-family query-value transfer

A new feedback-trained evaluator allocator passed its fixed-total fresh-bank gate. On twelve untouched 48-task mixed banks, at eight exact output calls per bank, it selected 341/576 correct programs versus 322 for the strongest fixed transformation/mutation schedule, 320 for AST-only, and 294 without queries. Nine paired banks improved, two lost, one tied; the exact bank-bootstrap interval for the twelve-bank sum was +9 to +28. Both six-bank panels gained. The audit retrained source models, regenerated all 576 tasks/pools and 1,067,008 candidate-predicted outputs, and rechecked 133,376 candidate final labels and every allocation. A separate audit showed the benchmark host family field is exactly recoverable from the public Unicode block on all 1,152 source/target tasks and reproduced every learned allocation from that visible cue. Training required 576 earlier verified task effects and large prediction compute; matched oracle calls do not imply matched total resource cost. An inspected update with 288 additional effects improved query-gain Brier error but tied the old policy's final choices on an already opened panel. Thus the evaluator learned a transferable resource decision, while incremental improver growth and a better child remain unproved. See `CROSS-FAMILY-QUERY-TRANSFER-RESULTS-2026-09-18.md`.

## Update after protected training-rule improver transfer

A bounded improver selected among six query-value evaluator training rules by leave-one-bank-out verified source correctness. The initial parent had 576 inspected query effects; the later parent had 864. Both received the same 288 new admission effects, and the admission gate accepted the later parent (+10 correct over fixed transform/mutation, four of six positive banks). On twelve subsequently frozen mixed transfer banks, the later child selected 340/576 correct programs versus the initial child at 342, its own frozen parent at 341, scrambled child at 341 and fixed ridge-10 trained on the later child's own rows at 343; all used 96 true output calls. Only one bank favored the later child over the initial child, with a -6 to +2 exact bank-bootstrap interval. Later-child source cross-validation tied ridge-10 and ridge-100 at 704/1,152; frozen catalog order chose ridge-100, which lost three transfer choices to fixed ridge-10 on the same rows. This is a failed improver-selection and recursive-transfer gate, while the earlier evaluator-allocation gain remains scoped evidence. The full independent task/pool/prediction/label audit **passed**, including all 864 tasks and 201,884 candidate labels; see `CROSS-FAMILY-META-IMPROVER-RESULTS-2026-09-18.md` and `runs/cross-family-meta-improver-transfer-20260918/audit.json`.

## Update after incumbent-aware rule correction

The first meta-improver transfer exposed a tie-break failure, so a new protocol froze a single correction: retain the incumbent training rule when it ties for best source cross-validation. On twelve new, separately frozen 48-task banks, the corrected later child tied the original catalog later child and initial child at **349/576** under the same **96 output calls**. Its frozen parent scored 350, scrambled child 350 and duplicate-history child 353; both ridge-10 and ridge-100 fixed controls scored 349. The corrected-minus-initial and corrected-minus-catalog paired-bank intervals were each **-4 to +4**, and both predeclared gates failed. The independent audit reconstructed all 576 tasks, 1,068,544 predicted probe-output cells and 133,568 final candidate labels and passed. The correction fixes an arbitrary selection rule but did not produce a stronger improver on fresh evidence. See `STABLE-CROSS-FAMILY-IMPROVER-RESULTS-2026-09-18.md`.

The corresponding bottleneck dissection keeps **coverage, ranking, information use and allocation** separate. On these 576 tasks, 492 had a reachable correct candidate, 304 were selected correctly without a query, 424 with one query on every task at six times the deployed output-call budget, and 349 with the learned eight-per-bank allocation. An unavailable hindsight eight-per-bank allocation would score 396, leaving 47 choices of allocation regret. This bounds the opportunity for better task-level query-value prediction but does not prove that a given learner can close it. See `SEED-IMPROVER-BOTTLENECK-DISSECTION-2026-09-18.md`.

## Update after rich candidate-consensus evaluator transfer

A richer public feature set measured candidate agreement, score-weighted support for the leading answer, rival-output rank gaps and candidate-source diversity. On inspected development, its source-selected ridge model scored 523 versus base features 516 under whole-bank cross-validation and 355 versus 345 on a separately opened validation set; neither paired interval excluded zero. In a frozen six-bank admission and twelve-bank transfer test, the later parent scored 173/288 versus initial 170 and strongest fixed 170 on admission, but won only three banks versus the fixed control, so protection rejected it. On untouched transfer, later child scored **335/576** versus initial child **339**, own frozen parent **337**, fixed rich ridge-100 on its own rows **339** and strongest base-feature rule **334**. The later-minus-initial interval was **-9 to +1** with one positive bank; its one-choice edge over the best base rule had interval **-4 to +6**. The audit retrained four parents and ten child/control states, regenerated all 864 tasks/pools/predictions/features/allocations, and rechecked 205,076 final candidate labels. Both evaluator-feature and recursive-child gates failed. See `RICH-EVALUATOR-AND-TYPED-EDIT-RESULTS-2026-09-18.md`.

The typed effect ledger on 1,440 opened tasks shows why the seed must measure edit interactions: AST widening added 56 reachable tasks but no fixed-ranker correct choices; replay ranking added 25, and a top-20 output query added 300 if bought for every task. Thirty-two newly reachable AST tasks were solved only after the search/ranker/sensor package. Global sharpening netted -16. Allowing a second query improved the eight-call-per-bank hindsight ceiling by only five choices across 30 banks, compared with a much larger gap in choosing first queries. These are development diagnostics and do not establish that a learned package improver transfers. See `RICH-EVALUATOR-AND-TYPED-EDIT-RESULTS-2026-09-18.md`.

## Update after four-slot AST package transfer

A cost-constrained package test let the improver choose four of eight AST tasks to widen per 48-task mixed bank. The frozen replay ranker and one exact output query per AST task were common to every active policy, giving the same 48 width slots and 96 query calls across twelve transfer banks. The later ridge child selected **319/576** versus initial child **323/576**, with zero positive paired banks and a **-7 to -1** exact bank-bootstrap interval. Its six-bank admission gain over random four occurred in only one bank, so the protected gate rejected it. Fixed public low-gap four selected **323**, deterministic random four **319** (paired interval **-3 to +10**), and full width **325** using twice the expansion slots. Thus neither a growing learned width improver nor the fixed low-gap selector passed its declared gate. Base and full-width reachability were **473** and **500**; widening without a query reduced top-choice correctness from 306 to 302, again showing that coverage only pays when ranking and sensing can use it. The full independent audit passed across 864 tasks, 577,696 AST predicted-output cells and 201,578 candidate final labels. See `AST-WIDTH-PACKAGE-IMPROVER-RESULTS-2026-09-18.md`.

The research harness generated every potential wide pool for counterfactual scoring. The selected four-slot low-gap policy used 16,746 effective extra candidate entries on transfer versus 34,116 for full width, but those effective counts are not measured offline wall-time savings. The study queried only AST tasks and therefore does not replace the stronger cross-family eight-call allocation result. A joint search-width and all-family query allocator remains untested.

## Update after candidate-level feedback replication and edit-effect inheritance

A candidate-level reranker trained from 576 verified source tasks again improved a fixed candidate pool on a second 576-task panel: E0 scored 326 correct zero-query choices versus the old ranker's 291, after scoring 11,380 old-top-20 candidate entries. The later same-rule E1 checkpoint used 288 more verified source tasks but gained only five over E0 zero-query, with five positive banks and interval -3 to +13; it lost one choice to E0 at the same 96 output calls. Its second-panel incremental gate failed. A prospectively frozen self-edit fallback gained five zero-query choices but had interval -1 to +11 and failed its own gate. Candidate-level learning is therefore a supported scoped *evaluator component*; reliable incremental evaluator improvement after the first checkpoint is still unproven.

A separate bounded parent/child edit-effect test used 288 versus 576 verified historical records to derive mechanism ranker routes and eight-call allocations from the same frozen base. The later child scored 182/288 on the protected second six banks versus initial 178, with interval +1 to +8, but it improved only three of six banks and failed admission 173 versus fixed E1 at 179 on the first six. A scrambled-history child scored 356/576 across all twelve versus later 355. Query-gain forecast MSE improved marginally from 0.12417 to 0.12272, while the scrambled control's selected calls gained more. The declared improver growth test failed; forecast calibration and selected utility remain separate outcomes. Full independent candidate-level replay and child reconstruction passed. See `CANDIDATE-FEEDBACK-REPLICATION-AND-IMPROVER-RESULTS-2026-09-18.md`.

## Update after candidate-conditioned query-value transfer

The next evaluator represented the answer groups formed by E0's reranked candidates at the planned probe, then learned a mechanism-interaction first-query gain. On two opened audited source panels, 24-bank leave-one-bank-out selection scored 724 versus the old frozen allocator's 708. On a third untouched 576-task panel, the frozen later evaluator scored **387 versus 374** with the same 96 logical output calls, ten bank wins, no losses and a paired bank interval **+9 to +17**. Its gain-forecast MSE was **0.11144 versus 0.12552**. Matched 1,152-task controls scored 373 with old features and 380 with candidate-conditioned features but no mechanism interaction. The fixed-output-call evaluator gate passed, and independent source/target replay plus child reconstruction passed.

The later parent's child scored **198/288** on protected transfer versus the initial parent's **196/288**, but only two of six banks improved and the interval was **0 to +4**. Its admission gate passed; its separate improver-growth gate failed. The new query features read E1 and 7-leaf model agreement, adding two top-20 inference passes relative to a minimal E0 system. Historical feedback acquisition and extra inference still need cost-matched testing. See `CANDIDATE-CONDITIONED-QUERY-GROWTH-RESULTS-2026-09-18.md`.

## Update after low-cost feature ablation and feedback rollback

Removing the E1 and 7-leaf agreement features leaves a 24-feature query-value model that can run from the old and E0 candidate orders. In a frozen fourth-panel test, cheap later tied the full matched-data 26-feature model at **370/576** correct choices and paired interval **-4 to +4**, while avoiding **22,768 deployable candidate-model predictions**. It scored **+11** over the old allocator's 359 at the same 96 output calls, eight bank wins, two losses and interval **+3 to +20**; the low-cost and fixed-call evaluator gates passed. The offline harness did not measure end-to-end time savings.

The additional 576 verified effect records worsened the cheap checkpoint: initial scored **374/576**, later **370/576**. Later failed six-bank admission 183 versus initial 188; its protected transfer advantage was only **+1**, interval **-2 to +4**. The protected process therefore retains initial. This is useful negative feedback: an intelligent improver must learn when to **reject or downweight** a new batch, then show that later parents make better children on fresh tasks. The candidate and child audits passed. See `LOW-COST-CANDIDATE-QUERY-RESULTS-2026-09-18.md`.

## Update after E1 ranker-plus-query package transfer

A combined test compared E0 and E1 candidate rerankers with the same 24-feature query rule trained on 2,304 prior task effects. On a fifth untouched 576-task panel, E1 selected **356** correct programs without calls versus E0 **344**; its no-query checkpoint gate passed on this panel. With 96 output calls and matched learned query allocation, E1 scored **385** versus E0 **380**, four positive and four losing banks, interval **-4 to +15**. The preregistered integrated package gate failed. E0's learner fixed 36 errors versus E1's 29; unavailable hindsight query fixes were 85 versus 76. Better ranking reduced the sensor's remaining opportunity, so isolated ranker and query gains were not additive.

The E1 later query child, trained on 2,304 effects, failed admission **189 versus earlier 192** and gained only **+2** on protected transfer, with two positive banks and interval **0 to +4**. Its forecast MSE fell but its selected query fixes fell by one. The independent candidate replay and child reconstruction passed. The supported seed remains E0 plus the protected low-cost candidate-conditioned query evaluator; E1 is a shadow component until a package-level admission and transfer test supports it. See `COMBINED-RANKER-QUERY-RESULTS-2026-09-18.md`.

## Update after shifted-AST mechanism transfer

The supported seed was next applied unchanged to 96 new tasks with familiar AST Unicode inputs but different arithmetic predicates. Full widened-pool reachability was **61/96**, old top-20 reachability **40/96**, E0 zero-query correctness **15/96**, cheap 48-call correctness **21/96**, and prior 48-call correctness **22/96**. One query on all 96 tasks reached only **23/96**; hindsight placement of the same 48 calls also reached 23. The learned allocator transfer gate failed, and its possible advantage over prior allocation was structurally capped at one choice on this bank. The audit replayed all 96 tasks, 366,480 output predictions and 45,810 candidate labels and passed. This separates the failure of **representation/search/shortlist use** from the value of further query-allocation feedback. See `SHIFTED-AST-SEED-TRANSFER-RESULTS-2026-09-18.md`.

The failure decomposition found that each of the 61 reachable tasks kept at least one final-correct candidate after the actual output probe. Among the 96 tasks, 35 were unreachable, 19 were unresolved with their correct candidate below the old top 20, and 19 were unresolved even though a top-20 correct candidate survived the probe; 15 were correct without a call and eight were corrected by one. The next improver should target **candidate coverage, shortlist recall and post-query ordering as separate edit effects**. The 48-call placement catalog on this changed mechanism is too narrow to establish intelligence growth. See `analysis/shifted-ast-failure-dissection-v2-20260918.json`.

## Update after post-query and changed-feedback integration

A fixed-top-20 post-query evaluator trained on 8,681 verified survivor labels tied E0 at **47/192** one-query choices on 24 new shifted-AST banks. At 96 calls it scored 35 versus E0 33, interval **0 to +5**, failing its declared gate. The independent audit passed. Full-pool reachability was 112, while the old top 20 reached only 53; a later opened diagnostic found top-50/100/200 recall of 75/91/104 and confirmed that all 112 reachable tasks retained a correct candidate after the probe. The evaluator's action set, not probe elimination, was a major limit. See `POST-QUERY-FEEDBACK-TRANSFER-RESULTS-2026-09-18.md`.

A subsequent frozen same-budget test asked whether 96 verified shifted query effects improved allocation on 192 additional shifted tasks. Protected cheap E0 scored **46/192** with 96 calls; the predeclared pooled update scored **44**, and a pooled joint call/ranker policy scored **48**, with intervals crossing zero. Both growth gates failed. At the protected call locations, an opened plain top-50 post-query edit scored 50, while a secondary learned route scored 51; the latter's extra task had interval **-4 to +6** versus cheap-plus-plain. More shifted feedback increased E0 gain-forecast error relative to familiar-only prior. A later edit-effect checkpoint trained on 288 rather than 96 shifted tasks tied the earlier routed checkpoint at 51 on opened validation, later-minus-earlier interval **-6 to +6**. This is evidence of **component interaction and failed feedback integration**, not retained improver intelligence growth. See `SHIFTED-FEEDBACK-VALUE-TRANSFER-RESULTS-2026-09-18.md`.

For the next seed, evaluate the same four quantities on each new bank: correct-program reachability in the full pool, recall at the action shortlist, candidate choice before and after a call, and realized gain from the chosen call/edit at fixed cost. A good evaluator must predict the *change in final oracle utility* caused by its chosen edit; a lower average forecast error or more candidates considered is insufficient if the selected actions do not improve outcomes. A good improver must retain or roll back updates based on protected external evidence and produce a better child improver from the same starting base on another untouched bank. Those latter requirements remain unproven.

## Update after shifted-survivor evaluator transfer

The next candidate-level feedback edit passed a scoped fresh gate. On 24 new shifted-AST banks, a plain top-100 post-query model trained on **1,527 verified survivors from 96 earlier shifted tasks** selected **61/192** correct programs at the existing 96 cheap call locations, versus E0 and a familiar-trained top-50 model at **44**; 15 banks improved and the paired interval was **+10 to +24**. A post-test familiar-trained top-100 control scored 45 despite 35,291 source survivor labels, supporting the importance of relevant feedback on this changed mechanism. The independent replay rebuilt all 192 tasks, 749,472 output predictions and 93,684 final candidate labels. Full-pool reachability was 109; top-100 reachability 96. See `SHIFTED-SURVIVOR-EVALUATOR-TRANSFER-RESULTS-2026-09-18.md`.

The later 288-task checkpoint scored 67, +6 over the 96-task checkpoint with interval **+1 to +12**, but only four banks improved and its preregistered incremental gate required eight. An equal-label sensor-feature model scored 62, five below the plain model. The stronger shifted evaluator also harmed familiar AST tasks in an opened one-query-each check: **25/96** versus E0's **36**, interval **-20 to -2**. Therefore the retained evidence is a **specialist component**, not a safe general seed upgrade or recursive improver growth. The next integration test needs a public-evidence applicability predictor that preserves the shifted gain and avoids familiar-task harm on untouched mixed banks, followed by a same-base later-parent-to-better-child improver test.

## Update after mixed specialist integration

The first protected applicability router did not safely integrate that specialist. On 24 new banks with four familiar and four shifted AST tasks each, E0 scored **49/192** and always-specialist **60** at 96 common calls. The predeclared conservative paired-effect router scored **56**: familiar subgroup +3 over E0 without a losing bank, shifted subgroup only +4, and overall **-4** versus always-specialist. Its declared integration gate failed. A zero-threshold secondary route scored 61, only +1 over always-specialist, interval **-5 to +7**. A scrambled-effect route scored 52. Independent replay rebuilt 192 tasks and 93,168 final candidate labels. See `SPECIALIST-APPLICABILITY-TRANSFER-RESULTS-2026-09-18.md`.

The failure decomposition gives the next improver a concrete objective. Among 49 queried shifted tasks, the specialist helped 14 and hurt none; the conservative router selected it on only nine tasks, capturing four helps. Among 47 queried familiar tasks, it helped four and hurt seven; the router captured three helps and no harms. The model learned to avoid familiar mistakes but its acceptance threshold was too strict on shifted tasks. A later improver must calibrate acceptance from protected mixed effects and show that its *child improver*, starting from an identical base, makes better edit choices on a second untouched bank at matched acquisition, query and inference cost. A fixed researcher-selected threshold is not that result.

## Update after incremental feedback screens and action-space analysis

On the already opened mixed panel, adding 96 verified mixed edit effects in two cross-fit folds did **not** improve the effect router: its fixed-zero-threshold result stayed 61/192, equal to the earlier checkpoint, while a scrambled control scored 59 and a duplicated-history control 62. Letting the added feedback select its own threshold reduced the later checkpoint to 53 versus 58 for the earlier one. An alternative two-head effect predictor scored 63/192 against the original 61, but its paired interval was -3 to +8. These are development screens, not fresh transfer results. See `analysis/mixed-effect-update-development-20260918.json` and `analysis/effect-predictor-alternatives-development-20260918.json`.

The audited mixed panel contained 125/192 tasks with a correct program somewhere in the full candidate pool, and all 125 retained a correct candidate after the actual output probe. The old top 100 reached 114. With one call on every task, E0 selected 68, the shifted specialist 77, and an unavailable oracle choosing between these two actions selected 97. At the real 96-call budget, the corresponding scores were 49, 60 and 67. Thus even perfect routing between these two rankers can add only seven over always-specialist at the fixed budget; 17 top-100-reachable tasks evade both one-call choices. The next evaluator action must change **candidate ranking before and after a call**, not just route these two post-query rankers. See `analysis/mixed-action-space-diagnostic-20260918.json`.

An opened zero-query screen found strong shifted-specific signal in verified candidate labels: a model trained on 96 shifted tasks selected 71/192 correct first choices on one opened shifted panel versus E0's 25; with 192 more shifted tasks it selected 81. The later model scored only 2/96 first choices on an opened familiar AST panel versus E0's 13. These results motivated a frozen fresh shifted test in `EXPERIMENT-zero-query-shifted-feedback-transfer.md`; they do not establish general evaluator transfer or improver growth. See `analysis/shifted-zero-query-reranker-development-20260918.json`.

## Validated incremental evaluator growth on shifted AST

The prospectively frozen zero-query test passed both gates and its full reconstruction audit. On 24 untouched shifted banks (192 tasks), E0 selected **23** correct first programs; the 96-source-task shifted ranker selected **60**; and the later checkpoint trained with 192 additional shifted tasks selected **74**. The later-minus-earlier gain was +14, with nine positive and no losing banks and a paired interval **+6 to +23**. A control with the later task labels scrambled selected 50, so the later checkpoint exceeded it by 24 (interval +14 to +35). At identical four-call-per-bank locations, the scores were E0 37, earlier 70 and later 77. The audit rebuilt all 192 tasks, 759,728 predicted output cells, 94,966 final candidate labels and all candidate scores and choices. See `ZERO-QUERY-SHIFTED-FEEDBACK-RESULTS-2026-09-18.md`.

This is the first protected **incremental evaluator** result in this sequence: more relevant verified feedback improved the same rule's first-choice decisions on a new shifted bank. It remains a scoped synthetic mechanism. The earlier opened familiar-task regression means the checkpoint is not a safe general replacement, and the candidate-scoring/training cost differs from E0. The improver itself has still not demonstrated inherited, parent-to-child improvement. The next claim requires a later edit controller to make a better child than its earlier self from a common base under matched feedback, proposal and evaluation budgets.

## Mixed integration and improver-feedback test

The follow-up prospectively compared the shifted ranker, a single pooled ranker, a public-feature route, and a paired-effect improver on 24 untouched mixed banks. At zero external output calls, E0 scored **24/192**, shifted AB **40**, pooled **33**, and the later public-feature route **45**. The route exceeded E0 by 21, but its +5 over always AB had nine positive and four losing banks and interval **-3 to +13**; the predeclared general integration gate failed. Its later checkpoint beat its earlier checkpoint 45 to 40, but tied closely with balanced duplicate history at 44. It was trained on task-type labels and cannot by itself establish improvement of the edit-effect model.

The direct paired-effect controller, trained to predict the verified AB-minus-E0 effect, scored **43** before and **44** after 192 more mixed effects. Later-minus-earlier was +1 (interval -2 to +4); later-minus-scrambled and duplicate controls were each +3 (interval -1 to +7). Its improver-growth gate failed. Full replay passed for 192 target tasks, 480 source effect rows, 771,952 predicted cells and 96,494 final candidate labels. The action dissection found 98 full-pool-reachable tasks, 85 top-100-reachable, a two-choice E0/AB oracle ceiling of 53 and a three-choice E0/AB/pooled ceiling of 61. A new three-action effect catalog is justified, but its post-test recombinations are not fresh evidence. See `ZERO-QUERY-MIXED-INTEGRATION-RESULTS-2026-09-18.md`.

## Three-action improver and candidate-ranking bottleneck

The three-action catalog was then tested prospectively on another 24 mixed banks. Separate outcome heads trained on 288 early task rows selected **43/192** correct programs; adding 192 verified mixed rows produced **42**. Scrambled added outcomes scored 39, balanced duplicate history 45, the prior two-action route 42, fixed AB 36, pooled 38 and E0 27. Later-minus-early was -1 (interval -4 to +2), later-minus-duplicate -3 (interval -6 to 0), and later-minus-AB +6 (interval 0 to +12). Both frozen integration and improver-growth gates failed. Full audit passed for 192 tasks, 480 source rows, 745,824 predicted cells and 93,228 final candidate labels. See `THREE-ACTION-IMPROVER-TRANSFER-RESULTS-2026-09-18.md`.

The latest bank sharpens the measurement target. It had **102** full-pool-reachable and **92** top-100-reachable tasks, but a hindsight choice among E0, AB and pooled first choices could solve only **56**. On familiar tasks alone, 46/96 had a correct top-100 candidate, while those three actions could solve only 20 and the later controller solved 10. The next evaluator improvement should raise **candidate-level top-choice accuracy inside the reachable shortlist**, rather than add another routing rule among weak first choices. An opened familiar-specific top-100 ranker trained on 192 familiar tasks selected 39/96 and 43/96 on two prior mixed panels versus E0's 15 on each; its later checkpoint added only one on each. A fresh familiar-only transfer is frozen in `EXPERIMENT-familiar-ast-zero-query-transfer.md` before any component claim.

## Validated familiar specialist; incremental checkpoint saturates

The fresh familiar-only test passed its component gate on 24 untouched eight-task banks. A top-100 ranker trained on 19,152 verified candidate labels from 192 familiar tasks selected **108/192** final-correct first programs, versus E0 **38** and pooled **49**. It improved 23 banks and lost none against either control; paired intervals were +58 to +82 versus E0 and +48 to +70 versus pooled. The old top 100 reached 112 tasks, so the early model was correct on 108 of those 112. A later checkpoint with 28,722 total labels selected 110, but its +2 over early appeared on only two banks and its interval included zero; the distinct incremental growth gate failed.

The initial replay command failed because retrained model-object hashes differed. A frozen audit addendum required exact probabilities across every evaluated source and target candidate row and full target replay. That qualified replacement audit passed: all four models matched on **28,722 source and 18,954 target rows each**, and it rebuilt 192 tasks, 745,504 predicted cells, 93,188 final labels and all frozen choices. Object byte identity remains unproved. See `FAMILIAR-AST-ZERO-QUERY-RESULTS-2026-09-18.md` and `AUDIT-ADDENDUM-familiar-ast-zero-query-2026-09-18.md`.

The candidate-evaluator evidence now supports **two specialists**: shifted AB and familiar early. Their large gains are mechanism-specific, and extra feedback at the later checkpoint did not pass a distinct growth gate on familiar tasks. The next improver trial must use both strong actions on common mixed banks, learn which action changes oracle utility from public evidence, and show later-parent-to-better-child transfer beyond scrambled and duplicate controls. The previous controller failures were partly an action-quality limit, but replacing weak actions with strong specialists is still a hypothesis for the improver, not a proven positive loop.

## Validated dual-specialist seed; feedback improver still flat

The next fresh 24-bank mixed test resolved that integration hypothesis for its synthetic contract. A fixed public confidence comparison between familiar early and shifted AB selected **85/192** correct first programs with zero external output calls, versus familiar-only **64**, shifted-only **43** and E0 **31**. It exceeded familiar by +21 (16 positive banks, interval +13 to +29) and shifted by +42 (21 positive banks, interval +30 to +55), passed the predeclared subgroup limits and **passed the integration gate**. The full replay audited 192 tasks, 384 source effect rows, 734,800 predicted cells, 91,850 final labels and all policy choices. See `DUAL-SPECIALIST-INTEGRATION-RESULTS-2026-09-18.md`.

The feedback-driven controller did not improve. Ridge effect routing trained on 192 earlier mixed task effects scored **87**; after 192 additional verified effects its later checkpoint scored **85**, tied the fixed confidence rule, trailed balanced duplicate history at 86, and exceeded scrambled effects by only one. Later-minus-earlier was -2 (interval -6 to +2); the improver-growth gate failed. The fixed confidence route reached 85 of 93 tasks reachable by choosing between its two specialists, leaving at most eight additional action-routing successes on this bank. Another ten tasks had a correct top-100 candidate neither specialist chose, and eleven full-pool-reachable tasks had no correct top-100 candidate. The next improver edit needs to **create or refine candidate-ranker and shortlist/search actions**, then demonstrate that later inherited edit knowledge produces a better child at matched acquisition and inference cost. More routing feedback inside this nearly saturated two-action menu is a low-headroom next step.
