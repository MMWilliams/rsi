# RSI to-do

## Programme, 2026-10-04: recursive growth through drawn levels

Plan in `PROGRAMME-RECURSIVE-2026-10-04.md`. Levels L0 solver, L1 world model,
L2 representation learner, L3 learner selector; every level earned, hedged,
with a capacity default. Screens gate every phase.

- [ ] **Phase 0.** Merge `worktree-learned-groups` into `master`. Correct rule 6
      (results file, paper §6.4, rule list below). Re-run cold start with the
      stream reservation fixed. Record CPU time, peak memory, failed runs.
      Add forecast commitment to the confirmation runner template.
- [ ] **Phase 1, C-growth-earned (next run).** Groups learned from atom sets the
      agent earned at budget B, 400 vs 1,600 earned worlds; controls handed-set,
      permuted, rank-r factorization, none. Report cells where earned groups
      are worse than none. If it fails, denoising is the L2 target.
- [ ] **Phase 2.** `make_environments` (θ: groups per world, family count, slip,
      skew, hierarchy). Screen M1 (L2 default regret vs per-environment oracle
      and rank-r default), M2 (selector from early statistics beats held-out
      likelihood at small N). Only then R1 (child under transmitted selector,
      every W and B) and R2 (compounding over environments).
- [ ] **Phase 3.** Atom invention from the ord_expr grammar, charged in scans;
      screen I1, then H1 (guided beats BFS at matched budget) and H2 (unfamiliar
      family reachable). Separate environment variant.
- [ ] **Phase 4.** All levels earned in one lifetime; factorial freezing each
      level; productivity per total resource vector.
- [ ] **Phase 5.** Second task form as a drawn variable, then a second domain.

## Status, 2026-09-21 (evening)

**Growth is demonstrated, in a new environment, and its boundary is located.**
`MECHANISM-GROWTH-RESULTS-2026-09-21.md`. Mechanisms are now *drawn* from a
catalog of 166,596 predicates rather than chosen from six hand-written
families, so a held-out mechanism is a random variable and a held-out world and
family are too.

| claim | status |
| --- | --- |
| within-world growth (G1) | **passed**, both replications: experience of 32 of a world's mechanisms beats every experience-free order by +1601 and +1603 of 1920 tasks at budget 256, and beats another world's experience by +1643 and +1644 |
| transfer to an unfamiliar world (G2) | **passed**, both replications, every budget: +127 to +204 of 640 over the best free rule on worlds whose family combination was never trained, with the no-structure and scrambled controls beaten. Worth four to five solved mechanisms of the new world |
| transfer to an unfamiliar family (G3) | **withdrawn**. Passed the predeclared gate at budget 1024 (+22 to +35) and is significantly negative at 256 and 4096. The gate read one budget; that was the flaw |
| why that boundary never falls | it is **syntactic**: clustering atoms by behaviour recovers the family labelling at adjusted Rand 0.144, so nothing computable on an atom can see it. No behavioural representation could have crossed it |
| transfer on worlds whose structure *is* behavioural | **three predeclared gates, three failures** (G4, G5, G6). G4 asked for something unidentifiable: 368 atoms cannot pin down 385 weights, and reducing the descriptor to 32 components recovers the weighting at 0.92. G5 and G6 then recovered it at Pearson 0.90-0.98 and beat both the free rule and a permuted copy at every cell of budgets 4096 and 16384 in every replication, and failed at the tightest budgets; in G6 replication 2 the permuted copy *beat* the metric at k=2, budget 256 (-22 [-36, -9]). G6 replication 1 passed every cell. **The claim is not made**, and no fourth gate may be restricted to the budgets that worked |
| selection among consistent hypotheses | no headroom: a fitted selector reaches 0.785 and 0.825 under mechanism and family holdouts against 0.787 and 0.830 for "pick the smallest consistent set". The binding constraint is reaching a good hypothesis, not choosing among those in hand |
| compounding | the acquisition margin rises monotonically with worlds seen (25 to 400) in all six cells and has not saturated; the no-structure control stays flat |
| the earned loop | closes at every budget from 128 to 4096, with no outcome feedback; a cold-start prior learned from other worlds takes it from 16% to 63% of the informed ceiling at budget 1024 |
| an RL-trained coach for the earned loop (2026-09-23) | **not confirmed, line closed**: first confirmation's deployment step abstained at 1024-2048; second deployed at 256 and lost there on untrained combinations (-328). Large generous-budget gains in both, ungated. `COACH-RESULTS-2026-09-23.md` §11-12 |
| a family-level world model at tight budgets (2026-09-23) | **confirmed, both replications, audited**: gains at every budget 128-4096 on trained and untrained combinations (+248 to +1,635 of 12,800), no loss on untrained-family worlds. The first predeclared tight-budget growth result. `COACH-RESULTS-2026-09-23.md` §14 |

The earlier programme's verdict stands for the old environment:
`WHAT-WORKED-WHAT-FAILED-2026-09-21.md`, archived in
`.claude/ARCHIVE-2026-09-21-growth-programme.md`.

| old claim | status |
| --- | --- |
| improver growth, routing | C1 +22/+23 and C2 +36/+47 hold as stated and reproduce to the integer, but one 60-leaf pooled model on the same history beats the routed system by 35 and 29 |
| improver growth, construction | withdrawn: capacity-matched pooled beats the built system by 50 and 36; in-sample router fitting inflated rep 1 by +14 |
| verifier growth | within-distribution only: worse than base E0 on **every** held-out mechanism (716 vs 1020), and the regression worsens with capacity |
| recursive growth | not found in three tested transmission classes |
| intelligence growth (adopted definition) | none demonstrated |

**Every transfer number in this repository is instance-level.** All frozen
panels are fresh seeds of the same six generators.

### The four rules that came out of it

1. **P2 / P2b / P2c / P2d** screen an action space before an improver is built
   for it (`TECHNICAL-DESIGN-EXPERIMENTATION-2026-09-20.md`). Screen the
   *transmissible state* too, before any recursive machinery.
