# Technical design: experimentation, evaluation and improvement

Status: design for the next phase of the RSI programme, written 2026-09-20 after
the region-acquisition transfer. It supersedes the "next steps" sections of
earlier results files where they conflict. The measurement contract in
`INTELLIGENCE-GROWTH-MEASUREMENT.md` remains in force; this document adds a
power precondition to it and fixes the action space.

## 1. Problem statement

The programme's goal is a retained system that gets better at judging candidate
solutions and changes, and better at producing useful changes, when applied to
the same starting system under the same resource limits, with the gain
transferring to fresh task instances. Three claims are kept separate:

- **Evaluator growth.** A later evaluator checkpoint makes better choices than an
  earlier one on identical candidate pools.
- **Improver growth.** A later improver checkpoint, given the same base and the
  same budget, produces a better child system than an earlier checkpoint.
- **Recursive growth.** A later improver produces a better *child improver*, as
  measured by that child's gain on a second untouched base.

Evaluator growth has been shown repeatedly. Improver and recursive growth have
never passed a gate across roughly forty attempts.

## 2. What the record now shows

### 2.1 The gates were unfalsifiable in the positive direction

`analysis/edit-catalog-headroom-20260918.json` measured, on two opened 576-task
runs, what an unavailable oracle could gain by choosing among the whole-bank
policies each improver was allowed to select: **+5 and +8**. The paired
twelve-bank interval on those runs had a half-width of about 9. Every improver
gate before 2026-09-20 required a learned policy to beat its controls inside that
band. A perfect improver would have failed most of them.

### 2.2 Enlarging the action space did not fix it

The region-acquisition transfer (`REGION-ACQUISITION-IMPROVER-RESULTS-2026-09-20.md`)
gave the improver a task-level purchase whose total value was ten times larger.
The evaluator component gate passed (+49/576, twelve of twelve banks, interval
+37 to +62). The improver gates failed at +6 and +5 with intervals crossing zero.
Decomposed on the same fresh banks:

| quantity | bank B | bank C |
| --- | --- | --- |
| construction value: all six specialists over E0 | +63 | +60 |
| selection ceiling at budget 3: oracle over E0 | +54 | +44 |
| captured by the later parent | +49 | +43 |
| selection headroom left after the later parent | **+5** | **+1** |
| ranking headroom left after all six | **+69** | **+79** |

The marginal decision was worth the same +1 to +5 as before, because value
concentrates in options every competent policy takes.

### 2.3 The verb is wrong

Every replicated gain has come from **constructing** a new evaluator component:
the first E0 reranker (+35 on two panels), the familiar AST specialist (+70 over
E0), the shifted AST specialist (+51 over E0), the six region specialists
(+49 here). Every failure has come from **choosing** among components already
built: training rules, thresholds, temperatures, width schedules, region
purchases.

## 3. Design principles

**P1. Construction, not selection.** *Superseded 2026-09-21: the routing
result was selection and succeeded; the construction result was withdrawn once
a capacity-matched pooled model entered the default set. The supported
principle is residual over the adversarial default, created by construction and
captured by selection; see section 5.2 of
`WHAT-WORKED-WHAT-FAILED-2026-09-21.md`. Retained for the record.* The
improver's action must be to build a
component under a budget, with enough degrees of freedom that different
histories produce materially different components. Choosing from a fixed menu is
allowed only as a control.

**P2. Power precondition.** No improver-growth gate is run until the action
space's oracle headroom over the strongest fixed control, measured on opened
development panels, is at least **+20 per 576 tasks**, about twice the observed
twelve-bank interval half-width. A gate that cannot be passed by an oracle is
not a test of the learner. This precondition is recorded in the protocol with
the development file that established it.

**P2b. Conditional action heterogeneity precondition** (previously named non-stationarity; the best action can vary by instance under i.i.d. sampling, and drift need not create a routing opportunity). P2 is necessary and not sufficient.
Before any improver gate, the environment's **fixed regret** must be measured:
the value a perfectly context-conditioned policy gains over the single best
constant policy. `ACTION-SPACE-STATIONARITY-2026-09-20.md` found fixed regret of
only **+6 and +12** per 576 tasks on the current i.i.d. banks, while eleven
banks of experience beat one bank by **+1 and -3**. In a stationary environment
the optimal action is a constant, so no learner can show growth at any action
space, and larger banks make it worse by shrinking the residual noise that fixed
regret is made of.

An environment therefore qualifies only if all three hold:

1. Banks are drawn with varying generator parameters, family mixes or
   difficulty, so the best construction differs by bank.
2. That dependence is predictable from public instance features, shown by a
   context-conditioned policy fitted on held-out banks beating the best constant
   policy.
3. Measured fixed regret exceeds **+20 per 576 tasks**.

