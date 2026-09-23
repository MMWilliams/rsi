# What worked, what failed, and why

RSI seed-improver programme, 2026-09-20 to 2026-09-21. Every number below is
read from an audited run or from an opened-panel analysis file named in
`REPRODUCIBILITY-LEDGER-2026-09-21.md`; nothing is quoted from memory.

## 1. Outcome

| claim | status | strongest evidence |
| --- | --- | --- |
| verifier (evaluator) growth | **within-distribution only; does not transfer** | pooled-60 beats frozen E0 by +73/+69 on fresh instances of the six familiar generators, audited. Under leave-one-family-out it is **worse than E0 on every held-out mechanism** (716 vs 1020 over six families, every interval negative; self-edit 111 vs 241). Transfer gap in-dist minus held-out **+478**. This is evaluator specialization, not intelligence growth under the adopted definition |
| improver growth, routing form | **holds as stated; dominated as a design** | C1 +22 / +23 and C2 +36 / +47 reproduce to the integer; but one 60-leaf pooled model on the same 24 history banks beats the routed system by **35 and 29** (intervals entirely negative), and by 62 and 37 with the specialists' source labels included. The router learns; the class it learns in loses to a free procedure |
| improver growth, construction form | **WITHDRAWN** | with out-of-fold routing and a capacity-matched (60-leaf) pooled baseline, the built system **loses by 50 and 36** at 24 banks; E3 negative or crossing zero against every baseline; router leakage inflated rep 1 by +14. Only E2 survives, and E2 is "more data helps", which the pooled model also shows |
| recursive child-improver growth | **not found** in the tested transmission classes at the tested budgets | G3 -2 (interval -15 to +12); three candidate transmissible states screened, none clears +20 |
| ~40 earlier improver failures | **explained** | they measured an environment property; four cheap preconditions now predict pass and fail |

Four frozen replications, four passing independent audits, 6,912 tasks
regenerated from seeds and 646,028 candidate labels rechecked. Both protocol
files are byte-identical to the hashes recorded when their banks were generated.

## 2. The question

Three claims are kept separate throughout, per `INTELLIGENCE-GROWTH-MEASUREMENT.md`:

- **Verifier growth**: a later evaluator makes better choices than an earlier one
  on identical candidate pools.
- **Improver growth**: a later improver, given the same base and budget, produces
  a better child system than an earlier improver.
- **Recursive growth**: a later improver produces a better child *improver*,
  measured by that child's gain on a second untouched base.

A claim counts only when it passes a gate predeclared and hashed before any
bank existed, replicates on disjoint fresh seeds, and survives an independent
audit that regenerates everything from seeds without sharing the runner's code.
The unit is correct zero-query top choices per 576-task panel, paired at bank
level, with an exact twelve-bank bootstrap interval.

## 3. What worked

### 3.1 Verifier growth by construction

Building a new evaluator component reliably improved choices on fixed candidate
pools, in every form tried. Six region specialists over the frozen E0 reranker
gained **+49/576** on fresh banks, twelve of twelve banks, interval +37 to +62,
audited across 1,440 tasks and 135,728 labels.

The purer form came free with the construction confirmations (section 3.5): the
system the improver builds from its own history, scored against E0 on the same
transfer panel:

| | E0 | pooled, same labels | built | built minus E0 | pooled minus E0 |
| --- | --- | --- | --- | --- | --- |
| rep 1 | 320 | 328 | 357 | **+37**, 11w/1l, +20 to +56 | +8, -2 to +18 |
| rep 2 | 326 | 332 | 358 | **+32**, 9w/1l, +18 to +44 | +6, -11 to +22 |

Every component behind the +37 and +32 was trained inside the frozen run, and
pooling the same labels at the same 15-leaf capacity barely moves E0.

> **Corrected 2026-09-21.** The sentence that followed here read "the evaluator
> improvement is a product of construction, not of label volume." It is
> withdrawn. A single 60-leaf pooled model on the same labels beats E0 by
> **+73 and +69** on these same transfer panels, roughly double the built
> system's gain, and the built system loses to it by 50 and 36. The evaluator
> improvement is a product of model capacity and verified labels. That is still
> verifier growth, and it is the strongest verifier built in any frozen run; it
> is not evidence that construction did anything a larger model could not.

