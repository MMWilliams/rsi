# V6: source-only contextual edit-effect diagnostic

Written 2026-09-16 before fitting this diagnostic. This is an exploratory
analysis plan: v4/v5 aggregate source results have already been inspected. It is
not a blind preregistration or a new online RSI experiment.

## Question and boundary

Can visible task examples and current search settings predict which existing
edit will help on a held-out source trajectory? Use only the balanced source
development evaluations from audited v4 and v5. No transfer, admission or final
outcome is a training label. Never open protected banks or final results in this
analysis. Journals contain other events; discard them before extracting data.

The expected data are nine sources, six menus per source, twelve edits per menu
and sixteen tasks per menu: 864 task contexts / 10,368 task-edit observations.
Each label is candidate oracle correctness minus parent correctness, in
{-1, 0, 1}. This reuses prior independently audited labels; it does not query the
oracle. Task IDs and generation/source IDs are metadata, never model features.

## Features and models

Use these fixed visible-example statistics: mean and standard deviation of
input/output lengths; mean output/input length ratio; fractions with output a
substring, prefix, suffix, exact copy, or case-insensitive substring of input;
whether all visible outputs agree; input/output fractions of uppercase letters,
digits, whitespace and non-alphanumeric non-whitespace characters; mean
input/output whitespace-delimited token counts. Length/token features divide by
32/8 respectively. Add the eight current search settings normalized by their
existing bounds. No generated program, solver trace, hidden example, reference
program, oracle parent correctness or literal token identity enters features.

Compare zero predictions, unconditional per-edit means, parent-only ridge,
visible-plus-parent ridge, and scrambled-visible-plus-parent ridge. Each ridge
has separate coefficients per edit and an unpenalized intercept. Standardize
using training rows only; constant columns get scale one. Scramble whole visible
feature vectors among training task contexts, using the same permutation across
all edits and leaving parent settings and labels intact. Validation/test context
stays real. Deterministic permutation seed is derived from ordered training IDs.

Leave one entire source out for each of nine outer folds. Within each outer
training set, leave one entire training source out to choose ridge alpha from
{1, 10, 100, 1000}, minimizing mean task-edit squared error; ties choose the
larger alpha. Refit on all outer training sources. All preprocessing and
scrambling repeat inside each inner training fold. The same tasks under all
twelve edits stay together. Structural templates can overlap within an archived
source-development split: this measures source transfer, not unseen-template
generalization. No tuning after inspecting outer results.

## Outcomes and advancement rule

Report task-edit MSE, MAE and nonzero-label MSE (sparse signals make the zero
baseline strong). For each held-out sixteen-task menu, average predicted gain
per edit and select the top two, descending score then ascending lexical name.
Utility is max(0, observed mean gain of either selected edit). The zero term is
the option to keep the parent. This is an offline proposal-ranking utility,
not admitted improvement, final accuracy or a simulated recursive trajectory.
Also report exact uniform-random two-edit expected utility over all 66 pairs
and the best-of-all-twelve oracle ceiling. Source means get equal weight.

Advance this particular predictor to a fresh online trial only if contextual
ridge has lower MSE than unconditional means, higher mean ranking utility than
unconditional means, parent-only and scrambled context, and strictly beats
unconditional means on ranking utility in at least five of nine sources. This
is a practical exploratory screen, not a statistical significance test. Report
all comparisons even on failure; do not change the features/grid to rescue it.

## Evidence and interpretation

Archive the sanitized dataset, features, folds, predictions, hyperparameter
scores, scaling, coefficients, permutation indices, selected edits and source
metrics. Hash inputs/code/plan and append durable timestamped run events. Refuse
to overwrite an existing run. Independently reconstruct regression arithmetic,
fold boundaries, nested selection and ranking metrics in an audit. Preserve
failed runs. No neural training, new search evaluations or paid model calls.

This tests one additive linear model with basic visible features. Failure does
not rule out nonlinear context, richer edits, larger calibration or RSI. Success
does not establish causal online benefit; subsequent states and admission
outcomes for all counterfactual edits were not observed. Acquisition costs belong
to the prior runs and must be charged in any later compute comparison.

## Research basis

[Hutter et al.](https://arxiv.org/abs/1211.0906) study empirical performance
models using instance features and algorithm settings. Our signed coverage-change
target differs from their runtime prediction; context-based selection is not a
novelty claim. [S3Gym](https://arxiv.org/html/2608.31100v1), read through its
August 31 version, reports that successful feedback need not become transferable
improvement and that useful memory depends on task structure. These motivate a
measured diagnostic; neither establishes that this model will work here.
