# Seed confirmation protocol (draft, not yet frozen)

Drafted 2026-10-11 after the development runs of `rsi/seed.py` (seeds s1, s2,
s3; `paper/seed-growth.pdf`). To be frozen with the SHA-256 of `rsi/seed.py`,
`rsi/seed_areas.py`, `rsi/invention.py`, `rsi/self_world_model.py`,
`seed_run.py`, `seed_check.py` and `audit_seed.py` before any confirmation
seed is opened. Nothing below has been run.

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
  per pool, cross-area 12 per pool, tolerance 2%, workers as the machine
  allows (workers never change results: the tie-break and every world seed
  are functions of the confirmation seed).
- Everything the seed reads is label-free (`rsi/seed.py`, docstring). Labels
  score only.

## Endpoints

Fresh held-out sets of each area with salt 7777, 24 worlds per pool, never
used by any proof. For each area: start = initial language, no model, no
prior; carried = the final state.

## Gates, both replications

1. Growth: carried total exceeds start total by at least 15% in every area
   (mech, drawn7, metric777001).
2. Safety: on no pool of any area is carried below 90% of start.
3. Economy: proof scans do not exceed 2.5 times live scans.
4. Provenance: every kept change's proof recomputes (audit) and every kept
   change's held-out salt is unique within its area.

Gate 2 is the one the development runs would fail today: s1's mech untrained
pool fell 24 -> 18 per world (version 24). The label-free guard being built
for that must be in place before freezing; if it is not, the protocol is
frozen as is and the failure is reported.

## Forecast (to be committed before the run)

Per gate and replication, an interval for each endpoint, scored by a proper
rule afterwards. Not yet written.

## Audit

`audit_seed.py` (to be written): rebuild each area from the state's specs,
recompute the carried and candidate scores of every kept change from the
ledger's salts and the state versions reconstructed by replaying the ledger,
and check equality; recompute the resource totals from the ledger.

## What a pass would and would not establish

A pass: one artifact grows across three areas of different structure on
sealed seeds, keeping only proven changes, without harming any pool, at a
stated cost. It would not establish recursive growth in the programme's sense
(the operations are fixed), transfer to a second task form or domain, or
growth past the schedule's length.