Fixed regret is cheap and is computed for every candidate environment *before*
any improver is built for it. An environment failing (3) is rejected without
running an improver.

**P2c. Default-regret precondition.** P2 and P2b are both necessary and still
not sufficient. **The adversarial default set must include model capacity: a
single larger model fitted on the same labels, at several sizes, not only
hand-written rules.** On 2026-09-21 this clause was missing, and every improver
result in the programme was measured against defaults with less capacity than
the improver's output; a 60-leaf pooled model dominated all of them and a
120-leaf model beat the partition environment's own latent oracle routing. Before any improver gate, measure **default regret**: the gap
between the action space's oracle and the best policy expressible with **no
verified history at all**, where that default is the strongest rule a competent
researcher would write before seeing labels. It must exceed **+20 per 576
tasks**.

`DEFAULT-REGRET-2026-09-20.md` measured it across four action spaces spanning
two orders of magnitude in total value and found 21, 1, 17 and 27, all at or
inside bank noise. In the per-task routing space the rule "trust whichever
specialist is more confident on this task" needs no history and beat a threshold
learned from twelve banks by 4 in one replication and lost by 2 in the other,
both intervals crossing zero.

Non-stationarity is necessary and not sufficient: the heterogeneous environment
raised fixed regret from 2.9 to 38-83 and made conditioning worth +58 and +84,
yet the *rule* for conditioning was guessable, so the improver still had nothing
to learn.

The default must be chosen adversarially. Measuring growth against a single
random draw, an uninformed constant, or a one-observation parent inflates the
result; that is the recurring methodological error behind roughly forty
experiments in this project, including the +80 of replication one.

**P2d. Learnability precondition.** P2c is still not sufficient. The residual
left after the best zero-knowledge default must be **capturable by a policy
fitted on held-out banks**, not merely present. Fit a selector on one audited
panel's public features, test it on another, and require it to beat the default
with a paired interval excluding zero.

The seven-action per-task space clears P2c at +38 and +51 and fails here: the
own-region specialist wins 11 of 12 region cells, so the residual is per task
rather than structural, and a trained selector **loses** to the default by -9
and -18. Large default regret can be pure task-level noise.

The four preconditions are cheap, ordered, and each rejects spaces the previous
one admits:

| condition | asks | observed failure |
| --- | --- | --- |
| P2, power | oracle headroom above noise | whole-bank menus, +5 and +8 |
| P2b, conditional action heterogeneity | does the best action vary by instance | i.i.d. banks, fixed regret +6 and +12 |
| P2c, default regret | can a no-history rule be beaten | per-task routing, +17 and +27, learned rule -4 and +2 |
| P2d, learnability | does a held-out policy capture the residual | seven-action per-task, -9 and -18 |

**Every action space tested in this project fails at least one of the four.**
Screen all four before building an improver; together they cost far less than a
single frozen transfer.

**P3. Matched budgets, charged selection.** Every arm spends the same verified
label budget. Any labels a construction uses to *decide* what to label (for
example, checking whether E0 was wrong on a task before choosing it) are charged
against that budget and reported separately.

**P4. Information, not volume.** Every improver comparison carries a
`duplicate` control holding the later parent's record count with the initial
parent's information. A later-over-initial gain that duplicate also shows is
volume, not knowledge.

**P5. Predeclare, hash, audit.** Protocol and runner are hashed into the run
manifest before any fresh bank is generated. An independent auditor regenerates
banks, pools, orders and labels and reconstructs every decision without
importing the runner's scoring. No result is cited until its audit passes.

**P6. Output-blind preparation.** Any stage that touches probe outputs uses
`public_ast_probe_prepare.py`. Zero-query ranking studies avoid probe outputs
entirely.

**P7. Separate the curves.** For each checkpoint report (1) solution-evaluator
choice quality on common pools, (2) edit-effect forecast error, calibration and
regret against verified effects, (3) same-base child system gain per cost, and
(4) the child improver's gain on a second base. A rising solver score satisfies
none of (2) to (4).

## 4. The construction action space

A construction is a recipe for building one candidate reranker from a fixed
verified-label budget L. Its degrees of freedom, in the order they enter the
programme:

| axis | values | public? | why it matters |
| --- | --- | --- | --- |
| composition: which source tasks to label | uniform; top regions; lowest E0 margin; E0-wrong | yes, except E0-wrong costs one label per screened task | opened evidence shows region-targeted models gain +20 to +70 and misapplied ones harm |
| depth: labels per task | 25, 50, 100 | yes | breadth versus depth at fixed L |
| region weights (Phase 2) | w on the six-region simplex | yes | replaces the discrete compositions with a continuous space the improver can search |
| coverage (Phase 3) | search arms and caps per region | yes | the 143-task reachable-but-unselected gap and the 468 to 484 head reachability ceiling |