2. **The adversarial default must include model capacity**: one larger model on
   the same labels, at several sizes. This clause was missing and it ended every
   improver claim.
3. **Score a small-history arm as an expectation over windows**, never one
   predeclared seed. One draw made two replications disagree by 54 points.
4. **Every evaluator claim reports held-out-mechanism performance at the
   deployed capacity**, and must not regress below the base there.

Reproduction audits reproduce flawed specifications faithfully. Reproduction,
information-flow, adversarial-baseline and mechanism-holdout checks are four
separate required steps.

### Five more rules, from the mechanism environment

5. **An acquired prior must never overrule present evidence.** The one collapse
   observed was entirely this: an atom seen solving a task *in the world at
   hand* was scored zero because training had not seen it.
6. **Hedge every acquired prior**: reserve a share of the budget for the rule
   the agent would use with no prior at all. Half the budget turned the
   out-of-support failure from nothing into +121 [26, 213] and cost nothing in
   support. No detector needed; the one tried never fired.
7. **Generalization reaches exactly as far as the representation it is stated
   over.** An identity prior cannot reach an unseen atom by construction.
8. **A gate must be read across the whole resource range, not at a point.**
9. **Tie-breaks are part of an arm.** Share one random tie-break or the
   baseline inherits a preference nobody declared.
10. **When a prior applies matters as much as how good it is.** A prior that
    conditions on what the agent has already achieved is absent for the stretch
    that decides whether it achieves anything.
11. **Charge the experience, or you are measuring a different quantity.**
12. **A cruder estimator can beat a better-specified one** at the evidence
    levels where a prior is actually needed.
13. **Do not read a threshold off two points.**

## Open

### A coach trained by RL on lifetimes (started 2026-09-22)

An external component whose parameters set the earned loop's free choices
(scan-order weights, retention, pick rule, hedge, allocation over time),
trained by policy search on the return of whole lifetimes in training worlds.
`rsi/growth_coach.py` (fast exact simulator; reproduces the audited
static/blind/warm/hedged/revealed arms hit for hit, `tests/test_growth_coach.py`).

- [x] Screen 1, seven order/retention/pick levers, hedge fixed at 0.5
      (`mechanism_coach_screen.py`). **No headroom by its predeclared rule**:
      the in-sample optimum's share of the champion-to-ceiling gap is 0.072,
      -0.001, 0.093, 0.175, 0.245, 0.489 at budgets 128-4096. The class only
      has room at generous budgets, which would reproduce G5/G6's shape.
      Soft retention is harmful at every setting; count evidence (0.5) is the
      best single lever. The in-sample coach also beats the champion on
      new-family worlds at every budget (+20 to +162 of 1600).
- [x] Screen 2, hedge share, hedge slope in log budget and allocation tilt
      added; optimum taken jointly over in- and out-of-support worlds
      (`mechanism_coach_screen2.py`). **No headroom by rule, same wall**:
      in-support gains 0.078, 0.011, 0.067, 0.209, 0.371, 0.808; out of
      support positive everywhere (0.034-0.575). The optimum front-loads the
      budget as far as allowed (tilt 0.95) and leaves the hedge at 0.5 with no
      slope. At budget 256 no arm in either screen exceeds ~0.02 of the gap.
      Diagnosis: at tight budgets the window almost never holds a consistent
      candidate, so evidence never arrives and every lever acts on nothing.
- [x] Near-misses as an evidence channel (`mechanism_near_miss_probe.py`):
      **no signal**. Atoms of window rows that fit the positives and fail a
      negative (or the reverse) are world atoms 6-9% of the time against 6-7%
      for the window as a whole; only exactly consistent rows are enriched
      (68-79%), and they are rare at tight budgets. Near-miss ranking recovers
      world atoms no better than window frequency.
- [x] Does cross-world experience move the tight-budget wall?
      (`mechanism_prior_scaling.py`, priors on 25-6400 handed worlds, all six
      budgets, three held-out splits). **No: the pair prior saturates by about
      400 worlds everywhere**; 400→1600→6400 changes are within noise at every
      budget and split. Seen-triple at budget 256: 21.2 / 20.9 / 22.2 of 100
      at 400 / 1600 / 6400 worlds, ceiling 80.7. The tight-budget limit is the
      prior's *form*, not its data. Most of its value is generic (a prior from
      worlds with no family structure gets 10.4 of structured 14.9 at 128).
- [ ] **Rule 6 needs a correction.** On new-family worlds the half-hedged
      prior loses to no prior at budget 4096: -224 [-363, -97] at 400 worlds,
      -237 [-386, -103] at 6400 (`mechanism-prior-scaling-20260923.json`).
      The +121 that established the rule was read at budget 1024 only. The
      hedge bounds the loss to at most a halving of the budget (hedged 43.2 vs
      blind-at-2048 30.7), which is what it promises, but "costs nothing out
      of support" is false at generous budgets. Update the rule, the paper's
      6.4 and the results file.
- [x] Window rotation (`Coach.rotate`, `mechanism_rotation_probe.py`): part
      of each task's scans on a slice further down the ordering, moved every
      task. **Hurts or does nothing**: -0.012/-0.026 of the gap at 128/256 for
      a quarter share, -0.60 at 4096 for a half share; no arm earns a screen.
- [ ] **What the coach line has established.** Four measurements agree: the
      earned loop's tight-budget gap is informational. No policy over its own
      evidence (10 levers, in-sample, two screens) closes more than ~2% of the
      gap at budget 256; the scan yields no side-channel; the only pre-solve
      information source saturates. Progress at tight budgets needs a new
      *representation* of worlds (what a prior can express before the first
      solve), not a better policy and not more data.
- [x] Write-up of the coach line so far: `COACH-RESULTS-2026-09-23.md` (§6 dev
      study pending).
