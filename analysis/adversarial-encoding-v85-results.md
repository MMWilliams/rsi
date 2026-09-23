# V85: adversarial code-point encoding

## Research question

Does the generic typed-body lineage learned from one code-point representation transfer the same underlying operator when held-out tasks use a different representation?

## Protocol

The mechanism families and generic search budget were kept fixed: 24 development, 24 admission, and 24 final tasks; 11-node bodies; 64 states per size; a global development-only body bank; immutable parents; two-task support credit; and frozen held-out replay. Development used `identity` code-point encoding. Admission and final used `xor55`, while retaining the same visible Unicode alphabet and the same task-family relation (`novel_operator_transition` to `stack_transition`). The solver was not given an encoding-aware primitive.

## Findings

| arm | development | admission | final |
|---|---:|---:|---:|
| legacy | 8/24 | 12/24 | 8/24 |
| direct grammar | 18/24 | 17/24 | 13/24 |
| generic body evolution | 8/24 | 12/24 | 8/24 |
| generic lineage | 8/24 | 12/24 | 8/24 |

The prior V84 matched-encoding runs produced 12/12 `bit_splice` transfer for both flat and hierarchical lineage. Under the held-out encoding shift, V85 lineage produced 0/11 `bit_splice`, 0/5 `fold_parity`, and 8/8 `fold_mod3` final successes. Thus the selective bit-splice signal did not survive the representation change. Direct synthesis remained the selected arm, but it also solved 0/11 bit-splice tasks because the encoding-aware operator was outside its fixed grammar.

## Interpretation

The V83–V84 selective result was representation-dependent. It is consistent with a code-point-correlated functional shortcut, not evidence that the retained body represented an encoding-invariant rotate/bit-splice operator. This is a useful negative result: changing the representation exposed a binding limitation that aggregate same-encoding transfer concealed.

## Limitations

This is one adversarial seed and one encoding shift. The encoding family, XOR constant, Unicode alphabet, typed instruction vocabulary, constants, depth/state bounds, support threshold, global-bank construction, synthetic family relation, and admission gate remain researcher-authored. The test changes the task generator but does not yet let the system infer or retain an explicit encoding transform. It is evidence about bounded representation transfer, not proof of open-ended RSI.

## Verification

The independent audit passed, replaying 288 arm-task rows and checking 25 sealed artifacts. Archive: `runs/generic-body-evolution-v85-encoding-xor55-20261017`. Results digest: `52bb15ded14cbeffc418687aa772b90961b7ae72abcb46ef2a7a66c46d0d920f`.
