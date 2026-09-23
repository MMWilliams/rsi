# Search coverage diagnostic — 2026-09-16

## Decision

A real search-space defect has been isolated and corrected in an experimental
kernel. Source-task accuracy and coverage improved, with regressions and higher
operation costs. Advance to fresh, prospective validation with cost curves.
This is a human-directed amplifier repair, not demonstrated recursive improvement.

The mission remains RSI for research, cybersecurity, social good and policy.
These string-program results establish no capability in those application domains.

## Why the experiment changed

V7's fragment proposals produced no verified gains. The subsequent cheaper-route
repair restored lost search paths but changed no source-task correctness. We then
tested every compatible single-fragment addition available in the source memories:
60 candidates across 36 parent menus, including 16 previously unselected.
Every candidate had zero correctness effect. Better ranking alone cannot rescue
this fixed candidate set at this budget. Combined additions and richer libraries
remain untested.

`fragment-headroom-20260916-v7` completed in 9.65 seconds. Its independent audit
reconstructed candidate completeness and regraded 1,536 outputs: 1,120 reused
only after exact request/dependency checks, plus 416 newly executed with exact
replays. It does not independently rerun every cached search.

Inspection then identified a different limitation: the old atom filter rejected
a program piece if it produced an empty string on even one visible example.
Valid concatenations can require such pieces. The corrected pool retains pieces
that are empty on some examples, while dropping those empty on all examples.
The position vocabulary already matches the generator; expanding position bounds
was not needed to fix this defect.

## Controlled comparison

Protocol: `PARTIAL-EMPTY-DIAGNOSTIC.md`, written before measurement.
Run: `runs/partial-empty-20260916-v8-diagnostic/`.

- 576 archived source-development tasks, six source groups and 36 parent requests.
- Same parent configurations, common macros, maximum four primitive atoms and
  128-expansion ceiling in both arms; both use cheaper-route reopening.
- Search receives only the three visible examples. Grading follows completed
  search and checks those examples plus 13 hidden examples.
- Each arm records an exact replay and a unique, cost-ordered frontier of up to
  64 programs. The baseline is additionally checked against the prior kernel.
- Exact dynamic programming separately checks whether any visible-fitting
  program exists in the filtered pool within the atom limit.
- No transfer, admission or final-bank queries; no neural training.

## Results

All counts below are tasks out of 576. Coverage@k means at least one verified
program among the first k deterministic search results. It is not IID neural
pass@k and does not imply that the first-choice solver selects that program.

| Measure | Original filter | Partially empty pieces allowed |
| --- | ---: | ---: |
| Visible solution exists within filtered space | 464 | 576 |
| Search finds a visible-fitting result | 433 | 496 |
| First-choice verified correct / coverage@1 | 357 (61.98%) | 401 (69.62%) |
| Coverage@4 | 386 | 444 |
| Coverage@16 | 396 | 456 |
| Coverage@64 | 398 (69.10%) | 458 (79.51%) |
| Reachable but search misses visible solution | 31 | 80 |
| Visible-fitting first choice fails hidden examples | 76 | 95 |

The correction restores visible reachability for 112 tasks, with none lost.
First-choice correctness improves by 7.64 percentage points: 65 wins and 21
losses. Coverage@64 improves by 10.42 points: 85 wins and 25 losses. None of
the 21 first-choice regressions is recovered within the corrected frontier of
64. Ranking alone is therefore insufficient to resolve those regressions.

| Source seed (96 tasks each) | Old first choice | Corrected first choice | Old coverage@64 | Corrected coverage@64 |
| --- | ---: | ---: | ---: | ---: |
| 181 | 63 | 75 | 69 | 84 |
| 193 | 59 | 64 | 65 | 75 |
| 211 | 64 | 71 | 69 | 80 |
| 223 | 60 | 62 | 70 | 73 |
| 239 | 55 | 60 | 64 | 69 |
| 251 | 56 | 69 | 61 | 77 |

All six groups improve on these two aggregate measures, but they belong to an
already inspected source bank. This is not a fresh replication.

## Costs and training opportunity

Equal expansion ceilings did not produce equal actual compute. Counts include
one execution and its replay in each arm; auxiliary validation and reachability
work are separately recorded in `results.json`.

| Search charge | Original filter | Corrected filter |
| --- | ---: | ---: |
| Expansions | 76,206 | 118,686 |
| Primitive executions | 5,401,242 | 8,834,448 |
| Generated nodes | 223,904 | 567,948 |

The correction uses 55.74% more expansions and 63.56% more primitive executions.
Study runtime was 59.36 seconds, excluding the subsequent audit. A compute-matched
advantage has not been established.

The corrected frontier contains verified solutions for 57 tasks missed by its
first choice, versus 41 in the baseline. This offers additional verified harvest
for a future distillation study. Yet total verified frontier programs fall from
5,456 to 4,425 while task coverage rises: raw trajectory count is not capability.
Any harvest comparison needs task balancing, fixed training budgets and retention
controls. No neural benefit has been measured from these frontiers.

## Verification and limits

The audit passed: 18 artifact hashes, 1,154 journal events, 1,152 reexecuted
searches, 1,152 visible-reachability checks and 17,937 regraded frontier programs.
An independent prefix-set algorithm checks reachability, while sharing the pool
builders. Search reexecution uses the frozen algorithm; hashes do not authenticate
a compromised host. Correctness on 16 examples is not all-input equivalence.
Pieces empty on every visible example remain excluded, so complete semantic
program-space coverage is not claimed.

The full suite passed 59 tests with two known PEFT fixture warnings. Regression
tests cover the lost solution, old-pool preservation, deterministic frontiers,
candidate omission and altered reused payloads after archive resealing.

Audit commands, from the project directory with the archived code version:

```powershell
.\.venv\Scripts\python.exe audit_fragment_headroom.py runs\fragment-headroom-20260916-v7
.\.venv\Scripts\python.exe audit_partial_empty.py runs\partial-empty-20260916-v8-diagnostic
```

## Next experiment

1. Freeze a fresh-bank protocol comparing the original and corrected filters
   across measured cost budgets. Include a fixed-total-budget combination to
   test whether preserving both search paths reduces regressions.
2. Validate before promoting a versioned kernel into the worker. Preserve the
   historical control and separate search coverage from first-choice correctness.
3. Test task-balanced verified-frontier distillation with retention controls,
   fresh neural pass@k and full acquisition/training/evaluation costs.
4. Resume common-ancestor improver and inherited-knowledge tests. RSI still
   requires a better improver and sustained coverage gains across generations.

Related-work scope and primary links: `research-reachability-update-2026-09-16.md`.
