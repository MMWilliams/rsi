# V66 self-describing AST proposer

Status: audited two-seed result. V66 replaces V65's named transform catalog with a typed AST proposer. It searches generic arithmetic ASTs, indexes equivalent observed behavior signatures, and retains executable predicates that explain visible examples. The held-out bank uses two affine-fold mechanisms with different constants; neither mechanism name is exposed to the proposer.

| Representation | Seed 39 final | Seed 40 final |
| --- | ---: | ---: |
| Baseline | 0/24 | 0/24 |
| Previous universal ordinal grammar | 0/24 | 0/24 |
| V65 primitive catalog | 0/24 | 0/24 |
| Self-describing AST proposer | 19/24 | 22/24 |

The AST proposer reached 22/24 and 20/24 on development/admission for seed 39, and 20/24 and 20/24 for seed 40. It was selected on both seeds. The remaining final errors are preserved as evidence of incomplete generalization rather than removed through task filtering.

Both independent audits passed. Each replayed 288 evaluation rows and checked 25 sealed artifacts, for 576 rows and 50 artifacts across the two replications. The audited archives are `runs/ast-v66-20260929/` and `runs/ast-v66-20260930/`.

## Interpretation

This is the strongest current evidence that the system can synthesize a new executable substrate from a generic typed AST rather than choosing among pre-authored transform families. V65's catalog could not solve this affine-fold bank, while the AST proposer discovered compositions involving multiplication, addition, division, and modulus.

It is still bounded recursive improvement, not open-ended RSI. The AST operations, constant bounds, behavior-signature retention policy, coherence/novelty priors, visible target alignment, and synthetic generator remain researcher-authored. The proposer improves the hypothesis language within an engineered meta-language; it does not yet rewrite and validate its own proposal machinery.

## Next discriminating test

Make the AST proposer itself mutable: generate alternative grammars, retention policies, and cost functions from failure traces; run them through held-out admission; retain only changes that replicate across new mechanism families. The next gate should require improvement in the proposer’s own transfer score, not merely a larger candidate pool.

The earlier XOR pilot remains excluded from the claim because visible examples admitted many equally consistent ASTs; that failure is a useful identifiability boundary, not a positive result.