A reference construction, `reachable_e0_wrong`, needs full head labels to select
its tasks; it is reported as a cost-unmatched upper reference, never as an arm.

The improver's transferable state is a table of verified construction effects
(construction description, budget, realized gain on a verified bank, harm by
region, cost vector) and, from Phase 2, a predictor from construction
parameters to expected gain.

## 5. Experiment programme

### Phase 0. Construction screen (development, running)

`construction_space_development.py` builds twelve cost-matched constructions
(four compositions by three depths) at L = 40,000 verified candidate labels from
the two source panels, and scores each on three opened target panels against
frozen E0. Output: `analysis/construction-space-development-20260920.json`.

Decision rule. Let S be the gain spread between the best and worst cost-matched
construction summed over the three panels, and H the best construction's gain
over the strongest simple fixed construction (`uniform@100`). Proceed to Phase 1
only if H >= +20 per 576 tasks on at least two of three panels (P2). If not,
skip to Phase 3, because depth and composition alone do not carry enough value
to test an improver.

### Phase 1. Construction-improver transfer (frozen)

Same shape as the region-acquisition protocol, with construction in place of
purchase.

- Base: frozen E0, identical pools and candidate order for every arm.
- Budget: L verified labels per parent, identical across arms.
- Parents: `initial` holds verified construction effects from one opened panel;
  `later` from three; `duplicate`, `scrambled`, `empty`; fixed `uniform@100`;
  unavailable `oracle` construction on the fresh bank.
- Selection rule, shared by all parents: pick the construction with highest
  mean verified gain; ties by name.
- Banks: fresh seeds, admission 6 x 48, transfer B 12 x 48, transfer C 12 x 48.
- Children: each parent's effect table plus one common admission observation,
  then a construction on bank C.
- Gates: G1 as before; G2 and G3 require gain >= +6, at most 4 losing banks of
  12, interval excluding zero, and later >= duplicate.

Two independent frozen replications with fresh seeds are required before either
G2 or G3 is reported as passed (Section 8).

### Phase 2. Parameterized construction

Replace the discrete compositions with a region-weight vector w and depth d. The
improver fits gain(w, d) by ridge on its verified effect table with
public region statistics as features, proposes argmax under budget, builds it,
and records the realized effect. The child inherits the table and predictor.

This is the first stage at which the improver can produce a construction no
researcher wrote. Development first: measure gain(w, d) on a grid over opened
panels, confirm the surface has structure a ridge can capture, and confirm the
oracle point satisfies P2 relative to `uniform@100`.

### Phase 3. Coverage as construction

Add candidate-generation arms and caps per region to the construction. Head
reachability is 468 and 484 of 576 on the fresh banks; all six specialists reach
399 and 405. The reachability gap is the only remaining pool of value larger
than the ranking gap, and no prior study has let an improver spend budget on it
under matched cost. Sensor use, if any, goes through the output-blind preparer.

### Phase 4. Meta-level construction

Only after Phase 1 or 2 passes twice. The child improver may then construct its
own effect predictor (feature set, model class, history weighting) from verified
forecast errors, and the gate becomes forecast regret on a second base.

## 6. Evaluation

Primary endpoint per phase: correct zero-query top choice on identical candidate
pools, per 576-task fresh bank, paired at bank level.

Secondary, always reported:

- Per-region realized gain and harm for each built component.
- Forecast error of the improver's own gain prediction against realized gain,
  and regret against the unavailable oracle construction.
- Resource vector: verified labels spent, selection labels charged, candidates
  rescored at deployment, preparation wall seconds.
- Reachability of the head and of the full pool, so a better generator cannot
  masquerade as a better evaluator.

Uncertainty: exact bank bootstrap over paired per-bank differences, twelve banks
per transfer, as in every prior study. Gate thresholds are fixed in the protocol
before fresh seeds exist.

## 7. Controls, in every frozen run

| control | isolates |
| --- | --- |
| `initial` versus `later` | the effect of extra verified history |
| `duplicate` | record volume from information |
| `scrambled` | whether the history's content matters |
| `empty` | the declared default with no history |
| fixed best-known | whether learning beats a researcher-written rule |
| unavailable oracle | the ceiling of the action space on this bank |
| E0 | the base with no construction |

## 8. Success criterion for "reliable intelligence growth"

The programme reports reliable improver growth when, on a construction action
space that satisfied P2 on opened development:

1. G2 passes on two independent frozen replications with disjoint seeds, and
2. G3 passes on two independent frozen replications with disjoint seeds, and
3. In each, `later` >= `duplicate` and `later` > `scrambled`, and
4. Each replication's independent audit passes.

Evaluator growth is reported separately, under its existing gate. A pass in one
does not discharge the other.

## 9. Audit and provenance