- [x] Dev ES training finished (40 generations, 5470 s). Final coach: hedge
      0.25 + 0.17·log2(B/1024) (none at 128-256, 0.62 at 4096), tilt 0.73,
      count 0.57, affinity 0.50, pick 0.22, depth1 -1.1. It learned a
      budget-dependent hedge that screen 2's search never found. Random search
      at matched lifetimes chose the opposite hedge (0.42 at 128, none at
      4096).
- [x] Dev study held-out results (`COACH-RESULTS-2026-09-23.md` §6). New
      combinations: +311 / +488 / +323 of 3200 at 1024 / 2048 / 4096, intervals
      positive; nothing at 128-256. **Not reliable**: new-family worlds lose
      -66 [-119, -10] at 256 and -124 [-208, -51] at 512; generation 10 lost
      748 at 4096. ES ties random search in support; random search collapses
      out of support (-724 at 4096); practice at unfamiliarity buys +19 to
      +228 out of support at no cost in support.
- [x] Guarded dev study (`mechanism_coach_guarded_dev.py`, seed 624101):
      hedge fixed at 0.5, hedged half forced to the fixed no-prior rule. Safe
      out of support (no significant loss on new-family worlds; +138, +269 at
      1024/2048) but **-106 [-155, -58] at 256 on new combinations**, worsening
      with training. The same trained parameters *without* the guard (hedge
      share still 0.5): no significant loss in any of 18 cells and gains at
      1024-4096 on all three splits (+176 to +456). Safety comes from holding
      the hedge share, not from constraining the hedged order. ES beat random
      search in 16 of 18 cells (it tied in support in the first dev run).
- [x] Independent reference for every lever (`reference_coach` in
      `tests/test_growth_coach.py`): full sorts, `interleave`, per-row scores;
      hit-for-hit with the fast simulator for count, affinity, pick, soft,
      depth1, tilt, rotate, hedge slope and the guard. 19 tests pass.
- [x] Fixed-hedge dev study (`mechanism_coach_fixed_hedge_dev.py`, seed
      625101): all 9 cells from 1024 up improve (+221 to +519 of 3200), no
      significant loss on new-family worlds, and **-96 [-169, -29] at 128 on
      new combinations**, growing with training. Would fail the drafted gate.
- [x] Lever ablation (`mechanism_coach_ablation.py`): resetting `count` alone
      removes the 128 loss (0 [-54, 53]). Trusting repetition entrenches wrong
      rows under a combination shift; in support it pays.
- [x] Practice dev study (`mechanism_coach_practice_dev.py`, seed 626101).
      Family-only coach at generation 40 passes every drafted cell; combination
      practice as a *training* signal did not help (-143, -220 at 128/256 on
      new combinations after the bug fix).
- [x] **Simulator bug found by the audit's replay check and fixed**: soft
      credit reused the name `share` and overwrote the hedge share. Screen 1
      unaffected; every affected arm re-scored (`mechanism_coach_rescore.py`).
      Withdrawn: dev run 1's "generation-10 collapse" (-748 → -114 n.s.).
      Every ES training run before the fix was biased by mis-scored soft
      perturbations. Regression test added; 20 tests pass.
- [x] High-confidence deployment (`mechanism_coach_validation_gate.py`, v2):
      deploy at a budget only if validation lifetimes of every kind
      (in-support, family shift, combination shift) show the coach's interval
      above zero. Retrospectively deploys at 1024-4096 on both fixed-hedge
      coaches and the deployed policy passes every drafted cell on both.
      Built into `mechanism_coach_confirmation.py` and its audit.
- [x] Dress rehearsal (`mechanism_coach_rehearsal.py`, dev seed 627101):
      deploys at 1024-4096, safe cells exactly zero, audit passed (75,313
      picks, 24 lifetimes replayed). Failed one improvement cell at 48 worlds
      (new combinations, 4096: +140 [-14, 288]); sample raised to 128 worlds
      per split from the rehearsal's per-world effects, criterion unchanged.
- [x] **Confirmation: C-coach failed as frozen** (`COACH-RESULTS-2026-09-23.md`
      §11; audit passed, 373,774 picks, 48 replayed lifetimes). Validation
      deployed the coach at 4096 only (A) and 512/1024/4096 (B), so the
      improvement cells at 1024-2048 read champion against champion. The
      family-shift validation kind (32 worlds) was the one short of
      significance every time. The **trained coach itself**, reported and not
      gated, passed all 36 cells: +664 to +2,165 of 12,800 at 1024-4096 on
      every split incl. an untrained family, no interval entirely negative at
      128-512.
- [ ] **Confirmation 2 running** (`EXPERIMENT-mechanism-coach-confirmation-2.md`,
      `mechanism_coach_confirmation2.py`): the byte-identical runner with one
      constant changed, validation worlds per kind 32 → 256 (sized from
      confirmation 1's validation variances), fresh seeds 961101/962101. The
      protocol says a failure ends this line; no third run.
- [x] **The tight-budget wall is not a property of the generator**
      (`mechanism_oracle_structure_probe.py`): told its world's three
      families, the earned loop solves 35.4 vs 18.2 of 100 at budget 256 and
      50.4 vs 25.6 at 512.
- [x] **A family-level world model moves it** (`rsi/family_inference.py`,
      `mechanism_family_inference_probe.py`): a posterior over family triples
      from the agent's own evidence (slip rate for wrong picks, prior from
      training-world triple frequencies) recovers about half the oracle's gain:
      27.6 vs 18.2 at 256, 37.8 vs 25.6 at 512, the whole gain at 128. In
      support, unhedged. Every policy lever before managed ~2% of the gap at 256.
- [x] Family inference development (`COACH-RESULTS-2026-09-23.md` §13): a
      training-frequency triple prior hurt on untrained combinations; a
      uniform prior fixed it; the sloped hedge lost at 512 out of support; a
      step hedge (none at 128-256, half from 512) passed on an untouched seed.
