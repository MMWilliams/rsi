# V71 raw-instruction stack discovery

Status: audited two-seed result. V71 removes V70's generic `fold_bits` instruction. The proposer constructs reductions explicitly from repeated ordinal loads, single-bit masks, shifts to bit zero, XOR/add reducers, modulo, and raw shift/or bit mixing. A failure-triggered evolutionary selector chooses between `bit_reduce` and `bitmix` families.

The held-out bank contains raw XOR parity, raw bit-sum modulo four, and raw splice modulo seven mechanisms. No named fold or popcount constructor is available to the proposer.

| Seed | Legacy development | Broad raw development | Evolved development | Legacy admission | Broad admission | Evolved admission | Legacy final | Broad final | Evolved final |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026091971 | 0/24 | 21/24 | 21/24 | 0/24 | 19/24 | 19/24 | 0/24 | 19/24 | 19/24 |
| 2026091972 | 0/24 | 20/24 | 20/24 | 0/24 | 18/24 | 18/24 | 0/24 | 21/24 | 21/24 |

Both evolved systems passed admission and matched broad raw synthesis. Both retained the full two-family raw basis, unlike V70's fold-only specialization. This is a partial but reproducible gain after removing the generic fold abstraction.

Both independent audits passed. Each replayed 216 evaluation rows and checked 20 sealed artifacts, for 432 rows and 40 artifacts across both replications. The audited archives are `runs/raw-stack-v71-20261009/` and `runs/raw-stack-v71-20261010/`.

## Interpretation

V71 strengthens the V70 result: the useful bit-reduction behavior remains discoverable when `fold_bits` is absent, using only repeated primitive stack instructions. The lower score than V70 shows the cost of removing the abstraction: raw synthesis is less expressive or less sample-efficient, and the evolved selector cannot yet compress the two raw families.

This remains bounded RSI evidence. The raw instruction vocabulary, template enumeration, mutation policy, visible target alignment, synthetic mechanisms, and admission protocol remain authored. The system does not yet invent its own instruction semantics or mutation language.

## Next discriminating test

Allow mutation over raw instruction sequences—not only selection between two researcher-defined families—and use counterexample-guided search to grow, delete, and splice instructions under a fixed execution budget. Test whether the system can discover a new reduction family without a predeclared `bit_reduce` template.
