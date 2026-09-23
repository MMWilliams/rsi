# V60 extrapolative operator invention

Status: audited two-seed result. V60 tests whether an invented operator can generalize beyond visible symbols. The parity-transition domain uses hidden Greek characters not present in the visible examples. The system compares baseline search, reflective runtime predicates, memorized character sets, and a synthesized modular ordinal predicate.

| Representation | Seed 20 final | Seed 21 final |
| --- | ---: | ---: |
| Baseline | 0/24 | 0/24 |
| Reflective predicates | 0/24 | 0/24 |
| Memorized `char_set` | 0/24 | 0/24 |
| Synthesized `ord_mod` | 24/24 | 24/24 |

The modular predicate reached 24/24 development, admission, and final on both seeds and was selected twice. Unlike V59, the winning rule was not a character lookup: it inferred a modulus-and-residue relation over ordinal values, allowing it to classify hidden symbols absent from visible examples.

This is the strongest operator-invention result so far, but it remains bounded program synthesis. The modulus grammar and visible target alignment are supplied by the experiment, and the parity domain is synthetic. A harder next test should require the system to invent the feature grammar itself from error traces rather than receive a modular hypothesis family.

Both independent audits passed, replaying 288 evaluation rows and checking 22 sealed artifacts per run.

Artifacts: `runs/extrapolative-v60-20260918/` and `runs/extrapolative-v60-20260919-seed21/`.
