# V12 credit-transfer result

V12 tested whether inherited effect estimates help a bounded improver choose edits on fresh tasks. Six conditions used the same V10 source evidence, six source groups, matched development and admission opportunities, and a common 256-task final bank. The run is archived at `runs/credit-transfer-20260917-v12`.

## Audit status

The independent audit passed after reexecuting 525 unique worker batches and their exact replays, regenerating 544 tasks, and regrading 13,792 task rows with the strict host oracle. The journal has 2,274 events and the run recorded zero runtime incidents. The audit reports post-run workspace drift in two unrelated modules and in the auditor script; the sealed source snapshot and runner start/end integrity check remain authoritative for this run.

## Final screen

The frozen ancestor solved 151/256 tasks (58.98%). Immediate-only transfer solved 153/256 on average (59.77%).

| condition | final accuracies for seeds 347, 359, 373, 389, 401, 419 | paired mean vs immediate-only |
| --- | --- | ---: |
| immediate-only | 60.55%, 58.98%, 60.16%, 59.77%, 58.98%, 60.16% | reference |
| observational descendant | same as immediate-only in all six groups | 0.00 pp |
| paired later-improvement credit | same as immediate-only in all six groups | 0.00 pp |
| scrambled paired table | 58.98% in all six groups | -0.78 pp |
| empty table | 60.16%, 58.98%, 58.98%, 58.98%, 60.16%, 58.98% | -0.39 pp |
| random selection | 58.98%, 58.98%, 58.20%, 58.98%, 58.98%, 59.77% | -0.78 pp |

No credit condition beat immediate-only in a source group. The engineering screen failed. Paired and observational tables made the same choices and final scores as immediate-only here; scrambled and random controls were worse.

## Compute and interpretation

The run charged 2,234 worker batches, including 1,117 exact replay batches, 1,915,074 search expansions, 129,403,658 primitive executions, and 220,672 strict-oracle string checks. This is a validated negative component result. It does not test model-weight improvement, self-created edit types, cross-domain mission value, or recursive self-improvement. The next useful step is to calibrate the effect estimator on larger independent source banks before reconnecting it to the amplify/verify/distill loop.