### 3.2 The four preconditions

The single most useful artifact of the programme. Each is one cheap computation
on opened rows, they are ordered, and each rejects action spaces the previous
one admits. Threshold throughout: **+20 per 576 tasks**, about twice the observed
interval half-width.

| precondition | asks | measured by |
| --- | --- | --- |
| **P2** power | is oracle headroom over the strongest fixed control above noise | oracle minus best fixed |
| **P2b** conditional action heterogeneity | does the best action vary by instance or is it a constant | **fixed regret**: per-bank hindsight minus best constant |
| **P2c** default regret | can the strongest rule a researcher writes *for free* be beaten | oracle minus best zero-knowledge rule |
| **P2d** learnability | does a policy fitted on held-out banks capture the residual | held-out selector minus best free rule |

Their record must be split, because a framework built from failures cannot
be credited with predicting them. **Retrospective**: P2, P2b and P2c were
formulated across the first seven failures and explain them after the fact.
**Prospective**: the complexity partition was screened before any improver was
built for it, predicted to pass, and passed on two frozen replications; the
rule-identity and depth-heterogeneous spaces and the acquisition, regime and
failure-memory transmissible states were screened before building and rejected,
so their negatives were never tested. **Retrospective again**: the partition
scheme was screened only after the recursive experiment had failed. The
prospective hit rate was recorded as one confirmed positive and five untested
rejections. **Corrected 2026-09-21:** the one positive was then overturned when
model capacity entered the adversarial default set (section 9), so the
prospective record is zero confirmed positives and five untested rejections. The
screens did not fail; they were run with an incomplete default set, and the
missing clause is now part of P2c.
Thresholds must be frozen before the next environment family is examined;
otherwise the programme learns which benchmarks pass the screen rather than
whether the screen predicts opportunity.
They also apply to the transmissible state of a recursive experiment (section
4.5), which was learned the hard way.

### 3.3 The complexity-partition environment (withdrawn as qualifying; see section 9)

> **Superseded 2026-09-21.** Re-screened with model capacity in the
> adversarial default (`partition_rescreen_capacity.py`), a single 120-leaf
> pooled model scores 412, 405 and 413 on the three screen panels, above the
> partition's own latent oracle routing at 392, 401 and 400, and the held-out
> selector loses to it by 2 (interval -10 to +7). **P2d fails.** The section
> below is retained as the record of what was believed and why.

The environment that made improver growth measurable. Specialists are
partitioned by **solution complexity**, how deep the first correct candidate
sits in the base ranker's order, instead of by mechanism family. That property
is **latent** (knowing it requires knowing the answer), **cross-cuts** family
(so no family rule can express it), and is **partly predictable** from public
pool statistics (so the residual is learnable rather than noise).

| panel | most-confident default | own-bin, latent | oracle | default regret | learnability |
| --- | --- | --- | --- | --- | --- |
| candidate-query-cost | 339 | 392 | 462 | **+123** | |
| combined-ranker-query | 346 | 401 | 447 | **+101** | held-out selector 369 vs 350, **+19**, +5 to +33 |
| candidate-conditioned | 350 | 400 | 439 | **+89** | |

First action space to clear P2c and P2d together. Source:
`analysis/complexity-partition-environment-20260920.json`.

### 3.4 Improver growth, routing form

Frozen protocol `EXPERIMENT-complexity-improver-confirmation.md`. Four
specialists trained once on opened panels; the improver fits a router over them
from its verified history and deploys per task. Small-history arm scored as the
expected value over every contiguous window; reference is the zero-knowledge
"most confident specialist" rule.

| | rep 1 | rep 2 |
| --- | --- | --- |
| C1, 24-bank router minus most-confident | **+22**, 7w/2l, +6 to +38 | **+23**, 9w/2l, +4 to +42 |
| C2, 24-bank minus expected 2-bank | **+36**, 10w/2l, +19 to +51 | **+47**, 12w/0l, +33 to +64 |
| curve, sizes 2 to 24 | 314.9 to 351.0, monotone | 321.0 to 366.0, monotone |
| audit | pass, 160,912 labels | pass, 161,932 labels |

### 3.5 Improver growth, construction form

