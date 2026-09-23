# Prospective same-base transfer test for improving the improver

Declared after inspecting all three v2 episodes and before generating any task in the transfer episodes. This is a new study. Earlier banks are development evidence and the old source-effect archive is an explicitly charged inherited input.

## Question and frozen states

Does later learned feedback-controller knowledge cause a stronger improver when every arm starts with the **same freshly trained evaluator**? Transfer only controller-effect records. Rebuild the evaluator from each episode's identical bootstrap labels; do not transfer trained evaluator parameters or prior task labels.

Construct source controller states from the three already archived `meta4_online__argmax__proper_tie` arms, without choosing donors by outcome. The common I0 state is the original 60 source-effect records. I2 appends the first two online effect records from **each** archived episode (six records). I4 appends all four from each (twelve records). Preserve donor/round order. I4_scrambled shuffles only the twelve appended utility values with RNG seed 941; it keeps states, tactics, labels, and state size. Empty has no effect records. All these states are frozen before fresh transfer tasks are generated. `I0_online` and `I4_online` begin with the corresponding frozen state and update their own table after each live candidate evaluation; compare them with frozen I0/I4 separately.

## Fresh episodes and resource allowance

Six complete independently seeded episodes use offsets +3000, +4000, +5000, +6000, +7000, +8000 from v2 base seeds 207001 through 207006. Each contains bootstrap **two tasks**, reservoir 48, admission 36, final mixed 24, final AST 12 and final changed arithmetic 12. Every task has eight randomized public examples and sixteen held-out examples. The changed arithmetic rules are `(11,3,4,7,2)`, `(3,17,5,6,4)`, `(13,9,7,11,6)`, `(5,19,4,9,7)` in `(multiplier, addend, divisor, modulus, residue)` order; these differ from prior study rules. Candidate sources remain V67/V73, cap 16 each, with source-order program deduplication. Do not discard tasks based on candidate reachability or outcome.

All arms buy exactly 48 previously unknown candidate labels per round for four rounds, with the same bootstrap and admission labels available. A single admission/deployment rule is used in each arm. Admission tasks are reused across rounds and charged separately. Final predictions at all checkpoints are frozen before any final oracle labels open.

Arms: I0, I2, I4, I4_scrambled, Empty, I0_online, I4_online all use argmax + proper-score tie retention. Fixed uniform, novelty, disagreement and combined use that same rule. Fixed uncertainty uses argmax + strict accuracy retention, the strongest fixed complete policy observed previously. The fixed policies do not inherit controller records. All arms fit the same evaluator architecture five times.

Primary comparison: I4 versus I0 at final checkpoint, paired by six complete episodes. Strong-control comparison: I4 against the better of fixed uncertainty/strict and fixed disagreement/proper in each episode. Secondary: I2 dose trend, I4 versus scrambled and empty, online versus frozen I4, candidate-selection gain and task losses at every update, initial behavioral evaluator. Claim transferred improver growth only if I4 beats I0 on at least five of six episodes, gains at least two correct choices per 48-task episode on average, and exceeds both strong fixed policies on average. A tie counts as no win. This screen is intentionally demanding; a failure remains a result. Any newly chosen policy still requires a later independent promotion test.

Report per-episode and panel curves, paired gains/losses, accepted edits, acquired tactics, bootstrap/improvement/admission labels, source acquisition cost, candidate-generation wall time and scope of replay. The external scoring oracle is task execution on hidden examples. Replay uses the same host interpreter, so it cannot certify universal program correctness or independent oracle implementation.
