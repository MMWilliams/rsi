# Frozen confirmation: improver growth in the complexity-partition environment

Predeclared 2026-09-20, before any bank for this experiment is generated.

## Why this environment

Nine action spaces failed the four preconditions, all because a free heuristic
over the specialists, usually their own confidence, was near-optimal. The
complexity-partition environment is the first to clear all four
(`analysis/complexity-partition-environment-20260920.json`):

| panel | most-confident default | own-bin latent | oracle | default regret |
| --- | --- | --- | --- | --- |
| candidate-query-cost | 339 | 392 | 462 | **+123** |
| combined-ranker-query | 346 | 401 | 447 | **+101** |
| candidate-conditioned | 350 | 400 | 439 | **+89** |

P2d also passes: a selector fitted on two panels and tested on a third scores
369 against the default's 350, **+19, interval +5 to +33**.

It works because specialists are partitioned by **solution complexity**, how
deep the first correct candidate sits in the old ranker's order, rather than by
mechanism family. That property is latent, cross-cuts family so no family rule
can express it, and is partly predictable from public pool statistics.

Opened development already shows a monotonic learning curve, 343.3 at two
history banks rising to 369.0 at twenty-four, with C1 +19 and C2 +25. This
protocol tests whether that survives on banks generated after it was hashed.

## Design

- **Base**, frozen and identical for every arm: the four complexity specialists
  (`shallow`, `mid`, `deep`, `pooled`) trained on the two source panels, plus
  `e0`. No arm retrains them.
- **Action**: per task, deploy one of the five.
- **Context**: public pool statistics (log pool size, top-1 margin, score
  spread, distinct-program fraction, head size) plus each specialist's stated
  top-candidate confidence. No hidden field is exposed.
- **Improver**: fits one correctness model per action on the banks of verified
  history it holds, then deploys the argmax per task. Every arm uses the
  identical fitting procedure; only the amount of history differs.

## Arms

- **Large history**: all 24 history banks.
- **Small history**: **expected** per-bank score over every contiguous 2-bank
  window of the history pool, never a single predeclared draw. Today's
  replication one produced a +80 that turned out to be a property of which
  single bank the baseline held; averaging removes that.
- **Zero-knowledge default**: most confident specialist per task. This needs no
  history and is the reference C1 must beat. Measuring against a weaker
  baseline is the error behind roughly forty earlier apparent results.
- **Unavailable references**: per-task oracle, and own-bin routing which uses
  the latent complexity label.

## Banks

Fresh seeds, never used. Six families, 48 tasks per bank, 12 banks per panel.

- Replication one: history_a 912100-912111, history_b 912200-912211,
  transfer 912300-912311.
- Replication two: history_a 913100-913111, history_b 913200-913211,
  transfer 913300-913311.

## Gates

Correct zero-query top choices per 576 tasks, paired at bank level, exact bank
bootstrap.

- **C1, contextual value.** Large-history policy minus the most-confident
  default on the transfer panel. Pass: gain > 0 and interval excludes zero.
- **C2, improver growth.** Large-history minus expected small-history on the
  transfer panel. Pass: gain >= +6, at most 4 of 12 losing banks, interval
  excludes zero.
- **C3, monotonicity.** Reported not gated: the expected total at history sizes
  2, 4, 8, 12, 16, 24 should rise. A non-monotonic curve does not fail the
  experiment but must be reported in the headline.

## Reporting rule

**Reliable improver growth is claimed only if C1 and C2 both pass on both
replications, each with a passing independent audit.** One replication is
reported as one replication. If C2 passes while C1 fails, the claim is limited
to growth relative to less history, not to beating a free rule, and the results
file must say so in its headline.

## Declared limits

- One synthetic string/program benchmark and one notion of complexity.
- The complexity bin is derived from the old ranker's order, so it is latent but
  not independent of that ranker. A different base ranker could change the
  partition.
- Specialists are trained once on the opened source panels and frozen; this
  tests the improver's routing, not specialist construction.
- Contiguous windows within one history pool are not independent samples.
- Nothing here tests recursive child-improver growth.