Frozen protocol `EXPERIMENT-construction-improver-confirmation.md`. The improver
receives history banks and nothing else: it computes the partition from its own
labels, trains every specialist and a pooled model, fits its own router, and
deploys. The baseline is the strongest free alternative, **one pooled model on
exactly the same history**, identical data and compute.

| history banks | rep 1 built | rep 1 pooled | rep 2 built | rep 2 pooled |
| --- | --- | --- | --- | --- |
| 4 | 310.8 | 307.8 | 309.7 | 302.7 |
| 8 | 328.2 | 320.8 | 334.2 | 321.2 |
| 16 | 344.7 | 323.8 | 362.7 | 326.3 |
| 24 | 357.0 | 328.0 | 358.0 | 332.0 |

| gate | rep 1 | rep 2 |
| --- | --- | --- |
| E1, built beats pooled | **+29**, 9w/1l, +12 to +50 | **+26**, 10w/1l, +5 to +46 |
| E2, construction growth | **+45**, 12w/0l, +27 to +67 | **+49**, 12w/0l, +37 to +62 |
| **E3, growth exceeds data volume** | **+26.0**, interval +7.8 to +49.0 | **+19.0**, interval **+0.2 to +38.3** |
| E4, monotone (ungated) | yes | **no** |
| audit | pass, 161,452 labels | pass, 161,732 labels |

E3 is the gate that carries the claim, and with its own paired interval it is
clean in replication one and marginal in replication two. Pooling the same data
grows by +20.2 and +29.3 on its own; that is more data helping and is exactly
what improver growth can be mistaken for. Construction grows +46.2 and +48.3.
The frozen `results.json` reported 45/21 and 49/29 because it rounded per-bank
differences before summing; the results file carries the correction record. The routing form
could not make this comparison because its components were fixed before the
experiment began.

Supporting development: five-fold rotation of the held-out panel passed both
gates in **5 of 5 folds**, with the built-minus-pooled gap widening monotonically
in every fold, mean **9.8, 18.0, 24.8, 37.4, 45.0** at 4, 8, 16, 32, 48 banks.

### 3.6 Reproducibility machinery

- Protocol and runner hashed into the manifest before any bank is generated; a
  post-hash runner edit means discarding the run (done once, section 4.7).
- Small-history arms scored as expectations over windows, never one draw.
- Auditors that re-derive partition, training, routing and deployment in their
  own code, verify cached feature matrices to 1e-5, and reproduce every curve
  point exactly.
- One panel per process, because Windows commit rather than RAM is the binding
  memory limit on this machine.

## 4. What failed

### 4.1 Forty gates on a stationary benchmark

Before this programme, roughly forty improver gates had failed. Measuring
**fixed regret** on the audited region-acquisition banks explained all of them
at once: a perfectly context-conditioned policy could gain only **+6 and +12**
over the best constant policy, and a policy fitted on eleven banks beat one
fitted on a single bank by **+1** (interval 0 to +3) and **-3** (interval -11 to
+5). Banks were drawn i.i.d. from a fixed family mix, so the optimal action was a
constant, one observation estimated it as well as twenty, and residual per-bank
variation was unlearnable noise. Larger banks would have made it worse. Source:
`ACTION-SPACE-STATIONARITY-2026-09-20.md`.

### 4.2 Nine action spaces

| action space | dies at | evidence |
| --- | --- | --- |
| whole-bank policy menus | P2 | oracle selection worth +5, +8 |
| region purchase, 3 of 6 | P2b | fixed regret +6, +12 |
| per-bank action, i.i.d. banks | P2b | fixed regret 2.9, context worth -0.8 |
| per-bank action, heterogeneous banks | P2c | contextual value +22, +26, both intervals crossing zero |
| per-task threshold routing | P2c | learned threshold **-4, +2** against naive *t*=0 |
| seven-action per-task | P2d | regret +38, +51 but own-region wins 11 of 12 cells; selector **-9, -18** |
| depth-heterogeneous, 12 actions | P2d | confidence genuinely deceptive, regret +43 to +55, selector **-6**; protected override best +1 |
| interacting typed edits | P2 | regret +3 to +6 per 288 |
| rule-identity, four hidden rules in one block | P2c | most-confident recovers the rule: regret +11, +7 |

