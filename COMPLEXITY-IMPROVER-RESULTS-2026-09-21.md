# Improver growth, confirmed on frozen banks, 2026-09-21

> **SCOPE NARROWED 2026-09-21 after the capacity-matched check.** C1 and C2
> below hold exactly as stated and were reproduced to the integer by an
> independent reimplementation (`routing_capacity_check.py`). What does not
> hold is any reading that the routed system is a good use of its history. A
> single 60-leaf pooled model trained on the same 24 history banks beats the
> routed system by **35 and 29**, and by **62 and 37** when it also sees the
> specialists' source labels, with every interval entirely negative. The router
> learns from history; the design class it learns within loses to a free
> procedure that needs no improver. See the capacity section at the end.

Protocol: `EXPERIMENT-complexity-improver-confirmation.md`, hashed before any
bank for either replication existed.
Runs: `runs/complexity-improver-confirmation-20260920/` and
`runs/complexity-improver-confirmation-rep2-20260920/`.

## Result

**Both frozen replications pass both gates.** A router fitted on twenty-four
banks of verified history beats one fitted on two, and beats the zero-knowledge
default, on banks generated after the protocol was hashed.

| | replication one | replication two |
| --- | --- | --- |
| **C1**, large history minus zero-knowledge default | **+22**, 7w/2l, interval **+6 to +38** | **+23**, 9w/2l, interval **+4 to +42** |
| **C2**, large history minus expected small history | **+36**, 10w/2l, interval **+19 to +51** | **+47**, **12w/0l**, interval **+33 to +64** |
| curve monotone in history size | yes | yes |
| default / oracle | 329 / 434 | 343 / 445 |

Learning curves, expected total over every contiguous window of that size:

| history banks | replication one | replication two |
| --- | --- | --- |
| 2 | 314.9 | 321.0 |
| 4 | 334.1 | 330.4 |
| 8 | 341.4 | 344.4 |
| 12 | 346.9 | 358.7 |
| 16 | 348.7 | 361.1 |
| 24 | **351.0** | **366.0** |

Both rise strictly with history. Replication two won on every one of twelve
transfer banks.

## Audits

Replication one: **passed**. 1,728 tasks regenerated from seeds, all pools and
both candidate orders recomputed, 160,912 candidate labels rechecked, the latent
complexity bin recomputed, and the whole history-size curve and both gates
rebuilt without importing the runner's scoring, router fitting or gate helpers.
Every curve point reproduced exactly. Zero failures.

Replication two: **passed**. 1,728 tasks regenerated, 161,932 candidate labels
rechecked, every curve point reproduced exactly (321.0, 330.4, 344.4, 358.7,
361.1, 366.0), both gates rebuilt independently. Zero failures.

**Both replications pass both gates with passing independent audits**, which is
the reporting rule declared in the protocol.

## Why this environment worked when nine others did not

`IMPROVER-GROWTH-FEASIBILITY-2026-09-20.md` screened nine action spaces against
four preconditions and every one failed at least one. The failures shared a
cause: the structure that decides which specialist works *was* the structure
that is visible, so a free heuristic always existed. Usually it was "use the
specialist matching this task's mechanism"; where that broke, the specialists'
own confidence recovered the mechanism anyway.

This environment partitions specialists by **solution complexity**, how deep the
first correct candidate sits in the old ranker's order, rather than by mechanism
family. That property

- is **latent**: knowing it requires knowing the answer;
- **cross-cuts** mechanism family, so no family-matching rule can express it;
- is **partly predictable** from public pool statistics, which is what makes it
  learnable rather than noise.

Measured on opened panels, default regret against the most-confident rule is
**+123, +101 and +89**, and a held-out selector beats that rule by **+19,
interval +5 to +33**. It is the first action space to clear P2c and P2d
together.

## What is and is not claimed

**Claimed, and now unconditional.** Within this synthetic benchmark, a retained
improver becomes
measurably better at deploying a fixed set of evaluator components as it
accumulates verified history, and that gain transfers to untouched banks,
survives a zero-knowledge baseline, replicates twice on frozen banks and
reproduces under independent audit.

**Not claimed.**

