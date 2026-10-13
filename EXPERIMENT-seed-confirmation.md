# Seed confirmation protocol (FROZEN 2026-10-11)

Drafted 2026-10-11 after the development runs of `rsi/seed.py` (seeds s1, s2,
s3; `paper/seed-growth.pdf`) and frozen the same day, before any confirmation
seed was opened, with these SHA-256 hashes:

```
fde98de8c41f65f8314c919a27f848504562110ffcafedf7ccbc3e589d88d850  rsi/seed.py
15a2b0f65ccb52ee60aa423a43ec2c2caf80af9091c33a28de182e8915fb49a9  rsi/seed_areas.py
aefd9cc94f7dbf8f54eb311baae6245522bf212bdbca4b6ac63cb5f13cfa9c83  rsi/invention.py
e9c6a2b3ed10cd6bb33306ca5234c06b5a087c739fcf71c65aa97593a205f2a3  rsi/self_world_model.py
98c0301b4b7575eff3fd3cca551af048ba1aaf99dd6b8441265434bd8b67fa0d  seed_run.py
b6f5f11a0632b5af605729377a9a75561440fda21c5e0ff27ad310d26dd0da6c  seed_check.py
271cb85d5a83c83173fbb3d63d441d187fed1a3850ae58e85f0c8f88e5828420  audit_seed.py
```

Runner: `confirm_seed.sh <name> <seed>` (the schedule below, then the check
and the audit), log `runs_seed_conf_<name>.log`.

## Claim under test

C-seed: one seed, started with the mechanism area's seed language (no
popcount, no xormod), no model and no prior, that lives a fixed schedule of
lives in three areas and keeps only changes it proves, ends with a carried
state that solves more of each area's fresh held-out set than its starting
state, without losing on any pool of any area.

## Seeds and schedule

- Confirmation seeds 919100 (replication A) and 919101 (replication B), sealed
  and unopened at the time of writing. Development seeds 643101, 644101,
  645101 are not used.
- Schedule, fixed: mech 4 lives, then drawn7 3 lives, then metric777001
  3 lives, then mech 2 lives. 48 worlds per life, budget 1,024, held-out 24
  per pool and at least 48 worlds (so 48 for drawn7, 48 for metric, 72 for
  mech), cross-area 12 per pool and at least 24 worlds, tolerance 2%,
  acceptance by paired bootstrap 95% interval above zero, workers as the machine
  allows (workers never change results: the tie-break and every world seed
  are functions of the confirmation seed).
- Everything the seed reads is label-free (`rsi/seed.py`, docstring). Labels
  score only.

## Endpoints

Fresh held-out sets of each area with salt 999 (`seed_check.py`), 24 worlds
per pool, never used by any proof (proof salts are 1000 x area index + life). For each area: start = initial language, no model, no
prior; carried = the final state.

## Gates, both replications

1. Growth: carried total exceeds start total by at least 15% in every area
   (mech, drawn7, metric777001).
2. Safety: on no pool of any area is carried below 90% of start.
3. Economy: proof scans do not exceed 2.5 times live scans.
4. Provenance: every kept change's proof recomputes (audit) and every kept
   change's held-out salt is unique within its area.

Gate 2 is the one the development runs came closest to failing: s1's mech
untrained pool fell 24 -> 18 per world at version 24 and recovered to 91% of
its start after the self-model prune. No label-free guard was built; the
protocol is frozen as is and a failure will be reported as one.

## Forecast (to be committed before the run)

Committed before opening 919100, from the three development seeds:

- Gate 1 growth >= 15% in every area: mech 0.95 (dev: +45% to +92%), drawn7
  0.70 (dev: +72%, +92%, -12%), metric 0.90 (dev: 3x to 5x). All three: 0.6.
- Gate 2 no pool below 90% of start: 0.45 (s1 untrained ended at 91%; the
  other seeds' pools were not checked).
- Gate 3 proofs <= 2.5x live: 0.5 (s1 2.46x before the half-set early stop;
  the larger single-pool sets add cost, the early stop removes some).
- Gate 4 audit: 0.8. The auditor replayed s2's two chain-time metric proofs
  and both mismatched (carried 381 recorded, 447 replayed) for a reason not
  found: the replay is deterministic across processes, worker counts and
  hash seeds, the held-out draw is reproducible, and the chain ran the same
  code. On a proof produced by the current code (throwaway seed 919, one
  mechanism life, language +40 + model kept) the audit passed exactly, totals
  and interval. Snapshots are now rewritten at every kept proof.
- All four gates on both replications: 0.15.

## Audit

`audit_seed.py` rebuilds each area from the state's specs, redraws each kept
change's held-out set from the ledger's salt, reruns the before and after
snapshots and checks the totals and the interval against the ledger.

## What a pass would and would not establish

A pass: one artifact grows across three areas of different structure on
sealed seeds, keeping only proven changes, without harming any pool, at a
stated cost. It would not establish recursive growth in the programme's sense
(the operations are fixed), transfer to a second task form or domain, or
growth past the schedule's length.

## Results

### Replication A, seed 919100 (`seeds/c1`, `runs_seed_conf_c1.log`), 2026-10-11

Fresh held-out sets (salt 999, 24 worlds per pool), start -> carried:

| area | start | carried | gain | pools start -> carried (tasks per world) |
| --- | --- | --- | --- | --- |
| mech | 1,128 | 1,997 | +77% | trained 21.5 -> 34.9, untrained 21.5 -> 35.6, unfamiliar 4.1 -> 12.8 |
| drawn7 | 236 | 385 | +63% | env 9.8 -> 16.0 |
| metric777001 | 405 | 1,055 | +160% | seen 14.3 -> 30.8, unfamiliar 2.6 -> 13.2 |

Kept changes (7 of 33 candidates): mech life 0 language +40 + model; mech
life 2 prune -18; drawn7 life 1 model; drawn7 life 2 prune -6; metric lives 0
and 1 model; mech life 4 model. Every extension after life 0 was rejected,
twice by the cross-area check (metric life 0 "together" cost mech 1002 -> 965
on 72 worlds; drawn7 life 1 "together" cost mech 1012 -> 945).

- Gate 1 growth >= 15% every area: PASS.
- Gate 2 no pool below 90% of start: PASS (every pool rose).
- Gate 3 proofs <= 2.5x live: FAIL, 5.96x (351M proof scans against 59M live).
  The larger held-out sets (48 worlds for single-pool areas, 24-world
  cross-area sets) and a language candidate on nearly every life, each
  tested together and alone across every other area, are the cost.
- Gate 4 audit: PASS, all 7 kept changes replay exactly; salts unique per area.

Forecast scoring: gates 1, 2 and 4 were given 0.6, 0.45 and 0.8 and passed;
gate 3 was given 0.5 and failed.

### Replication B, seed 919101 (`seeds/c2`, `runs_seed_conf_c2.log`), 2026-10-11

| area | start | carried | gain | pools start -> carried (tasks per world) |
| --- | --- | --- | --- | --- |
| mech | 1,223 | 1,944 | +59% | trained 25.0 -> 33.2, untrained 21.0 -> 29.8, unfamiliar 4.9 -> 18.0 |
| drawn7 | 271 | 318 | +17% | env 11.3 -> 13.2 |
| metric777001 | 318 | 1,619 | +409% | seen 8.7 -> 40.4, unfamiliar 4.5 -> 27.0 |

Kept changes (8): mech life 0 language +40 + model; mech life 3 language +40
+ prune -27 + model; drawn7 life 0 language +40 + prune -26 + model; drawn7
life 1 language +40; metric life 0 language +40 + prune -20 + model; metric
life 1 model; metric life 2 prune -51; mech life 4 model. This seed accepted
four extensions where seed 919100 accepted one; its drawn7 gain is the
smallest of the six area results and the closest to the 15% line.

- Gate 1: PASS. Gate 2: PASS (every pool rose). Gate 3: FAIL, 5.88x.
- Gate 4: PASS, all 8 kept changes replay exactly; salts unique per area.

### Verdict

Gates 1, 2 and 4 pass on both sealed seeds; gate 3 fails on both. The
protocol as frozen is therefore failed on cost and passed on growth, safety
and provenance. Development seeds s1, s2, s3 and these two confirmation seeds
are now all used; any cost fix must be confirmed on new sealed seeds.


## Protocol v2 (FROZEN 2026-10-11, after the v1 verdict)

v1 failed only its cost gate, on both seeds, and the arithmetic says why: a
fresh held-out set every life makes the carried state's re-score alone 1.5x
the cost of a 48-world life in the mechanism area (72 worlds), and three
candidates per life on top make 4x to 6x unavoidable however early the
losers stop. v2 changes the schedule's economics, not the acceptance rule:

- Lives are 96 worlds (was 48): the agent lives twice as long between tests.
- Every acceptance test uses 48 worlds in every area (mechanism 16 per pool,
  was 24 per pool = 72); the cross-area check stays at 24 worlds minimum.
- The held-out set of an area changes only after an acceptance in that area;
  a set on which nothing was accepted carries no selection bias, and the
  carried state's score on it stays cached.
- A candidate stops at the half set when its mean gain there is not positive
  (was: only when the half-set interval lay wholly below zero).

Dev measurement before freezing (seed 778, mech 2 / drawn7 1 / metric 1,
`runs_seed_d2.log`): proof scans 2.06x live; the same schedule under v1 with
the first two cuts alone read 5.1x (`runs_seed_d1.log`, seed 777). Growth on
those dev lives was unchanged in kind (mech held-out 749 -> 1121, drawn7
529 -> 822, metric 444 -> 1368 on the per-life sets).

Seeds: 919102 (replication C) and 919103 (replication D), sealed and unopened
at the time of writing. Schedule as v1 (mech 4, drawn7 3, metric 3, mech 2
lives), endpoints and gates as v1 (growth >= 15% every area, no pool below
90% of start, proofs <= 2.5x live, every kept change replays with salts
unique per area). Runner `confirm_seed.sh <name> <seed>` now passes
`--worlds 96 --held-out 48`.

Hashes:

```
5673d937d45063bbafd31cd03a0b17bf55c6424befc2beb42dd7c87f49996f7d  rsi/seed.py
15a2b0f65ccb52ee60aa423a43ec2c2caf80af9091c33a28de182e8915fb49a9  rsi/seed_areas.py
aefd9cc94f7dbf8f54eb311baae6245522bf212bdbca4b6ac63cb5f13cfa9c83  rsi/invention.py
e9c6a2b3ed10cd6bb33306ca5234c06b5a087c739fcf71c65aa97593a205f2a3  rsi/self_world_model.py
b2fadf612c34d4c122011dfce15b5711abeae6d50bb3c01c164bec205c9109f9  seed_run.py
b6f5f11a0632b5af605729377a9a75561440fda21c5e0ff27ad310d26dd0da6c  seed_check.py
271cb85d5a83c83173fbb3d63d441d187fed1a3850ae58e85f0c8f88e5828420  audit_seed.py
3676f13465e58b584b0e180e89630310a9216682bc3e996a2818161c5deb294c  confirm_seed.sh
```

Forecast, committed before opening 919102: gate 1 0.85, gate 2 0.6 (both
v1 seeds passed with every pool up), gate 3 0.75 (dev 2.06x; a seed that
accepts on many lives re-scores more often), gate 4 0.9; all four gates on
both seeds 0.35.

### Replication C, seed 919102 under v2 (`seeds/c3`, `runs_seed_conf_c3.log`), 2026-10-11

| area | start | carried | gain | pools start -> carried (tasks per world) |
| --- | --- | --- | --- | --- |
| mech | 1,020 | 2,010 | +97% | trained 20.6 -> 30.9, untrained 19.2 -> 37.1, unfamiliar 2.6 -> 15.8 |
| drawn7 | 281 | 409 | +46% | env 11.7 -> 17.0 |
| metric777001 | 364 | 1,550 | +326% | seen 9.3 -> 38.8, unfamiliar 5.8 -> 25.8 |

Kept changes (8): mech lives 0, 1, 2 (language +40 + model each, the third
with prune -34); drawn7 life 0 (language +40 + prune -43 + model); metric
life 0 (language +40 + prune -26 + model), metric life 1 (prune -4, then
model, two separate acceptances), mech life 4 (language +40 + prune -37 +
model). Proof scans 222M against 118M live.

- Gate 1: PASS. Gate 2: PASS (every pool rose). Gate 3: PASS, 1.89x.
- Gate 4: replay PASS, all 8 kept changes reproduce exactly; the salt
  uniqueness clause FAILS: in metric life 1 the prune was accepted and then
  the model was accepted in the same life, on the same held-out set (salt
  3001 twice). The parts of one life share that life's set by construction,
  in v1 as in v2; this is the first run in which two parts of one life were
  both accepted. The second acceptance is a paired comparison against the
  first's score on the same worlds, so the replay is exact, but the set was
  used to accept twice, which the clause forbids. Recorded as a gate 4 fail.

Fix for a v3, not applied while 919103 runs under the v2 hashes: after an
acceptance within a life, the remaining parts draw a fresh set (salt from
the acceptance count at proof time, not at life start).

### Replication D, seed 919103 under v2 (`seeds/c4`, `runs_seed_conf_c4.log`), 2026-10-11

| area | start | carried | gain | pools start -> carried (tasks per world) |
| --- | --- | --- | --- | --- |
| mech | 1,200 | 1,697 | +41% | trained 21.1 -> 31.9, untrained 23.8 -> 22.3 (94% of start), unfamiliar 5.1 -> 16.5 |
| drawn7 | 255 | 363 | +42% | env 10.6 -> 15.1 |
| metric777001 | 363 | 1,428 | +293% | seen 11.0 -> 32.7, unfamiliar 4.2 -> 26.8 |

Kept changes (5): mech life 0 (language +40 + model), mech life 1 (model),
drawn7 life 1 (model), metric life 0 (language +40 + prune + model), metric
life 1 (language + prune + model). Proof scans 233M against 118M live.

- Gate 1: PASS. Gate 2: PASS, with the untrained pool at 94% of its start,
  the only pool of the four confirmation seeds to fall and the closest any
  came to the 90% line. Gate 3: PASS, 1.98x. Gate 4: PASS, 5 of 5 replay,
  salts unique.

### Verdict on v2

Seed 919103 passes all four gates. Seed 919102 passes growth, safety, cost
and replay and fails the salt-uniqueness clause of gate 4 (two parts of one
life accepted on one set). v2 therefore passes on one sealed seed and fails
one clause on the other; the clause's fix is a v3 (fresh set after any
acceptance within a life) that would need two further sealed seeds. The
untrained-pool dip on 919103 is within tolerance but is the same effect as
on the development seed, in milder form, and remains unguarded.

