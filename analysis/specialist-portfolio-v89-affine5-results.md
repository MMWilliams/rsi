# V89: specialist portfolio under affine encoding

## Research question

Does the specialist portfolio transfer beyond the XOR representation shift to a bijective affine code-point encoding?

## Protocol

V89 used a fresh bank (`bank_seed=2026101704`) with identity development encoding and `affine5` admission/final encoding. The same 11-node/64-state global search, adaptive hypotheses, immutable lineage, portfolio composition, admission gate, and development-first selector were used as in V88.

## Findings

| arm | development | admission | final |
|---|---:|---:|---:|
| legacy | 6/24 | 0/24 | 0/24 |
| direct grammar | 14/24 | 0/24 | 0/24 |
| encoding-adaptive lineage | 6/24 | 9/24 | 10/24 |
| specialist portfolio | 14/24 | 9/24 | 10/24 |

The portfolio was selected and recovered all 10/10 final `bit_splice` tasks, but solved 0/10 `fold_parity` and 0/4 `fold_mod3` tasks. Plain lineage and direct grammar solved none of the final tasks.

## Interpretation

The portfolio’s representation adaptation is not limited to XOR: it preserved the retained bit-splice specialist under affine5 and produced a large gain over the controls. However, the transfer is operator-specific, so the current system has not learned a general encoding-invariant algebra.

## Limitations

This is one affine seed. The affine transform, candidate catalog, visible alignment, typed language, and family relation remain authored, and the adaptive arm receives extra hypothesis-search work. Broader replication and compute-matched comparisons are still required.

## Verification

The independent audit passed, replaying 288 arm-task rows and checking 25 sealed artifacts. Archive: `runs/generic-body-evolution-v89-specialist-portfolio-affine5-20261017`. Results digest: `90efd0121179cb39c060e1e8b581e82b1d604056879538bd307fffadfba0a276`.