- **Specialist construction.** The four complexity specialists are trained once
  on opened source panels and frozen. This tests improver *routing*, not
  improver *construction*.
- **Recursive growth.** No child-improver test was run. Nothing here shows a
  later improver producing a better *improver*.
- **Generality.** One synthetic string/program benchmark and one notion of
  complexity. The nine failed spaces are evidence that this result depends on
  environment structure, not only on the learner.

## Methodology that made the difference

Two errors were found and corrected earlier the same day, and both are built
into this protocol rather than rediscovered:

1. **Baseline strength.** Earlier apparent passes, including a +80, were
   measured against a one-observation parent. Against the strongest rule a
   researcher would write for free, that +80 became -4. Here C1 exists precisely
   to force the comparison against the zero-knowledge default.
2. **Baseline draw.** The small-history arm is scored as its *expected* value
   over every contiguous window, never one predeclared seed. The earlier
   replication pair disagreed (+80 then +26) only because one drew a baseline
   bank scoring 46 and the other drew 92.

The four preconditions, P2 power, P2b non-stationarity, P2c default regret and
P2d learnability, cost one cheap screen each and correctly predicted both the
nine failures and this success.

## Limits

- The complexity bin derives from the old ranker's order, so it is latent but
  not independent of that ranker; a different base ranker could change the
  partition.
- Contiguous windows within one history pool are not independent samples.
- Oracle and own-bin routing use final or latent labels and are upper
  references, not deployable policies.
- Specialists were trained on panels that are opened, so their construction is
  not part of the frozen evidence.

## Capacity-matched check, 2026-09-21

External review asked whether the routed system beats the strongest free
alternative, not only the most-confident rule. Feature caches were built for
both frozen runs (`routing_cache_build.py`) and `routing_capacity_check.py`
compared the 24-bank routed system against single pooled models on the untouched
transfer panels. The routed and most-confident totals reproduce the frozen
results to the integer.

| arm | rep 1 | rep 2 |
| --- | --- | --- |
| routed, 24-bank router over the four frozen specialists | 351.0 | 366.0 |
| most-confident rule (the C1 default) | 329.0 | 343.0 |
| pooled-15, source panels plus history | 336.0 | 329.0 |
| **pooled-60, the 24 history banks only** | **386.0** | **395.0** |
| **pooled-60, source panels plus history** | **413.0** | **403.0** |

| routed minus | rep 1 | rep 2 |
| --- | --- | --- |
| most-confident | +22.0, 7w/2l, +6 to +37 | +23.0, 9w/2l, +4 to +42 |
| pooled-15, all labels | +15.0, 8w/3l, 0 to +29 | +37.0, 9w/0l, +20 to +57 |
| **pooled-60, history only** | **-35.0**, 1w/10l, **-51 to -20** | **-29.0**, 2w/10l, **-43 to -14** |
| **pooled-60, all labels** | **-62.0**, 0w/12l, **-75 to -48** | **-37.0**, 1w/11l, **-54 to -20** |

Two readings, both correct, and the distinction between them is the point.

Under the measurement contract as written, C1 and C2 stand: a later improver
checkpoint (24 banks) produces a better child system than an earlier one (2
banks) from the same base, and beats the rule that needs no history. That is
improver growth in the contract's literal sense.

Under the adversarial-default standard the programme itself adopted in P2c, the
default must be the strongest thing a researcher can do for free, and "fit one
larger model on the same labels" is free. Against that default the routed
system has negative residual value in both replications. The improver grew
toward a ceiling that sits below the default. On this standard, which is the
one that matters for a self-improvement claim, routing-form improver growth is
not demonstrated. The error in the original protocol was that its adversarial
default set contained rules but not model capacity.

The same omission affected the environment this run was built on. The sentence
"it is the first action space to clear P2c and P2d together" above was true
against the defaults then in use. Re-screened with a 120-leaf pooled model in
the default set (`analysis/partition-rescreen-capacity-20260921.json`), that
model scores 412, 405 and 413 on the three screen panels, above the partition's
own latent oracle routing at 392, 401 and 400, and a held-out selector loses to
it by 2 (interval -10 to +7). P2d fails. The complexity partition was four
small models outperforming one small model, not latent structure.
