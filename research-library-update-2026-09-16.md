# Library-learning comparison check, 2026-09-16

This note records what was actually read while designing v7. It is a targeted
primary-source check, not a complete priority search or reproduction.

## Established library learning

[Stitch, Top-Down Synthesis for Library Learning](https://arxiv.org/abs/2211.16605),
abstract inspected. It synthesizes DSL library functions from program corpora
using corpus-guided top-down search and evaluates compression against DreamCoder.
The corresponding [project repository](https://github.com/mlb2251/stitch) was
located but not audited. V7's contiguous two-/three-atom fragments are simpler
than parameterized abstractions; adding them to a search library is not a novel
algorithm merely because the solutions came from the system itself. We have
not reproduced the paper's performance or compression results.

## Recent skill construction

[Repo-To-Skill](https://arxiv.org/abs/2609.02749), September 2 abstract inspected.
The authors distill reusable operating knowledge from repositories and compare
skill-equipped research agents under a fixed downstream setup. Our inference:
this is relevant prior art for explicit reusable knowledge; a downstream gain
from adding skills alone does not answer whether the learned improver produces
a better descendant from the same initial solver. Acquisition cost also remains
a separate comparison. Full methods and code inspection are still open.

[SkillRevise v4](https://arxiv.org/html/2606.01139v4), revised September 3:
abstract, sections 3.2 and 5.4, and Appendix C's logging details inspected.
Its main seven-principle memory is manually consolidated and frozen; separate
domain studies build principle banks on calibration tasks and freeze them for
evaluation. Candidate records include selected/ignored principles, execution
anchors and operational costs. This is relevant to provenance and bounded
revision, but does not show our inherited fragment proposer improves. Its code
and reported gains have not been reproduced here. V7 was already running when
these additional sections were read; its protocol and behavior were not changed.

## Consequence for our experiment

V7 inherits a **proposal memory** while resetting the active solver configuration
and library in every arm. A remembered fragment must produce a measured gain
and pass a separate admission slice before installation. This separates a
better preloaded solver from a proposer that makes better changes under the
same downstream opportunity budget. It does not by itself prove recursive
compounding or novelty. The proposing algorithm remains fixed; only its memory
and the solver library grow. The source corpus comes from oracle-verified whole
solutions, while fragments are separately tested as solver changes.

The numerical-pair and frozen-library controls receive the same acquisition
charge and downstream query schedule. Composition-scrambled memory checks one
aspect of inherited structure, but collisions or useful surviving fragments can
weaken this control. Every such construction is logged. These are explicit
limits, not evidence that the intervention works.
