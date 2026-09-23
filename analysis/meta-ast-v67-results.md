# V67 meta-evolution of the AST proposer

Status: audited two-seed result. V67 evolves the AST proposer's own ranking genome over visible candidate features (`div`, `mul`, `xor`, `mask`, `shr`, negation, and program length). A development-selected genome must pass an admission gate against the frozen V66 scorer before it is used on the fresh final bank.

| Policy | Seed 41 final | Seed 42 final |
| --- | ---: | ---: |
| Frozen V66 scorer | 15/24 | 17/24 |
| Evolved scorer | 18/24 | 22/24 |

The evolved scorer improved development from 19/24 to 23/24 and admission from 15/24 to 20/24 on seed 41. On seed 42 it improved development from 19/24 to 21/24 and admission from 16/24 to 18/24. It was retained and selected on both seeds.

Both independent audits passed. Each replayed 216 evaluation rows and checked 19 sealed artifacts, for 432 rows and 38 artifacts across the two replications. The audited archives are `runs/meta-ast-v67-20261001/` and `runs/meta-ast-v67-20261002/`.

## Interpretation

This is the first current result where the improver’s own selection policy changes through an evolutionary loop, passes a held-out admission gate, and transfers to a fresh final bank. The retained change is not a new task predicate; it is a learned scoring policy over the proposer’s AST candidates, which is closer to recursive improvement of the improver itself.

It remains bounded RSI evidence, not proof of open-ended RSI. The mutation operators, feature vocabulary, AST primitives, candidate generator, oracle-labeled development/admission protocol, and synthetic domain are researcher-authored. The evolved object is a policy genome, not the full system architecture or learning machinery.

## Next discriminating test

Evolve the candidate grammar and proposer architecture—not only its linear scoring weights—using source-level mutations, neural proposal priors, and compute-matched admission. Require the evolved proposer to create a new primitive and improve on mechanism families withheld from both its development and mutation catalog.
