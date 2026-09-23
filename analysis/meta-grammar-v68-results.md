# V68 meta-evolution of the AST grammar architecture

Status: audited two-seed null result. V68 evolved the executable sub-grammar of the V66/V67 AST proposer. Each architecture genome selected enabled numeric operators, a maximum retained expression complexity, and a structural ranking mode. The candidate bank was generated once by the fixed superset grammar; evolution saw correctness only on development. An evolved architecture had to match or beat the frozen V67 scorer on admission before final evaluation.

| Seed | Frozen development | Evolved development | Frozen admission | Evolved admission | Frozen final | Evolved final | Selected |
|---|---:|---:|---:|---:|---:|---:|---|
| 2026091943 | 12/24 | 12/24 | 17/24 | 17/24 | 18/24 | 18/24 | frozen |
| 2026091944 | 21/24 | 21/24 | 19/24 | 19/24 | 16/24 | 16/24 | frozen |

Both evolved architectures passed the admission eligibility condition, but neither improved development or final performance. The gate therefore retained the frozen architecture on both seeds. The evolved architecture converged to a smaller operator set (`add`, `div`, `mod`, `mul`, `not`) with shortest-program ranking, but that structural simplification had no transfer benefit on this affine-transition family.

Both independent audits passed. Each replayed 144 evaluation rows and checked 18 sealed artifacts, for 288 rows and 36 artifacts across the two replications. The audited archives are `runs/meta-grammar-v68-20261003/` and `runs/meta-grammar-v68-20261004/`.

## Interpretation

V68 is a useful boundary result for recursive improvement. Evolving which operators are available and how expression complexity is retained was not sufficient to improve an already capable typed AST proposer. V67's policy-level evolution remains the positive result; V68 shows that a larger mutation surface does not automatically produce a better improver.

This does not establish that architecture evolution is ineffective in general. The candidate-bank superset, operator vocabulary, mutation operators, ranking modes, visible supervision, admission protocol, and synthetic affine domain remain researcher-authored. The architecture could not invent operators outside the protected superset, and the experiment did not test mechanism families withheld from that superset.

## Next discriminating test

Move the mutation boundary outward: let the improver mutate the AST generator's constant/constructor grammar or propose a new typed operator from failure signatures, then test on a mechanism family whose constructor is absent from the mutation catalog. Keep the admission gate and independent replay, and pre-register compute limits because V68's full synthesis/replay cost was about ten minutes per archive.
