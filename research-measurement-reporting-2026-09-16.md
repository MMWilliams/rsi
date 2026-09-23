# Measurement and reporting update — 16 September 2026

Targeted primary-source check while v9b runs. This changes report presentation
and provenance, not its frozen experiment, thresholds or metrics. No v9b final
scores were examined to make these decisions.

## What the source establishes

[NIST AI 800-3, February 2026](https://doi.org/10.6028/NIST.AI.800-3), especially
section 3.1 and Table 1, distinguishes expected performance on a fixed benchmark
from expected performance over a larger item population. A realized score is
an estimate, not either expectation itself. Their uncertainty calculations depend
on the target and assumptions about sampling. The report offers mixed models as
an additional method, not a universal requirement. The
[NIST announcement, updated March 18](https://www.nist.gov/news-events/news/2026/02/new-report-expanding-ai-evaluation-toolbox-statistical-models)
summarizes these distinctions and cautions against implicit assumptions.

Scope inspected: the report's definitions, section 3.1 discussion and summary
of uncertainty methods, plus the official announcement. This is not a replication
of its statistical experiments or an audit of every theorem.

## Consequences for this experiment — our design inferences

1. Report observed raw neural pass@k on the frozen final DSL bank. Broader
   generalization needs additional assumptions and independent bank replications.
   Task-template exclusions help separation but do not establish representativeness
   of research, cybersecurity, social-good or policy workloads.
2. The same final tasks recur across arms, checkpoints and seeds. Training seed
   also determines generation seed. Three seeds therefore do not yield three
   independent task populations or isolate training variance from sampling noise.
3. Preserve per-seed paired contrasts. Do not treat tasks times seeds times k
   values as independent observations. The pass@k curve reuses one sample set;
   at n=k=64, each task's estimator is a binary observed success indicator.
4. Keep the predeclared engineering advancement screen. It is not a significance
   test. This report adds no confidence interval derived from unvalidated
   independence assumptions and does not alter promotion decisions.
5. State why each admission decision occurred using its recorded rule and scores.
   Treat training-loss changes and gradient norms as observations, not explanations
   of weight-level mechanisms. Interpret the controlled arm contrasts at the
   pipeline level, with the retained task-distribution and compute limitations.

## Report-integrity finding and correction

The previous renderer trusted a stale passing audit and checked only results,
configuration and harvest hashes. A copied fixture with an extra fabricated
training-pool row still produced a report; the regression test initially failed
because the expected rejection did not happen. No real study archive was changed.

The renderer now requires a completed, nonfailed run, reexecutes the independent
auditor, and checks all sealed bytes before audit, after audit and before writing.
Its JSON stores a receipt, manifest/auditor/audit hashes, the complete evidence
hash mapping and the additional audit cost. Reports must be written outside the
sealed archive. This binds local provenance; it does not authenticate a hostile
host or replay neural optimization. Tests cover unchanged valid input, stale
audit state, a resealed forgery, a failed run and an output inside the archive.

Existing experimental sources remain frozen. The reporting repair is a
human-directed integrity improvement, not evidence of a better recursive improver.