Forecast scoring for v2: gate 1 (0.85) passed twice, gate 2 (0.6) passed
twice, gate 3 (0.75) passed twice, gate 4 (0.9) passed once and failed once;
all four on both seeds (0.35) did not happen.

## Protocol v3 (FROZEN 2026-10-11, after the v2 verdict)

`seed_run.py` draws the held-out set from the acceptance count at proof
time, so the parts tested after an acceptance within a life get a fresh set;
this closes the clause 919102 failed. Everything else as v2: schedule, lives
of 96 worlds, 48-world tests, gates, endpoints, runner. The untrained-pool
guard is not built; 919103's 94% is the standing evidence that the effect is
mild under v2.

Seeds: 919104 (replication E) and 919105 (replication F), sealed and unopened
at the time of writing.

Hashes:

```
5673d937d45063bbafd31cd03a0b17bf55c6424befc2beb42dd7c87f49996f7d  rsi/seed.py
15a2b0f65ccb52ee60aa423a43ec2c2caf80af9091c33a28de182e8915fb49a9  rsi/seed_areas.py
aefd9cc94f7dbf8f54eb311baae6245522bf212bdbca4b6ac63cb5f13cfa9c83  rsi/invention.py
e9c6a2b3ed10cd6bb33306ca5234c06b5a087c739fcf71c65aa97593a205f2a3  rsi/self_world_model.py
4babdfde950755e0511ffeefa2ca7272cce42323298e7a7eca5d4941ffcf476f  seed_run.py
b6f5f11a0632b5af605729377a9a75561440fda21c5e0ff27ad310d26dd0da6c  seed_check.py
271cb85d5a83c83173fbb3d63d441d187fed1a3850ae58e85f0c8f88e5828420  audit_seed.py
3676f13465e58b584b0e180e89630310a9216682bc3e996a2818161c5deb294c  confirm_seed.sh
```

Forecast, committed before opening 919104: gate 1 0.9, gate 2 0.6, gate 3
0.7 (a fresh set after each in-life acceptance adds re-scores on the lives
that accept more than one part), gate 4 0.9; all four on both seeds 0.4.

### Replication E, seed 919104 under v3 (`seeds/c5`, `runs_seed_conf_c5.log`), 2026-10-11

| area | start | carried | gain | pools start -> carried (tasks per world) |
| --- | --- | --- | --- | --- |
| mech | 1,276 | 1,807 | +42% | trained 27.1 -> 33.9, untrained 22.2 -> 24.8, unfamiliar 3.9 -> 16.7 |
| drawn7 | 280 | 364 | +30% | env 11.7 -> 15.2 |
| metric777001 | 373 | 1,927 | +417% | seen 11.0 -> 46.7, unfamiliar 4.5 -> 33.6 |

Kept changes (7): mech lives 0 and 1 (language +40 + model), drawn7 life 0
(model) and life 1 (prune -21), metric life 0 (language +40 + model) and
life 2 (model), mech life 4 (prune -29). Proof scans 270M against 118M live.

- Gate 1: PASS. Gate 2: PASS (every pool rose). Gate 3: PASS, 2.29x.
- Gate 4: FAIL. Salts are unique, and 6 of 7 kept changes replay exactly,
  but version 6 (metric life 2, model) does not: the ledger's carried score
  is 1,479 and the replay reads 1,526 (the candidate, 1,791, replays
  exactly; the replayed interval is [+2.9, +8.1], so the acceptance stands).
  Cause, found: v2's reuse of a held-out set across lives caches the
  carried state's score per version, but the carried state's search prior
  is built from all of the area's experience, which grows every life
  whether or not anything is accepted. At metric life 1 the carried score
  was computed with 864 experience records; at life 2, with 960, the cache
  was reused. The baseline was stale by 47 tasks. The s2 chain-time
  mismatches predate this cache and remain unexplained.

Fix for a v4: the cached carried score also records the area's experience
count and is recomputed when it changes. This gives back part of v2's cost
saving (the carried is re-scored on every life of an area with a prior), so
gate 3 is at risk again; the honest baseline comes first.

### Replication F, seed 919105 under v3 (`seeds/c6`, `runs_seed_conf_c6.log`), 2026-10-11

| area | start | carried | gain | pools start -> carried (tasks per world) |
| --- | --- | --- | --- | --- |
| mech | 1,147 | 2,366 | +106% | trained 25.7 -> 43.3, untrained 17.4 -> 36.7, unfamiliar 4.7 -> 18.6 |
| drawn7 | 180 | 342 | +90% | env 7.5 -> 14.2 |
| metric777001 | 322 | 1,518 | +371% | seen 10.0 -> 44.8, unfamiliar 3.4 -> 18.5 |

Kept changes (6). Proof scans 1.94x live.

- Gate 1: PASS. Gate 2: PASS (every pool rose). Gate 3: PASS, 1.94x.
- Gate 4: FAIL, the same cause as 919104: version 2 (mech life 3, model)
  records a carried score of 1,327 where the replay reads 1,300; the
  candidate (1,412) replays exactly and the acceptance stands. Salts unique,
  5 of 6 replay.

### Verdict on v3

Growth, safety and cost pass on both sealed seeds. The audit fails on both,
once each, for one cause: the carried score cached on a reused set goes
stale as the area's experience grows. Every acceptance stands on replay. v4
fixes the cache and must be confirmed on two further sealed seeds.


## Protocol v4 (FROZEN 2026-10-11, after the v3 verdict)

The cached carried score on a reused held-out set now records the area's
experience count and is recomputed when that count changes, so the baseline
of every test is the carried state as it is at that moment. Everything else
as v3. Cost rises by one carried re-score per life in an area with a prior.

Seeds: 919106 (replication G) and 919107 (replication H), sealed and unopened
at the time of writing.

Hashes:

```
8771b419951b80571c920ebd0a0522f30e62113a9e20aed4c472403fb978f7e4  rsi/seed.py
15a2b0f65ccb52ee60aa423a43ec2c2caf80af9091c33a28de182e8915fb49a9  rsi/seed_areas.py
aefd9cc94f7dbf8f54eb311baae6245522bf212bdbca4b6ac63cb5f13cfa9c83  rsi/invention.py
e9c6a2b3ed10cd6bb33306ca5234c06b5a087c739fcf71c65aa97593a205f2a3  rsi/self_world_model.py
4babdfde950755e0511ffeefa2ca7272cce42323298e7a7eca5d4941ffcf476f  seed_run.py
b6f5f11a0632b5af605729377a9a75561440fda21c5e0ff27ad310d26dd0da6c  seed_check.py
271cb85d5a83c83173fbb3d63d441d187fed1a3850ae58e85f0c8f88e5828420  audit_seed.py
3676f13465e58b584b0e180e89630310a9216682bc3e996a2818161c5deb294c  confirm_seed.sh
```

Forecast, committed before opening 919106: gate 1 0.9, gate 2 0.65, gate 3
0.55 (v3 read 2.29x and 1.94x with the stale cache saving a re-score on the
lives that kept nothing), gate 4 0.85; all four on both seeds 0.3.

