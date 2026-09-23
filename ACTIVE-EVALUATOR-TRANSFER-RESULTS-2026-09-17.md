# Active evaluator transfer: result

The learned one-query evaluator did **not** transfer a gain over the best
fixed one-query policy. External output feedback substantially improved
candidate selection within a task, but this is a different result from
growth of the retained evaluator or improver.

## Setup

The frozen protocol is `EXPERIMENT-active-evaluator-transfer.md`. Six new
64-task AST-transition banks used two public examples, eight unlabeled probe
inputs, and 14 final scoring examples per task. V67 and V73 each supplied up
to 128 candidates; the common pool averaged 86.9 candidates per task.
The same initial evaluator ranked every pool. The learned pairwise and ridge
probe selectors were fitted to the prior 384-task development set, then frozen.
Each one-query selector picked an input before its oracle output was used.
The selected output filtered candidates; the initial ranker broke remaining
ties. A two-query sequential weighted-entropy rule was measured at twice the
oracle output budget.

| Evaluator policy | Correct / 384 | Output queries / arm |
| --- | ---: | ---: |
| Initial ranker, no query | 179 | 0 |
| Deterministic random probe | 219 | 384 |
| Entropy, fixed | 250 | 384 |
| Pairwise learned | 252 | 384 |
| Ridge learned | 252 | 384 |
| Uniform minimax, fixed | **256** | 384 |
| Sequential weighted entropy | **301** | 768 |

Candidate reachability was 353/384. The two-query result remains 52 tasks
below that ceiling. It exceeds one-query minimax by 45 tasks, but uses 384
additional output queries. Compared at the same one-query budget, learned
pairwise lost four tasks to fixed minimax.

## Transfer and uncertainty

The pairwise-minus-minimax differences across the six independent banks were
`[-1, 0, -3, 0, 0, 0]` tasks. Pairwise alone solved 10 tasks; minimax alone
solved 14. An exact six-bank resampling percentile interval for the mean
paired difference was `[-1.67, 0]` tasks per 64-task bank. The predeclared
screen required gains on at least four banks and a positive interval; it
failed. The development-only pairwise advantage had been 237 versus 233/384,
driven by 13 versus 9 discordant wins, and did not replicate. Reusing these
confirmation banks for retuning would make them development data.

The two-query-minus-one-query-minimax differences were `[5, 11, 8, 8, 6, 7]`
tasks by bank; a six-bank resampling interval for the mean difference was
`[6.17, 9]` tasks per bank. This measures the value of another oracle answer
for these candidate pools. It does not show a learned policy beating a fixed
policy at matched query budget.

## What improved

The evaluator's *within-task decision* improved as it received external
feedback. The policy narrowed a candidate pool using a real target output,
then selected a better program on disjoint final examples. This is directly
measured by the no-query and queried rows above. There is no evidence here
that the **retained evaluator** became more capable across tasks: the learned
query rule lost to a fixed one. There is no child-improver result, so this
experiment says nothing positive about recursive improver growth.

The strongest tested seed for this scoped AST candidate evaluator is the
fixed uniform-minimax one-query selector when the budget is one oracle output
per task; sequential weighted entropy performs best when two outputs are
allowed. These are provisional components for subsequent improver tests, not
promoted RSI systems.

## Audit and cost

`runs/active-evaluator-transfer-20260917/audit.json` passed all 384 cases.
The audit regenerated banks from seeds, checked candidate visible fit and
digests, reconstructed unlabeled choices from frozen model weights, and
recomputed final outcomes. The source data and runner hashes were stored in
the prepare manifest. All confirmation choices were recorded before the
separate scoring command. This is a reproducible code-flow safeguard, not an
independent filesystem or oracle access-control boundary.

Preparation took 94.5 seconds of wall time with eight candidate-generation
workers. The pool required 266,928 candidate-program evaluations on the
eight probe inputs, shared across policies. The development source required
384 tasks with all eight probe outcomes available during fitting, plus its
own candidate generation. These acquisition and candidate-execution costs
are material; query counts alone do not describe total compute.

The task family is a finite synthetic DSL. Correctness means passing all 14
fresh final examples, not a proof of program equivalence or general
intelligence. The benchmark generator, oracle, and candidate sources remain
researcher-written. Next, test a cost-aware sequential evaluator that learns
when a second query is useful from old tasks and transfers to untouched banks;
compare it with fixed two-query policies at matched total queries. Then cross
evaluator checkpoints with same-base improver checkpoints and measure whether
a later improver creates a better child improver.