The unifying observation: wherever specialists exist here, some free heuristic
over them is near-optimal, usually their own confidence and otherwise "match the
mechanism, take the most data." Two spaces were built specifically to break
that, and confidence still recovered the mechanism in one, while the other's
residual was unlearnable noise.

### 4.3 The pass that wasn't

The first per-bank contextual improver on the heterogeneous environment passed
G2 at **+80** (interval +17 to +146) and was reported as the first improver
growth in the project. Three checks unwound it.

1. Against the strongest *free* rule, "trust whichever specialist is more
   confident," the learned policy scored **-4** in one replication and **+2**
   in the other, both crossing zero. The +80 was measured against a
   one-observation parent, a baseline weaker than a free rule.
2. Replication two gave **+26** (interval -1 to +62) with nothing changed. The
   history-size curve explained why: single-bank parents span **46 to 104**
   (mean 75), replication one drew 46 and replication two drew 92, which
   equals the best constant. The gate was measuring the baseline draw.
3. The predeclared falsification check, that a balanced control should show a
   null, instead passed at +29 in replication one, because "later" simply found
   the better constant. Only in replication two did the control behave.

Withdrawn. The two fixes, zero-knowledge baseline and expected-over-windows
small arm, are built into every later protocol.

### 4.4 Per-task threshold learning

The most promising action space by headroom (+79 and +109 over the best
constant). Pooling twelve banks beat the expected single-bank draw by **+13**
(+6 to +22) and **+12** (+4 to +20), consistently. Then against the naive *t*=0
rule: **-4** and **+2**. Under the project's historical baseline convention this
would have been reported as a clean double replication. It was not run to fresh
banks.

### 4.5 Recursive growth

Parents selected a partition scheme by cross-validation on their own history and
transmitted only that; every child received an identical fresh 12-bank history
and built its own system. Parents genuinely disagreed (early chose `flat`, late
chose `coarse`). Children scored **366, 364, 366, 362** for early, late,
default, scrambled. **G3 -2** (interval -15 to +12).

The after-the-fact screen explained it: default regret over the scheme catalog is
**+1, +11, +2, +13** at child sizes 3, 6, 12, 24, and a size-adaptive rule buys
**+6 in total**. The other two candidate states were then screened before any
machinery was built for them. **Regime boundaries**: built is at or above pooled
at every size in both confirmations, so "when to partition" transmits nothing.
**Acquisition policy**: at K=8 nine selection rules, including eight averaged
random draws, all score between 320 and 327; regret against the trivial default
is **-21** at K=4 and **-4** at K=8. The defensible conclusion is that no practically sufficient recursive
advantage was found in the tested transmission classes, at the tested budgets,
under the specified endpoint. It is not a proof that every recursive mechanism
in the environment is exhausted; in particular the endpoint is accuracy, and an
inherited procedure that reached the same accuracy at lower construction cost
would not have been detected.

### 4.6 Monotonicity

Construction growth is real and replicated in aggregate and is **not strictly
monotone** in history size. Replication two dips from 362.7 at 16 banks to 358.0
at 24; the rotation agreed at four of five folds. Replication one's clean curve
was the luckier draw. E4 was predeclared as reported-not-gated and is reported.

### 4.7 Process errors

Recorded because each cost real time and each is now a rule.

1. **Baseline strength.** Growth was measured against one-observation parents,
   random draws and uninformed constants for roughly forty experiments and once
   more in this programme. Rule: compare against the strongest rule a
   researcher would write for free, chosen adversarially and stated.
2. **Baseline draw.** One predeclared seed as the small-history arm made two
   replications disagree by 54 points. Rule: score small arms as expectations
   over windows.
3. **Screening after building.** The recursive experiment was built and run
   before its transmissible state was screened, hours after the screening
   discipline was established for action spaces. The screen costs minutes and
   predicted the null exactly. Rule: P2c and P2d on the transmissible state
   before any recursive machinery.
4. **A confounded reading.** The construction-space screen was first read as
   "shallow labelling beats deep." It was a 40k-label budget cap acting on a
   single global model, which at depth 100 labelled 424 of 1,152 tasks and
   lost breadth. The regional grid reversed it: deeper helps region models, and
   testing wider is better or flat at every train depth. Corrected in the doc.
