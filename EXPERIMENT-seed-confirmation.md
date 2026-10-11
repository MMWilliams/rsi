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