For each frozen run:

- The protocol file and runner are hashed into `bank_manifest.json` before any
  bank is generated. A runner edit after that point requires discarding the run;
  this was done once on 2026-09-20 when a G1 gate cap did not match the protocol.
- `frozen_records.json` hashes are recorded and checked at scoring time.
- The auditor regenerates all tasks from seeds, all pools, both candidate orders,
  and every final candidate label; it reconstructs every parent and child
  decision from the inherited records alone and recomputes totals and gates with
  its own code.
- Results are not cited in `INTELLIGENCE-GROWTH-MEASUREMENT.md` until
  `audit.json` reports `passed: true`.

## 10. Resource accounting and environment

- One region acquisition unit is about 15,000 to 18,000 verified candidate
  labels. L = 40,000 is roughly 2.3 units.
- Bank preparation for 1,440 tasks is about 530 s wall on eight workers;
  scoring and auditing each re-evaluate about 136,000 candidate labels.
- Run with `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  PYTHONIOENCODING=utf-8`. The first setting avoids BLAS thread contention with
  the eight-process pool; the last avoids cp1252 failures on Unicode task text.
- This machine's **commit limit**, not physical RAM, is the binding memory
  constraint. On 2026-09-20 ComfyUI and Ollama held about 60 GB of commit while
  idle, leaving 0.5 GB free and failing 200 KiB allocations. Check
  `FreeVirtualMemory` before a run; do not kill another service to make room
  without asking.
- Parse each 100 MB panel JSON once into a compact cache
  (`analysis/region-specialist-cache-20260920/`), never repeatedly per region.

## 11. Risks and stop conditions

| risk | signal | response |
| --- | --- | --- |
| construction spread also concentrates | Phase 0 fails P2 | skip to Phase 3; do not run Phase 1 |
| opened-panel tuning inflates development | fresh gain far below development | report as forecast error; do not re-tune on the fresh bank |
| depth trades against breadth in a way that swamps composition | best construction is the same at every composition | collapse to depth-only and re-check P2 |
| coverage edits shift what ranking is worth | G1 passes but per-region harm appears | report harm by region; treat as a package, not additive |
| commit exhaustion mid-run | MemoryError with free physical RAM | check FreeVirtualMemory; wait for idle services to release |

A phase that fails P2 or its gate is recorded as a negative result with its full
audit, and the programme moves to the next phase. No component is promoted on a
solver score alone.

## 12. Revision after the stationarity measurement

Phases 1 and 2 above are **suspended**. They were written before fixed regret
was measured, and they would run an improver gate on an environment whose
optimal action is a constant. Phase 0 passed P2 by a factor of fourteen (spread
281) and the environment still fails P2b at +6 and +12. Power was never the
binding constraint; stationarity was.

The programme order becomes:

- **Phase E, environment construction.** Specified and simulated; see
  `MECHANISM-HETEROGENEITY-ENVIRONMENT-2026-09-20.md`. The generator draws a
  per-bank **familiar/shifted AST share from Beta(0.4, 0.4)** and exposes it
  only through public task features. Resampling audited rows gives fixed regret
  **48.3** for beta and **38.4** for a drifting schedule, against **2.9** for
  the balanced design every prior run used. Family-mix heterogeneity was tested
  first and rejected at 16.8: it fails because every region specialist helps and
  none harms, whereas the shifted model costs **-14** on familiar tasks.
  `split` banks are rejected despite the largest regret (83.4) because
  all-or-nothing composition makes the right action inferable from one task,
  testing detection rather than accumulated experience. The real generator must
  reproduce these numbers on generated banks before any improver is built.
- **Phase E2, learnability check.** On opened banks from that generator, fit a
  context-conditioned construction policy on held-out banks and confirm it beats
  the best constant policy with a paired interval excluding zero. This separates
  real structure from per-bank noise, which the current environment failed.
- **Phase 1', construction-improver transfer.** Only then, the frozen
  parent/child protocol of Section 5, unchanged in form, on the new generator.
- **Phase 3, coverage.** Independent of the above and still worth running on the
  existing benchmark, because it targets evaluator growth, not improver growth,
  and the head reachability gap of 468 and 484 of 576 is real.

## 13. Immediate sequence

1. Region-acquisition audit: **passed**, 1,440 tasks, 135,728 labels, zero
   failures. Measurement file updated.
2. Phase 0 construction screen: **passed P2**, cost-matched spread 281.
3. Stationarity: **failed P2b**, fixed regret +6 and +12, experience worth +1
   and -3. Phases 1 and 2 suspended.
4. Next: implement the Phase E generator, measure its fixed regret, and report
   it before building any improver for it.
5. In parallel, Phase 3 coverage development on the existing benchmark as an
   evaluator-growth line, which stationarity does not affect.
