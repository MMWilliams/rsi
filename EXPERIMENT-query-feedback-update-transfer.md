# Incremental query-value feedback: frozen transfer protocol

Frozen before generating seeds 902264–902269 on 2026-09-17.

The common evaluator is the same temperature-0.25 listwise ranker, candidate sources/caps, eight public probe inputs, maximum-entropy probe among its top 16 candidates, and full-pool reranking after one exact oracle output. Every active policy buys exactly **95 output queries across six new 32-task banks**; all query allocations and probe indices are frozen before outputs are read. Final scoring uses 15 separate examples per task. Candidate source training used 31,500 verified labels and is common to every arm.

The feedback edit updates the 18-feature ridge query-gain predictor from 192 to 384 verified development tasks by adding the second six-bank study. Its penalty stays 10 and feature schema stays fixed. The new feedback was acquired by counterfactually evaluating one public probe on every added development task, then measuring its final-task gain. Compare:

- **Updated:** genuine 384-task query gains.
- **Previous:** frozen 192-task model, no update.
- **Scrambled update:** same 384 feature rows and gain prevalence per new bank, with new gains shuffled within each bank.
- **Duplicated prior:** 384 rows formed by repeating the original 192 tasks; a row-count/optimization control without new information.
- **Fixed top disagreement:** strongest prior static allocation rule at the same query budget.
- **No query:** resource reference.

The primary endpoint is updated minus previous final top-choice correctness. A supported incremental evaluator upgrade requires wins on at least five of six banks, a strictly positive exact six-bank resampling 95% interval, and higher aggregate correctness than fixed top disagreement, scrambled update, and duplicated prior. Report source acquisition cost separately; the policies have identical live query, candidate, and ranker budgets.

Preparation freezes model outputs, public features, probe plans and 95-task allocations before oracle outputs or final labels are opened. An independent audit must regenerate pools, allocations and final outcomes. Even a positive evaluator update would not by itself establish a better improver or child improver.
