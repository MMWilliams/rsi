# Incremental verified-feedback update pilot

This is **development-only evidence** on six previously inspected 32-task banks. Each episode started from the frozen listwise-120 evaluator, acquired full candidate correctness labels from one bank, updated a copy, and tested it on the next bank. Across six episodes this used 30,676 additional candidate labels for 192 transfer decisions. The source checkpoint and target candidate pools were identical for every variant within an episode.

| Update from one feedback bank | Correct / 192 transfer tasks |
| --- | ---: |
| No update | **130** |
| All weights, 10 epochs, learning rate 0.0001 | 130 |
| All weights, 30 epochs, learning rate 0.0001 | 128 |
| All weights, 30 epochs, learning rate 0.0003 | 126 |
| Output head only, 30 epochs, learning rate 0.0003 | 129 |
| Scrambled feedback labels, 30 epochs, learning rate 0.0001 | 130 |
| Continue on original source labels, 30 epochs, learning rate 0.0001 | 131 |

The feedback bank was disjoint from the test bank within each episode. None of the update rules outperformed the fixed checkpoint in aggregate; the mild ten-epoch update tied, and scrambled feedback also tied. Continued source training gained one task without new labels. This does not support incremental evaluator growth from the new bank feedback, much less an improved improver. It suggests the current ranker is already stable under small updates and that the improvement loop should explore training objectives or architecture edits with protected admission tests instead of treating more gradient steps as progress.

The six banks and all their labels were already inspected before these rules were selected. This pilot did not use a fresh confirmation bank. Code: `incremental_ranker_feedback_development.py`. Machine-readable results: `analysis/incremental-ranker-feedback-development.json`.
