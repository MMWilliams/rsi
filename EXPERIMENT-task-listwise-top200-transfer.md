# Task-level top-200 ranker: frozen fresh transfer

Date: 2026-09-18. Written before new target tasks or their oracle labels are generated.

## Questions

1. Does optimizing the probability of selecting *any correct candidate in a task* outperform candidate-level correctness training with exactly the same verified top-200 source candidates and labels?
2. Does the later task-listwise checkpoint, after 192 more verified source tasks, improve over its early checkpoint and corrupted/history-only controls on untouched banks?
3. Is the resulting evaluator a useful edit for the two-specialist zero-query seed when cost is charged?

The prior opened-bank screen (`analysis/task-listwise-top200-development-20260918.json`) is development evidence only. Its third panel was included in later training and cannot count as transfer. The fourth panel was inspected before this protocol.

## Source and target

The early task-listwise and candidate-BCE models use the same 75,024 exact candidate labels from 384 tasks in two audited mixed-bank panels. Later models add the same 37,586 exact labels from 192 tasks in a third audited panel: 112,610 labels total. Both train on the same 191 public structural/ranking/specialist-probability features for candidates in the old-ranker top 200. The listwise MLP has 32 hidden units, 120 AdamW epochs, temperature .25, fixed seed 905200. BCE uses the established 15-leaf HGB class. Scrambled feedback permutes additional labels within task; duplicate history resamples early task groups. Model files and hashes are frozen before target preparation.

Target: 24 new deterministic eight-task mixed familiar/shifted AST banks, seeds 905300–905323, 192 tasks. Candidate generation, old ranking, specialist models and exact hidden-example oracle follow the previously audited contract. The target evaluator sees only public examples, candidate programs and public model scores; it cannot read family, reference or hidden examples. The oracle remains external.

## Arms, cost and gates

At top 200: early/later listwise, scrambled and duplicate listwise, early/later BCE, the prior candidate-level stacked model trained only through top 100, fixed dual confidence and fixed candidate mean. Include fixed dual top 100 as the operating seed. Score all arms on identical pools. Charge exact source labels and candidate prediction counts by model, and record wall time for public target preparation. Candidate-score equality is not a claim of equal CPU/GPU work; report that limitation.

The *objective gate* requires later listwise to beat matched-data later BCE by at least six correct tasks, with paired 95% bank-bootstrap lower bound above zero and at least ten positive banks. The *incremental feedback gate* requires later listwise to beat early, scrambled and duplicate by at least five tasks each, with a positive lower bound and at least eight positive banks against early. The *integration gate* requires later listwise to beat the fixed dual top-200 and the prior stacked top-200 by at least eight tasks each, with positive lower bounds, at least twelve positive banks against dual, and no more than eight lost correct choices versus each specialist on its own subgroup. All gates require a passing replay audit. No model, epoch, feature or threshold selection on target outcomes.

Freeze and hash tasks, pools, public records, per-arm choices and costs before scoring hidden labels. Audit regenerates tasks and candidates, reproduces model predictions/choices, and re-evaluates all target candidate labels. Report reachability, subgroups, paired intervals, harmful changes and the full resource vector. Even a passed evaluator gate is not a parent-to-child improver result.
