# Reproducibility ledger

Generated 2026-09-21 from run manifests, results and audits by
`analysis/reproducibility-ledger-20260921.json`. Nothing here is typed from
memory; every hash and count is read from the artifact it describes.

## Frozen runs behind the growth claims

| claim | run | protocol hash (prefix) | drift since run | seeds | gates | audit | tasks / labels rechecked |
| --- | --- | --- | --- | --- | --- | --- | --- |
| improver, routing, rep 1 | `runs/complexity-improver-confirmation-20260920` | `2cac1e3e408e25be` | none | 912100-912311 | C1 pass, C2 pass | **pass**, 0 failures | 1,728 / 160,912 |
| improver, routing, rep 2 | `runs/complexity-improver-confirmation-rep2-20260920` | `2cac1e3e408e25be` | none | 913100-913311 | C1 pass, C2 pass | **pass**, 0 failures | 1,728 / 161,932 |
| improver, construction, rep 1 | `runs/construction-improver-confirmation-20260921` | `0ce1ad60bae102cf` | none | 916100-916311 | E1, E2, E3, E4 pass | **pass**, 0 failures | 1,728 / 161,452 |
| improver, construction, rep 2 | `runs/construction-improver-confirmation-rep2-20260921` | `0ce1ad60bae102cf` | none | 917100-917311 | E1, E2, E3 pass; **E4 fail** (ungated) | **pass**, 0 failures | 1,728 / 161,732 |

Totals: four frozen replications, four passing independent audits, 6,912 tasks
regenerated from seeds and 646,028 candidate labels rechecked. Both protocols
were hashed into their run manifests before any bank was generated, and both
files are byte-identical to what was hashed.

The verifier-growth claim rides on the construction runs: built-at-24 minus the
frozen base evaluator E0 is +37 (interval +20 to +56) and +32 (interval +18 to
+44), with every component trained inside the frozen evidence.

## How to reproduce any run

Each runner is staged and refuses to overwrite: `prepare` generates banks and
hashes the protocol, `score` or `cache` opens labels, `improver` runs the gates.
Each auditor rebuilds one panel per process, then combines. Run from the project
root with the venv interpreter and the thread limits, which avoid BLAS
contention with the eight-worker pool and cp1252 failures on task text:

    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONIOENCODING=utf-8

| run | runner | auditor |
| --- | --- | --- |
| routing rep 1 | `complexity_improver_confirmation.py {prepare,score,improver}` | `audit_complexity_improver_confirmation.py {panel} ...` then no argument |
| routing rep 2 | `complexity_replication_two.py {prepare,score,improver}` | `audit_complexity_rep2.py` |
| construction rep 1 | `construction_improver_confirmation.py {prepare,cache,improver}` | `audit_construction_improver_confirmation.py` |
| construction rep 2 | `construction_confirmation_rep2.py {prepare,cache,improver}` | `audit_construction_rep2.py` |

Panels are `history_a`, `history_b`, `transfer`. Regenerating a run from its
seeds reproduces the task ids, pools, both candidate orders, every label, the
cached feature matrices, and every curve point exactly; that is what each audit
checks and reports.

## What the auditors do not share with the runners

The auditors re-derive the partition, specialist training, router fitting and
deployment in their own code rather than importing the improver's, so a runner
bug cannot be reproduced by shared code. They verify cached feature rows to
1e-5, which the construction improver trains on directly.

## Machine constraints that affect reproduction

Windows commit, not physical RAM, is the binding limit on this machine; runs die
with `MemoryError` at hundreds of kilobytes while tens of gigabytes are free
when ComfyUI or Ollama hold models. Check free commit before a run and rebuild
one panel per process. Bash heredocs mangle some Python; write scripts with a
file tool.

## Development evidence, not frozen

`analysis/construction-improver-rotation-20260921.json` (5/5 folds),
`analysis/construction-improver-development-20260921.json`,
`analysis/complexity-partition-environment-20260920.json` (four-precondition
screen), `analysis/recursive-improver-development-20260921.json` (failed G3),
`analysis/scheme-choice-regret-20260921.json` (why G3 failed).

## Amendment, 2026-09-21: construction runs

The two construction runs remain computationally reproducible and their audits
remain valid as reproduction audits. Their **claim is withdrawn**: the
specification they reproduce fits the router on in-sample specialist views and
compares against a pooled baseline with one quarter of the built system's leaf
capacity. `runs/construction-improver-confirmation-*/oof_audit.json` holds the
out-of-fold and capacity-matched rerun on the same caches. A reproduction audit
cannot detect a flawed specification; information-flow and adversarial-baseline
checks are separate steps and are now required before any gate result is
reported.

## Amendment, 2026-09-21: every transfer number here is instance-level

All four frozen runs draw their transfer panels from fresh seeds of the same
six generators. They establish that results reproduce on new instances of
familiar mechanisms and nothing more. Leave-one-family-out on the evaluator
(`analysis/mechanism-holdout-verifier-*-20260921.json`) shows the evaluator
improvement is worse than the base on every unseen mechanism and worsens with
capacity. Nothing in this ledger is evidence of transfer to unfamiliar
mechanisms.

## Amendment, 2026-09-21: routing runs and the partition environment

The routing runs reproduce to the integer under an independent reimplementation
(`routing_capacity_check.py`: routed 351.0 / 366.0, most-confident 329.0 /
343.0). Their C1 and C2 gates stand as stated. Against a capacity-matched
pooled model on the same history they are dominated by 35 and 29
(`runs/complexity-improver-confirmation*/capacity_check.json`). The
complexity-partition environment fails P2d when a 120-leaf pooled model is in
the default set (`analysis/partition-rescreen-capacity-20260921.json`). The
frozen artifacts, hashes and audits are unchanged; what changed is the
adversarial default they should have been measured against.