# Region-acquisition improver transfer

Predeclared 2026-09-20, before any fresh bank for this study is generated.

## Why this action space

Every previous improver test in this project chose among **whole-bank** policies:
a training rule, a threshold, a temperature, a width schedule. The opened
headroom audit measured what an unavailable oracle could gain from that class of
choice: **5 correct tasks per 576 on one run and 8 on another**
(`analysis/edit-catalog-headroom-20260918.json`). Paired bank noise on the same
runs was about the same size. Those gates were therefore unfalsifiable in the
positive direction: a perfect improver would have failed most of them.

This study moves the improver to a **task-level acquisition action** whose
opened headroom is an order of magnitude larger. On three opened 576-task
panels, installing per-region candidate specialists raised correct zero-query
choices from E0's 327/344/349 to 423/412/418
(`analysis/region-specialist-repayment-development-20260920.json`).

## The decision under test

A region is one of the six public task families; family is exactly recoverable
from the public Unicode block, so region identity uses no hidden metadata.

One **acquisition unit** buys every verified top-100 candidate label for one
region across the two source panels (`candidate-reranker-transfer-20260918`,
`candidate-reranker-replication-20260918`) and trains that region's specialist
reranker. The improver's decision is which regions to buy.

Opened per-region repayment over E0, by panel:

| region | cost | c-query-cost | combined-ranker | c-conditioned | mean |
| --- | --- | --- | --- | --- | --- |
| ast_transition | 1 unit | +32 | +32 | +19 | 27.7 |
| transform_transition | 1 unit | +28 | +18 | +27 | 24.3 |
| novel_operator_transition | 1 unit | +10 | +14 | +17 | 13.7 |
| stack_transition | 1 unit | +8 | +5 | +9 | 7.3 |
| self_edit_transition | 1 unit | +4 | +5 | +4 | 4.3 |
| mutation_transition | 1 unit | +14 | -6 | -7 | 0.3 |

Mutation is the informative region: one panel ranks it third, three panels rank
it last. An improver that has only seen the first panel should buy it; an
improver that has seen all three should not.

## Budget

**B = 3 acquisition units.** Declared reason, from opened development only:
B=3 is the smallest budget at which the initial and later parents select
different region sets. At B=2 both select {ast, transform} and the comparison
has no power; at B=4 they differ only on a region pair whose expected separation
is smaller. Sizing an experiment so its arms differ is a design step, not an
outcome; no fresh bank existed when B was fixed.

## Parents

All parents share the same frozen base system (E0 reranker, identical candidate
pools and candidate order), the same six trained specialists, the same budget B
and the same selection rule. They differ only in inherited repayment records.

| parent | inherited records | expected selection |
| --- | --- | --- |
| `initial` | 1 opened panel (c-query-cost) | ast, transform, mutation |
| `later` | 3 opened panels | ast, transform, novel_operator |
| `duplicate` | the initial panel repeated 3x | ast, transform, mutation |
| `scrambled` | 3 panels, region labels permuted within panel | rule-determined |
| `empty` | none; declared default = 3 largest mean-pool regions | ast, novel_operator, stack |

`duplicate` is the control that carries the claim: it holds the same number of
records as `later` and the same information as `initial`. A `later` advantage
over `initial` that `duplicate` also shows is record volume, not knowledge.

Selection rule, identical for every parent: take the B regions with the highest
mean observed repayment; break ties by region name ascending.

Fixed controls: `largest_pool`, `all_six` (six units, cost-unmatched ceiling
reference), and `e0` (no specialist). Unavailable reference: `oracle_b3`, the
best 3-region set scored on the fresh bank with final labels.

## Banks

Fresh seeds, generated only after this file is hashed into the run manifest.

- Bank A, admission: 6 banks x 48 tasks = 288, six families, seeds 907100-907105.
- Bank B, transfer 1: 12 banks x 48 tasks = 576, six families, seeds 907200-907211.
- Bank C, transfer 2: 12 banks x 48 tasks = 576, six families, seeds 907300-907311.

## Child improvers

Each parent P produces a child improver C(P) by transmitting its repayment
estimates. C(P) observes verified repayment for all six regions on bank A, adds
that single observation to its inherited records, reapplies the same selection
rule, and allocates B=3 on bank C. Every child starts from an identical frozen
base. The admission observation is common to all children and equally charged.

## Endpoints and gates

Scored on zero-query top-choice correctness. Uncertainty is the exact
bank-bootstrap interval over paired per-bank differences, as used throughout
this project.

- **G1, evaluator component.** The installed-specialist system beats E0 on bank
  B. Pass: total gain > 0 and the paired 12-bank interval excludes 0.
- **G2, improver growth.** `later` beats `initial` on bank B. Pass requires all
  of: total gain >= +6; at most 4 of 12 losing banks; paired interval excludes
  0; and `later` >= `duplicate`.
- **G3, recursive child growth.** C(`later`) beats C(`initial`) on bank C, under
  the same three thresholds, plus C(`later`) >= C(`duplicate`).

G2 and G3 are separate claims. G1 passing does not discharge either.

## Secondary, reported but not gated

- Per-region realized repayment on banks B and C against the opened estimates,
  as forecast error for the improver's own predictions.
- Regret of each parent's selection against `oracle_b3`.
- Resource vector: acquisition units bought, candidate labels charged,
  candidates rescored at deployment, and preparation wall time.

## Declared limits

- One synthetic string/program benchmark. No claim transfers to research,
  security, policy or social-good domains.
- Specialists share E0's candidate pool and order, so this measures ranking, not
  coverage.
- The budget was chosen on opened development data so the arms would differ.
  That makes G2 a fair test of whether extra history helps, not an unbiased
  estimate of how often a budget of 3 would matter in deployment.
- A `later` win over `initial` and `duplicate` shows that this improver used
  more verified history to make a better purchase. It does not by itself show
  open-ended recursive self-improvement.
