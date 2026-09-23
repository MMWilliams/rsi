# V86: bounded representation adaptation

## Research question

Can a retained generic body recover cross-family transfer after an adversarial code-point shift if the improver explicitly searches a small representation hypothesis set?

## Protocol

V86 reuses the V85 bank and search budget: identity development, `xor55` admission/final, 24 tasks per split, 11-node bodies, 64 states per size, global development-only body bank, immutable lineage, and two-task support credit. The new arm evaluates each retained body under four visible-alignment hypotheses: `identity`, `xor55`, `affine5`, and `rotate3`. The encoding is serialized in `load_ord` instructions and selected only when the resulting predicate matches visible target/other behavior.

## Findings

| arm | development | admission | final |
|---|---:|---:|---:|
| legacy | 8/24 | 12/24 | 8/24 |
| direct grammar | 18/24 | 17/24 | 13/24 |
| generic lineage | 8/24 | 12/24 | 8/24 |
| encoding-adaptive lineage | 8/24 | 19/24 | 19/24 |

Encoding-adaptive lineage solved 11/11 final `bit_splice` tasks, 0/5 `fold_parity`, and 8/8 `fold_mod3`. Plain lineage solved 0/11 bit-splice tasks. Adaptive lineage passed the admission gate but was not selected because the current selector ranks development correctness first and direct grammar scored 18/24 there versus adaptive lineage's 8/24.

## Interpretation

Explicit representation hypotheses recover the operator transfer that the V85 adversarial shift removed. This is a bounded meta-learning result: the retained body was reusable once the representation transform became an explicit hypothesis. It is not yet recursive self-improvement because the hypothesis set, encoding operators, selection criterion, and serialization primitive were researcher-authored. The failure to select the stronger held-out arm shows that representation adaptation and architecture selection are separate bottlenecks.

## Limitations

One bank and one held-out encoding were tested. The four encodings are a closed catalog, visible alignment is a hand-designed criterion, and no neural representation learner or open-ended primitive invention is present. The adaptive arm gets extra candidate hypotheses, so its accuracy is not directly comparable as a compute-matched improvement over the controls; its admission/final transfer is the primary result.

## Verification

The independent audit passed, replaying 288 arm-task rows and checking 25 sealed artifacts. Archive: `runs/generic-body-evolution-v86-encoding-adaptive-20261017`. Results digest: `cb4132bfc9cf9668c3c4e331213b66a82388c2a458e13f46a94beece17f5faf1`.
