# V87: admission-first architecture selection

## Research question

Can admission validation select the representation-adaptive lineage arm prospectively, and does that selection improve fresh-bank performance?

## Protocol

V87 used a fresh bank (`bank_seed=2026101702`) with identity development encoding and `xor55` admission/final encoding. It retained the V86 four-hypothesis representation adapter, 11-node/64-state global body search, immutable lineage, two-task support credit, and 24-task development/admission/final splits. The only selection intervention was to rank admission-eligible arms by admission correctness before development correctness.

## Findings

| arm | development | admission | final |
|---|---:|---:|---:|
| legacy | 10/24 | 7/24 | 4/24 |
| direct grammar | 21/24 | 12/24 | 15/24 |
| generic lineage | 10/24 | 7/24 | 4/24 |
| encoding-adaptive lineage | 10/24 | 17/24 | 13/24 |

The selector chose encoding-adaptive lineage, as preregistered. It solved 9/9 final `bit_splice` tasks, but scored 13/24 overall versus direct grammar's 15/24. Combined with V86, adaptive lineage recovered 20/20 available encoded bit-splice tasks; final overall performance was 19/24 and 13/24, versus direct grammar's 13/24 and 15/24.

## Interpretation

Admission-first selection successfully recognized the held-out representation capability, but did not reliably maximize aggregate final accuracy. Representation transfer and architecture selection remain distinct problems. The two-seed result supports a selective capability recovery, not a general performance improvement or recursive self-improvement claim.

## Limitations

Only two seeds and one held-out encoding were tested. The encoding catalog, visible-alignment criterion, selector policy, typed language, and synthetic task families remain authored. The adaptive arm has extra hypothesis-search cost, and admission is finite and distribution-specific.

## Verification

The independent audit passed, replaying 288 arm-task rows and checking 25 sealed artifacts. Archive: `runs/generic-body-evolution-v87-admission-selector-20261017`. Results digest: `176a092857b19201f37ce39f3bc778a880b4055f10961376e65ad2749008ee80`.