- [x] **C-family CONFIRMED** (`EXPERIMENT-mechanism-family-confirmation.md`,
      seeds 971101/972101, 128 worlds per split): gains at every budget
      128-4096 on trained and untrained combinations in both replications
      (+248 to +1,635 of 12,800), no significant loss at any budget on
      untrained-family worlds. Audit passed (381,853 picks, 48 replayed
      lifetimes). `COACH-RESULTS-2026-09-23.md` §14.
- [x] Coach confirmation 2 **failed**: with 256 validation worlds the rule
      deployed at 256, and the coach lost there on untrained combinations in
      replication A (-328 [-499, -158]). Audit passed. The coach line is
      closed by its own protocol; no third run.
- [x] Git: repo initialised 2026-09-23, first commit `103edc4` on `master`
      (no remote). `core.autocrlf` off locally so frozen protocol hashes stay
      valid; run journals, two >100 MB dumps and LoRA adapters are ignored.
      Work continues on branch `worktree-learned-groups`
      (`.claude/worktrees/learned-groups`, `vendor/` linked by junction).
- [x] **Learned grouping** (`rsi/learned_groups.py`,
      `mechanism_learned_groups_probe.py`, seed 633101): atoms clustered by
      positive PMI of co-occurrence across training worlds. Adjusted Rand
      against the families 0.15 / 0.84 / 0.89 / 0.89 at 100 / 400 / 1600 /
      6400 worlds; small families merge (rotmod into mod, which is a real
      regularity: viable rotmod worlds nearly always include mod). On learned
      groups from 1,600 worlds the family agent recovers ~80% of the syntactic
      agent's in-support gains, **improving past the 400 worlds where the pair
      prior saturates**, but loses at 256 on untrained-family worlds (-89 to
      -103, significant) and is weak at 256-512 on untrained combinations.
- [x] Likelihood-selected group count (`learn_groups(select='likelihood')`,
      5-6 groups): the agent on groups from 1,600 worlds matched the syntactic
      agent at every budget and split on seed 634101 and on the untouched seed
      635101 (64 worlds); groups from 1,600 beat groups from 400 in 15 of 18
      cells. Hedging from 256 only costs. Full-sort reference
      `rsi/learned_reference.py`, held pick for pick by tests.
- [x] **C-growth CONFIRMED, C-learned FAILED by one cell**
      (`EXPERIMENT-mechanism-learned-confirmation.md`, committed `515d109`
      before the run, seeds 981101/982101; `COACH-RESULTS-2026-09-23.md` §16;
      audit passed, groups relearned exactly). Groups learned from 1,600
      worlds beat groups from 400 by +6,993 and +8,077 tasks pooled over 18
      cells: acquisition of unfamiliar worlds grows with experience through a
      representation learned without labels. C-learned failed at untrained
      combinations, budget 512, replication A (+153 [-59, 367]), the cell the
      protocol named; B passed all 18; no safety cell failed.
- [ ] Next: budget 512 on untrained combinations is the one cell both the
      syntactic and learned agents are weak at (the hedge switches on there).
      Understand it before any further gate; do not predeclare a rerun of
      C-learned on the strength of this run's arms.
- [ ] Merge branch `worktree-learned-groups` into `master` (left to the user).
- [ ] Also open: model wrong picks better (slip is one constant); combine the
      family model with the coach's generous-budget levers, each under its own
      predeclared gate.
- [ ] Update the paper draft (`PAPER-DRAFT-drawn-mechanisms-2026-09-22.md`):
      rule 6 correction, the informational analysis, C-family, and the two
      failed coach confirmations.
- [ ] Confirmation ready but not frozen: `EXPERIMENT-mechanism-coach-confirmation.md`
      (DRAFT), `mechanism_coach_confirmation.py` (journals every decision with
      its example strings), `audit_mechanism_coach_confirmation.py` (rebuilds
      tasks from strings, interpreter sample, replays lifetimes through
      `rsi/coach_reference.py`). Smoke-tested end to end; the audit passes.
      The smoke touched seeds 941101/942101, so the frozen run must use fresh
      ones chosen when the protocol is frozen.
- [ ] Scope decision for any confirmation is **the user's call**: the screens
      found headroom only at budgets ≥ 1024, and a gate restricted to those is
      what the G5/G6 stop refused. Proposed form, which reads every budget:
      improvement required where the loop receives evidence (≥ 1024),
      non-inferiority required everywhere else and on every split. The
      informational analysis is an independent reason for the split, but it
      was found after the screens.

### Mechanism environment, next

- [ ] **Do not iterate the gate again on this data.** Three gates have now been
      read on the same phenomenon and a fourth restricted to the budgets that
      passed would be selection on results already seen, which is what withdrew
      G3. The next study fixes its budget range by a rule stated and justified
      before it runs, for instance "every budget at which the free procedure
      solves less than half", on fresh seeds, with at least 32 worlds per split.
- [ ] Why the metric fails at the tightest budgets specifically. At budget 256
      a permuted sparse weighting concentrates an ordering about as well as a
      learned one, and in one replication better. Either the top of the order
      is decided by concentration rather than direction, which is testable by
      comparing orderings rather than outcomes, or the fitted weights are
      accurate in aggregate and wrong about the few atoms that matter most at
      the head. Measure the rank of the world's own atoms under each weighting.
- [ ] G4's headroom is real and unclaimed. On behaviourally-defined worlds the
      *true* weighting beats the free unweighted proximity rule by +58 to +168
      of 640, and a diagonal metric fitted to co-membership recovers only part
      of it (fitted-to-true weight correlation 0.117 and 0.329) and cannot be
      told apart from a permuted copy of itself at budgets 256 and 16384.
      Better estimators to try, chosen before looking at the budget curve: fit
      on *ranked* co-membership rather than sampled pairs; use a full rather
      than diagonal metric on a reduced descriptor; fit the world radius as
      well as the direction. Gate again across the whole budget range.
