# Sharp-ranker transfer to withheld task mechanisms

Frozen before generating seeds 902270–902275 on 2026-09-17.

The temperature-0.25 and 1.0 listwise rankers and E192 classifier were trained on only stack, mutation, and self-edit transition tasks. Test them without additional labels or training on those three known mechanisms plus transformation, AST, and novel-operator transitions, which were withheld from this evaluator-training study. Each of six new banks has 48 tasks, cycling evenly through all six families (eight per family per bank). Use one visible example, eight unused probe inputs, 15 final examples, and the same two family-specific candidate sources capped at 128 each. All evaluators see identical candidate pools and make zero oracle output queries.

Primary endpoint: temperature 0.25 minus temperature 1.0 top-choice correctness on the 144 tasks from the three withheld families, paired by six bank seeds. To extend the evaluator-growth claim to withheld mechanisms, require positive differences on at least five of six banks, a strictly positive exact six-bank resampling 95% interval, and positive aggregate differences in each withheld family. Also report known-family and overall results, E192, the temperature-0.5 intermediate, first-generated and shortest-program controls, candidate reachability, and source training/optimization costs. A known-family win cannot substitute for a withheld-family win.

Freeze all candidate pools and evaluator choices before opening final labels. An independent audit must regenerate tasks, candidate pools, model choices and final outcomes. This test measures finite-example correctness on synthetic mechanism shifts, not universal equivalence or improver growth.
