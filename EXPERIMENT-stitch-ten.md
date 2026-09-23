# Ten-version stitched comparison

The first implementation is a two-lane integration pilot. It compares a
common-interface router with nine semantic-program arms (V65, V67, V69, V70,
V72, V73, V75, V77, V80) on six mixed synthetic mechanism families. V8 runs
in a separate string-DSL lane against its own frozen baseline because its
program interpreter and task format differ. No pooled score combines lanes.

## Common interface

Each semantic arm receives identical visible examples and returns candidates
in one envelope: executable program, visible behavior signature, estimated
cost, required operations, structural complexity, and provenance. The host
validates visible execution and hides reference/hidden outputs from the arm.
Development and admission scores can rank sources; final outputs cannot.

## Stitched policy

The pilot gives every semantic arm the same task calls and caps saved
candidates per arm at four. It deduplicates identical programs, then learns a
source priority from development and admission. Admission may fall back to
the best native arm. The router selects one program per final task. Macro
libraries are mined only from visible training examples. The V8 lane compares
the original and corrected search filters with the same search budget. The
V12 credit selector is excluded because its transfer screen failed.

## Required comparisons

1. each native semantic arm and the selected router on the same mixed final bank;
2. router with one semantic arm removed at a time;
3. frozen direct grammar and random-priority controls;
4. V8 versus original search on a disjoint DSL final bank;
5. per-arm calls, generated candidates, wall time, and DSL search charges.

This pilot is an interface and replay validation with two task-bank seeds. It
does not match actual per-arm primitive executions, train the V67/V72/V73
native meta-policies jointly, or establish superiority. Promotion requires a
later preregistered six-seed, compute-matched replication that beats the best
native arm on at least four seeds without a final-bank regression. A positive
router result would show useful integration, not open-ended RSI.