- [ ] Whatever is tried there, the permuted-copy control is the one that bites.
      A sparse random weighting concentrates an ordering as well as a learned
      one does at the extreme budgets; any future arm must beat it at every
      budget or the claim is about concentration, not about what was learned.

- [x] **Charge the experience.** `mechanism_lifelong.py`, 24 worlds, 120 tasks,
      all experience earned under a fixed per-task budget. **The loop closes
      and needs no feedback**: an agent that keeps the atoms of whatever it
      submitted solves 19.7 of 120 at budget 1024 against 1.8 for the arm that
      never updates (+429 [289, 576]), and its solve rate goes 0.037 in the
      first ten tasks to 0.292 in the last ten. Being told whether it was right
      buys nothing (17.2). The ceiling, told the true mechanism each time, is
      99.0 and 0.925. (An apparent takeoff threshold in this run was an artifact
      of two budget points; see the six-point curve below.)
- [x] Why the G2 cross-world prior does **not** accelerate the earned loop
      (+86 [-40, 222] at budget 1024): it conditions on atoms already solved,
      so for the stretch that decides whether the loop starts it is the
      no-experience ordering. **An unconditional pair-co-occurrence prior,
      applied before the first solve, is worth more than everything else in
      this line of work**: +314 [193, 432] over the earned-loop champion at
      budget 256 and +621 [384, 841] at 1024, permuted control beaten by +306
      and +558; share of the informed ceiling recovered goes 4% → 27% and
      16% → 63%. `mechanism_cold_start.py`. Most of it is knowing which atoms
      appear in worlds at all, not which pairs go together (+56 [17, 102] for
      the pair structure at 256, +53 [-5, 106] at 1024).
- [x] On a family no training world held, the cold-start prior is worth
      nothing (-5 [-93, 76] at budget 1024) and in the first run was worse than
      its permuted control. **Reserving half the scan budget for the no-prior
      order turns that into +121 [26, 213]**, and costs nothing in support
      (+325 [186, 515] against +298 unhedged at 1024, about a seventh of the
      gain at 256). `mechanism_hedged_start.py`. This is the first bound this
      project has on how badly an acquired prior can go wrong outside its
      support. Hedge by default.
- [ ] The out-of-support **detector never fired**: the fraction of the agent's
      known atoms that appear in no training world stays below a quarter even
      in a world whose third family was withheld, because wrong picks import
      atoms from the families training did contain. Either find a statistic
      that is not diluted by foreign picks (weight by the atoms of *correct*
      answers only), or drop the detector: the hedge needs no statistic.
- [ ] Re-run the cold-start comparison with the stream reservation fixed: it
      reserved evaluation mechanisms from training by index order rather than
      by the shuffled stream. The prior is a function of atom keys alone so no
      answer can leak, but the run should be repeated before the number is
      quoted anywhere but here.
- [x] Map the takeoff threshold: **there isn't one.** Six budgets from 128 to
      4096, `mechanism_takeoff.py`: the earned loop closes at every one, with
      the interval entirely positive at every one, and the last-twenty rate is
      4 to 10 times the first-twenty rate throughout. What grows with the
      budget is the fraction of the informed ceiling it recovers: 3.7%, 6.2%,
      10.6%, 16.5%, 35.5%, 68.1%. The ceiling itself saturates by budget 256.
      The "threshold" in the earlier note was an artifact of having two points.
- [x] Replace pairwise affinity with joint world retrieval. **Worse**, by -22
      to -54 of 640 across `seen_triple` and `new_triple`, intervals entirely
      negative in most cells (`mechanism_world_retrieval.py`). Weighting
      concentrates on the few training worlds containing the one to four
      observed atoms; a maximum over pairwise counts pools the same evidence
      more robustly. The run also reproduces G2 on a third seed (+106 to +194
      at budget 1024). Do not revisit without a reason the small-evidence
      argument does not cover.
- [ ] Re-ask G3 with a gate that requires the same sign at 256, 1024, 4096 and
      16384, and with a representation chosen before seeing the budget curve.
      The spectral descriptor separates families unevenly (+0.396 threshold,
      +0.296 mod, +0.080 popcount, and popcount was one of the withheld
      families); a descriptor that separates the weak families is the obvious
      thing to try, chosen on training families only.
- [x] Does the *ability to acquire a world* improve with the number of worlds
      seen? **Yes, and it has not saturated at 400.** Margin over the free rule
      at 25/50/100/200/400 worlds is monotone in all six (k, budget) cells;
      at k=2 and budget 1024 it runs +21, +60, +79, +90, +122 of 800 tasks,
      while the unstructured control stays flat or negative everywhere
      (-14 [-37, 8] at 400). A prior fitted on 25 worlds is *worse than none*
      at budget 4096 (-95 to -146, intervals entirely negative).
      `mechanism_compounding.py`. Next: extend the sweep past 400 to find where
      it flattens, and ask whether the estimator itself can be improved from
      the same worlds, which is the recursive question this only sets up.
- [ ] Second task form in the same catalog (for example: the answer is the
      second run, or a two-predicate composition), to separate "growth in this
      environment" from "growth in this readout".
- [ ] `meta_both` is withdrawn: identity affinities and fitted metric
      probabilities are not on a common scale and the maximum is always the
      metric. Combine them on a calibrated scale or not at all.
- [ ] The grading rule is sound and 0.14% conservative against the interpreter
      (0 unsound, 105 of 75,063 permissive). Either accept it in writing, which
      `rsi/mechanism_space.py` now does, or widen the hypothesis class to the
      interpreter's reading and re-measure; do not leave it implicit.

### Decision required before any of it starts