5. **Premature closure.** After nine action spaces failed, the programme was
   declared infeasible in this benchmark. The tenth space, specified by that
   same analysis, succeeded. The feasibility document carries a superseded
   banner; its real content, that growth is impossible wherever a free heuristic
   already captures the value, still holds.
6. **Provenance.** A runner applied a losing-bank cap to G1 that the protocol did
   not specify. Because the manifest hashes the runner at prepare time, the run
   was stopped and restarted rather than patched afterwards.
7. **A wrong context feature.** The heterogeneous protocol assumed familiar and
   shifted AST generators used disjoint Unicode blocks. Both emit 0x800. Caught
   before compute and replaced with label-free model confidence.
8. **A misused helper.** Bootstrap intervals were computed by passing 200
   across-draw totals to a helper that bootstraps sums of paired per-bank
   differences, inflating them about 200-fold. Replaced with percentiles and a
   win rate.
9. **Commit exhaustion.** Runs died with `MemoryError` at hundreds of kilobytes
   while tens of gigabytes of RAM were free, because Windows commit was held by
   idle model servers. Fixed by trimming JSON parsing and running audits one
   panel per process, without touching the other processes.

## 5. Why

### 5.1 Growth is measurable only where no free heuristic captures the value

Every failure and every success reduces to one quantity: what remains after the
best thing a researcher can do without any verified labels. Fixed regret asks
that of constants; default regret asks it of hand-written rules; learnability
asks whether what remains is structure or noise. Enlarging the action space
tenfold, from whole-bank menus (+5) to region purchases (+54), multiplied total
value and left the learnable residual flat at +1 to +12, because what grew was
the value of the constant.

### 5.2 Residual over the default: created by construction, captured by selection

An earlier draft framed this as construction versus selection. That is too
strong, and the routing result refutes it: routing is selection, and it
succeeded. The supported statement is narrower. Selection fails when defaults
already capture the available value or when the remainder is unlearnable;
construction can create complementary components that leave a residual worth
selecting over. Every replicated gain, +35 for the first E0 reranker, +70 and
+51 for the AST specialists, +49 for the region specialists, +37 and +32 for the
complexity specialists built in-run, came from construction creating that
residual, and the routing and construction confirmations are the two cases in
which selection then had something to capture. The failures were selection over
menus with no residual.

### 5.3 Why the complexity partition is different

In this benchmark the mechanism family is visible in the Unicode block, or
recoverable from specialist confidence, and specialists transfer poorly across
families, so "match the family, take the most data" is near-optimal and free.
The complexity partition is invisible before solving, does not align with
family, and correlates with public pool statistics. That is exactly the
combination P2c and P2d require: unguessable and learnable. It was found by
asking what the nine failures had in common and constructing its negation.

### 5.4 Why recursion fails one level up

The same structure recurs at the process level. Partition scheme, when to
partition, and which banks to acquire each have a default that is already good
enough, with regret between -21 and +13. A parent cannot transmit what a child
can guess. Demonstrating recursive growth here would require an environment
whose *construction process* has a non-obvious optimum, and none of the
transmissible states this improver exposes has one.

### 5.5 What this says beyond the benchmark

Nothing here shows that good defaults dominate in general. It shows that they
dominate in this synthetic domain and that this is measurable in advance for a
few minutes of compute. The transferable result is the screening framework and
the two baseline rules, which together turn "did the improver grow" from a
question answered by forty expensive negatives into one answered by four cheap
screens and then one frozen run.

## 6. What is not claimed

- **Generality.** One synthetic string/program benchmark, one notion of
  complexity, one base ranker whose order defines the latent bin.
- **The partition rule.** Bin edges on first-correct rank are researcher
  written. The improver computes the partition and trains every model; it did
  not invent the rule. This is the remaining purity gap.
- **Monotonicity.** More history helps on average and not at every step.
- **Recursive growth.** Not found in three tested transmission classes at the
  tested budgets under an accuracy endpoint. Not shown impossible.
- **Total-compute superiority.** Label and candidate-score budgets are matched
  in every gate; end-to-end wall time is reported, not gated.

## 7. Reproduction

`REPRODUCIBILITY-LEDGER-2026-09-21.md` lists each frozen run with its protocol
hash, seed ranges, gates, audit status and the exact staged commands. Every run
regenerates from seeds to the same task ids, pools, candidate orders, labels,
feature matrices and curve points; that is what each audit checks and reports.

