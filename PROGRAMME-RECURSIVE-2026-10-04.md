# Programme: recursive growth through drawn levels

Written 2026-10-04 after C-growth (`COACH-RESULTS-2026-09-23.md` §16). Plan,
not result. Every phase below has a screen that can stop it before machinery is
built.

## 1. Where the record stands

Confirmed, predeclared and audited, in the mechanism environment: G1
(within-world growth), G2 (transfer to unseen family combinations), C-family (a
family-level world model moves the tight-budget wall), C-growth (a grouping
learned without labels improves acquisition with worlds seen, past the point
where the pair prior saturated). Closed by protocol or argument: the RL coach,
metric-world transfer (G4-G6), unfamiliar-family transfer by prediction (G3,
the boundary is syntactic), joint world retrieval. Era 1 (seed improvers on the
string DSL) stays closed: every improver was dominated by a capacity-matched
pooled model and every recursive transmissible state failed P2c.

Three things are still fixed, and recursive growth needs each of them to move:

1. The within-world learner (order, scan, pick, keep atoms) is one rule for its
   whole life.
2. The representation learner (`rsi/learned_groups.py`: PMI, spectral,
   likelihood-selected group count, slip 0.05, three groups per world) is
   researcher written. C-growth grew its input, not the learner.
3. The hypothesis language is closed: the truth is always in the 166,596-row
   catalog, so the agent never extends its own reach.

One accounting gap: C-growth learned groups from true world atom sets that were
handed over. Rule 11 was applied at levels 0 and 1 and not at the level where
the representation is built.

## 2. Diagnosis

Every recursive test failed the same way: a free default already captured the
transmissible state's value (partition scheme +1 to +13, acquisition policy
-21, regime boundaries never wrong). The old environment had one level of
structure, so a parent held nothing a researcher could not write down.

What has worked three times (cold-start prior, family posterior, learned
groups) is hidden structure that is *drawn*, so a held-out instance is a random
variable, plus a representation that applies *before* the agent has evidence.
Each gain was largest exactly where the free rule had nothing to act on.

So apply the pattern one level up. Worlds are drawn from an environment; draw
environments from a meta-distribution. Then the representation learner has a
random variable to generalize over, and a parent that has lived many
environments holds something that a child with a few earned worlds cannot
recover and a default cannot encode: which learner to trust, and how early.

## 3. The framework

Nested drawn levels, every level earned, one resource vector, a label-free
internal evaluator, a capacity default and a hedge at every level.

| level | component | resource |
| --- | --- | --- |
| L0 | solver: the earned loop | scans per task |
| L1 | world model: groups + posterior over the world's group set | worlds lived |
| L2 | representation learner: earned world sets → L1 | environments lived |
| L3 | learner selector (new): early co-occurrence statistics of a new environment → L2 configuration and trust threshold | environments lived |

- **Internal evaluator**: held-out likelihood of earned worlds under a
  candidate grouping (already in `learn_groups`), and for the invention axis
  "does a candidate atom make unsolved tasks consistent". Both label-free.
- **Forecaster**: interval forecasts per gate cell committed before every
  confirmation, scored by a proper rule afterwards. Never done so far; costs
  nothing.

The four objects of `PROGRAMME-TARGET-INTELLIGENCE-GROWTH-2026-09-21.md`:
intelligence = acquisition curves on held-out worlds and environments at frozen
resources; improvement productivity = cumulative tasks per total resource
vector with every level earned; evaluation reliability = rank correlation
between the internal score the agent used and the realized acquisition gain;
forecasting accuracy = proper score per confirmation.

Standing requirements, each bought already:

- Three resource axes (scans, worlds, environments); a gate holds across the
  whole range of each (rule 8).
- Floors stated per cell relative to measured oracle headroom, never an
  absolute count (the G5 flaw).
- "One larger model on the same worlds" in every default set: a rank-r
  co-occurrence factorization with soft membership at r in {4, 8, 16, 32}.
- Every acquired state interleaved with the no-state order at a reserved share;
  its cost measured in support and its bound out of support, across the whole
  range (rule 6 as corrected).
- Shared random tie-break; full-sort reference replay for every new simulator
  path; sealed seeds; one confirmation per claim, no re-gating on seen results.

External work that maps (wake/sleep library learning, Bayesian model selection
by held-out likelihood, hierarchical learning-to-learn, open-ended environment
generation) is not cited until read directly.

## 4. Phases

### Phase 0, housekeeping

- Merge `worktree-learned-groups` into `master`.
- Correct rule 6 in `MECHANISM-GROWTH-RESULTS-2026-09-21.md`, the paper draft
  §6.4 and `.claude/TODO.md`.
- Re-run cold start with the stream reservation fixed before quoting it.
- Record CPU time, peak memory and failed-run count from here on.
- Add a forecast-commitment step to the confirmation runner template.

### Phase 1, charge level 2: C-growth-earned

Learn groups from the atom sets the agent itself acquired in its own lifetimes
at budget B (noisy: wrong picks import foreign atoms), not from true sets.

- Arms: groups from 400 and from 1,600 earned worlds, B in {128 … 4096}.
- Controls: handed-set groups (the C-growth arm, as an upper reference),
  permuted labels, rank-r factorization on the same earned sets, no grouping.
