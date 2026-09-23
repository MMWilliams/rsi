# Reachability, program frontiers and abstraction learning

## Why the next measurement changed

The complete v7 source-memory single-addition audit found no useful candidate
among all sixty compatible fragments, including the sixteen previously untested
ones. Under those fixed memories, parents, tasks and budget, better ranking
alone cannot create a gain. That is narrower than concluding that library
learning is ineffective. Combined changes and other abstraction languages were
not evaluated.

Code inspection then found that the atom pool prunes pieces empty on any visible
example, although the task generator allows such pieces in valid concatenations.
A regression fixture demonstrates lost visible reachability. The next diagnostic
therefore separates filtered-space reachability, bounded-search success and
selection among the returned programs. It uses source tasks only and changes no
historical worker or final result.

## Primary literature checked in this turn

[Prospective Compression in Human Abstraction Learning](https://arxiv.org/abs/2605.09985),
May 11 abstract inspected. It studies human abstraction choices under evolving
task curricula and contrasts prospective reuse with retrospective compression.
Our inference is limited: frequency in previously solved programs need not be
the right target for future usefulness. Its behavioral result does not establish
a solution for our DSL, and neither methods nor code were reproduced here.

[TheoryCoder-2](https://arxiv.org/abs/2602.00929), January 31 abstract inspected.
It learns reusable abstractions from experience and integrates them with
hierarchical planning. This is relevant prior art for learned procedural
structure; our contiguous fragments are a narrower construction. Its reported
planning gains do not demonstrate that our proposer improves recursively.

[LAPS](https://arxiv.org/abs/2106.11053) was located through its abstract and
the authors' PMLR paper: it couples library and search-heuristic learning with
language supervision. No method-level implementation comparison was made in this
pass. Earlier Stitch/DreamCoder and September skill-learning checks remain in
`research-library-update-2026-09-16.md`.

## Measurement boundary

The original search retains many candidates internally but returns one by a
fixed cost ordering. A diagnostic can measure whether correct alternatives were
already found. Those deterministic, correlated candidate sets require a search
coverage metric, not the unbiased pass@k estimator used for IID neural samples.
An oracle-best-of-frontier gain would show available verified training data; it
would not show that a deployed first-choice solver became more accurate. Any
later distillation must control task weighting, training budget and retention,
then measure raw neural coverage on fresh tasks. Distillation remains untested.

## Completed diagnostic

The source-only measurement restored visible reachability for 112/576 tasks.
First-choice correctness rose from 357 to 401, and deterministic coverage@64
from 398 to 458. There were 21 first-choice regressions and 63.56% more primitive
charges despite equal expansion ceilings. The audit reexecuted all 1,152 searches.
The corrected frontier adds verified solutions for 57 tasks beyond first choice;
this is a training opportunity, not a measured neural gain or RSI. Fresh cost
curves and controlled frontier distillation are next. Full methods, costs and
limits: `search-diagnostic-results-2026-09-16.md`.
