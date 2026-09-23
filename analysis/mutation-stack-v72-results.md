# V72 counterexample-guided grow/delete/splice mutation

Status: audited two-seed result. V72 removes the predeclared `bit_reduce` and `bitmix` templates used in V71. After a visible failure, it evolves typed instruction fragments with grow, delete, reducer, modulus, and splice mutations. Candidate programs are retained by visible behavior signatures and evaluated on hidden outputs only after selection.

The held-out family contains XOR parity, bit-sum modulo five, and low-nibble bit-count modulo three mechanisms. No mechanism-family label or reduction template is passed to the mutation layer.

| Seed | Legacy development | Broad mutation development | Evolved development | Legacy admission | Broad admission | Evolved admission | Legacy final | Broad final | Evolved final |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026091981 | 0/24 | 23/24 | 23/24 | 0/24 | 18/24 | 18/24 | 0/24 | 19/24 | 19/24 |
| 2026091982 | 0/24 | 20/24 | 20/24 | 0/24 | 18/24 | 18/24 | 0/24 | 21/24 | 21/24 |

The evolved policy selected an eight-term budget with shortest-program ranking on both seeds. It passed admission and matched broad mutation on both fresh final banks. The result is partial transfer rather than the perfect V70 stack result, but it removes the explicit family templates and demonstrates reusable mutation-generated programs.

Both independent audits passed. Each replayed 216 evaluation rows and checked 20 sealed artifacts, for 432 rows and 40 artifacts across both replications. The audited archives are `runs/mutation-stack-v72-20261011/` and `runs/mutation-stack-v72-20261012/`.

## Interpretation

V72 is the strongest current test of open-endedness within the bounded instruction substrate. The system grows, deletes, and splices executable fragments in response to visible counterexamples; it is not merely selecting among a named operator catalog. The repeated eight-term solution is evidence that the useful representation is an emergent composition of primitive bit operations.

It remains bounded RSI evidence. The instruction vocabulary, typed-fragment grammar, mutation operators, population limits, visible target alignment, synthetic mechanisms, and admission protocol remain researcher-authored. The system has not yet invented new instruction semantics or its own mutation language.

## Next discriminating test

Let the mutation engine alter its own fragment grammar and instruction vocabulary under a protected execution sandbox, with a held-out instruction family and a minimum-description-length gate. Require a new primitive or macro to be created and transferred without adding a researcher-authored operation to the evaluator.
