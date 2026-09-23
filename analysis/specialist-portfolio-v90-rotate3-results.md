# V90: specialist portfolio under rotate3 encoding

## Research question

Does the representation-adaptive specialist portfolio remain safe and useful under a third held-out code-point encoding, a 3-bit cyclic rotation?

## Protocol

V90 used a fresh bank (`bank_seed=2026101705`) with identity development encoding and `rotate3` admission/final encoding. The V88/V89 portfolio, four representation hypotheses, 11-node/64-state global search, immutable lineage, two-task support credit, and development-first selector were unchanged.

## Findings

| arm | development | admission | final |
|---|---:|---:|---:|
| legacy | 7/24 | 7/24 | 7/24 |
| direct grammar | 10/24 | 24/24 | 24/24 |
| encoding-adaptive lineage | 7/24 | 14/24 | 14/24 |
| specialist portfolio | 10/24 | 24/24 | 24/24 |

The portfolio was selected and reached 24/24 final: 7/7 `bit_splice`, 10/10 `fold_parity`, and 7/7 `fold_mod3`. Direct grammar also reached 24/24, so this is a robustness/tie result, not an accuracy gain.

## Encoding matrix

Across the three held-out encoding families, the selected portfolio results were 24/24 for `xor55`, 10/24 for `affine5`, and 24/24 for `rotate3`. It recovered every available final `bit_splice` task in all three runs: 11/11, 10/10, and 7/7.

## Interpretation

The portfolio’s selective bit-splice transfer is robust to multiple representation shifts, while broader fold-family transfer varies by encoding and bank. The result supports a reusable specialist-portfolio architecture, but not a general encoding-invariant algebra or open-ended RSI.

## Limitations

V90 is one rotation seed; the encoding catalog, visible-alignment rule, typed language, portfolio ranking, and synthetic families remain authored. The adaptive arm receives extra candidate-generation work. Compute-matched portfolio evaluation and replication across unseen encodings remain necessary.

## Verification

The independent audit passed, replaying 288 arm-task rows and checking 25 sealed artifacts. Archive: `runs/generic-body-evolution-v90-specialist-portfolio-rotate3-20261017`. Results digest: `0a57f6940510485c913f8e475413964247f40f27833182734609f5d937d6a0e5`.
