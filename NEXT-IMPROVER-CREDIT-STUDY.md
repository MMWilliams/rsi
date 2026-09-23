# Next improver-credit study — design requirements

Status: **proposed, not executed or preregistered**. Freeze task counts, seeds,
budgets and decision thresholds in a separate protocol before running it. This
does not amend the live v9b neural experiment.

## Evidence motivating the change

The [V5 credit diagnostic](analysis/descendant-credit-20260916.md) reconstructed
all historical credits and checked local selection sensitivity. Descendant
statistics were sparse and affected few recorded choices. Repeated operator
occurrences could receive the same later observation more than once, and later
rejected candidates also contributed. These are observational lineage statistics.
The diagnostic does not estimate an alternative policy's final performance.

## Hypothesis to test

An inherited estimate of an edit's effect on **later improvement**, measured with
paired counterfactual branches, can select more productive edits than immediate
gain alone. This is separate from the hypothesis that a richer searcher produces
better distillation targets, which v9b tests.

## Acquisition unit and paired branches

For a source parent state S and candidate edit e, record S and e(S). From each,
run the same predeclared downstream improvement policy with matched budgets and
fresh development/admission tasks. Keep model checkpoint, macro library, oracle,
edit catalog and randomness settings fixed between the branches except for e.
Archive every descendant request and actual cost, even if the initial edit or a
later candidate is rejected. Final evaluation must remain outside the branch
selection and memory update paths.

Separate two quantities on a common held-out *source measurement* bank:

- **Total descendant effect:** terminal quality from e(S) minus terminal quality
  from S. This includes the initial edit's immediate benefit.
- **Change in later improvement:** the terminal-minus-starting gain from e(S),
  minus the terminal-minus-starting gain from S. This distinguishes immediate
  quality from subsequent improvement and can differ in sign from total effect.

The source measurement bank may train inherited memory; it is not a final
holdout. Repeated measurements and reuse must be logged as adaptive development.
Report each branch pair as one dependent experimental unit, with identities for
parent state, edit occurrence, source batch and downstream policy. Operator names
alone cannot stand in for independent trials. Common seeds do not force paths
to stay identical after states diverge.

## Controls needed before an inheritance claim

1. Immediate-effect memory only.
2. Immediate effects plus the existing observational descendant statistic.
3. Immediate effects plus paired descendant estimates, keeping the two quantities
   above distinguishable rather than mixing them into one unnamed score.
4. Empty, scrambled and random-selection controls.

All conditions receive the same acquired source evidence and its full acquisition
cost. Controls intentionally ignore or permute specified fields; they do not get
less compute silently. Compare later inherited improvers from the same frozen
ancestor at equal downstream opportunities, and separately report total compute.
Use generation snapshots to distinguish better improvers from a better terminal
artifact. Hold evaluation banks outside inheritance and selection.

## Requirements before launch

- Check effect headroom on source-only data before fitting a predictor: an oracle
  selector over the tested edit menu supplies a ceiling, not a deployable result.
- Select the amplifier version explicitly. The historical V5 kernel and the
  validated corrected filter have different reachable programs; do not mix their
  labels or assume inheritance transfers between them.
- Predeclare how estimates and uncertainty enter selection. A positive-effect
  count and a signed improvement estimate answer different questions.
- Size the study using pilot variability at the branch/source unit. Do not count
  correlated ancestor credits, task examples or generated samples as independent
  source replications.
- Audit branch reconstruction and checkpoints, test swapped branch labels and
  duplicate-observation handling, and preserve failed attempts and zero effects.
- After component validation, reconnect validated choices to the interleaved
  amplify/verify/distill/self-modify loop and rerun coverage, common-ancestor and
  inheritance tests. No component result alone completes RSI.

## Related-work boundary

[Dream-RSI, September 14](https://arxiv.org/html/2609.14858v1), sections 2–4,
reuses recorded discovery trees to improve exploration policies. Its replay
cannot reveal unrecorded continuations. Our local score-removal diagnostic is
narrower: it does not even replay a full alternative policy. Proposed paired
branches would require new execution whenever states diverge. The paper is
relevant prior art, not evidence that this proposed credit estimator will work.
