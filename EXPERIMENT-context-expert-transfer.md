# Public-context evaluator expert transfer: frozen protocol

Frozen before generating seeds 902222–902227 on 2026-09-17.

The global E192 classifier, three public Unicode-block experts, and their
equal-weight blend are frozen in `analysis/context-expert-evaluator-development.json`.
All were trained from the same 31,500 verified candidate labels on 192 source
tasks. The blend uses the block of the task's one visible input to choose
an expert; no host family label or final example enters that choice. It
averages global and expert structural weights at 0.5 each. Development scores
on already inspected banks were: A global99/blend98; B global102/blend112;
later router banks global95/blend115. These are selection evidence only.

Six fresh 32-task banks cycle stack, mutation, and self-edit mechanisms, one
visible example, 23 hidden examples (eight unused probe inputs and 15 final
scoring examples). Candidate sources/caps stay fixed at 128 per source.
Each evaluator sees exactly the same pool and makes zero oracle-output
queries. Freeze all indices before opening final labels. Controls are E192,
pure context expert, the frozen E192/pairwise router, and its equal-weight
component combination. Candidate reachability is reported separately.

Primary endpoint: blended expert minus global E192 correct top choices on all
15 final examples, paired by task and bank. Promote the blend as a supported
evaluator component only if it wins at least five of six banks, its six-bank
resampling 95% interval is positive, and it beats the strongest feasible
control in aggregate. Report source-label and inference costs. A positive
result remains scoped to this synthetic distribution and does not establish
improver or child-improver growth.

Preparation saves candidate pools, model outputs, and choices. Scoring and an
independent reconstruction audit occur afterward. Local files do not provide
an independent host access-control boundary.