## 8. Corrections after external review, 2026-09-21

Two reviews of this document were received. The following are accepted and
applied above; each is also recorded in the results file it affects.

1. **E3 traceability.** The reviewers' endpoint arithmetic, 26.0 and 19.0, was
   right and the reported 24 and 20 were rounding artifacts. E3 is now one
   estimand with its own paired interval, and replication two's interval touches
   zero. Sections 1 and 3.5 updated.
2. **Out-of-fold routing.** In the construction runs the router was fitted on
   specialist predictions for the specialists' own training rows. The
   independent auditor reproduced that faithfully because it follows the same
   specification, which is the reviewers' point that an information-flow audit
   is not a reproduction audit. The routing confirmation is not affected: its
   specialists were trained on separate source panels and its router saw only
   out-of-sample views. An out-of-fold rerun on both construction replications,
   with capacity-matched and feature-augmented pooled baselines, is
   `construction_oof_audit.py`; its result supersedes E1 and E3 above.
3. **P2b is heterogeneity, not non-stationarity.** Per-instance variation in the
   best action exists under i.i.d. sampling, and drift need not create any
   routing opportunity. Renamed in the design document.
4. **Retrospective versus prospective.** Section 3.2 now splits the screening
   record: one confirmed prospective positive, five untested rejections.
5. **Construction versus selection** is not the divide; residual over the
   default is. Section 5.2 rewritten.
6. **"Closed for this environment"** overstated the recursive null. Narrowed to
   the tested classes, budgets and endpoint.
7. **Reproduction is not independence.** 646,028 rechecked labels establish
   computational reproducibility. The sampling unit for the improver claims is
   the transfer bank, twelve per replication; for any recursive claim it would
   have to be the whole lineage. The exact-enumeration interval assumes bank
   exchangeability and is not a coverage guarantee.
8. **Adaptive holdout reuse.** One opened panel served as the held-out target
   for the partition screen, the routing and construction development runs, the
   recursive experiment and its scheme screen, and replication one's frozen
   transfer panel was later read by the acquisition screen. A sealed replication
   set, seeds 919100 to 919311, is reserved and will not be opened until a final
   confirmatory protocol is hashed.

9. **Construction-form improver growth is withdrawn.** The out-of-fold and
   capacity-matched audit (`construction_oof_audit.py`) on both frozen
   replications found that one pooled model with 60 leaves beats the built
   system by **50 and 36** at 24 banks, at every history size, with intervals
   entirely negative, and that in-sample router fitting had inflated
   replication one by **+14** (interval +1 to +27). E3 crosses zero or is
   negative against every baseline. E2 survives and means only that more
   verified data helps, which the pooled model demonstrates too. The reviewers
   named capacity-matched pooling as the largest risk to the headline; it was
   the actual flaw. Sections 1 and 3.5 are superseded by this item and by the
   withdrawal section of the results file. Verifier growth is strengthened by
   the same audit: the capacity-matched pooled model beats E0 by +73 and +69.
   The routing-form claim was not examined by this audit and has not been
   compared against a capacity-matched pooled model; that check is owed.

## 9. Final position after the capacity-matched audits

After the reviews, three further checks were run on the frozen caches and the
opened screen panels, each adding a single larger pooled model to the set of
zero-knowledge defaults. That one addition changes the programme's conclusion.

| check | finding |
| --- | --- |
| construction, out-of-fold router | leakage inflated replication one by **+14** (interval +1 to +27) |
| construction, 60-leaf pooled baseline | beats the built system by **50 and 36** at 24 banks; E3 negative or crossing zero everywhere |
| construction, 60-leaf specialists too | trails pooled-60 at 4 to 16 banks and is level with it at 24 (E1 +6 and +3, intervals crossing zero); E3 vs pooled-60 **+14.7** (interval +0.3 to +30.3) and +8.3 (crossing zero), a weak growth-rate hint at matched capacity, not a result; pooled-120 beats it at every size |
| routing, 60-leaf pooled on the same history | beats the routed system by **35 and 29**; with the specialists' source labels, by **62 and 37**, every interval negative |
| partition environment, 120-leaf pooled default | beats the latent own-bin oracle on all three screen panels; **P2d fails**, selector -2 (interval -10 to +7) |

