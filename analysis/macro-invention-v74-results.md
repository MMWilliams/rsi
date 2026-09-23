# V74: visible-only macro invention and cross-task replay

## Research question

Can an improver mine a compact executable abstraction from successful visible-only programs, retain it in a library, and reuse it on later tasks without exposing later-task hidden examples?

## Protocol

The run used a fresh 48-task training bank plus 24 development, 24 admission, and 24 final tasks from the synthetic `macro_transition` family. Three arms were compared:

- `legacy`: the prior ordinal-expression grammar;
- `direct_grammar`: direct synthesis from the V73 safe stack grammar;
- `mined_macro`: macro predicates mined from development visible examples only, then replayed on admission and final.

Macro bodies were normalized by removing their trailing visible-task modulus, hashed, deduplicated, and stored with source-task provenance. The evaluator replays a macro by executing its body and applying the stored modulus; no hidden examples enter mining or candidate construction.

## Findings

| arm | development | admission | final |
|---|---:|---:|---:|
| legacy | 15/24 | 11/24 | 8/24 |
| direct grammar | 24/24 | 24/24 | 24/24 |
| mined macro | 24/24 | 24/24 | 24/24 |

The mined arm was eligible and selected. The library contained three macros, with 144 macro candidates across the 72 evaluation tasks. The compact call representation was 48 canonical bytes versus 112, 166, and 887 bytes for the three mined inline bodies, suggesting a measurable description-length reduction.

## Interpretation

This is positive evidence that an invented executable representation can persist beyond the task that generated it: development-only macro mining transferred through admission to final without hidden-example access. However, the result is not evidence that macro retention improves accuracy beyond direct grammar synthesis: both arms reached 24/24. The strongest paper claim is therefore reusable abstraction and compression, not performance superiority.

## Limitations

The stack instruction vocabulary, macro normalization rule, candidate family, visible alignment heuristic, bounded admission gate, and synthetic task generator are researcher-authored. The run is a single fresh seed, and the development/evaluation family is shared even though task instances are held out. Macro mining is not open-ended invention from arbitrary code, and the result does not establish open-ended RSI.

## Verification

`audit_macro_invention_v74.py` passed, replaying 216 arm-task rows and checking 22 sealed artifacts. The run archive is `runs/macro-invention-v74-20261019`.
