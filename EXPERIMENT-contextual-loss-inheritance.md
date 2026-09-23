# Contextual evaluator-edit inheritance: frozen parent/child protocol

Frozen before generating seeds 902276–902287 on 2026-09-17.

Each of six independent episodes has a new 48-task parent bank and a separate 48-task child bank, with eight tasks per mechanism: transformation, AST, novel operator, stack, mutation, and self-edit. For each bank, the first 24 tasks (four per family) are admission feedback and the final 24 are the policy outcome. Each task has one visible example, eight unused probe inputs, 15 final examples, and the same two family-specific candidate sources capped at 128 each. All policies see identical candidate pools and use zero inference oracle output queries.

The common edit catalog is the three already trained 120-epoch listwise rankers at loss temperatures 0.25, 0.5, and 1.0. All use the same 31,500 source candidate labels. The improver chooses one temperature **per public task family** using verified top-choice success counts. Ties prefer 0.25, then 0.5, then 1.0. Compare:

- Empty parent: zero prior counts, then the same live feedback.
- Inherited parent: the previous audited six-family transfer's 48 outcomes per family and edit, discounted to eight effective tasks per family, then the same live feedback. Historical acquisition cost is separate.
- Scrambled parent: the same inherited row totals assigned to the wrong family by a frozen cyclic permutation, then the same live feedback.
- Fixed controls: always 0.25, always 0.5, always 1.0, and the fixed per-family best temperature from the inspected prior bank.

All three catalog choices are verified on identical parent admission tasks before parent final choices are frozen. After freezing parent choices, all parent final outcomes are verified and update each policy's family table. All three choices on child admission tasks then update the tables; child final choices are frozen before child final labels are opened. Every policy receives the same live labels and candidate/training budgets. Report distinct selected-program oracle evaluations and the extra historical cost of inheritance.

Primary endpoint: inherited minus empty **child final top-choice correctness**, paired by six episodes. Promote a growing contextual improver only if inherited wins at least five of six child banks, the exact six-bank resampling 95% interval is strictly positive, and its aggregate exceeds scrambled inheritance and the strongest fixed contextual control. Report parent final, child final, per-family results, candidate reachability, and AST reachability separately. A parent gain alone is not child growth; a fixed context map tie is not an improver advantage.

Freeze common model choices before feedback, parent policy choices before parent final labels, and child choices before child final labels. Require independent reconstruction of tasks, pools, model choices, all policy updates and final outcomes. This is a synthetic finite-example test within a fixed edit catalog; it does not show new edit-type creation or unrestricted RSI.
