# Dual-specialist zero-query integration: fresh transfer

## Decision

The prospectively frozen **integration gate passed** on 24 untouched mixed AST banks (192 tasks). A fixed public confidence rule chose between the validated familiar early and shifted AB top-100 evaluators and selected **85** final-correct first programs with zero external output calls. Always using familiar selected **64**, always using shifted **43**, and E0 **31**. The confidence rule gained **+21** over familiar on 16 positive and one losing bank, paired interval **+13 to +29**; it gained **+42** over shifted on 21 positive and one losing bank, interval **+30 to +55**. Familiar subgroup correctness was 53 versus the familiar specialist's 54; shifted subgroup correctness was 32 versus shifted AB's 38. Both subgroup loss limits passed.

The separate **improver-growth gate failed**. A ridge controller predicting verified shifted-minus-familiar effects scored 87 after the first 192 source tasks and **85** after 192 more. The later controller tied the static confidence rule, scored 84 with scrambled added effects and 86 with balanced duplicate history. Later-minus-earlier was -2 (interval -6 to +2), later-minus-duplicate -1 (interval -4 to +2), and later-minus-confidence zero (interval -3 to +3). The later controller made three new errors and corrected one earlier error on this target. Thus a better fixed combined evaluator is established within this synthetic mixed contract, while a positive feedback loop in the improver is not.

The frozen protocol is `EXPERIMENT-dual-specialist-integration-transfer.md`; complete paired outcomes and the replay audit are in `runs/dual-specialist-integration-transfer-20260918/`.

The independent replay **passed**: it rebuilt all 192 target tasks, 384 source effect rows, 1,920 source and 960 target controller predictions, 734,800 predicted probe-output cells, 91,850 final candidate labels and all frozen policy choices.

## Same-bank results

| Zero-query first-choice policy | All 192 | Familiar 96 | Shifted 96 |
|---|---:|---:|---:|
| E0 | 31 | 19 | 12 |
| Familiar early top-100 | 64 | **54** | 10 |
| Shifted AB top-100 | 43 | 5 | **38** |
| Prior public-feature route | 67 | 36 | 31 |
| Fixed public confidence rule | **85** | 53 | 32 |
| Early verified-effect ridge controller | 87 | 53 | 34 |
| Later verified-effect ridge controller | 85 | 53 | 32 |
| Scrambled added effects | 84 | 51 | 33 |
| Balanced duplicate history | 86 | 53 | 33 |
| Later nonlinear effect model | 84 | 52 | 32 |

The two specialists' unavailable per-task hindsight choice would score **93**; the static confidence rule reached 85 of those 93 action-reachable tasks. The full candidate pool contained a correct program for **114/192** tasks and the old top 100 for **103**. Eight action-level mistakes, ten further top-100-reachable tasks missed by both specialist first choices, and eleven correct candidates below top 100 remain. Those are distinct evaluator, shortlist and search opportunities; none establishes that the controller improves itself.

## Cost and scope

The shared target generation produced 27,452 base candidates and 64,398 additional AST candidates. The existing preparation pipeline computed 734,800 predicted probe-output cells, and each of the A, AB and familiar top-100 models scored 19,092 candidates. The fixed confidence route does not require new paired-effect feedback after the two specialists are trained. The learned controller used 192 early and 192 additional verified task effects plus controller inference, yet did not beat the static rule. Equal output-call count does not imply equal total acquisition or inference cost.

A minimal reusable selector in `dual_specialist_seed_evaluator.py` removes the unused A and task-type model passes. Given only public `id` and `visible` task fields plus the public candidate record, it reproduced **all 192 audited confidence choices** and scored 38,184 candidates across the two specialist models. The durable check is `analysis/dual-specialist-seed-equivalence-20260918.json`. Candidate generation and any remaining pipeline preparation costs are separate from this selector cost.

The supported seed for this **synthetic mixed familiar/shifted AST contract** is the two specialist rankers with the frozen public confidence comparison. Retain E0 as fallback outside those tested mechanisms. Do not claim transfer to research, cybersecurity, social-good or policy tasks, open-ended RSI, or an improving improver from this result. A later controller must beat its earlier self and fixed confidence on a new matched bank before the feedback-loop claim advances.
