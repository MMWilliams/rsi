# Where growth was actually seen: a distillation, 2026-10-10

Every number is read from an audited run or an opened analysis file named in the
results documents; nothing is from memory. Five eras, three domains (the string
DSL with the neural loop, the string DSL seed-improver programme, the
drawn-mechanism environment). Ordered by strength of evidence, then by how
close the finding sits to recursive self-improvement.

## 1. Confirmed, predeclared, two replications, audited (mechanism environment)

**C-growth: the ability to acquire unseen worlds improves with experience,
through a structure learned from that experience, and keeps improving past
where the fixed prior saturated.** Groups learned from 1,600 worlds against
groups from 400, same agent, summed over 18 cells of 12,800 tasks: +6,993
[5,890, 8,110] and +8,077 [6,932, 9,264]. The groups from 400 worlds hurt in
places (-354, -237 at budget 512); the groups from 1,600 turn those cells
around. No labels. `COACH-RESULTS-2026-09-23.md` §16. This is the closest
thing to RSI in the record: experience improves the representation the learner
runs on. The learner itself is fixed, so it is one level of recursion, not two.

**C-family: a world model built from the agent's own evidence moves the
tight-budget wall that no policy could.** Family agent minus champion at every
budget 128 to 4,096, trained and untrained combinations, both replications:
+248 to +1,635 of 12,800 per cell; no harm on worlds of a family never trained.
Per world of 100 tasks at budget 128 on untrained combinations: 15.7 and 16.5
solved against 8.4 and 7.4. §14 of the same file.

**G1 and G2: experience of a world's own mechanisms is worth +1,601 and +1,603
of 1,920 tasks at budget 256 over every experience-free order; experience of
other worlds is worth +127 to +204 of 640 on worlds whose family combination
was never trained.** `MECHANISM-GROWTH-RESULTS-2026-09-21.md` §4.

**C-earned, two of three gates: a representation learned from the agent's own
charged picks grows with experience and beats its permuted copy.** Growth
1,600 vs 400 earned worlds +3,639 and +3,275; structure +5,513 and +5,498;
safety failed at budgets 256 to 512 (-326 to -350). Recovers about a quarter of
the handed-set gain. `EARNED-GROUPS-RESULTS-2026-10-05.md`. This is the only
result in which every level of the chain was earned.

## 2. Development evidence, not gated (mechanism environment)

**The earned loop closes without feedback.** An agent that keeps the atoms of
whatever it submitted, right or wrong, raises its own solve rate 4 to 10 times
across a 100-task lifetime at every budget from 128 to 4,096, and recovers
3.7%, 6.2%, 10.6%, 16.5%, 35.5%, 68.1% of the informed ceiling as the budget
grows. Being told whether it was right buys nothing. §6.

**An unconditional prior applied before the first solve is worth more than
everything else combined.** Pair co-occurrence from training worlds, used as the
starting order: +314 [193, 432] over the earned-loop champion at budget 256 and
+621 [384, 841] at 1,024, taking the ceiling share from 4% to 27% and from 16%
to 63%. Outside the trained families it is worse than its permuted control
(-147), and a half-budget hedge turns that into +121 [26, 213]. §6.

**Compounding.** The acquisition margin over the free rule rises monotonically
with worlds seen, 25 to 400, in all six (k, budget) cells, and has not
saturated; the control on worlds with no structure stays flat. §5.

**L1 world and self model (this week).** From confident picks alone the agent
recovers the families at adjusted Rand 0.90 to 0.93 on two seeds, files
import-only atoms correctly, and self-simulation inside it predicts its own
per-atom discovery rate to within 0.02 mean absolute error of a second run of
the true generator, at the split-half ceiling within every family. Not yet fed
back into the agent. `SELF-SIMULATION-WORLD-MODEL-2026-10-10.md`.

**Metric worlds G5/G6.** On worlds whose structure is behavioural rather than
syntactic, the weighting is recovered at Pearson 0.90 to 0.98 and beats the
free rule and a permuted copy at every cell of budgets 4,096 and 16,384 in every
replication; it fails at tight budgets, so the predeclared gates failed and no
claim is made. §7.

