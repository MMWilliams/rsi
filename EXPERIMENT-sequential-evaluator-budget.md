# Sequential evaluator budget transfer: frozen protocol

Frozen before generating the final banks on 2026-09-17. Prior active-evaluator
confirmation banks `902117..902122` were inspected and are now development
data for this separate question.

## Question

Does a retained evaluator learn from old feedback which tasks deserve a
second oracle output query? The first query on every task is selected by the
same fixed weighted-entropy rule. After that answer, every policy sees the
same surviving candidate pool. A learned ridge effect predictor ranks tasks
by predicted *incremental correctness* from a second query. The second probe
input itself is selected by the fixed weighted-entropy rule. The learned
component is only the allocation policy.

## Development and frozen choice

- Source: 384 inspected tasks in `runs/active-evaluator-transfer-20260917/`.
  Six-bank leave-one-bank-out development results were used to select 16
  second queries per 64-task bank. At that budget the learned allocation
  scored 287/384 versus 281 for fixed entropy allocation, 279 for fixed
  top-disagreement, 261 for survivor count and 261 for deterministic random.
  This is development evidence, not confirmation.
- Train the ridge effect predictor once on all 384 source tasks using the
  features in `sequential_budget_development.py`, fixed penalty 10.
- Six untouched 64-task AST banks, seeds `902123..902128`, two public examples,
  eight probe inputs, 14 final examples, V67/V73 candidate cap 128 each.
  The audited I0 initial ranker and candidate sources remain fixed.
- Each policy receives 64 first-query outputs and may buy 16 second-query
  outputs per bank, exactly 80 output queries per bank. Static allocations:
  second-probe entropy, top-candidate disagreement, survivor fraction, and
  deterministic random. Same second-query mechanism for every allocation.
  Also report one-query and all-two-query endpoints at their actual budgets.

## Endpoint and gate

Primary endpoint: learned minus fixed entropy correct solutions on all 14
final examples, paired by task and reported per independent bank. Report
other fixed controls, reachability, source acquisition cost and candidate
execution cost. A retained evaluator-growth claim requires learned to win at
least four of six banks and a bank-level 95% resampling interval above zero.
Otherwise it is a null. Do not retune on these banks.

Prepare writes candidate pools, first answers, feature vectors and *all*
second-query allocation decisions before any second answers or final labels
are used. Score then opens second answers and final examples. Frozen source
and runner hashes are recorded. This is code-flow separation with auditable
records; local bank files are not access controlled by an independent host.
