# Sharper listwise loss: frozen transfer protocol

Frozen before generating seeds 902234–902239 on 2026-09-17.

## Edit

Use the same 192 source tasks, 31,500 exact-verifier candidate labels, 175→32→1 model, initialization seed, optimizer, learning rate, weight decay, and 120 epochs as the prior listwise-120 evaluator. Change only the listwise loss temperature from 1.0 to 0.25: `T × (logsumexp(all_scores/T) - logsumexp(correct_scores/T))`. This emphasizes the candidates competing for the top choice. The checkpoint and normalization in `analysis/temperature-ranker-development.json` are frozen; development selection used already inspected bank scores of 149/192 versus temperature 1.0's 130/192. Temperature 0.5 is a frozen intermediate control.

## Fresh bank and controls

Use six untouched 32-task banks, seeds 902234–902239, with stack, mutation, and self-edit mechanisms, one visible example, eight unused probe inputs, and 15 final examples. Candidate sources/caps and zero inference oracle queries match the prior listwise transfer. Compare on identical candidate pools: temperature 0.25 at 120 epochs (primary), 0.25 at 80 epochs, 0.5 at 120, 1.0 at 120, E192, public-context expert, 50/50 context blend, and available pairwise/router controls. Freeze all choices before final labels are scored.

The primary endpoint is temperature 0.25 minus temperature 1.0 top-choice correctness. Promote as a supported evaluator edit only if it wins at least five of six banks, the exact six-bank resampling 95% interval is strictly positive, and its aggregate correctness exceeds every other tested control. Report reachability, mechanism-specific gains, label and optimization costs, and any negative transfer. A narrower positive result may be reported without promotion.

Prepare/score separation, source and runner hashes, and an independent reconstruction audit are required. This is a synthetic finite-example evaluator test; a better evaluator is not yet an improved improver. The final-label separation is an auditable code boundary, not independent host access control.
