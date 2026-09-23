# Improver growth in this benchmark: a feasibility result

> **SUPERSEDED 2026-09-21, then largely reinstated the same day.** A tenth
> action space, the complexity partition, appeared to clear all four
> preconditions, and improver growth passed two frozen replications with
> independent audits on it. External review then asked for a capacity-matched
> pooled model in the adversarial default set. Against that default the
> partition environment fails P2d, both improver-growth forms are dominated, and
> the construction form is withdrawn. See section 9 of
> `WHAT-WORKED-WHAT-FAILED-2026-09-21.md`. This document's conclusion therefore
> stands in a stronger form than it was withdrawn in: growth is impossible
> wherever a free heuristic, **including one larger model on the same labels**,
> already captures the available value, and that was true of all ten. The nine screens below remain
> correct as measurements and as the diagnosis that produced the preconditions;
> only the headline claim of infeasibility is withdrawn. Its real content was
> narrower and still holds: growth is impossible wherever a *free* heuristic
> already captures the available value, which was true of all nine.

2026-09-20. Synthesis of the day's screens. All numbers come from audited runs
or from opened panels reconstructed by a passing audit.

## Claim

**Withdrawn as stated; see the banner above.** As written this said improver
growth was not measurable in this benchmark at any action space, and a tenth
space disproved it. What survives: **an action space admits improver growth only
where no free heuristic already captures the value.** Nine action spaces spanning three orders of magnitude in total value were
screened against four preconditions. Every one fails at least one.

Evaluator growth is unaffected and remains replicated and audited.

## The four preconditions

Each is cheap, they are ordered, and each rejects spaces the previous one
admits.

| precondition | asks |
| --- | --- |
| **P2** power | is the oracle headroom over the strongest fixed control above bank noise |
| **P2b** non-stationarity | does the best action vary by instance, or is it a constant |
| **P2c** default regret | can the best *zero-knowledge* rule be beaten, where that rule is the strongest a researcher would write before seeing labels |
| **P2d** learnability | does a policy fitted on held-out banks actually capture the residual |

The threshold throughout is **+20 correct tasks per 576**, roughly twice the
observed twelve-bank interval half-width.

## The nine screens

| action space | P2 | P2b | P2c | P2d | where it dies |
| --- | --- | --- | --- | --- | --- |
| whole-bank policy menus | **fail** | - | - | - | oracle selection worth +5 and +8 |
| region purchase, 3 of 6 | pass | **fail** | - | - | fixed regret +6 and +12; 11 banks of experience beat 1 by +1 and -3 |
| per-bank action, 3 actions, i.i.d. | pass | **fail** | - | - | balanced banks: fixed regret 2.9, context worth -0.8 |
| per-bank action, 3 actions, heterogeneous | pass | pass | **fail** | - | contextual value +22 and +26, both intervals crossing zero |
| per-task threshold routing | pass | pass | **fail** | - | default regret +17 and +27; learned threshold **-4 and +2** against naive *t*=0 |
| seven-action per-task | pass | pass | pass **+38, +51** | **fail** | own-region wins 11 of 12 region cells; selector **-9 and -18** |
| depth-heterogeneous, 12 actions | pass | pass | pass **+43, +55** | **fail** | confidence genuinely deceptive, yet selector **-6** against own-region-deep |
| interacting typed edits | **fail** | - | - | - | default regret +3 to +6 per 288 against a per-family rule |
| rule-identity, 4 hidden rules in one block | pass | pass | **fail** | - | confidence recovers the rule: most-confident 103 and 134 against oracles 114 and 141, regret +11 and +7 |
| depth-heterogeneous, protected override | pass | pass | pass | **fail** | best margin +1 with interval crossing zero; train-fitted margin gives -6 |

## What each screen taught

**Enlarging the action space does not help.** Going from whole-bank menus to
region purchases multiplied total value roughly tenfold, from +5 to +54, and
left the learnable residual flat at +1 to +12. What grew was the value of the
constant, not the value of conditioning.

**Non-stationarity is necessary and not sufficient.** Building a Beta(0.4, 0.4)
heterogeneous generator raised fixed regret from 2.9 to between 38 and 67 on
generated, audited banks, and made conditioning worth +58 and +84. The improver
still had nothing to learn, because the *rule* for conditioning, "trust whichever
specialist is more confident on this task", is guessable and needs no history.

**Breaking the guessable rule is also not sufficient.** The depth-heterogeneous
set was constructed so confidence would be deceptive, and it is: shallow models
are systematically more confident while deep models are more correct, so
"most confident" collapses to 339 against own-region-deep's 423. Default regret
rose to +43 to +55. A selector trained on two panels and tested on a third still
lost by 6.