- [ ] **Capacity-to-learn programme** (`PROGRAMME-TARGET-INTELLIGENCE-GROWTH-2026-09-21.md`).
      Four procedurally generated domains with instance/composition/mechanism
      splits (three do not exist), a multidimensional IRT model calibrated
      against a capacity-scaled reference population, a research forecaster with
      prospectively committed proper-scored predictions, and a five-arm
      factorial over independent lineages for about six generations with
      common-state replay, evaluator-swap and inheritance-reset probes. Weeks of
      compute on this machine before any battery exists. **Not started; this is
      an investment decision, not a next step.**

### Cheap and runnable now

- [ ] Partitioned-vs-pooled at matched capacity, properly powered. The only
      unresolved signal: E3 vs pooled-60 was +14.7 (interval +0.3 to +30.3) and
      +8.3 (crossing zero). Needs pooled models at 60/120/240 in the default set
      and far more than twelve banks per replication. **Screen first**: default
      regret against the largest pooled model must clear +20 or it is not worth
      running.
- [ ] Record CPU time, peak memory and failed-run counts. Never captured; the
      cost ledger is labels and wall time only.
- [ ] Read STOP, HGM, DreamCoder/LAPS, GEA (2602.04837), Chollet, tinyBenchmarks,
      the emergent-abilities mirage paper, observational scaling laws, TRACED,
      ProcessBench, reward-model overoptimization and the Red Queen Gödel
      Machine **directly** before citing any of them. The reviews' summaries are
      not a substitute.

### Sealed, do not open

- [ ] Replication set **919100-919111 / 919200-919211 / 919300-919311** is
      reserved and must not be opened until a final confirmatory protocol is
      hashed. One opened panel (`candidate-conditioned-query-transfer`) and
      replication one's frozen transfer panel have both informed design
      decisions and are no longer clean.

### Older threads, unchanged

Carried forward from before 2026-09-20; none was revisited this cycle.

## Kyberos mission and evidence (2026-09-16)

- [x] Owner clarified applications: **research, cybersecurity, social good and
      policy**. Align frontend/backend claims with measured capabilities.
- [x] Audited allowlisted public snapshot exported to both repos. Check drift
      with `.venv/Scripts/python.exe export_kyberos_evidence.py --check`.
- [x] Record mission review, source/result boundaries and validation in
      `../../kyberos/docs/RSI-MISSION-REVIEW-2026-09-16.md` and C008.
- [x] Finish the v4 runner and independent auditor; 33 tests passed. Complete
      `inheritance-20260916-v4` once and audit 13,568 search outputs/396 edits.
      Small mean inheritance gain, inconsistent across sources; see
      `inheritance-results-2026-09-16.md`. RSI remains unproved.
- [x] Replicate v4 with six new source seeds and 256 fresh final tasks. V5 failed
      its declared screen; g6 averaged below empty/g3/random controls. All 30,976
      outputs and 792 selection/edit decisions audited. Current rule not promoted.
- [x] Log selection scores/random-draw provenance without changing behavior;
      add independent selection reconstruction and readable change explanations.
- [x] Test source-only contextual edit-effect prediction with nested whole-source
      folds. V6 failed its screen: MSE improved 0.658% relative to unconditional
      means, but utility tied parent-only and beat means in only 1/9 sources.
      Final/transfer/admission outcomes stayed out of fitting. Audit reconstructed
      891 regressions and 51,840 predictions; 43 tests passed. Do not promote it.
- [x] Predeclare and implement v7 fragment-proposer inheritance with identical
      initial solvers, numerical-pair/frozen-library/scrambled controls, matched
      query opportunities and explicit source-acquisition charges. 50 tests pass.
- [x] Complete and audit v7: 40,512 outputs / 504 attempts reconciled. No fragment
      installation or final gain; g6 trailed the numerical control by 1.0417 pp.
      Do not promote this proposer. See `library-results-2026-09-16.md`.
- [x] Diagnose cheaper macro routes discarded by first-arrival state suppression;
      add a separate reopening kernel and test all 44 recorded source additions
      with corrected parents. Audit passed 1,120 outputs plus recorded exact
      replays; restored paths did not change correctness. Full suite: 53 passed.
- [x] Audit every compatible source-memory addition at the same budget: all 60
      had zero correctness gain, including 16 previously unselected. Audit passed
      all 1,536 outputs; 416 fresh, 1,120 verified reuse. Ranking alone cannot
      rescue this fixed candidate set.
- [x] Complete/audit `partial-empty-20260916-v8-diagnostic`: first-choice correct
      357 -> 401/576; coverage@64 398 -> 458. Audit reexecuted 1,152 searches.
      There were 21 first-choice regressions and 63.56% more primitive charges.
      Source-only repair, not RSI. See `search-diagnostic-results-2026-09-16.md`.
      Full suite: 59 tests passed.
- [x] Predeclare fresh-bank cost curves for the original/corrected filters and
      a combination with total expansion ceiling 128. Same ceilings are not
      equal compute; record full operation vectors and process/wall time.
- [x] Complete and audit `search-validation-20260916-v8`: first-choice correct
      332 -> 377/576; coverage@64 374 -> 438. Screen passed in 5/6 groups;
      17 first-choice regressions remain. Audit regenerated all 576 tasks and
      reexecuted 4,608 searches. Full suite: 61 passed. Cost curves and limits:
      `search-validation-results-2026-09-16.md`.
- [ ] Test task-balanced verified-frontier distillation with retention controls
      after fresh search validation; preserve neural and improver-quality tests.
      V9 protocol/runner/auditor implemented: four harvest controls, three seeds,
      two rounds, fixed anchor replay and exact checkpoint rollback. 65 tests
      pass; GPU fixture audit passed 8 decisions/steps and 1,664 sample checks,
      including tokenizer-level costs. Four additional audit tests passed. V9 failed
      with CUDA memory exhaustion after four decisions; its 104 files are preserved.
      Recovery `frontier-distillation-20260916-v9b` completed all 24 decisions,
      but its independent audit failed on a published/interpreter versus host-oracle
      semantic mismatch. No verified neural research outcome; see C023.