- Gate: 1,600 earned beats 400 earned summed over cells, both replications.
  Report every cell where earned groups are worse than none; this regime will
  now depend on B.
- If it fails, denoising (weight atoms by evidence count, use only atoms of
  picks consistent with every visible example) is the level-2 improvement
  target, with headroom measured by the handed-set reference.

This is the next run: it applies rule 11 where it has not yet been applied.

### Phase 2, the meta-environment and the first recursive claim

**Build.** `make_environments(seed)` draws θ per environment: groups per world
g in {2 … 5}, family count F in {6 … 12}, slip s in {0, .05, .15}, group-size
skew, optionally a two-level hierarchy. Worlds are drawn from θ as now. Splits
at level 2: seen θ, unseen θ combination, unseen g (out of support: no gain
claimed, only the hedge's bound).

**Screen M1, default regret at level 2.** L2 grid: per_world in {2 … 5}, slip,
affinity (PMI, raw, Jaccard), clustering (spectral, agglomerative), group-count
rule, trust threshold N in {4, 8, 16, 32, 64} earned worlds. Oracle: best grid
point per environment on held-out worlds. Fixed: best single grid point across
environments. Capacity default: rank-r factorization. Default regret must clear
a floor stated as a share of oracle headroom. If one fixed L2 is near-oracle
everywhere, widen the meta-distribution before building anything.

**Screen M2, learnability.** Fit a selector on environments 1..k from
statistics visible after N earned worlds (co-occurrence spectrum, degree
distribution, likelihood-curve shape); test on k+1. It must beat held-out
likelihood alone with the interval off zero at small N. If likelihood alone is
near-oracle at every N, level-2 selection is free, report that, and go to
Phase 3.

**R1, child acquisition under a transmitted selector.** The parent lives E
environments and hands the child the fitted selector and trust thresholds,
nothing else. The child enters a held-out environment at a fixed per-task
budget and lives W worlds.

- Endpoint: cumulative tasks over the child's first W worlds, at W in
  {4, 8, 16, 32, 64} and B in {128 … 4096}.
- Comparators: fixed L2 with held-out likelihood (the free rule); the
  selector on permuted statistics; the capacity default; the selector trained
  on handed rather than earned environments; a scrambled-state child.
- Hedge: a share of the child's worlds run the fixed L2.
- Gate: above the free rule at every W and B on seen θ and unseen θ
  combinations, non-inferior on unseen g, both replications. If the pattern
  holds the gain sits at small W.

**R2, compounding at level 2.** Selector fitted on 4, 8, 16, 32, 64
environments; the R1 margin must rise monotonically. Control: environments from
a degenerate meta-distribution (one θ), where nothing accumulates.

A pass would be a later parent improving the process it hands on, on earned
experience at every level: this repository's definition of recursive growth,
met for the first time, in one environment family. It says nothing about the
solver rule, the hypothesis language or another domain.

### Phase 3, the hypothesis-space axis

The G3 wall is syntactic, so prediction from behaviour cannot cross it;
construction from the grammar can. Seed the solver with atoms from a subset of
families and parameter ranges and let it extend its atom set from the ord_expr
operators in `_char_predicate`, with enumeration charged in the scan unit
(declare the conversion). The 368 atoms are a hand-picked subset of a grammar
with thousands of depth-one expressions, so where to look is real structure,
and the L1 posterior predicts which operator subtrees to expand. Check
`rsi/expression_synthesis.py` and `rsi/primitive_synthesis.py` for reuse.

- Screen I1: headroom (full catalog vs seed catalog on worlds needing a missing
  family), default regret (oracle extension vs breadth-first grammar
  enumeration at matched cost), learnability.
- H1: a guided inventor reaches more at matched total budget than breadth-first,
  random extension and no extension.
- H2: an unfamiliar family becomes reachable at finite budget at all (a reach
  claim; speed claims in support only).
- Invented atoms enter the co-occurrence data L2 learns from; L1 directs
  invention.

This deliberately reintroduces coverage failure. Keep it a separate environment
variant with the full catalog as the oracle bound.

### Phase 4, closure

All levels earned in one lifetime (environments, worlds, tasks), one resource
vector matched coordinate by coordinate. Factorial with each level frozen in
turn: L0; L0+L1; L0+L1+L2; all four. Common-state replay and inheritance-reset
probes. Endpoint: cumulative tasks per total resource vector, beating every arm
with a level frozen. Forecasts committed before each run and the forecaster's
score reported as its own curve.

### Phase 5, environment or readout

A second task form in the same catalog (the answer is the second run, or a
two-predicate composition) as a drawn variable, then a second alphabet or
domain. Without it every claim remains "one task form, one hypothesis
language".

## 5. Not doing

- Reopening the coach, metric worlds or joint retrieval.
- A neural model in the treatment arm. It belongs in the default set as the
  capacity baseline.
- The four-domain IRT programme. Its factorial runs in hours here.
- Selection: Occam is within 0.3 points of exact Bayes. An evaluator only
  matters if the task form changes (fewer or noisy examples), a Phase 5
  question.
- Any phase without its P2c/P2d screen.

## 6. Order and rough cost

Phase 0-1: this week (Phase 1 is minutes per panel on the fast simulator).
Phase 2 screens: next week; R1 confirmation the week after. Phase 3: through
late October. Phase 4: November.
