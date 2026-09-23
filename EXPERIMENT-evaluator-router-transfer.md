# Two-evaluator router transfer: frozen protocol

Frozen before new banks on 2026-09-17. This tests whether verified feedback
can improve the evaluator by combining two previously measured components.
It does not test whether a later improver creates a stronger improver.

## Frozen components and learned state

- Structural classifier E192 and random-pairwise ranker are frozen in
  `analysis/pairwise-evaluator-development.json`. Both use the same 31,500
  source candidate labels; pairwise training constructs 9,664 comparisons
  without new oracle labels.
- The router in `analysis/evaluator-router-frozen.json` was trained on 384
  inspected tasks from two earlier target episodes. Only 73 tasks on which
  the two evaluators differed in correctness trained the router. It sees
  candidate count and each evaluator's top probability and top-two margin;
  it cannot see task reference rules or final labels at inference time.
- Whole-episode development transfer: A-to-B router 107 versus E192 102/192;
  B-to-A router 99 versus E192 99/192. These are development findings.

## Fresh test

Six fresh 32-task banks, seeds 902216–902221, cycle stack, mutation, and
self-edit mechanisms. Each has one visible example, eight unused probe inputs,
and 15 final examples. Candidate sources and 128-per-source caps are those
of the prior mixed-mechanism tests. All evaluators see identical pools and
make zero oracle-output queries. Freeze choices for E192, pairwise, their
equal-weight combination, the learned router, higher-margin routing, and a
deterministic random router before opening final labels. Candidate
reachability and oracle union of the two base decisions are diagnostic only.

Primary endpoint: learned-router minus E192 top-choice correctness on all
15 final examples, paired by task and bank. The retained-evaluator growth
screen requires positive gain on at least five of six banks, a positive
six-bank resampling 95% interval, and superiority to the strongest other
feasible control in aggregate. Report Brier only for the component models;
the router's selection score is not a calibrated probability. Charge the
384-task router feedback acquisition and both component-training costs.

Prepare saves candidate pools and every model/router decision; a separate
score stage opens final labels. Audit reconstructs the decisions and labels.
The local file boundary is code-flow protection, not independent host access
control. These synthetic tasks and finite examples do not establish broad
intelligence growth.
