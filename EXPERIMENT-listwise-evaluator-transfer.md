# Nonlinear listwise evaluator transfer: frozen protocol

Frozen before generating seeds 902228–902233 on 2026-09-17.

## Edit and controls

The candidate edit replaces E192's independent-candidate logistic classifier
with a task-level listwise ranker: a 175→32→1 ReLU model. For each training
task with both correct and incorrect candidates, the loss is the log sum of
all candidate score exponentials minus the log sum over verified correct
candidate exponentials. It uses the same 31,500 source candidate labels as
E192, no additional oracle feedback, but substantially more GPU training.
Source label acquisition and optimization time are charged separately.

The 120-epoch checkpoint in `analysis/listwise-evaluator-development-v2.json`
was selected after development scores on two inspected 192-task banks:
119 and 134 correct versus E192's 99 and 102. Earlier 40- and 80-epoch
checkpoints are fixed controls for the learning curve. The global E192
classifier, pure public-context experts, and their 50/50 blend are additional
controls, each on identical candidate pools.

## Fresh test and growth gate

Six untouched 32-task banks, seeds 902228–902233, cycle stack, mutation, and
self-edit mechanisms. Each has one visible example, eight unused probe
inputs, and 15 final scoring examples. Candidate sources/caps remain the
same as earlier mixed tests (two sources, 128 each). All choices are frozen
before final labels are opened; no oracle output query is used at inference.

Primary endpoint: 120-epoch listwise minus E192 top-choice correctness,
paired by task and bank. A supported evaluator upgrade requires wins on at
least five of six banks, a positive six-bank resampling 95% interval, and
more correct choices than the strongest feasible control in aggregate.
Report reachability, per-family scores, inference time, source labels, and
GPU training time. Checkpoints 40/80/120 show whether the training edit
actually improved incrementally; monotonicity is measured, not assumed.

This is a synthetic finite-example result. A stronger evaluator is not by
itself a better improver or recursive intelligence growth. The final files
are local and the oracle is separated by auditable prepare/score code flow,
not independent host access control.
