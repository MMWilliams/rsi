# V59 online predicate invention

Status: audited two-seed result. V59 introduces a vowel/consonant transition domain for which the existing baseline DSL and reflective character methods provide no useful predicate. From visible input/output examples, the system invents a `char_set` predicate, compiles it into the generic span schema, and tests it on hidden examples from each task.

| Representation | Seed 18 final | Seed 19 final |
| --- | ---: | ---: |
| Baseline | 0/24 | 0/24 |
| Reflective runtime predicates | 0/24 | 0/24 |
| Self-authored `char_set` predicate | 24/24 | 24/24 |

The self-authored arm reached 24/24 development, admission, and final on both seeds and was selected by the admission gate twice. Its predicates were synthesized from visible target alignment, not imported from the runtime or a named semantic vocabulary. This demonstrates a bounded form of online operator invention: the system extended its executable hypothesis language when existing primitives failed.

The result is not open-ended RSI. The task is synthetic, visible target alignment supplies strong supervision, and character-set predicates do not extrapolate to unseen symbols. The next pressure test should require invention from indirect feedback or a new operator whose membership cannot be copied directly from visible targets.

Both independent audits passed, replaying 216 evaluation rows and checking 22 sealed artifacts per run.

Artifacts: `runs/online-invention-v59-20260918/` and `runs/online-invention-v59-20260919-seed19/`.
