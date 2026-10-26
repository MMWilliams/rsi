# Response plan: review 002 of "A Seed That Grows by Proving Its Own Changes"

Review text: `C:\Users\reese\Downloads\seed_growth_review002.txt` (2026-10-26). It
read the version with 89 sealed pairs and one completed seed of the final
protocol; the current paper has v11.1 on two seeds.

## R2. The final protocol on 5 to 10 seeds (no new code)

v11.1 on 919127-919134 (`c24`-`c31`), preregistered in
`EXPERIMENT-seed-confirmation.md`. About 1.5 h a seed, run one at a time:
about 12 h. Output: gates per seed, per-pool ratio with seed-bootstrap
intervals over ten seeds.

## R1 + R3. Ablations and the cost of acceptance (new arms, built on branch `worktree-review002`)

Same schedule as v11.1 (seven areas, same lives, worlds, budgets), meta-level
off in every arm so level 0 is what is compared; each arm on the same three
seeds (919127-919129, already lived by the full protocol in R2, so the full
arm is the R2 run with meta on plus one full run with meta off).

| arm | what changes | answers |
| --- | --- | --- |
| full | v11.1 level 0 | reference |
| no-guidance | never fit model or prior: search order is the experience-free Occam order | how much is learned guidance |
| frequency | no model; rows ordered by how often their atoms were earned | is a simple frequency rule enough |
| no-invention | no extend, no prune | how much is invention |
| accept-all | every proposed combination kept, no proof | value of acceptance (no cost) |
| point | kept if the held-out point gain is positive on half the set, no interval, no cross-area check | a simpler validation rule |
| matched | accept-all, plus extra lives until live scans equal full's live + proof scans | proof compute spent on experience instead |

Scored on the same fresh check sets as `seed_check.py`; total scans
(live + proof) reported beside every score, so R3's plot is performance
against total compute. Harmful acceptances (kept, then lower on the fresh
set) counted per arm.

## R5 (optional, cheap). Robustness of acceptance, offline

From the ledgers of c1-c31: re-judge every recorded proof at half and quarter
set size and at cross-area tolerance 0, 2, 5, 10%, against the candidate's
later fresh-set effect: harmful-accept and good-reject rates against cost.
`extension_triggers.py` already does the set-size part for one rule.

## R4 (optional). LLM agent with reusable functions

Out of scope for this revision; say so in the paper's limits.

## Presentation

Level 0 (state) against levels 1-2 (procedure) made explicit in the
introduction; related work: continual learning, adaptive search, DreamCoder-
style library learning; chronology of versions to an appendix with the table
kept in the body.

## Evaluation (2026-10-26)

R3 is the one that can change the thesis. Of 1,068 proofs on the sealed seeds
c1-c23, 479 were rejected after the full held-out set and 394 of those (82%)
scored above the carried state, short of the interval; neutral changes would
sit near 50%. The test discards mostly-good changes, and the model compounds
with experience, so accept-all or matched could beat full. Run R1+R3 as one
grid, R3 arms first. The "9% untrained" the review cites is dev agent s1
before gate 2 (paper line 321); sealed v11.1 pools all rose (weakest 118%):
say dev-only in the limits section. R4: decline in the limits section.
