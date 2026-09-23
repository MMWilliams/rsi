# V13: framework sweep and findings program

Status: exploratory planning framework. The generated plan is not a set of
completed experiments and cannot be cited as observed evidence.

## Objective

Map the response surface of the RSI prototype across search, generation,
training, retention, curriculum, and controller variables. The goal is not to
maximize one lucky run; it is to identify robust mechanisms that survive fresh
banks, matched vector budgets, negative controls, and independent auditing.

## Variable families

The planner varies search budget and grammar depth; cost weights, widening and
macro discount; sample count and generation controls; LoRA steps, batch size,
anchor allocation and learning rate; replay mode; curriculum; bandit reward;
and program-search family. The complete declared space is in
`plan_research_sweep.py` and the generated plan in
`analysis/research-sweep-v13-plan.json`.

Continuous factors use a seeded Latin-hypercube design. Discrete factors can
be expanded into a factorial design for small screening studies. Every
variant receives a stable ID, full override record, hypothesis, metric list,
and status. A variant is not a finding until its run is sealed and audited.

## Frameworks to introduce

- ML: factorial ablations, multi-fidelity successive halving, Pareto model
  selection, and novelty-aware replay.
- RL: UCB1, Thompson sampling, contextual bandits, off-policy replay, and
  self-paced curriculum. Rewards must be defined before final scoring.
- AI: MCTS program search, novelty search, MAP-Elites archives,
  self-consistency and reflection proposals.
- CS: program synthesis, MDL complexity penalties, causal ablations,
  property-based tests and metamorphic tests.

The lightweight allocation and analysis primitives live in
`rsi/research_frameworks.py`. They are research controls around the existing
runner, not a claim that the prototype already implements full PPO, MCTS or a
general autonomous agent.

## Findings storage

`analysis/findings-ledger.json` stores the current evidence. Each finding has
a stable ID, status, scope, source, metrics, implication and confidence. The
ledger distinguishes observed, null, failed and planned work. Exploratory
discoveries must be independently replicated before they can be promoted to a
confirmatory claim in the paper.

## Execution order

1. Run cheap CPU screening and property/metamorphic tests.
2. Use multi-fidelity pruning to discard dominated configurations.
3. Run surviving neural variants with matched vector budgets and fresh bank
   groups.
4. Audit every completed archive and append only audited outcomes.
5. Re-run the top mechanisms on held-out template-disjoint banks.
6. Report the Pareto frontier: capability, diversity, cost, retention and
   robustness—not just the maximum pass@64.

Generate a 64-variant plan with:

```powershell
.\.venv\Scripts\python.exe plan_research_sweep.py --samples 64
```

