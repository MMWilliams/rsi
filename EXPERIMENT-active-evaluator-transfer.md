# Active evaluator transfer: frozen protocol

Frozen before generating the confirmation bank on 2026-09-17. This is a scoped
test of evaluator policy transfer, not a test of general intelligence or of a
self-improving improver.

## Question and conditions

Can a probe policy learned from 384 development tasks choose a single oracle
query better than the strongest fixed one-query rule on new AST transition
tasks? The primary comparison is pairwise learned versus uniform minimax.
The secondary comparisons are ridge learned, entropy, deterministic random,
and no query. A two-query weighted-entropy policy is a separate, higher-cost
reference. All policies see the same candidate pools and eight unlabeled probe
inputs per task. Each selected query reveals one target output from the
external oracle, then the evaluator chooses the highest-ranked consistent
candidate. Final correctness is judged on 14 disjoint examples.

## Frozen data and budgets

- Source: `analysis/probe-policy-development-v4.json`, seed 209501, 384
  development tasks, whole-task cross-validation performed before this test.
- Initial candidate ranker: checkpoint I0 from audited `runs/seed-low-9000`.
- Confirmation: six fresh banks of 64 AST transition tasks, seeds
  902117 through 902122; two visible examples, eight unlabeled probe inputs,
  14 final examples. Candidate sources V67 and V73, cap 128 per source,
  deduplicated. These task seeds have not been inspected in this study.
- The pairwise and ridge models are fitted once on all 384 source tasks.
  No confirmation labels may alter weights, feature definitions, or budgets.
- Each one-query policy uses exactly one output query per task with candidates.
  Deterministic ties use the lowest probe index. Random choice uses a task-ID
  SHA-256 key. Count candidate-generation time, candidate executions, and
  oracle output queries separately.

## Outcome and decision rule

Primary endpoint: paired difference in number of tasks with a selected
candidate correct on all 14 final examples, learned minus minimax, reported
per independent bank and in aggregate. Also report wins/losses/ties by task,
candidate reachability, no-query ranker correctness, and source training cost.
An observed positive aggregate difference is exploratory unless it is positive
on at least four of six banks and the paired bank-level 95% bootstrap interval
excludes zero. The bank-level rule is deliberately hard given the small
development edge. Failure is a measured null, not license to retune on these
banks. A positive result supports policy transfer only within this generator
family. A stronger evaluator-improver claim still requires same-base improver
checkpoint and child-improver tests.

The prepare stage saves candidate pools and all probe decisions before any
confirmation probe output or final correctness is evaluated. The score stage
reads those frozen decisions, uses output labels, and writes a separate
result. The runner source and frozen source data hashes are recorded in the
prepare manifest. The sealed bank is a local file and is not protected by an
independent access-control boundary; the safeguard is frozen code flow and
auditable decision records.