## 3. The invention line (string DSL, V55 to V88, two seeds each, audited, no programme gates)

Growth of reach: the system extends its own hypothesis language and solves
mechanisms outside it. `analysis/findings-ledger.json`.

- Failure-driven typed primitive invention: 20/24 on hidden quotient-periodic,
  Gray-code and multi-bit-field tasks on both seeds, against 5/24 and 6/24 for
  the fixed expression grammar and 0/24 for the ordinal grammar (V65).
- Lower-level stack discovery after removing the named popcount, rotation and
  gcd constructors: 24/24 on both seeds against 13/24 and 9/24 (V70).
- Self-editing executable grammar over a sandbox of dormant operations: 18/24
  against 12/24 and 13/24 against 5/24, converging to the same compact operation
  set on both seeds (V73).
- Extrapolative modular operator invention where every fixed vocabulary scored
  0/24: 24/24 on both seeds (V60).
- Generic span schema learned on delimiter tasks transferring to a
  delimiter-free domain: 48/48 against 41/48 (V52).
- Meta-evolved scoring policy for the AST proposer: 15 to 18 and 17 to 22 of
  24, selected twice against the frozen scorer (V67).

What did not hold in this line: the second generation. Gen-1 macro induction
improved 30/48 to 32/48 and Gen-2 tied Gen-1 (V42); quality-diversity recursion
was 39/72 for Gen-2 against 40/72 for Gen-1 (V48). Every gain here is one
generation deep.

## 4. The seed-improver programme (string DSL, six generators, 2026-09-17 to 21)

Growth that reproduced and was then dominated. Verifier growth +73 and +69 of
576 for a 60-leaf pooled model on verified labels (within distribution only;
worse than the base evaluator on every held-out mechanism family, 716 vs 1,020).
Improver growth, routing form +22/+23 and +36/+47; construction form E2 +45/+49
and E3 +26/+19; a capacity-matched pooled model on the same labels beats the
built system by 50 and 36. Recursive child-improver growth G3: -2 [-15, +12].
`WHAT-WORKED-WHAT-FAILED-2026-09-21.md`. The growth was labels plus capacity.
Its lasting product is the four preconditions (P2, P2b, P2c, P2d) and the rule
that the adversarial default must include model capacity.

## 5. The neural loop (Münchhausen prototype, 2026-09-16 to 17)

Micro signals only: verified LoRA self-training pass@1 0/16 to 2/16 then
regressing; CEGIS substrate +5/48; generator-derived Bayesian prior +2/48;
verified macro compression +2/72. Retention lost coverage; inherited effect
tables and fragment libraries tied their controls. No growth claim survives.

## 6. What this says about RSI

Growth of the improver itself, measured as a later improver producing a better
child improver, has not been seen in any domain: G3 in the seed programme, Gen-2
in the invention line, and the coach line all came back null or unstable.

Three kinds of growth have been seen and reproduced:

1. **Within-lifetime growth without feedback** (the earned loop), at every
   budget, in the mechanism environment.
2. **Growth of acquisition with experience through a learned representation**
   (C-growth, C-family, C-earned's growth and structure gates), confirmed and
   audited, one level deep.
3. **Growth of reach by invention** (V60 to V73), large and reproduced on two
   seeds, one generation deep, in the string DSL.

They have never been put together. Kind 2 lives in the mechanism environment,
whose unfamiliar-family boundary is syntactic and cannot be crossed by any
representation; kind 3 is exactly the machinery that crosses such a boundary,
and it has only run in the string DSL. The self model of this week predicts
per atom what the agent will not find. The most promising RSI experiment in
the record is therefore the one that joins them: an agent whose earned world
and self model (kind 2) directs invention (kind 3) at the atoms and families it
predicts it cannot discover, charged in scans, with the next generation earning
on the extended language. Each piece has reproduced on its own. Whether the
loop compounds past one generation is the open question, and it is now a
well-posed one.
