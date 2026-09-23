# V88: specialist portfolio for representation-shift robustness

## Research question

Can a per-task portfolio preserve direct-grammar coverage while invoking an encoding-adaptive retained body only when it is the shortest visible-compatible specialist?

## Protocol

V88 used a fresh bank (`bank_seed=2026101703`) with identity development encoding and `xor55` admission/final encoding. The global 11-node/64-state typed-body search, immutable lineage, two-task support credit, and 24-task splits were unchanged. The portfolio arm selected the shortest candidate from direct grammar and encoding-adaptive lineage per task. Architecture selection remained development-first, with admission eligibility.

## Findings

| arm | development | admission | final |
|---|---:|---:|---:|
| legacy | 8/24 | 8/24 | 8/24 |
| direct grammar | 16/24 | 16/24 | 17/24 |
| encoding-adaptive lineage | 8/24 | 16/24 | 15/24 |
| specialist portfolio | 16/24 | 24/24 | 24/24 |

The portfolio was selected prospectively. It solved every final task, including 7/7 `bit_splice`, 9/9 `fold_parity`, and 8/8 `fold_mod3`. It retained direct grammar's development performance while adding adaptive coverage on the held-out shift.

## Interpretation

Specialist composition repaired the V87 failure mode: admission-first selection recognized the adaptive capability but selected it globally, causing a final regression; the portfolio instead preserved the baseline candidate when it was available and used the adaptive specialist for shifted tasks. This is evidence for a useful mixture-of-experts/search-portfolio pattern and a concrete component-level improvement, not open-ended RSI.

## Limitations

The prospective portfolio result has one fresh seed. The candidate-ranking rule, encoding catalog, visible compatibility criterion, typed language, and synthetic task relation remain authored. The portfolio receives extra candidate-generation work from the adaptive arm, so total compute and latency are not yet matched to direct grammar. Replication across `affine5`, `rotate3`, and unrelated alphabets is required.

## Verification

The independent audit passed, replaying 288 arm-task rows and checking 25 sealed artifacts. Archive: `runs/generic-body-evolution-v88-specialist-portfolio-20261017`. Results digest: `05b01e4b8b1852d4c580c506746aa53d2b564455e563b9ad7de8a39e8cde0241`.