**What stands.** Verifier growth: a larger model on more verified labels is a
better evaluator, replicated, audited, and now the strongest component built in
any frozen run. The four preconditions as a screening framework. The
reproducibility machinery, which reproduced every specification faithfully. The
two baseline rules from earlier in the day. The recursive null, narrowed.

**What does not.** No learned improver in this programme produced a system
that beats the strongest free procedure on the same labels. Both forms of
improver growth hold in the measurement contract's literal sense, a later
checkpoint beats an earlier one from the same base, and both are dominated by
"fit one larger model", which needs no improver. The complexity partition was
not latent structure; it was four small models outperforming one small model.
By the adversarial-default standard the programme itself adopted, applied with
model capacity in the default set, **no RSI-relevant improver growth is
demonstrated in any form.**

**The single rule that would have caught all of it in one screen.** P2c's
adversarial default set must contain model capacity, a single larger model on
the same labels, and not only hand-written rules. Every apparent improver result
here was measured against defaults that had less capacity than the improver's
output. The reviewers named this as the largest risk to the headline before any
of these checks were run; they were right, and the framework was one clause
short of catching it itself.

**On the reviews' proposed next programme.** A restricted constructor
language, a three-arm lineage design and common-state replay remain the right
shape for a recursive test. But this outcome moves the prerequisite: before any
constructor language is built, the target environment must be shown to have
residual value over a capacity-matched pooled default, and the constructor
language must be able to express "one larger model" so that it can only win by
doing something a larger model cannot. Otherwise the next programme rediscovers
this one.

## 10. Mechanism holdout: the last claim is instance-level

The third review observed that fresh seeds establish instance-level transfer
only, and the programme adopted "improvement on unfamiliar problems" as the
definition of intelligence growth. The first mechanism-level test,
`mechanism_holdout_verifier.py`, trains the 60-leaf pooled evaluator on five
families and scores it on the sixth, 288 tasks per family over 36 banks.

| family | E0 | held out | in distribution | held out minus E0 |
| --- | --- | --- | --- | --- |
| transform | 169 | 107 | 218 | -62, interval -77 to -47 |
| ast | 41 | 1 | 88 | -40, interval -52 to -29 |
| novel operator | 140 | 114 | 190 | -26, interval -39 to -13 |
| stack | 238 | 214 | 262 | -24, interval -40 to -8 |
| mutation | 191 | 169 | 191 | -22, interval -37 to -7 |
| self edit | 241 | 111 | 245 | -130, interval -149 to -111 |
| total | 1020 | 716 | 1194 | -304 |

The evaluator that beat E0 by +73 and +69 on fresh instances is worse than E0
on every mechanism it has not seen, every interval negative. Its in-distribution
gain over E0, +174, is smaller than its transfer gap, +478: the improvement is
familiarity with the six families, not a better judge of candidates. E0 saw all
six families, so the E0 comparison flatters E0; the transfer gap does not use
E0 and says the same thing.

**Final position.** Every transfer result in this repository is instance-level.
Improver growth in every form is dominated by one larger pooled model on the
same labels. Verifier growth is within-distribution specialization that
regresses below the base on unseen mechanisms. Under the adopted definition,
the programme has demonstrated no intelligence growth. What it has produced is
a screening framework, two baseline rules, an adversarial-default clause that
must include model capacity, a mechanism-holdout gate that must accompany every
evaluator claim, and a reproducibility apparatus that reproduced each flawed
specification faithfully and was therefore unable to catch any of this. Record
in `MECHANISM-HOLDOUT-VERIFIER-2026-09-21.md`.

**Capacity buys familiarity.** The same holdout at 15, 60 and 120 leaves gives
in-distribution totals of 1000, 1194 and 1230 and held-out totals of 762, 716
and 706; the transfer gap widens from +238 to +478 to +524. Larger evaluators
are better on the six familiar generators and worse on the one they have not
seen. The capacity that beat every improver in this programme is the same
capacity that fails to transfer. Two rules follow: the adversarial default must
include model capacity, and the held-out-mechanism gate must be run at the
deployed capacity, with any capacity increase justified on held-out mechanisms.