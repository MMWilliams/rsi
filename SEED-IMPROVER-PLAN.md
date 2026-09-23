# Seed improver research plan

Goal: identify and verify the strongest seed improver supported by comparisons of individual evaluator/improver methods, combinations, and feedback integrations. Preserve separate evidence for evaluator growth, improver growth from the same base, and growth of the combined loop. A universal optimum is not established by a finite experiment; report the best supported configuration, its comparison set, budget and limits.

## Completion evidence required

- Compare lexical, structural and behavioral evaluators separately, with ensembles and conservative baselines.
- Compare uniform feedback, uncertainty, disagreement, novelty and their combinations; measure verified evaluator gains per declared feedback budget.
- Compare unconditional replacement with admission-gated integration and retained earlier checkpoints.
- Test later improver knowledge against an initial improver on the same new bootstrap, feedback reservoir, budget and final bank. Include the best static strategy and scrambled knowledge.
- Test evaluator snapshots on identical candidate pools; use an external task oracle for the reported outcomes.
- Verify a positive feedback loop through multiple accepted updates, and distinguish it from one useful update or a static combination.
- Test randomized visible examples, mechanism shifts, retention and failures as separate cases; include fresh confirmation seeds selected before any outcome is inspected.
- Replay candidates, selections, label access, state inheritance and artifact hashes; document semantic-oracle limits and actual resource costs.
- Save a runnable seed configuration with the learned state and a report of the comparisons, uncertainty and remaining limitations.

Current evidence does not yet meet these requirements. The active goal remains open.

## Lessons driving the next search

The earlier feedback pilot's lexical representation collapsed correct and incorrect programs on 14/24 AST tasks. A development-only semantic evaluator now distinguishes candidates by predicate behavior on 256 unlabeled character probes. On the previously inspected AST banks it improves from 17/24 to 19/24 as feedback grows; a structural/behavioral ensemble moves from 12/24 to 19/24. Those are development observations, not confirmation.

Freshness correction: the old 60-task source archive has 46 unique visible-example sets; 25 tasks belong to repeated visible-example groups. The next generator samples visible examples independently from the same task mechanism and checks duplicate public inputs. New mechanism cases change arithmetic constants and remain a separate transfer test.

The source search will compare candidate judgment, feedback selection and integration separately before confirming a seed on fresh episodes. Preserve all negative arms. Admission outcomes may guide the improver but must not become final evidence.

Background: counterexample-guided synthesis separates candidate construction from verification feedback ([Solar-Lezama, Program sketching](https://link.springer.com/article/10.1007/s10009-012-0249-7)). Model selection requires evaluation outside the data used to select it ([scikit-learn nested cross-validation](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html)). These motivate the information boundaries here; they do not establish novelty or success of this implementation.