- [x] Reproduce and close the report renderer's stale-audit gap; five targeted
      tests pass. Fresh independent audit and complete evidence hashes now gate
      publication. Record measurement scope and observation/mechanism limits.
- [x] Quantify V9b's saved-sample semantic mismatch: 198,656 outputs, 3
      oracle-only accepted trailing-comma programs, and 106 visible behavior
      disagreements. Choose the canonical generated DSL grammar, tighten the
      independent oracle, and add regression tests. Preserve V9b as a completed
      runner with a failed publication audit (C023).
- [ ] Snapshot the repaired oracle/auditor in a new protocol, regenerate excluded
      tasks, rerun the controlled neural study, and require a fresh independent
      audit before publishing pass@k or admission results. V11 completed under
      `EXPERIMENT-v11-frontier-contract-repair.md` with bank seed 9162612;
      independent and report-time audits passed, but its advancement screen
      failed. Preserve as a negative transfer result (C024/C025).
- [x] Save the 2026-09-17 validated checkpoint and human-readable V11 report:
      `STATUS-2026-09-17.md` and `frontier-distillation-results-2026-09-17.md`.
- [x] Freeze V12 credit-mode comparison protocol/config and implement/test
      immediate-only, observational-descendant, paired-credit and scrambled
      table construction. Full suite: 141 passed. No V12 bank generated yet.
- [ ] Implement and independently audit the V12 runner; then launch fresh
      transfer tasks with matched downstream opportunities and source-evidence
      cost charged to every condition.
- [x] Audit descendant credit and local score influence in V5: 5/72 source
      entries have nonzero descendant sums; term removal flips 2/288 recorded
      adaptive transfer choices. Three diagnostic tests pass. No policy rollout
      or causal descendant benefit is inferred from this retrospective analysis.
- [x] Preregister a bounded paired-branch source probe before generating fresh
      tasks. Its 10-task implementation fixture passed independent reconstruction
      and five focused tests. Full 6-group / 72-pair V10 run completed and its
      independent audit passed; later-improvement effects were nonzero in 10 pairs.
      This is source headroom, not a tested inherited selector. See
      `EXPERIMENT-v10-paired-credit-probe.md` and C022.
- [x] Audit V10 and report immediate effect, terminal effect, and change in
      later improvement with group dependence and measured costs (C022).
- [ ] Design/preregister a prospective inherited-improver comparison with
      immediate-only, observational-credit and paired-credit controls at matched
      acquisition and downstream compute. Preserve common-ancestor RSI tests;
      requirements are in `NEXT-IMPROVER-CREDIT-STUDY.md`.
- [ ] Build domain-specific outcome evaluations with research, defensive
      security, public-interest and policy collaborators. DSL results do not
      establish improvement in those application domains.

## Goal (2026-09-16)

Achieve RSI ourselves at small scale through novel means, not just study it. Adopted for prototype implementation on 2026-09-16 following the user's instruction to build and test: an amplify, verify, distill, self-modify loop in which GATS-inspired DSL search is the amplifier, the amplifier's own self-model (per-operator effect statistics, verified macros, operator catalog) is what improves, and the RSI claim rests on large-k coverage compounding past the base, crossover improver-quality tests, and inheritance ablations. First domain: the 2606.07856 string DSL. The engineering pilot uses Qwen3-0.6B; a Qwen3-4B replication remains separate work.

- [x] Targeted primary-source literature check: STOP, Darwin Gödel Machine, HGM, Gödel Agent, ADAS, AlphaEvolve, ExIt, ReST-EM, SPADE, plus SOAR, RHI, and SelfMem. Findings and qualified novelty claim: `flagship-literature-check-2026-09-16.md`. Broader priority search remains before publication.
- [x] Adopt the system-level prototype as the flagship; retain H1 as a later study of whether tester training should be a modification operator.
- [x] Check whether 2606.07856's code and task bank are public: `https://github.com/izzortsi/trapdoor-loom` has DSL, scripts, and `banks/`. Verify bank hashes and generate a fresh final holdout before experiments.

## Implementation and pilot

Active continuation (2026-09-16): continue toward RSI while making every change's evidence and explanation auditable. `CHANGE-REGISTER.md` links interventions, controls, observed outcomes, hypotheses and remaining tests. The previous diagnostic turn produced new evidence that changed the next experiment; classified as progress.

- [x] Implement reusable model coverage decisions, verified cumulative replay and exact adapter rollback; 29 tests passed before the retention run.
- [x] Add timestamped durable events, per-step training draws/losses/gradient norms, complete candidate/selected checkpoint lineage, atomic result writes and an independent retention audit.
- [x] Check primary-source retention/diversity research through September 2026; record scope and limits in `research-retention-2026-09-16.md`.
- [x] Complete and audit `retention-20260916-v3`; record causal contrasts and failures in the change register. Replay preserved variety but not sustained final coverage; the small validation gate missed the regression.
- [x] Add per-attempt search-edit proposal/resolution records with lineage, evidence links, statistics and decision reasons. Current suite: 30 tests passed.
- [ ] Replicate the retention intervention across independent neural seeds; integrate validated choices into the complete interleaved loop. The v3 runner currently isolates distillation using frozen harvest.