**Large default regret can be pure noise.** Two spaces cleared P2c and both died
at P2d. In the seven-action space the own-region specialist wins 11 of 12 region
cells, so the residual is task-level idiosyncrasy, not structure a policy can
hold.

## The deepest finding: confidence is a near-sufficient router

Two spaces were built specifically to destroy the guessable rule, and both
failed anyway, for different reasons that together explain the pattern.

**Rule identity.** `shifted_ast_bank` emits four distinct arithmetic predicates
that all present in Unicode block 0x800, so the public signature genuinely
cannot identify the mechanism and no region-matching rule can exist. Per-rule
specialists were trained and the hidden-rule upper bound reaches 112 and 140
against oracles of 114 and 141. But "use whichever specialist is most confident"
reaches **103 and 134**, leaving default regret of only **+11 and +7**. Even
when the surface signature is uninformative, the specialists' own confidence
recovers the mechanism.

**Depth heterogeneity, the one near miss.** Here confidence *is* broken:
shallow models are systematically more confident while deep models are more
correct, so most-confident collapses to 339 against own-region-deep's 423 and
default regret rises to +43 to +55, clearing P2c. P2d then failed by 6. Because
that margin was small, the learning problem was re-posed in the easier and
better-suited protected-admission form: keep the default unless a learned model
says a specific alternative wins by more than a margin fitted on training panels.

| margin | total | overrides | vs default |
| --- | --- | --- | --- |
| 0.00 (train-selected) | 412 | 298 | **-6**, interval -16 to +5 |
| 0.10 | 415 | 60 | -3, interval -10 to +4 |
| 0.15 | 419 | 31 | +1, interval -6 to +7 |
| 0.25 | 419 | 14 | +1, interval -2 to +4 |
| 0.40 | 418 | 7 | +0, interval -3 to +3 |

As the margin rises the policy simply converges back to the default, and the
best any margin achieves is +1 with an interval crossing zero. The residual is
not a harder learning problem; it is noise.

So the rule generalizes beyond region matching. **Wherever specialists exist in
this benchmark, some free heuristic over them, usually their own confidence and
otherwise "match the mechanism, take the most data", is near-optimal.** That is
what leaves an improver nothing to learn.

## Why this benchmark is structurally hostile

The task distribution is cleanly partitioned by mechanism, specialists transfer
poorly across mechanisms, and more training data monotonically helps. The
optimal routing policy is therefore "use the specialist matching this task's
mechanism, trained on the most data", which is both near-optimal and writable
without a single verified label. Everything left over is noise.

An improver can only demonstrate growth where the optimal policy is **not
guessable**. That is a property of the environment, not of the improver, and no
amount of improver design fixes it.

## What would qualify

An environment must clear all four preconditions. From these screens, the
binding constraints are P2c and P2d together: the optimal policy must be both
unguessable and predictable from public features fitted on held-out banks. That
combination requires structure that is real but not obvious, for example:

- **Mechanisms whose best specialist is reliably a different mechanism's**, so
  own-region matching is wrong in a stable, learnable way. The cross-region
  matrix shows this benchmark has the opposite property.
- **Applicability depending on feature interactions** rather than on one
  dominant public signal, so no single-statistic rule captures it.
- **Costs that vary by instance**, making the value of an action depend on a
  budget state the improver must track, which no static rule can express.

Each should be screened for all four preconditions before any improver is built,
which costs one cheap computation per candidate on opened rows.

## Status of the programme

| claim | status |
| --- | --- |
| evaluator growth | **achieved**, replicated and audited: +49/576 on fresh banks, twelve of twelve banks, interval +37 to +62 |
| improver growth | **not achieved**, and shown infeasible in this benchmark across seven action spaces |
| recursive child-improver growth | **not tested**; it presupposes improver growth |

The honest summary of roughly forty prior failed improver gates is that they
were measuring an environment property. They were run against baselines weaker
than a free hand-written rule, inside action spaces whose learnable residual was
at or below bank noise. That diagnosis is now a set of preconditions rather than
a pattern to be rediscovered.

## Limits

- One synthetic string/program benchmark. Nothing here says good defaults
  dominate in other domains; it says they dominate here, and that this is
  measurable in advance.
- All oracles use final labels and are upper bounds, not deployable policies.
- Default regret depends on which zero-knowledge rule is proposed; a weak
  proposal inflates it, so the rule must be chosen adversarially and stated.
- P2d was tested with gradient-boosted selectors on public pool, score, region
  and confidence features. A substantially richer feature set or model class
  could in principle capture residuals these missed.
