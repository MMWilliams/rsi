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
