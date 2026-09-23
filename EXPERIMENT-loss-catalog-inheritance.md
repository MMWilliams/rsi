# Inherited evaluator-edit knowledge: parent and child policy transfer

Frozen before generating seeds 902240–902251 on 2026-09-17.

## Common base and edit catalog

Every policy starts with the same three already trained 120-epoch evaluator checkpoints at listwise loss temperatures 1.0, 0.5, and 0.25. They used the same 31,500 source candidate labels and candidate-generation system. Each task has one visible example, two candidate sources capped at 128 each, eight unused probe inputs, and 15 final examples. No inference-time output query is used. For six independent episodes, assign one 32-task bank as the parent bank and the following 32-task bank as the child bank: (902240, 902241), ..., (902250, 902251). The first 16 tasks of each bank provide admission feedback; the final 16 are the policy-choice outcome.

## Improver checkpoints and feedback

The edit policy scores each catalog evaluator's chosen program on the same verified admission tasks and selects the temperature with the largest accumulated success count; ties prefer the base 1.0, then 0.5, then 0.25. Each policy receives the same admission labels and makes one catalog choice per bank. Parent final choices are frozen before parent final oracle outcomes are read. After that parent bank is fully verified, all three catalog outcome counts from its 32 tasks update the policy table. Child admission choices are then verified and child final choices frozen before child final labels are read.

- **Empty parent I0:** starts with no prior edit-effect counts.
- **Inherited parent I1:** carries outcomes from the previously completed six-bank temperature transfer, discounted to the equivalent of 64 tasks. The source prior scores were 130/192 (1.0), 137/192 (0.5), 143/192 (0.25). The full 192-task acquisition cost is reported separately.
- **Scrambled inheritance:** same prior values and size, cyclically assigned to wrong temperature names, then receives identical live feedback.
- **Fixed controls:** always choose temperature 1.0, 0.5, or 0.25.

All policies evaluate the same three selected candidate programs on the same admission tasks; identical programs share an oracle evaluation. Parent-bank final outcomes for all three catalog arms are charged as feedback for the child update. The source 31,500 labels and three trained models are common costs. Report distinct program evaluations, example executions, candidate generation, policy compute, and inherited prior acquisition separately.

## Primary and secondary endpoints

Primary: child final top-choice correctness, inherited I1 minus empty I0, paired by episode. A supported inherited-improver upgrade requires positive differences on at least five of six independent child banks, a strictly positive exact six-bank resampling 95% interval, more correct choices than scrambled inheritance, and more than the strongest fixed temperature in aggregate. Parent final accuracy and selection regret against the best available catalog edit are secondary. Report any tie with a fixed policy plainly.

All task pools and three evaluator choices must be frozen before feedback; the parent/child policy choice journal must be frozen before the respective final labels. An independent audit must regenerate pools, decisions, admission choices, table updates, and final outcomes. This tests inheritance within a fixed edit catalog, not creation of novel edit types or unrestricted recursive intelligence.
