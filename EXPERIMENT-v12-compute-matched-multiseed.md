# V12 protocol: compute-matched multi-seed frontier study

Status: planned protocol. This document addresses the limitations exposed by
the audited V11 run; it is not evidence that V12 has been executed.

## Why V12 is needed

V11 passed its independent archive audit, but its engineering screen failed
and RSI remains unproved. The three training seeds shared one final task bank
and one bootstrap. Equal sampling ceilings and optimizer steps also did not
make total compute or target-token consumption equal across arms. The bounded
DSL and finite-example oracle limit the claim to observed correctness in this
task family, and same-host hashes do not authenticate a hostile host.

## Primary design

- Use five predeclared training seeds: `17, 29, 43, 59, 71`.
- Generate three independent final-bank groups after the protocol is frozen.
  Each group has 128 tasks; validation has 64 tasks per round and harvest has
  192 tasks per round. No final task is used for admission or checkpoint
  selection.
- Use the same arm definitions, model revision, tokenizer, prompt format and
  training schedule for every seed and bank group. A seed is never described
  as an independent replication when its bank or bootstrap is shared.
- Add a template-disjoint out-of-distribution bank with held-out operation and
  composition mixtures. Score it only after all decisions close.
- Keep the strict independent oracle and the finite-example wording: success
  means passing the declared hidden examples, not all-input program
  equivalence.

## Matched-budget rule

The primary comparison is made on a common-cost frontier, not on a common
search ceiling. Before bank generation, freeze a vector budget for every arm
covering at least:

`search expansions`, `generated nodes`, `primitive executions`, `oracle
checks`, `prompt tokens`, `generated tokens`, `supervised tokens`, `optimizer
steps`, and `wall/process time`.

The runner must stop or censor an arm when it reaches any component cap. An
arm is compared only through the largest prefix affordable by every arm, or
through an identical predeclared vector cap. Any unused budget and any
censoring are reported. A single scalar cost is a display summary only; the
vector is authoritative.

Shared bootstrap and common harvest work are recorded once in a `shared`
bucket. Arm-specific sampling and training are charged to the owning arm.
The `rsi.accounting` helpers and unit tests define the required split between
shared and arm-specific vectors. The historical runner remains unchanged
because its sealed fixture pins the runner source hash; the V12 executor must
integrate these helpers and enforce the caps during execution.

## Advancement screen

The primary effect is later-improver pass@64 minus its identical ancestor on
the common-cost frontier, averaged across the predeclared seed-by-bank cells.
Advance only if all of the following are true:

1. the audit passes and the archive is unchanged;
2. the mean primary contrast is positive with no post-hoc arm or checkpoint
   selection;
3. the contrast is positive in at least two of the three bank groups and four
   of five seeds;
4. validation pass@1 and pass@64 do not regress, while fresh final coverage
   improves; and
5. the result beats both the frozen bootstrap and the unadapted base under the
   same cost vector.

Report every cell, every rejected or censored arm, the full cost vector,
bank-level contrasts, and uncertainty intervals. Do not convert this screen
into a claim of general RSI, unrestricted algorithm invention, inheritance,
or mission-domain benefit.

## Trust and reproducibility limits

Retain the independent auditor, detached artifact manifest and pre-registered
source snapshot. Copy the manifest, audit receipt and result hashes to an
independent location before interpreting the outcome. These controls improve
reproducibility and detect later archive changes; they do not protect against
a malicious host that controls execution and the oracle.