### Replication G, seed 919106 under v4 (`seeds/c7`, `runs_seed_conf_c7.log`), 2026-10-11

| area | start | carried | gain | pools start -> carried (tasks per world) |
| --- | --- | --- | --- | --- |
| mech | 1,129 | 2,136 | +89% | trained 24.6 -> 38.3, untrained 20.3 -> 36.8, unfamiliar 2.2 -> 13.9 |
| drawn7 | 202 | 299 | +48% | env 8.4 -> 12.5 |
| metric777001 | 343 | 1,647 | +380% | seen 11.4 -> 42.3, unfamiliar 2.9 -> 26.3 |

Kept changes (6). Proof scans 2.32x live.

- Gate 1: PASS. Gate 2: PASS (every pool rose). Gate 3: PASS, 2.32x.
- Gate 4: PASS, 6 of 6 replay exactly, salts unique.

All four gates pass.

### Replication H, seed 919107 under v4 (`seeds/c8`, `runs_seed_conf_c8.log`), 2026-10-11

| area | start | carried | gain | pools start -> carried (tasks per world) |
| --- | --- | --- | --- | --- |
| mech | 1,138 | 2,263 | +99% | trained 24.4 -> 45.3, untrained 20.8 -> 29.7, unfamiliar 2.2 -> 19.3 |
| drawn7 | 275 | 382 | +39% | env 11.5 -> 15.9 |
| metric777001 | 248 | 1,901 | +667% | seen 7.0 -> 44.2, unfamiliar 3.4 -> 35.0 |

Kept changes (7). Proof scans 2.04x live.

- Gate 1: PASS. Gate 2: PASS (every pool rose). Gate 3: PASS, 2.04x.
- Gate 4: PASS, 7 of 7 replay exactly, salts unique.

### Verdict on v4

All four gates pass on both sealed seeds, 919106 and 919107. The protocol
passes. Forecast scoring: the 0.3 given to this outcome was too low; gate 3
(0.55) passed twice at 2.32x and 2.04x.

### Summary over the eight sealed seeds

Growth of at least 15% in every area on all eight (smallest +17%, drawn7 on
919101; largest +667%, metric on 919107). No pool below 90% of its start on
all eight (lowest 94%, untrained on 919103). Cost under 2.5x on the six
seeds after v1. Every acceptance stood on replay on all eight; the audit
found two stale recorded baselines (v3) and one doubled set (v2), each a
flaw of the test's bookkeeping and each fixed before the next pair of seeds.


## Protocol v5 (FROZEN 2026-10-11, after the v4 pass)

v4 passed. v5 adds the one guard the development results asked for and the
confirmation runs left unguarded: the untrained pool. The guard is
label-free. Before a candidate that adds atoms to the shared language is
accepted, the candidate and the carried language are also scored with the
area's model and prior switched off, on the even-indexed half of the
held-out set; the candidate is rejected if its unguided score falls more
than 10% below the carried language's. The carried language's unguided score
is cached per language and held-out draw. Candidates that only remove atoms
are not guarded (removal cannot dilute unguided search, and the own-area
test covers it). Rationale: the ablation of the development seed traced the
untrained-pool loss to the grown language diluting the half of the budget
that searches without the model, which is what worlds the model does not
recognise fall back on. Everything else as v4. Gates and thresholds
unchanged.

Dev measurements (mech 2 / drawn7 1 / metric 1, 96-world lives): the guard
at 2% on the full set fired on three of four extensions and read 2.94x
(seed 779); at 10% with the baseline cached by language, 2.69x (seed 780);
on the half set with prune-only candidates skipped, 2.62x (seed 781), the
guard firing once (unguided 398 -> 336 on 24 worlds, extension dropped,
model alone kept). The cost gate is at risk by design: a rejected extension
is re-proposed next life and guarded again. The gate stays at 2.5x.

Seeds: 919108 (replication I) and 919109 (replication J), sealed and unopened
at the time of writing.

Hashes:

```
fc8564c580bc5ab46260753867750ffad0e901698d3c64cd9d45e8520fb699f6  rsi/seed.py
15a2b0f65ccb52ee60aa423a43ec2c2caf80af9091c33a28de182e8915fb49a9  rsi/seed_areas.py
aefd9cc94f7dbf8f54eb311baae6245522bf212bdbca4b6ac63cb5f13cfa9c83  rsi/invention.py
e9c6a2b3ed10cd6bb33306ca5234c06b5a087c739fcf71c65aa97593a205f2a3  rsi/self_world_model.py
4babdfde950755e0511ffeefa2ca7272cce42323298e7a7eca5d4941ffcf476f  seed_run.py
b6f5f11a0632b5af605729377a9a75561440fda21c5e0ff27ad310d26dd0da6c  seed_check.py
271cb85d5a83c83173fbb3d63d441d187fed1a3850ae58e85f0c8f88e5828420  audit_seed.py
3676f13465e58b584b0e180e89630310a9216682bc3e996a2818161c5deb294c  confirm_seed.sh
```

Forecast, committed before opening 919108: gate 1 0.85 (the guard can hold
back the extensions that unfamiliar-family worlds need), gate 2 0.75, gate 3
0.35, gate 4 0.9; all four on both seeds 0.15. Secondary question, not a
gate: whether the untrained pool rises more than under v4 (v4: 20.3 -> 36.8
and 20.8 -> 29.7) and whether the unfamiliar pool rises less.

### Replication I, seed 919108 under v5 (`seeds/c9`, `runs_seed_conf_c9.log`), 2026-10-11

| area | start | carried | gain | pools start -> carried (tasks per world) |
| --- | --- | --- | --- | --- |
| mech | 1,179 | 1,990 | +69% | trained 18.4 -> 41.3, untrained 28.0 -> 25.0 (89% of start), unfamiliar 2.8 -> 16.6 |
| drawn7 | 367 | 388 | +6% | env 15.3 -> 16.2 |
| metric777001 | 281 | 1,872 | +566% | seen 10.0 -> 43.6, unfamiliar 1.7 -> 34.4 |

Kept changes (7): three extensions (+40, +40, +40 with prune -30), three
models, one prune. Proof scans 2.48x live. The guard was evaluated five
times and never fired: the largest unguided loss it saw was 9% (drawn7
life 0, 265 -> 240 on 24 worlds, accepted); the two rejected metric
candidates fell to the cross-area check, not to the guard.

- Gate 1: FAIL. drawn7 grew 6% (367 -> 388); its start, 15.3 tasks per
  world, is the highest start of any seed in that area, and only one model
  was accepted there in three lives.
- Gate 2: FAIL. The untrained pool fell to 89% of its start (28.0 -> 25.0),
  the first pool below 90% in nine sealed seeds, and it fell with the guard
  in place and silent: the three accepted extensions passed the guard at
  unguided losses of 6%, 2% and 9%.
- Gate 3: PASS, 2.48x. Gate 4: PASS, 7 of 7 replay, salts unique.

What this says about the guard: a 10% tolerance on half-set unguided search
does not protect the untrained pool; the dip on this seed accrued across
three extensions that each cost a little. The pool also started high
(28.0, against 19 to 24 on the other seeds), so part of the 11% is the
start's draw. Neither excuses the gate.

### Replication J, seed 919109 under v5 (`seeds/c10`, `runs_seed_conf_c10.log`), 2026-10-11

| area | start | carried | gain | pools start -> carried (tasks per world) |
| --- | --- | --- | --- | --- |
| mech | 1,111 | 2,151 | +94% | trained 22.8 -> 39.9, untrained 20.5 -> 35.9, unfamiliar 3.0 -> 13.8 |
| drawn7 | 278 | 334 | +20% | env 11.6 -> 13.9 |
| metric777001 | 404 | 1,626 | +302% | seen 13.3 -> 44.6, unfamiliar 3.5 -> 23.2 |

Kept changes (7): six models and one extension. The guard fired three times
(mech lives 0 and 1, drawn7 life 0, each an unguided loss of 17% on 24
worlds) and let one metric extension through. Proof scans 2.53x live.

- Gate 1: PASS. Gate 2: PASS (every pool rose). Gate 3: FAIL, 2.53x.
- Gate 4: PASS, 7 of 7 replay, salts unique.

### Verdict on v5

Fails. 919108 failed growth and safety with the guard silent; 919109 failed
cost by 0.03 with the guard firing three times and holding back two
mechanism extensions until life 3. The guard as built neither protects the
untrained pool (a per-candidate tolerance lets a drift accrue) nor pays for
itself. It is retired: `rsi/seed.py` is restored to the v4 hash, and v4
remains the confirmed protocol. A guard that bounds cumulative drift against
the initial language's unguided score is the next design, if one is wanted;
it would need its own pair of sealed seeds.

### Summary over the ten sealed seeds