- [x] Build a dedicated bounded DSL searcher with progressive widening and syntactic transpositions.
- [x] Add an independent oracle, hidden-data exclusion, candidate replay, tamper-evident journals, and rejection of forged execution reports.
- [x] Add operator-effect statistics, generation-0/3/6 transfer, and intact/empty/scrambled inheritance controls.
- [x] Add pinned local Qwen inference, separate LoRA adapters, verified trajectory certificates, and raw pass@k evaluation through 64.
- [x] Add a bounded model-proposed edit catalog and an ablation for accepted extensions.
- [x] Complete and inspect the combined CPU/GPU pilot; preserve diagnostic/interrupted runs. Results: `pilot-results-2026-09-16.md`; controlled run: `runs/pilot-20260916-v2-complete/`. 23 tests pass; 7,680 raw samples and 179 training trajectories audited. RSI criteria were not met.
- [x] Interleave updated model proposals, search edits, verified harvest, and LoRA distillation across two rounds in the calibrated v2 pilot.
- [ ] Validate and integrate model promotion into the full loop. Gate and exact rollback are implemented in the retention runner, but its 12-task admission slices missed a final regression; reliable coverage protection remains unproven.
- [x] Test cumulative verified replay against fresh-round-only distillation on a fresh holdout. The one-seed v3 result preserved more variety but did not improve sustained coverage.
- [ ] Replicate retention and test parent-policy regularization separately, using predeclared fresh holdouts and measured validation errors.
- [x] Test a context-conditioned effect predictor (v6): lower MSE did not produce reliable ranking gains. Richer context models remain untested; this version is not promoted.
- [ ] Preregister a larger study with fresh banks, multiple neural seeds, and matched total compute after the retention and transfer issues are addressed.

## V12 inherited-credit transfer

- [x] Freeze the immediate-only, observational-descendant, paired-credit, scrambled, empty, and random conditions and source evidence.
- [x] Implement and fixture-test the runner and independent auditor.
- [x] Run six source groups on a common final bank and complete the sealed audit. The selector screen failed: paired and observational credit tied immediate-only; scrambled and random were worse.
- [ ] Calibrate inherited effect estimates on larger independent source banks, or retire this selector and move to another measured bottleneck. No RSI promotion is justified.

## Recommended trio and ten-version stitch

- [x] Run and audit a shared-bank V67/V72/V73 smoke pilot. It exposed representation-family mismatch; no ranking conclusion was drawn.
- [x] Implement the common candidate envelope and mixed-family router specified in `EXPERIMENT-stitch-ten.md`.
- [x] Run and independently audit two small fresh-bank integration pilots, with native, stitched, leave-one-out and random-priority controls. V8 is a separate DSL lane. See `STITCH-TEN-PILOT-RESULTS-2026-09-17.md`.
- [ ] Run a narrower V67+V73 router against native/direct controls at matched candidate-generation compute on at least six fresh banks before claiming integration superiority.
- [x] Run and independently audit a preregistered V67+V73 evolving-ranker pilot on three fresh 12-task transfer banks, plus compatible top-four type bundles. V67+V73 candidate complementarity transferred (29/36 learned, 30/36 frozen, versus V73 21/36); ranker evolution itself regressed by one task. The top-four policy tied the pair at 29/36, with no added oracle reachability. See `POLICY-TRANSFER-AND-LEARNING-RESULTS-2026-09-17.md`. This is not the six-bank matched-compute claim above.
- [x] Transfer the retained V86 encoding library to two fresh 24-task banks and independently audit both. Adaptive lineage improved over identity on both; a prospectively frozen V73-direct-else-adaptive rule reached 24/24 on the second bank. Integrated a typed five-component policy and replayed 60 decisions. Closed-catalog, synthetic result; no awareness or open-ended RSI claim.

## H1 follow-up experiment

- [ ] Apply the measurement corrections in `gap-audit-2026-09-16.md`: independent task oracle, matched solver/tester metrics, and same-sample proxy-versus-oracle scoring.
- [ ] Finalize the H1 protocol: align base model, tasks, algorithm, and solver updates for frozen-verifier and co-trained-verifier arms; account for total compute separately.
- [x] Specify a third H1 arm in brief v4: extra tester budget spent on solver updates with the tester frozen. Runtime/cost-matching implementation remains unbuilt.
- [ ] Specify held-out evaluation, seed count, checkpoints, and pass@k values through large k before running the arms.
- [ ] Log held-out pass@1 and pass@k, fitted learning curves, tester mutation score, proxy-reality gap, task diversity, entropy, KL, stale-rollout ratio, clipped fraction, and mean completion length by role.
- [ ] Run the three arms; compare measured performance at fixed compute and full pass@k curves, treating fitted asymptotes as exploratory.

## Research and writing

- [x] Run a targeted primary-paper audit of the H1, test-reward, and adaptive-proposer claims; findings are in `gap-audit-2026-09-16.md`.
- [ ] Expand the targeted audit into a fuller related-work search before claiming novelty; some September 2026 entries were identified from listings rather than full texts.
- [x] Revise H1 status to partly covered in local brief v4 and theory v3; scope ACE's optimized-versus-random comparison and distinguish separate frozen testers.
- [x] Fix the audit's H1 rationale: CURE rewards its coder with ground-truth unit tests; its paper describes coder-only optimization and SFT as separate alternatives, not a clean frozen-tester control. Rest "partly covered" on ACE (optimized vs random tests at matched compute), noting ACE's single model, execution-failure signal for adversarial inputs, ground-truth tests for solver selection, and random-test (not frozen-tester) control.
- [x] Correct the H1 design/diagram to require separate role adapters; local brief v4 distinguishes this proposed hardware layout from the executed prototype.
- [ ] Implement and validate the separate tester/solver/proposer adapters for H1 before running its three-arm study.
- [x] Correct local brief v4's 2606.07856 attribution: distinguish the paper's self-training pass@k crossover from its separate learned-critic selection result.
- [ ] Declare the compute unit for arm C before the pilot (tester cost is mostly CPU mutant execution, solver cost is GPU).
- [ ] Re-estimate the budget for three arms plus pilot plus pass@k to large k (n >= k samples per task, checkpoint, seed, arm).
- [ ] Set seed count from pilot seed variance instead of a fixed three.
- [ ] Pick a real-bug source for synthetic tasks: base-model solutions that pass weak tests and fail a strong oracle (EvalPlus-style).
- [x] Reconcile the gap register count: eleven questions. With H1 corrected, one closed, three open and seven partly covered.
- [ ] Work through the questions in `load-bearing-theory.html`, preserving their current status.
- [ ] Keep the technical brief, narrative version, PDF, close readings, and published pages aligned after substantive revisions.
