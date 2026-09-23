# Sequential AST output feedback and child-improver transfer

Frozen before new admission and transfer labels on 2026-09-18. All tasks are synthetic string-program AST tasks. The generator is V67/V73 cap 512, the candidate ranker is the frozen replay AST specialist, and each task has eight initially unlabeled output-probe inputs plus fifteen final examples. The external oracle owns true outputs and final correctness.

## Decision rules and source

A static ridge-10 allocator predicts first- and second-query value from public examples, rank scores and candidate-predicted probe outputs, then commits all eight calls per eight-task bank. The proposed sequential rule uses the same first-query model. After it buys a first output, it measures the surviving candidate set and predicted second-probe ambiguity, then uses a separately trained ridge-10 model for the second-query value. At every step it buys the highest predicted next marginal value until eight calls are spent, with at most two per task. It may read a true output only after buying that query; it never reads final correctness while allocating.

On 384 already inspected tasks, leave-one-bank-out development scored sequential conditional 139, prior-only sequential 134, static ridge 135 and one-each 126, each at 384 calls. This is model selection/development evidence, not confirmation. Model structure, penalty 10, features, tie-breaking and query selector are frozen here.

P0 learns from those 384 tasks. P1 adds the 144 already inspected tasks from the contextual AST improver's admission and transfer, for 528 source tasks. Scrambled P1 mispairs the 144 additional task-effect triples within stream while keeping their feature rows. Duplicate P1 uses 144 repeated P0 rows. P1's extra historical acquisition is 288 probe outputs plus final correctness labels and candidate work. Every arm uses the same frozen solver/ranker/pool and exactly eight live query calls per bank. Prior-only sequential P1, static ridge P0/P1, one-each, random, high entropy and high disagreement are controls.

## Protected sequence

1. Freeze all four parent models. Admission uses three mixed eight-task AST subsets (seeds 902384–902386, generated from full 48-task mixed banks) and three AST-only eight-task banks (902387–902389). The parent policies make eight sequential calls per bank. For a common child-training set, collect both probe outputs and all 0/1/2 final correctness outcomes on all 48 tasks: 96 shared acquisition calls plus final-label work.
2. Apply the identical ridge-10 training rule to each parent's source table plus those 48 new verified rows. Admit the conditional P1 child as a replacement for fixed one-each only if its **parent** beats one-each by at least three correct tasks on admission, improves at least two banks, and loses no more than one. Freeze this choice before transfer. Raw child results are still scored whether admitted or not.
3. Transfer uses six mixed eight-task AST subsets (902390–902395) and six AST-only eight-task banks (902396–902401). Freeze task pools, rank scores, model weights, first probe and static allocations before any true outputs. Sequential policies reveal outputs only as purchased. Every arm spends exactly 96 logical calls over the 96 tasks.

Primary recursive endpoint: conditional P1 child minus conditional P0 child final correct choices across transfer banks. Require at least eight positive paired banks and an exact bank-bootstrap 95% interval lower bound above zero. For promotion, the protected P1 child must beat the strongest fixed 96-call control and the scrambled/duplicate children. Separately test conditional P1 child against prior-only sequential P1 and static ridge P1 at identical calls. Report parent-on-transfer diagnostics, child-minus-parent, reachability, candidate evaluations, predicted output cells, live/acquisition calls and per-bank traces. A positive result would be scoped fixed-design improver growth, not evidence of self-generated edit types or general RSI.

An independent audit must regenerate pools and candidate outputs, retrain models, replay every sequential action and final label, and confirm the gates and summaries.
