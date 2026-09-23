# Top-choice evaluator edits and context experts

The global top-error correction edit regressed. Public-context experts gave
larger aggregate gains, including on a fresh bank set, but failed the
predeclared uncertainty and strongest-control gates. E192 remains the
confirmed evaluator component; no improver checkpoint has shown reliable
growth.

## Direct top-error correction

E192 missed 89 reachable tasks in its own 192-task training source. For each,
we paired its highest-ranked incorrect program with the best-ranked verified
correct program, then optimized 89 pair constraints while anchoring the new
weights to E192. All variants used the same 31,500 source candidate labels.

| Model | Source correct / 192 | Inspected target A / 192 | Inspected target B / 192 |
| --- | ---: | ---: | ---: |
| E192 | 102 | 99 | 102 |
| Anchor 1.0 | 94 | 96 | 95 |
| Anchor 0.1 | 87 | 77 | 86 |
| Anchor 0.01 | 44 | 37 | 50 |

The update damaged even source top-choice accuracy. This is evidence against
this particular shared-weight edit. It does not prove that top-error training
is inherently unhelpful; the 89 constraints may conflict in one linear
model, and the method was not prospectively confirmed.

## Public-context experts

Three experts were fitted from the same E192 source labels, separated only by
the Unicode block of each visible input. The 50/50 blend averages the global
E192 weights with the matching expert's weights. Both decisions and source
assignment use public data. Results before fresh confirmation were mixed:

| Inspected development set | Global | Pure expert | 50/50 blend |
| --- | ---: | ---: | ---: |
| A, 192 tasks | 99 | 90 | 98 |
| B, 192 tasks | 102 | 107 | 112 |
| Earlier router banks, 192 tasks | 95 | 106 | 115 |

The blend was then frozen and tested on six new 32-task banks, seeds
902222–902227, alongside E192, the pure experts, and the frozen pairwise
router. All methods used identical candidate pools and zero output queries.

| Fresh-bank evaluator | Correct / 192 |
| --- | ---: |
| Global E192 | 101 |
| Equal-weight E192/pairwise | 107 |
| Learned E192/pairwise router | 107 |
| Pure context experts | **110** |
| 50/50 context blend | **110** |

All 192 tasks had a reachable correct candidate. Blend-minus-E192 differences
by bank were `[3, 6, 1, 1, 1, -3]`; the six-bank resampling 95% interval for
mean difference was `[-0.67, 3.67]` tasks per bank. The blend won five banks
but lost three tasks on the sixth. It tied the strongest feasible control,
the pure experts, and its interval includes zero. The predeclared promotion
gate in `EXPERIMENT-context-expert-transfer.md` therefore failed. The
independent 192-case reconstruction audit passed at
`runs/context-expert-transfer-20260917/audit.json`.

The fresh preparation used 29,746 shared candidates and 70.6 seconds with
eight workers. The expert system used no additional source labels beyond
E192's 31,500, but fitted three additional weight vectors. The observed
advantage is scoped to public Unicode blocks in these synthetic tasks; it
does not establish broad transfer or an improving improver.

## Research decision

Retain E192 as the confirmed evaluator control. Put the context blend in the
candidate edit catalog as an unpromoted option. The global top-pair update
should not be admitted in its current form. The next improver study must
decide whether to apply an edit using held-out top-choice outcomes and test
that decision on an untouched second bank, then test whether a later parent
creates a better child improver from the same base and budget.
