# V39 MDL/BPE macro grammar induction

Status: audited fresh-bank null. V39 replaces the hand-selected fragment-length/frequency library rule with an MDL-style byte-pair grammar learner. It mines merges from the system’s own oracle-verified active CEGIS trajectories and uses the learned merges as width-one macros.

| Arm | Development | Admission | Fresh final |
| --- | ---: | ---: | ---: |
| Control | 13/24 | 14/24 | 16/24 |
| BPE macro grammar | 15/24 | 15/24 | 16/24 |

The BPE learner discovered five merges and improved development/admission scores, but tied control on the fresh bank. This isolates a remaining failure mode: corpus compression can produce reusable-looking grammar rules without reliable cross-bank semantic transfer.

The archive passed independent replay: 144 evaluations, 24 verified training programs, and 25 sealed artifacts were checked. Limitations include the base AST-shape vocabulary, oracle-dependent training, fixed width constraints, and small banks. This is not proof of RSI.

Artifact: `runs/bpe-macro-v39-20260917/`.