v4 is the confirmed version (919106, 919107: all gates). Across all ten,
growth of at least 15% in every area on nine (919108's drawn7, +6%), no pool
below 90% on nine (919108's untrained, 89%), cost under 2.5x on six of the
eight after v1, and all 68 accepted changes standing on replay.


## Protocol v6 (FROZEN 2026-10-11, after the v5 verdict)

The v4 code, unchanged (every source hash below but the runner's equals
v4's), with a wider schedule: six areas instead of three. The goal this
programme set is growth in as many areas as possible; the sealed-seed
evidence so far covers three. The schedule is mech 4, drawn7 3,
metric777001 3, drawn11 2, drawn13 2, metric555001 2, mech 2 lives (18 lives,
96 worlds each). drawn11 is 12 groups with 4 per world and no slip; drawn13
is 6 groups with 2 per world and slip 0.15; metric555001 is the metric
structure under a second sparse weighting, never lived by any seed before.
Gates unchanged and applied to every area: growth of at least 15% in each
of the six on fresh held-out sets (salt 999, 24 worlds per pool), no pool
below 90% of its start, proofs at most 2.5x live, every kept change
replaying with a salt unique within its area. Fresh check over six areas.

Seeds: 919110 (replication K) and 919111 (replication L), sealed and
unopened at the time of writing.

Hashes:

```
8771b419951b80571c920ebd0a0522f30e62113a9e20aed4c472403fb978f7e4  rsi/seed.py
15a2b0f65ccb52ee60aa423a43ec2c2caf80af9091c33a28de182e8915fb49a9  rsi/seed_areas.py
aefd9cc94f7dbf8f54eb311baae6245522bf212bdbca4b6ac63cb5f13cfa9c83  rsi/invention.py
e9c6a2b3ed10cd6bb33306ca5234c06b5a087c739fcf71c65aa97593a205f2a3  rsi/self_world_model.py
4babdfde950755e0511ffeefa2ca7272cce42323298e7a7eca5d4941ffcf476f  seed_run.py
b6f5f11a0632b5af605729377a9a75561440fda21c5e0ff27ad310d26dd0da6c  seed_check.py
271cb85d5a83c83173fbb3d63d441d187fed1a3850ae58e85f0c8f88e5828420  audit_seed.py
64ea9eeedd36f643554d23bc0995d291ff7e1d7de718f3b36fae0f447eb430ce  confirm_seed.sh
```

Forecast, committed before opening 919110: gate 1 0.6 (two lives in a new
area have passed 15% on the development seed for drawn11 and drawn13, 199
-> 360 and 294 -> 442, but a two-life area has one or two chances to accept
anything, and metric555001 is untried), gate 2 0.6 (six areas, nine pools),
gate 3 0.7 (more areas, more cross-area checks per language candidate),
gate 4 0.9; all four on both seeds 0.2.

### Replication K, seed 919110 under v6 (`seeds/c11`, `runs_seed_conf_c11.log`, `runs_seed_conf_c11_check.log`), 2026-10-11

The host ran out of memory during the fresh check on the first attempt;
the check and audit were rerun after reese said to proceed (the 18 lives
and their state were complete and untouched).

| area | start | carried | gain | pools start -> carried (tasks per world) |
| --- | --- | --- | --- | --- |
| mech | 1,197 | 2,442 | +104% | trained 24.6 -> 45.2, untrained 21.6 -> 37.5, unfamiliar 3.7 -> 19.0 |
| drawn7 | 305 | 375 | +23% | env 12.7 -> 15.6 |
| metric777001 | 299 | 1,415 | +373% | seen 8.0 -> 40.8, unfamiliar 4.5 -> 18.2 |
| drawn11 | 291 | 424 | +46% | env 12.1 -> 17.7 |
| drawn13 | 375 | 483 | +29% | env 15.6 -> 20.1 |
| metric555001 | 356 | 1,833 | +415% | seen 13.3 -> 50.4, unfamiliar 1.5 -> 26.0 |

Kept changes (10): four in mech, two in drawn7, two in metric777001, one in
drawn11, one in drawn13; metric555001 kept nothing in its own two lives yet
rose 415% on its fresh set from the state the other areas built, the
language above all (unfamiliar centres 1.5 -> 26.0). Proof scans 2.78x
live.

- Gate 1: PASS, six of six areas, smallest +23%.
- Gate 2: PASS, all nine pools rose.
- Gate 3: FAIL, 2.78x. Six areas mean up to five cross-area checks per
  language candidate; v4's 2.0x to 2.3x on three areas does not carry.
- Gate 4: PASS, 10 of 10 replay exactly, salts unique.

### Replication L, seed 919111 under v6 (`seeds/c12`, `runs_seed_conf_c12.log`), 2026-10-11

| area | start | carried | gain | pools start -> carried (tasks per world) |
| --- | --- | --- | --- | --- |
| mech | 1,187 | 2,160 | +82% | trained 22.1 -> 45.0, untrained 23.7 -> 30.9, unfamiliar 3.7 -> 14.1 |
| drawn7 | 305 | 384 | +26% | env 12.7 -> 16.0 |
| metric777001 | 355 | 1,585 | +346% | seen 10.5 -> 39.0, unfamiliar 4.3 -> 27.0 |
| drawn11 | 206 | 341 | +66% | env 8.6 -> 14.2 |
| drawn13 | 176 | 314 | +78% | env 7.3 -> 13.1 |
| metric555001 | 283 | 1,475 | +421% | seen 10.2 -> 40.2, unfamiliar 1.6 -> 21.3 |

Kept changes (11): two in mech (both language +40 with a model), two in
drawn7 (model, prune -39), three in metric777001 (language +40 with a
model, two model refits), one each in drawn11 and drawn13 (models), one
prune -13 in drawn13, one model in metric555001. Proof scans 2.64x live.

- Gate 1: PASS, six of six areas, smallest +26%.
- Gate 2: PASS, all nine pools rose.
- Gate 3: FAIL, 2.64x.
- Gate 4: PASS, 11 of 11 replay exactly, salts unique within area.

### Verdict on v6

Growth, safety and audit pass on both seeds: twelve of twelve areas up by
at least 23%, eighteen of eighteen pools up, 21 of 21 acceptances stand on
replay. The cost gate fails on both (2.78x, 2.64x). v6 FAILS as frozen.

The cost failure has one cause and it was forecast at 0.3: the gate was
set at 2.5x on three areas, and every language candidate that passes its
own area is then checked on every other lived area (24 worlds each), so
the test bill grows with the number of areas. v4's two seeds on three
areas read 2.32x and 2.04x (mean 2.18); v6's two on six read 2.78x and
2.64x (mean 2.71): an increase of 0.53 for three further areas, 0.18 per
area. The structural ceiling is 0.25 per area per life (one 24-world
check against a 96-world life, the carried side cached per version), met
only if every life produces a language candidate that passes its own area.

The cost gate was a guard against testing swamping living, not against
checking more areas. A gate that scales with the areas checked is declared
below as v7; v6's seeds do not count toward it, since the scaled threshold
was chosen after they were read.

## Protocol v7 (FROZEN 2026-10-11, after the v6 verdict)

Same code, same schedule and same gates 1, 2 and 4 as v6 (every hash below
equals v6's). Gate 3 becomes: proof scans at most (2.5 + 0.25 x (k - 3))
times live scans, where k is the number of areas lived; at six areas,
3.25x. The 0.25 per area is the structural ceiling derived above, not the
measured 0.18, so the gate tests whether the cost structure holds on new
seeds rather than whether two numbers repeat.

Seeds: 919112 (replication M, `seeds/c13`) and 919113 (replication N,
`seeds/c14`), sealed and unopened at the time of writing.

Hashes:

```
8771b419951b80571c920ebd0a0522f30e62113a9e20aed4c472403fb978f7e4  rsi/seed.py
15a2b0f65ccb52ee60aa423a43ec2c2caf80af9091c33a28de182e8915fb49a9  rsi/seed_areas.py
aefd9cc94f7dbf8f54eb311baae6245522bf212bdbca4b6ac63cb5f13cfa9c83  rsi/invention.py
e9c6a2b3ed10cd6bb33306ca5234c06b5a087c739fcf71c65aa97593a205f2a3  rsi/self_world_model.py
4babdfde950755e0511ffeefa2ca7272cce42323298e7a7eca5d4941ffcf476f  seed_run.py
b6f5f11a0632b5af605729377a9a75561440fda21c5e0ff27ad310d26dd0da6c  seed_check.py
271cb85d5a83c83173fbb3d63d441d187fed1a3850ae58e85f0c8f88e5828420  audit_seed.py
64ea9eeedd36f643554d23bc0995d291ff7e1d7de718f3b36fae0f447eb430ce  confirm_seed.sh
```

Forecast, committed before opening 919112: gate 1 0.75 (twelve of twelve
areas passed under v6, but two-life areas have one or two chances), gate 2
0.7 (eighteen of eighteen pools rose under v6; mech's untrained pool is
the historically weak one, 94% of start on one v3 seed), gate 3 0.8 (2.64x
and 2.78x against 3.25x), gate 4 0.9; all four on both seeds 0.35.

### Replication M, seed 919112 under v7 (`seeds/c13`, `runs_seed_conf_c13.log`), 2026-10-11

| area | start | carried | gain | pools start -> carried (tasks per world) |
| --- | --- | --- | --- | --- |
| mech | 1,014 | 2,070 | +104% | trained 19.8 -> 36.7, untrained 18.5 -> 29.5, unfamiliar 4.0 -> 20.0 |
| drawn7 | 214 | 374 | +75% | env 8.9 -> 15.6 |
| metric777001 | 493 | 1,723 | +249% | seen 16.2 -> 41.7, unfamiliar 4.3 -> 30.1 |
| drawn11 | 217 | 415 | +91% | env 9.0 -> 17.3 |
| drawn13 | 237 | 375 | +58% | env 9.9 -> 15.6 |
| metric555001 | 308 | 1,390 | +351% | seen 10.8 -> 38.7, unfamiliar 2.0 -> 19.2 |

Kept changes (10): three language extensions of 40 atoms (mech life 0,
metric777001 life 1 with prune -6, drawn11 life 0 with prune -15), five
model refits (mech, drawn7, metric777001, drawn13, metric555001), two
prunes (drawn11 -9, metric555001 -14). Proof scans 2.88x live, the highest
of the four six-area seeds and the one with the most language candidates
passing their own area; 0.23 per area over v4's mean, under the 0.25
ceiling.

- Gate 1: PASS, six of six areas, smallest +58%.
- Gate 2: PASS, all nine pools rose; the weakest rose to 158% of its start.
- Gate 3: PASS, 2.88x against 3.25x.
- Gate 4: PASS, 10 of 10 replay exactly, salts unique within area.

All four gates pass on 919112. 919113 (replication N) opened next.

### Replication N, seed 919113 under v7 (`seeds/c14`, `runs_seed_conf_c14.log`), 2026-10-11

| area | start | carried | gain | pools start -> carried (tasks per world) |
| --- | --- | --- | --- | --- |
| mech | 1,269 | 1,878 | +48% | trained 23.5 -> 36.2, untrained 26.6 -> 29.5, unfamiliar 2.7 -> 12.5 |
| drawn7 | 230 | 334 | +45% | env 9.6 -> 13.9 |
| metric777001 | 389 | 1,667 | +329% | seen 11.6 -> 35.3, unfamiliar 4.6 -> 34.1 |
| drawn11 | 249 | 369 | +48% | env 10.4 -> 15.4 |
| drawn13 | 258 | 375 | +45% | env 10.8 -> 15.6 |
| metric555001 | 284 | 1,823 | +542% | seen 10.3 -> 50.8, unfamiliar 1.5 -> 25.2 |

Kept changes (8): five language extensions of 40 atoms (mech lives 0 and 3,
drawn7 life 0 with prune -31, drawn11 life 0 with prune -15, drawn13 life 0
with prune -15), two model refits (metric777001, metric555001), one prune
(drawn13 -10). Proof scans 2.32x live: the most language extensions of any
seed yet the lowest six-area cost, because four of the five passed in the
first life of their area, when few other areas had been lived and the
cross-area bill was one to four checks, and the rejected candidates stopped
on the half set.

- Gate 1: PASS, six of six areas, smallest +45%.
- Gate 2: PASS, all nine pools rose; the weakest (mech untrained, 26.6 ->
  29.5) to 111% of its start.
- Gate 3: PASS, 2.32x against 3.25x.
- Gate 4: PASS, 8 of 8 replay exactly, salts unique within area.

### Verdict on v7

All four gates pass on both sealed seeds. v7 PASSES. v7 is the confirmed
protocol for six areas; v4 remains the confirmed protocol for three.

Across the four six-area seeds (919110 to 919113; the first two under v6,
whose only difference from v7 is the cost threshold): 24 of 24 areas rose
by at least 23% on fresh held-out sets (median +80%, range +23% to +542%);
36 of 36 pools rose (the weakest to 111% of its start); 39 of 39
acceptances replay exactly; cost 2.78x, 2.64x, 2.88x, 2.32x (mean 2.65x)
against the scaled gate of 3.25x. The two metric areas gained most
(+249% to +542%); metric555001 did so on two seeds without keeping any
change in its own lives, from the language and models the other areas
built, which is the carried-forward transfer the programme set out to
show.

## Nineteen sealed seeds, summary

| version | seeds | areas | growth | safety | cost | audit |
| --- | --- | --- | --- | --- | --- | --- |
| v1 | 919100, 919101 | 3 | pass, pass | pass, pass | FAIL (6x) | pass (one stale baseline) |
| v2 | 919102, 919103 | 3 | pass, pass | pass, pass | pass, pass | FAIL (own-set clause, one seed) |
| v3 | 919104, 919105 | 3 | pass, pass | pass, pass | pass, pass | FAIL (stale cache, one proof per seed) |
| v4 | 919106, 919107 | 3 | pass, pass | pass, pass | pass, pass | pass, pass |
| v5 | 919108, 919109 | 3 | FAIL, pass | FAIL, pass | pass, FAIL | pass, pass |
| v6 | 919110, 919111 | 6 | pass, pass | pass, pass | FAIL, FAIL (2.5x gate) | pass, pass |
| v7 | 919112, 919113 | 6 | pass, pass | pass, pass | pass, pass (3.25x gate) | pass, pass |
| v8 | 919114, 919115 | 7, two forms | pass, pass | pass, pass | pass, pass (3.5x gate) | pass, pass |
| v9 | 919116, 919117 | 7, two forms | FAIL (drawn7 +8%), pass | pass, pass | pass, pass (3.5x gate) | pass, pass |
| v10 | 919118, 919119 | 7, two forms | pass, (rerun pending) | pass, - | pass (2.92x), - | pass, - |

171 acceptances across nineteen seeds; every one stands on replay. Growth of
at least 15% in every area on seventeen of nineteen seeds (the misses: 919108
under the retired v5 guard, 919116 under v9 in drawn7) and no pool below
90% on eighteen of nineteen (919108). Seed 919119 (v10) was interrupted by
the host at life 20 of 21 and awaits a clean rerun.


## Protocol v8 (FROZEN 2026-10-12, after the v7 pass)

A second task form. Every area so far shares one task form: a hidden
predicate over characters, found by scanning a catalog of candidate
predicates. v8 adds an area of a different form, string transformation
tasks over the published trapdoor DSL (2606.07856): a task is three visible
and six hidden input-output pairs of a hidden program, a program
concatenates up to three rows, a row is the substring between two positions
(with or without a case operation) or a constant, and the keys are the
positions (C-12 to C12; the start or end of the first, second or third
WORD, DIGITS, UPPER or LOWER match), the three case operations and six
constants: 58 keys, 9,400 rows. A world is 14 keys from three key families
and 100 tasks over programs on those keys alone, the mechanism area's
structure transposed; its pools are trained, untrained and unfamiliar
triples of families, with the UPPER and LOWER positions withheld from the
starting language (46 keys, 5,334 rows). The seed's scan window in this
form is the first `budget` rows of its catalog in the order its evidence,
prior and model give, as in the mechanism form; a task is solved by the
first program of rows inside the window that reproduces the visible
examples, and counted a hit if it reproduces the hidden ones. Invention
proposes keys the language lacks (positions to C16 and the fourth match,
the case operations, the constants) that, with what a stuck world earned,
complete programs for at least two of its unsolved tasks on their visible
examples. Nothing in the form reads a family label or a hidden program.

The seed's four operations are unchanged; `rsi/seed.py` dispatches the
worker by the form of the worlds, filters each form's keys out of the
other's catalog, and checks a shared-language change on the other lived
areas of the same form only (the other form's catalog is built from its own
keys and cannot change). The string form's starting vocabulary is part of
every new seed's initial language.

Development (seed 644101, `seeds/d_str2`, `runs_seed_d_str2*.log`): four
string lives kept a language extension of 15 keys (six survived the prune:
the withheld UPPER and LOWER positions, all six from the generator's own
universe), a model and a prior in life 0, held-out 2,827 -> 3,735; lives 1
to 3 kept only a prune, the area plateauing at about 81% of tasks. Fresh
check: str7 4,641 -> 5,965 (+29%; trained 75.0 -> 84.0, untrained 68.1 ->
82.4, unfamiliar 50.2 -> 82.2 per world); one mechanism life on the same
seed then kept a language extension and model, mech 1,232 -> 1,621 (+32%,
untrained 20.5 -> 19.8). The auditor replayed all three acceptances
exactly.

Schedule: mech 4, drawn7 3, metric777001 3, drawn11 2, drawn13 2,
metric555001 2, str7 3, mech 2 lives (21 lives, 96 worlds each); fresh
check over seven areas. Gates as v7 with k = 7: growth of at least 15% in
each of the seven areas, no pool below 90% of its start, proof scans at
most 2.5 + 0.25 x 4 = 3.5 times live scans, every kept change replaying
with a salt unique within its area.

Seeds: 919114 (replication O, `seeds/c15`) and 919115 (replication P,
`seeds/c16`), sealed and unopened at the time of writing.

Hashes:

```
cbfef54eebe9a1aab3213778eea2e3665107422214129a5fd1f0a795ebfd1c23  rsi/seed.py
15a2b0f65ccb52ee60aa423a43ec2c2caf80af9091c33a28de182e8915fb49a9  rsi/seed_areas.py
043225574c68e4b5115946fbcf1383492da030884fe4c3da938691e89b0221cc  rsi/seed_string.py
aefd9cc94f7dbf8f54eb311baae6245522bf212bdbca4b6ac63cb5f13cfa9c83  rsi/invention.py
e9c6a2b3ed10cd6bb33306ca5234c06b5a087c739fcf71c65aa97593a205f2a3  rsi/self_world_model.py
2bbb0f02a31e0fc4987ba0f77a3c7304d0a1a3fea2f9a8886d7fcd247e108988  seed_run.py
1623b2b09ccdffbcbb1d600f2a887bd97b918d19687f19de7b8ec55a64bb1894  seed_check.py
271cb85d5a83c83173fbb3d63d441d187fed1a3850ae58e85f0c8f88e5828420  audit_seed.py
6b140671e341b9e23dc80ebae9cad44103ed91343aaf64a8a9d090a2b1e960e6  confirm_seed.sh
```

Forecast, committed before opening 919114: gate 1 0.7 (the string area
passed 15% in one development life, but a three-life area whose growth
comes in life 0 has one real chance; the six-area record is twelve of
twelve), gate 2 0.65 (eleven pools now; the string area's untrained pool
rose on the development seed, mech's untrained dipped to 97%), gate 3 0.75
(cross-form checks are skipped, so the string area adds its own proofs
only), gate 4 0.9; all four on both seeds 0.3.

### Replication O, seed 919114 under v8 (`seeds/c15`, `runs_seed_conf_c15.log`), 2026-10-12

| area | start | carried | gain | pools start -> carried (tasks per world) |
| --- | --- | --- | --- | --- |
| mech | 1,185 | 2,300 | +94% | trained 23.9 -> 35.6, untrained 21.0 -> 40.3, unfamiliar 4.4 -> 20.0 |
| drawn7 | 166 | 460 | +177% | env 6.9 -> 19.2 |
| metric777001 | 344 | 1,422 | +313% | seen 8.5 -> 32.2, unfamiliar 5.8 -> 27.0 |
| drawn11 | 249 | 381 | +53% | env 10.4 -> 15.9 |
| drawn13 | 215 | 439 | +104% | env 9.0 -> 18.3 |
| metric555001 | 371 | 1,605 | +333% | seen 13.3 -> 43.5, unfamiliar 2.2 -> 23.4 |
| str7 | 4,749 | 6,026 | +27% | trained 65.6 -> 75.4, untrained 81.5 -> 95.2, unfamiliar 50.8 -> 80.5 |

Kept changes (13): five language extensions (mech lives 0 and 2, drawn13
life 0, each of 40 atoms; str7 life 0 of 14 keys with prune -7 and str7
life 2 of 2 keys with prune -8), five model refits (drawn7, metric777001,
drawn11, metric555001 lives 0 and 1), three prunes (drawn7 -28, drawn11 -4,
metric555001 -15). The eight string keys that survived are the six withheld
UPPER and LOWER positions (M(UPPER,1..3,end), M(LOWER,1..3,start)) and two
positions outside the generator's universe (C-13, C-14), the first novel
keys kept in the string form; unlike the development seed, the string area
kept a change after life 0. Proof scans 2.61x live, inside the six-area
range (2.32x to 2.88x): the string area's proofs are charged like any
other's, and no cross-form check is made, so the seventh area added no
cost beyond its own.

- Gate 1: PASS, seven of seven areas, smallest +27% (str7).
- Gate 2: PASS, all eleven pools rose; the weakest (str7 trained, 65.6 ->
  75.4) to 115% of its start.
- Gate 3: PASS, 2.61x against 3.5x.
- Gate 4: PASS, 13 of 13 replay exactly, salts unique within area.

All four gates pass on 919114. 919115 (replication P) opened next.

### Replication P, seed 919115 under v8 (`seeds/c16`, `runs_seed_conf_c16.log`), 2026-10-12

| area | start | carried | gain | pools start -> carried (tasks per world) |
| --- | --- | --- | --- | --- |
| mech | 1,174 | 1,885 | +61% | trained 21.1 -> 33.5, untrained 23.0 -> 29.1, unfamiliar 4.8 -> 15.9 |
| drawn7 | 320 | 413 | +29% | env 13.3 -> 17.2 |
| metric777001 | 309 | 1,409 | +356% | seen 8.9 -> 33.6, unfamiliar 4.0 -> 25.1 |
| drawn11 | 251 | 386 | +54% | env 10.5 -> 16.1 |
| drawn13 | 322 | 430 | +34% | env 13.4 -> 17.9 |
| metric555001 | 300 | 1,321 | +340% | seen 10.2 -> 39.0, unfamiliar 2.3 -> 16.0 |
| str7 | 4,119 | 5,419 | +32% | trained 61.8 -> 77.3, untrained 54.4 -> 68.1, unfamiliar 55.4 -> 80.4 |

Kept changes (11): four language extensions (mech lives 0 and 2 of 40
atoms, the second with prune -16; drawn7 life 0 of 40 atoms with prune
-38; str7 life 0 of 12 keys with prune -2), six model refits (metric777001
lives 0 and 1, drawn11, drawn13, metric555001, str7 life 2 with prune -6),
one prune (drawn13 -10). The six string keys that survived are exactly the
six withheld UPPER and LOWER positions, the same six as on 919114, and no
novel key. Proof scans 2.71x live.

- Gate 1: PASS, seven of seven areas, smallest +29% (drawn7).
- Gate 2: PASS, all eleven pools rose; the weakest (str7 trained 61.8 ->
  77.3 and untrained 54.4 -> 68.1) to 125% of their start.
- Gate 3: PASS, 2.71x against 3.5x.
- Gate 4: PASS, 11 of 11 replay exactly, salts unique within area.

### Verdict on v8

All four gates pass on both sealed seeds. v8 PASSES. v8 is the confirmed
protocol for seven areas in two task forms; v7 remains the confirmed
protocol for six areas and v4 for three.

Across the two seven-area seeds (919114, 919115): 14 of 14 areas rose by
at least 27% on fresh held-out sets (median +78%, range +27% to +356%);
22 of 22 pools rose (the weakest to 115% of its start); 24 of 24
acceptances replay exactly; cost 2.61x and 2.71x against the gate of
3.5x, inside the range of the four six-area seeds, because a form whose
catalog is disjoint adds its own proofs and no cross-form check. The
string area rose +27% and +32%, and both seeds kept the same six withheld
positions (M(UPPER,1..3,end), M(LOWER,1..3,start)), proposed by invention
from what stuck worlds had earned and accepted on held-out tasks, with no
family label read; 919114 also kept two positions outside the generator's
universe. The committed forecast gave this outcome 0.3.

Across the six seeds of six or more areas (919110 to 919115): 38 of 38
area scores rose, 58 of 58 pools rose, 63 of 63 acceptances replay.


## Protocol v9 (FROZEN 2026-10-12, after the v8 pass)

One change from v8, in the string worker's consistency filter; nothing in
the schedule, the gates or the other areas' code. Diagnosis on the
development seed (`diag_string.py`, 24 fresh worlds, 2,400 tasks): under
v8's worker 1,901 tasks hit, 126 fit the visible pairs and not the hidden
ones, and 373 were unsolved, of which 283 had no program over the full
58-key catalog at any budget. The cause was the worker's own filter: a row
was compatible only if its output was non-empty on every visible input,
and a prefix row had to leave something to complete on every input,
whereas the generator's rows are the substring between two positions that
may coincide on some inputs. The filter now admits a row that is empty on
some visible inputs (not all) and a prefix row that completes the target
on some inputs. Same state, same worlds: 2,015 hit, 163 wrong, 222
unsolved (16 with no program anywhere, 206 with one in the carried
language outside the window). The invention test uses the same two
functions and inherits the change.

Development (seed 644101, `seeds/d_str3`, `runs_seed_d_str3.log`): three
string lives under the fixed worker. Life 0 kept a language extension of
17 keys (all twelve withheld UPPER and LOWER positions, and five positions
outside the generator's universe, C-16 to C-13 and C13) with a model and
prior, held-out 2,949 -> 3,906; lives 1 and 2 kept nothing (refits within
noise; a prune of 11 at an interval whose lower bound was exactly 0).
Fresh check: str7 4,712 -> 6,230 (+32%; trained 78.2 -> 88.9, untrained
66.7 -> 85.3, unfamiliar 51.4 -> 85.4 per world). Audit 1 of 1. Cost 1.25x
over the three lives.

Schedule, gates and seeds as v8: mech 4, drawn7 3, metric777001 3, drawn11
2, drawn13 2, metric555001 2, str7 3, mech 2 lives (21 lives, 96 worlds
each); growth of at least 15% in each of the seven areas, no pool below
90% of its start, proof scans at most 3.5 times live scans, every kept
change replaying with a salt unique within its area. Seeds: 919116
(replication Q, `seeds/c17`) and 919117 (replication R, `seeds/c18`),
sealed and unopened at the time of writing.

Hashes (only `rsi/seed_string.py` differs from v8):

```
cbfef54eebe9a1aab3213778eea2e3665107422214129a5fd1f0a795ebfd1c23  rsi/seed.py
15a2b0f65ccb52ee60aa423a43ec2c2caf80af9091c33a28de182e8915fb49a9  rsi/seed_areas.py
3055e82052dec8aaf0ebee0f9d91438c1ce018ef2bf84be877c2fa9f2cb83213  rsi/seed_string.py
aefd9cc94f7dbf8f54eb311baae6245522bf212bdbca4b6ac63cb5f13cfa9c83  rsi/invention.py
e9c6a2b3ed10cd6bb33306ca5234c06b5a087c739fcf71c65aa97593a205f2a3  rsi/self_world_model.py
2bbb0f02a31e0fc4987ba0f77a3c7304d0a1a3fea2f9a8886d7fcd247e108988  seed_run.py
1623b2b09ccdffbcbb1d600f2a887bd97b918d19687f19de7b8ec55a64bb1894  seed_check.py
271cb85d5a83c83173fbb3d63d441d187fed1a3850ae58e85f0c8f88e5828420  audit_seed.py
6b140671e341b9e23dc80ebae9cad44103ed91343aaf64a8a9d090a2b1e960e6  confirm_seed.sh
```

Forecast, committed before opening 919116: gate 1 0.7 (the string area now
starts higher, 65 to 78 tasks per world, and must still gain 15%; the
development run gained 32% in one life; the six other areas are untouched
and passed fourteen of fourteen under v8), gate 2 0.65 (every string pool
rose on the development seed and on both v8 seeds), gate 3 0.8 (2.61x and
2.71x under v8; the string area's proofs are unchanged in number), gate 4
0.9; all four on both seeds 0.35.

### Replication Q, seed 919116 under v9 (`seeds/c17`, `runs_seed_conf_c17.log`), 2026-10-12

| area | start | carried | gain | pools start -> carried (tasks per world) |
| --- | --- | --- | --- | --- |
| mech | 1,072 | 2,088 | +95% | trained 21.8 -> 37.3, untrained 18.1 -> 34.2, unfamiliar 4.7 -> 15.5 |
| drawn7 | 258 | 279 | +8% | env 10.8 -> 11.6 |
| metric777001 | 259 | 1,715 | +562% | seen 8.2 -> 41.8, unfamiliar 2.6 -> 29.7 |
| drawn11 | 220 | 377 | +71% | env 9.2 -> 15.7 |
| drawn13 | 224 | 384 | +71% | env 9.3 -> 16.0 |
| metric555001 | 339 | 1,485 | +338% | seen 11.0 -> 41.0, unfamiliar 3.2 -> 20.8 |
| str7 | 5,076 | 6,248 | +23% | trained 79.1 -> 85.2, untrained 79.6 -> 90.4, unfamiliar 52.8 -> 84.8 |

Kept changes (14): seven language extensions (mech lives 0, 1 and 2 of 40
atoms, the third with prune -33; drawn7 life 0 of 40 with prune -37;
metric777001 life 0 of 40 with prune -30; drawn11 life 1 of 40 with prune
-18; str7 life 0 of 19 keys with prune -2), five model refits
(metric777001 life 2, drawn11 life 0, drawn13 life 0, metric555001 lives 0
and 1), two prunes (metric777001 -24, drawn13 -25). String keys kept:
eleven of the twelve withheld UPPER and LOWER positions (all but
M(UPPER,1,start)) and eight positions outside the generator's universe
(C-16 to C-13, C13 to C16). Proof scans 2.33x live.

- Gate 1: FAIL, drawn7 +8%; the six other areas +23% (str7) to +562%.
- Gate 2: PASS, all eleven pools rose; the weakest (drawn7) to 108%.
- Gate 3: PASS, 2.33x against 3.5x.
- Gate 4: PASS, 14 of 14 replay exactly, salts unique within area.

Where drawn7 stood, by version (`replay_versions.py c17 drawn7`: the fresh
24-world set scored by the state after each kept change): start 258;
after drawn7's own change (v4) 283; after metric777001's extension (v5)
271; after its prune and refit (v6, v7) 275; after drawn11's extension
(v9) 259; after drawn13's prune (v11) 283; after metric555001's refit
(v13) 283; after str7's extension (v14) 279. The accepted drawn7 change
gained 207 on its 48-world proof set (599 -> 806, interval 1.2 to 7.5 per
world) and 25 on the fresh set (1.0 per world, below its interval); later
shared-language changes moved the score by at most -24, and the final
state stands at 99% of the area's peak on this set. Not cumulative drift:
one accepted change whose proof gain did not generalise, after which
lives 1 and 2 rejected five candidates with gains of 50 to 74 tasks on 48
worlds (+7% to +10%) whose intervals straddled zero.

### Replication R, seed 919117 under v9 (`seeds/c18`, `runs_seed_conf_c18.log`), 2026-10-12

| area | start | carried | gain | pools start -> carried (tasks per world) |
| --- | --- | --- | --- | --- |
| mech | 1,217 | 2,416 | +99% | trained 24.5 -> 41.4, untrained 22.6 -> 36.7, unfamiliar 3.6 -> 22.5 |
| drawn7 | 241 | 432 | +79% | env 10.0 -> 18.0 |
| metric777001 | 326 | 1,584 | +386% | seen 10.2 -> 38.9, unfamiliar 3.4 -> 27.1 |
| drawn11 | 275 | 416 | +51% | env 11.5 -> 17.3 |
| drawn13 | 305 | 442 | +45% | env 12.7 -> 18.4 |
| metric555001 | 384 | 1,716 | +347% | seen 12.5 -> 48.8, unfamiliar 3.5 -> 22.8 |
| str7 | 4,910 | 6,127 | +25% | trained 68.2 -> 82.5, untrained 81.5 -> 89.0, unfamiliar 54.8 -> 83.8 |

Kept changes (11): six language extensions (mech lives 0 and 2 of 40
atoms, the second with prune -21; drawn7 life 0 of 40 with prune -21;
metric777001 life 0 of 31 with prune -21; metric555001 life 0 of 40 with
prune -11; str7 life 0 of 17 keys with prune -30), five model refits
(metric777001 life 1, drawn11 life 0, drawn13 life 0, metric555001 life 1,
mech life 4). String keys kept: eleven of the twelve withheld positions
(all but M(UPPER,1,start)) and six outside the generator's universe (C13
to C16, M(WORD,4,start), M(LOWER,4,start)). Proof scans 2.27x live.

- Gate 1: PASS, seven of seven areas, smallest +25% (str7).
- Gate 2: PASS, all eleven pools rose; the weakest (str7 untrained, 81.5
  -> 89.0) to 109% of its start.
- Gate 3: PASS, 2.27x against 3.5x.
- Gate 4: PASS, 11 of 11 replay exactly, salts unique within area.

### Verdict on v9

One seed fails the growth gate, in drawn7, an area v9's change does not
touch; the other passes all four. v9 FAILS as a protocol; v8 remains the
confirmed protocol for seven areas. The change itself held: under the
fixed worker the string area starts higher (5,076 and 4,910 against 4,749
and 4,119 under v8) and still rose 23% and 25%, and each seed invented
eleven of the twelve withheld positions where the v8 seeds found six.

The miss is at the noise floor of the gate, not a regression: drawn7 had
risen on all eighteen seeds before (by 29% to 177%), on this seed its one
accepted change generalised to +10% rather than its proof's +35%, and the
candidates that followed, at +7% to +10% on 48 worlds, were rejected on
intervals that straddled zero. The seed's acceptance test has the power to
detect a 15% effect in a single-pool area only barely at 48 worlds: that
is the next thing to change in the seed, to be developed on 644101 first.


## Protocol v10 (FROZEN 2026-10-12, after the v9 verdict)

One change from v9, in the seed's prove operation; nothing in the
schedule, the gates or the areas. A candidate whose gain on the full
held-out set has a bootstrap interval straddling zero, with a positive
mean large enough that a doubled set would clear zero if the gain held
(lower bound above mean x (1 - sqrt 2)), is run once more on an extension
set of the same size drawn with its own salt (the proof's salt plus 500),
the carried state is scored on that set too, and the decision is the
interval over the union of the two sets. Every other candidate is judged
as before. The ledger records the extension (salt, both scores, the union
interval) and the auditor replays both sets and recomputes the union
interval. Motivation: on 919116 drawn7's lives 1 and 2 rejected five
candidates at +7% to +10% on 48 worlds whose intervals straddled zero. On
the four seven-area seeds the rule would have re-tested three to five
candidates per run, each extension costing about one life of scans, so
0.15 to 0.25 on the cost ratio.

Development (seed 644101, `seeds/d_ext`, `runs_seed_d_ext.log`; drawn7 3,
metric777001 2, mech 2 lives, not the confirmation schedule): four
extensions, all in drawn7 lives 1 and 2; three rejected on the union
(extension-set gains +29, +9 and -6 against proof-set gains +59, +26 and
+38) and one accepted (life 2, language +40 with prune -13 and a refit:
+57 on the proof set, interval -0.12 to 2.60; +27 on the extension set;
union interval 0.05 to 1.74). On the fresh 24-world set that acceptance
was neutral (275 -> 271; `replay_versions.py d_ext drawn7`), the area's
growth there coming from life 0 (211 -> 275) and from later changes in
other areas (314 at the end, +49%). Fresh check: drawn7 211 -> 314 (+49%),
metric777001 270 -> 1,833 (+579%), mech 1,232 -> 1,669 (+35%) with mech's
untrained pool at 82% of its start (20.5 -> 16.8): mech was lived last
here, after three shared-language extensions by other areas with no lived
mechanism area to check them on; the confirmation schedule lives mech
first. Audit 6 of 6, the extended acceptance replaying exactly. Cost 2.46x
over seven lives.

Schedule, gates and seeds as v8 and v9. Seeds: 919118 (replication S,
`seeds/c19`) and 919119 (replication T, `seeds/c20`), sealed and unopened
at the time of writing.

Hashes (`rsi/seed.py` and `audit_seed.py` differ from v9):

```
8e169908bf1c527aac0c5178ac618053bf795f92909e4c2a01eca2e777f6e7de  rsi/seed.py
15a2b0f65ccb52ee60aa423a43ec2c2caf80af9091c33a28de182e8915fb49a9  rsi/seed_areas.py
3055e82052dec8aaf0ebee0f9d91438c1ce018ef2bf84be877c2fa9f2cb83213  rsi/seed_string.py
aefd9cc94f7dbf8f54eb311baae6245522bf212bdbca4b6ac63cb5f13cfa9c83  rsi/invention.py
e9c6a2b3ed10cd6bb33306ca5234c06b5a087c739fcf71c65aa97593a205f2a3  rsi/self_world_model.py
2bbb0f02a31e0fc4987ba0f77a3c7304d0a1a3fea2f9a8886d7fcd247e108988  seed_run.py
1623b2b09ccdffbcbb1d600f2a887bd97b918d19687f19de7b8ec55a64bb1894  seed_check.py
5874a3b678eaec3c07ad68fe72a541947633e39fe6d7363fc860c7c8d80b89d3  audit_seed.py
6b140671e341b9e23dc80ebae9cad44103ed91343aaf64a8a9d090a2b1e960e6  confirm_seed.sh
```

Forecast, committed before opening 919118: gate 1 0.75 (the rule adds
power where v9 failed; six of seven areas passed on both v9 seeds), gate
2 0.6 (more shared-language acceptances mean more drift on the other
areas, each still checked at 2% on 24 worlds; the untrained pool is the
historical weak point), gate 3 0.8 (2.33x and 2.27x under v9, plus 0.15
to 0.25), gate 4 0.85 (a new replay path, exercised once in development);
all four on both seeds 0.3.

### Replication S, seed 919118 under v10 (`seeds/c19`, `runs_seed_conf_c19.log`), 2026-10-12

| area | start | carried | gain | pools start -> carried (tasks per world) |
| --- | --- | --- | --- | --- |
| mech | 1,159 | 2,484 | +114% | trained 20.5 -> 41.1, untrained 23.2 -> 46.6, unfamiliar 4.6 -> 15.8 |
| drawn7 | 273 | 349 | +28% | env 11.4 -> 14.5 |
| metric777001 | 450 | 2,283 | +407% | seen 13.5 -> 56.5, unfamiliar 5.2 -> 38.6 |
| drawn11 | 241 | 439 | +82% | env 10.0 -> 18.3 |
| drawn13 | 286 | 379 | +33% | env 11.9 -> 15.8 |
| metric555001 | 378 | 1,329 | +252% | seen 12.9 -> 36.2, unfamiliar 2.8 -> 19.2 |
| str7 | 4,722 | 6,193 | +31% | trained 70.3 -> 83.6, untrained 77.0 -> 89.6, unfamiliar 49.4 -> 84.8 |

Kept changes (15): five language extensions (mech lives 0 and 2 of 40
atoms, the second with prune -11; metric777001 lives 1 and 2 of 40 with
prunes -12 and -8; str7 life 0 of 18 keys with prune -1), nine model
refits (drawn7, metric777001 life 0, drawn11, drawn13, metric555001 lives
0 and 1, str7 life 2 with prune -12, mech lives 4 and 5), one prune
(drawn13 -31). Extensions, three: metric777001 life 0, a candidate at +67
on the proof set and +28 on the extension set, union interval -0.17 to
2.22, rejected; metric777001 life 2, language +40 with prune -8 and a
refit, +132 and +115, union 0.77 to 4.41, kept (version 6); str7 life 2,
prune -12 with a refit, +59 and +80, union 0.20 to 2.84, kept (version
13). Both accepted extensions were confirmed by their extension set at a
similar gain. String keys kept: six withheld positions, no novel key.
Proof scans 2.92x live (2.33x and 2.27x under v9).

- Gate 1: PASS, seven of seven areas, smallest +28% (drawn7).
- Gate 2: PASS, all eleven pools rose; the weakest (str7 untrained, 77.0
  -> 89.6) to 116% of its start.
- Gate 3: PASS, 2.92x against 3.5x.
- Gate 4: PASS, 15 of 15 replay exactly, the two extended acceptances
  included; salts unique within area.

All four gates pass on 919118. 919119 (replication T) opened next.

### Note: the mechanism area's untrained pool across the nineteen sealed seeds (2026-10-12)

The pool the development runs flagged as the weak point (untrained family
combinations, which the shared language can dilute) rose on seventeen of
nineteen sealed seeds, to a median 163% of its start; the two dips, 94% on
919103 (v2) and 89% on 919108 (v5, the retired guard), are both under
early versions. Its ratio shows no relation to the number of
shared-language changes other areas kept (one to four per seed; 919116
kept four and the pool rose to 189%), and the extension rule's first seed
(919118, three extensions) ended at 201%. The 82% seen on the development
seed `d_ext` came with the mechanism area lived last, after three
extensions by other areas with no lived mechanism area to check them on;
the confirmation schedule lives it first. No cumulative-drift guard is
needed on this evidence; the per-candidate 2% check on 24 worlds has held
in the schedule as run.

### Development: the eighth area, str11 (`seeds/d_str11`, `runs_seed_d_str11.log`, 2026-10-12)

str11 is StringArea with env_seed 11: the same 58 keys and catalog as str7
and a different random split of the seven key families into trained,
untrained and unfamiliar triples. No new code. Three lives of 48 worlds on
644101 (held-out 48): life 0 kept a language extension of 13 keys with a
model and prior (held-out 3,252 -> 3,936, +10.9 to +17.7 per world); life 1
kept nothing (model -3.1 to +1.2); life 2 kept a prune of 7 keys (+0.0 to
+0.6) and a refit model (+0.4 to +3.6). Fresh check (24 worlds per pool,
salt 999): 4,604 -> 6,277 (+36%); trained 67.9 -> 84.7, unfamiliar 49.1 ->
83.8, untrained 74.8 -> 93.0 per world. Six invented keys survive, all in
the generator's universe and the same six the v8 seeds found on str7:
M(UPPER,1..3,end) and M(LOWER,1..3,start). Audit 3 of 3. Proof scans
2.67x live over three lives.

Draft v11, NOT frozen until the v10 verdict: the v10 schedule plus three
str11 lives after str7 (24 lives, eight areas, two forms), cost gate 2.5 +
0.25 x 5 = 3.75x; the string form's cross-area check then has a second
lived area to fire on (str7 and str11 check each other at 2% on 24 worlds).

Two str7 lives on the same state (`runs_seed_d_str11_str7.log`), the first
time two lived areas of the string form check each other. str7 life 0 kept
a language extension of 16 keys with a prune of 1, a model and a prior
(held-out 3,162 -> 3,972, +12.1 to +22.0 per world); the cross-area check
scored that candidate on str11's 24-world set at 3,096 -> 3,066 (-1.0%,
inside the 2% tolerance). Life 1 kept nothing (three candidates at -1.4 to
+0.6). Fresh check of both areas: str7 4,712 -> 6,154 (+31%; trained 78.2
-> 89.1, unfamiliar 51.4 -> 82.7, untrained 66.7 -> 84.7); str11 4,604 ->
6,158 (+34%; 6,277 before the str7 lives, so the str7 change cost it 1.9%
on the fresh set, the direction and size the check read). 21 invented
keys kept: eleven of the twelve withheld positions (all but
M(UPPER,1,end), which the str7 prune removed) and ten outside the
generator's universe (C-16 to C-13, C13 to C16, M(WORD,4,start),
M(LOWER,4,start)). Audit 4 of 4. Proof scans 2.90x live over five lives.
The check works inside the string form as it does in the character form;
its tolerance is per candidate, as before.

### Note: how often the extension rule fires, from the sealed ledgers (2026-10-12)

`extension_triggers.py` reads a seed's ledger and counts the full-set
rejections that v10's rule would send to an extension set (interval
straddling zero, positive mean, lower bound above mean x (1 - sqrt 2)),
with an upper bound on the cost (carried and candidate both scored on one
extension set). On c19, the one seed that ran v10, it counts zero such
rejections left behind, as it must; the three that qualified were extended
(one rejected, two accepted). On c1 to c18, 77 of 407 full-set rejections
(19%) would have been extended, most in metric777001, mech and drawn7; a
further 80 (20%) had intervals above zero and were rejected by the
cross-area check. The cost bound is +0.33x live on average (max +0.92x, on
c2 under v1's economics); on the seven-area seeds c15 to c18 it is +0.15x
to +0.24x, so a v11 run should land near 2.6x to 3.2x against its 3.75x
gate. Forecast for v11 when it is frozen: 0.35.

## The improver as state: level 1 (producer policy) and level 2 (meta-proof), development (2026-10-12)

Reese's direction: true recursive self-improvement, the seed improving its
improver and its producer, not only its state. What is built, on top of the
unchanged level-0 acceptance test:

Level 1, the producer policy (`Seed.fallback_policy`): which parts the
producer tests on their own after the combined candidate fails is no longer
fixed. It is a pure function of the seed's own ledger: a fallback with
`patience` rejections in a form and no acceptance since is retired, tried
again once every `probation` lives of the form, and an extension retired on
its own gives way to the extension with the model (the menu: model, prune,
extend, extend+model). Motivation from the nine multi-area sealed ledgers
(c11 to c19): an extension tested alone was kept 0 times in 129 and cost 13%
of all proof scans; model alone 47 of 134; prune alone 13 of 105; the
combination 43 of 174 (57% of proof cost). Each life's policy is recorded as
a `revise` ledger entry; the auditor recomputes every one from the ledger
before it.

Level 2, the meta-proof (`seed_run.py --meta-every N`, `Seed.mutation`,
`Seed.branch`, `Seed.meta_proof`, `Seed.adopt`): the knobs of the producer
and of the level-1 rule live in `state['procedure']` (patience 4, probation
4, extend_cap 40, recurrence 2). Every Nth life the meta-producer proposes
one mutation (round-robin over the knobs, each to the next value of its
cycle: patience and probation 2/4/8, extend_cap 20/40/80, recurrence 2/3).
Two branches of the seed run the proposal-and-proof phase from the same
lived worlds, one under the current procedure and one under the mutation,
and both final states are scored on a meta set no proof used (salt 5000 +
100 x area + life, --held-out worlds), paired over worlds. The mutation is
adopted if its branch's gain has an interval above zero, or if the interval
straddles zero with a non-negative mean and the branch's proof cost is at
least 10% lower. The branch not taken and the meta set are charged to proof
scans. The auditor replays every meta-proof from the winner's version
snapshot and the loser's filed snapshot. Level 2 changing level 1's knobs
is the recursion; the fixed substrate is the comparison harness itself and
its schedule.

Development `d_meta` (644101, str7, meta every life; `runs_seed_d_meta.log`;
stopped by the host for low memory in life 5 of 6, not restarted): the
machinery ran end to end for five lives. Every mutation was declined,
correctly: patience 8, probation 8, extend_cap 80, recurrence 3 and patience
8 again each left that life's proposals and fallbacks unchanged, so both
branches made the same decisions, the meta set read +0.0 on every world and
the costs were equal. In life 5 level 1 fired for the first time: the model
fallback, rejected four times in the string form, was retired and the phase
tested prune and extend only. Two lessons went straight into the code: (1) a
mutation whose branch would propose and test exactly what the current
procedure proposes this life is detected by comparing the two plans
(proposed atoms, drops, model and active fallbacks) before any proof, and is
recorded as a no-op rather than run, which removes most of the meta-level's
cost (with every mutation run, proof scans were 8x living on this seed);
(2) the one-life horizon can only see knobs that change the current life,
so second-order knobs such as patience show an effect only on the life in
which a retirement threshold is crossed; longer branch horizons are the
next step and cost lives. Audit and fresh check pending (memory).

Development `d_meta2` (644101, mech 6 lives then drawn7 2, meta every life,
no-op detection on; `runs_seed_d_meta2.log`, `runs_seed_d_meta2_check.log`):
fresh check mech 1,232 -> 2,030 (+65%; trained 25.6 -> 45.0, untrained 20.5
-> 24.6, unfamiliar 5.2 -> 15.0), drawn7 211 -> 334 (+58%); 43 invented
atoms kept (13 xormod, 5 popcount, 25 novel). Audit: 6 of 6 proofs, 4 of 4
meta-proofs, every policy revision. Level 1 fired in the character form:
`extend` alone was retired after its fourth rejection (mech life 5) and
both drawn7 lives tested `extend+model` in its place (rejected, -1.9 to
+1.1 and -5.0 to +1.5 per world). Level 2: of eight mutations, four were
no-ops (patience 8, probation 8, twice each: no retirement threshold was
crossed) and four ran as branch pairs, all declined by the rule: extend_cap
80 at mech life 2 ended in the identical state at equal cost; recurrence 3
at mech life 3 kept a slightly different extension, meta set 1,118 -> 1,157,
interval -0.1 to +1.8 (not above zero, equal cost); extend_cap 80 at drawn7
life 0 kept the combination its branch had proved (+0.0 to +5.9) but read
616 -> 582 on the meta set, mean negative, so cheaper did not count;
recurrence 3 at drawn7 life 1 ended identical and dearer. Cost: proof
scans 8.75x living with a meta-test every life (a branch pair doubles a
phase; v10's protocol runs at 2.3 to 2.9x). Conclusions: the harness and
its audit work in both forms; the rule declined correctly every time; no
mutation of these four knobs showed a benefit within one life. Second-order
knobs (patience, probation) act over lives, not within one, so the next
increment is a branch horizon of several lives, and the meta-test must be
rationed (every few lives) or chosen by evidence.

Development `d_meta3` (644101, str7 9 lives, `--meta-every 3 --meta-lives 3`:
every third life a branch pair runs three lives each on the same world
draws before the meta set scores them; `runs_seed_d_meta3.log`,
`runs_seed_d_meta3_check.log`). The seed's mutations now alternate through
a knob's other values. Life 2, extend_cap 40 -> 20: identical final states
(4,147 = 4,147), equal cost, declined. Life 5, probation 4 -> 2: identical
states, the mutated branch dearer (31.9M against 29.5M proof scans, the
retired model fallback re-tried more often), declined. Life 8, patience
4 -> 2: identical states (4,259 = 4,259) and the mutated branch 15%
cheaper (27.0M against 31.9M): under patience 2 the branch retired the
model and extension fallbacks sooner and tested fewer parts that were
going to be rejected. ADOPTED by the cheaper rule; the seed's procedure
now reads patience 2. This is the first change the seed has made to the
rule that revises its own producer, proven on a three-life horizon, and
the auditor replays it (meta 3 of 3, proofs 3 of 3, every revision).
Fresh check: str7 4,712 -> 6,233 (+32%; trained 78.2 -> 89.4, untrained
66.7 -> 84.8, unfamiliar 51.4 -> 85.5), the same six withheld positions
invented. Cost 5.5x living over eleven lives: a three-life branch pair
every third life doubles those lives' proofs and charges the loser's
living. The procedure is one object shared by both forms, so a knob
adopted on string evidence governs the character form too; whether that
is right is open.

Where this leaves true RSI: level 0 (state) proven by held-out tests;
level 1 (producer policy) revised automatically from the ledger; level 2
(the knobs of the producer and of level 1) mutated by the seed and adopted
only on a shadow-branch comparison; the comparison harness, its schedule
(--meta-every, --meta-lives) and the adoption rule (better, or no worse at
10% less cost) are fixed code. Next: ration or evidence-drive the
meta-tests so a sealed schedule stays near the cost gate, decide per-form
versus shared procedures, then a frozen version with the meta-level on.

Per-form procedures and a meta budget (2026-10-12). The procedure is now
one set of knobs per form (`state['procedure']['character' | 'string']`;
older seeds migrate by copying their single procedure to both), since the
sealed ledgers show the forms differ in what pays (model alone kept 35% of
the time in the character form, 0 of 7 in strings). `--meta-budget F`
rations the meta-level: a mutation is tested only while the scans charged
to testing the procedure (the branch not taken plus the meta sets, now
recorded per meta entry as `charged`) are below F of all proof scans.

Development `d_meta4` (644101, str7 6 lives then mech, `--meta-lives 2
--meta-budget 0.25`, meta every third string life and every second
character life; `runs_seed_d_meta4.log`; stopped by the host for low
memory in mech life 4, not restarted). Strings: one meta-test at life 2
(extend_cap 40 -> 20, identical states, equal cost, declined; 51.6M
charged), after which the budget gate held every later test back, through
mech life 3 (the gate reads charged 51.6M against 0.25 x proof scans, 31M
to 47M). Growth continued under the gate: mech held-out 753 -> 1,004 (life
0), then a prune and a model kept; the string model fallback was retired at
life 5 by level 1. Audit and fresh check pending.

Evidence-driven mutations (2026-10-12, code only, no run yet: memory). The
meta-producer no longer cycles its knobs blindly, which made most tests
no-ops. It reads votes from the form's ledger since each knob was last
tested: patience down for every fallback tested past its second straight
rejection and rejected again, up for one kept after that; probation down
for a retired fallback kept on its re-try, up for one rejected; recurrence
up for every extension rejected on its own, down for every life that could
propose none; extend_cap up for a kept extension that filled the cap. The
knob with the most votes moves one step that way; with no votes, the old
round-robin. The votes are recorded in each meta entry. On the development
ledgers it proposes patience 2 for d_meta4's string form (three wasted
fallback proofs against two extensions rejected on their own) and for
d_meta2's character form (two wasted fallback proofs), the change d_meta3
adopted on strings, and recurrence 3 for d_meta3's string form (five
extensions rejected on their own).

Development `d_meta5` (644101, str7 9 lives, evidence-driven mutations,
`--meta-every 3 --meta-lives 2 --meta-budget 0.5`; `runs_seed_d_meta5.log`,
`runs_seed_d_meta5_check.log`). Life 2: the only vote (recurrence down, from
lives that proposed no extension) had nowhere to go from 2, so round-robin
gave extend_cap 20: identical states, equal cost, declined. Life 5: votes
patience -2, so patience 2 over two lives: identical states (4,036 =
4,036) but the mutated branch dearer (22.1M against 19.7M: it retired
extend earlier and tested extend+model in its place, and re-tried the
retired model on probation), declined. Life 8: votes recurrence +3, so
recurrence 3: identical states, equal cost, declined. Fresh check str7
4,712 -> 6,233 (+32%), the same six withheld positions; cost 5.1x; audit 3
of 3 proofs, 3 of 3 meta-proofs, every revision. The producer chose what
its ledger said each time. Note the conflict with `d_meta3`, where
patience 2 was adopted on a three-life horizon as 15% cheaper: on a
two-life horizon at a different life it read 12% dearer. The cheaper rule
is sensitive to which proofs happen to fall inside the horizon, so the
meta-test's power at these horizons is low; pooling repeated tests of the
same mutation, or lengthening the horizon when votes are strong, is the
next improvement to the improver's improver.

