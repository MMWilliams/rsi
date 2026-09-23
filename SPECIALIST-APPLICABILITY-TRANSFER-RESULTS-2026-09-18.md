# Integrating the shifted evaluator specialist

Status: **the predeclared applicability router failed integration.** It prevented familiar-AST harm but withheld too many useful specialist choices on shifted tasks. A secondary looser rule looked better, but did not establish a stronger improver or pass the primary gate.

## Frozen mixed test

The [protocol](EXPERIMENT-specialist-applicability-transfer.md) froze 24 new eight-task banks (192 tasks), each with four familiar and four shifted AST tasks, one visible and 23 hidden examples each. Both task types used the same V67/V73 AST pool, replay ranker, E0 candidate ranker, entropy probe and protected cheap four-call allocation. Every budgeted policy bought **96 exact output calls** at the same locations. Unqueried tasks used E0. The router saw only the original visible example, the purchased probe input/output, and candidate/survivor scores. It did not receive task family, generator name, rule reference, seed or ID as a feature.

The specialist was the previously audited 96-task shifted top-100 survivor model. The paired-effect router learned from 192 familiar AST and 192 shifted AST source tasks disjoint from the specialist's candidate training. Its primary threshold, predicted gain **>0.15**, was selected on opened development before these new banks were generated. A zero-threshold effect route, public-example classifier, scrambled-effect route, always-specialist policy, fixed E0 and true-type oracle control were frozen alongside it.

| Policy | Correct / 192 with 96 calls | Familiar / 96 | Shifted / 96 |
| --- | ---: | ---: | ---: |
| E0 | 49 | 26 | 23 |
| Always shifted specialist | 60 | 23 | 37 |
| **Conservative paired-effect route, primary** | **56** | **29** | **27** |
| Zero-threshold effect route, secondary | 61 | 26 | 35 |
| Public-example classifier route | 60 | 27 | 33 |
| Scrambled-effect route | 52 | 26 | 26 |
| True-type route, unavailable control | 63 | 26 | 37 |

The primary route gained **+7** versus E0, five winning banks and no losses, paired bank interval **[+2,+13]**. It improved familiar tasks by +3 without a losing bank. Yet it captured only **+4** shifted gains versus E0 and scored **four fewer** than always using the specialist, interval **[-13,+4]**. It missed every declared overall and shifted-subset requirement and **failed the integration gate**. The zero-threshold route scored +12 over E0, interval [+4,+20], and avoided net familiar harm at this budget. It exceeded always-specialist by only one, interval **[-5,+7]**, so this secondary ablation does not establish a superior router. At one call on every task, the primary route scored 78, E0 68 and always-specialist 77; this is a separate double-call-budget reference.

The frozen pool was reachable on **125/192** tasks and the old top 100 on **114**. An unavailable per-task oracle that chose E0 or the specialist after seeing final labels at the same 96 call locations would score **67**. Thus the available action menu offered at most +7 over always-specialist or +6 over the zero-threshold route on this panel; those ceilings depend on unavailable final labels.

## Failure decomposition

Among the 49 queried shifted tasks, the specialist would help 14 and hurt none. The conservative router accepted it on nine tasks, capturing four helps and missing ten. On the 47 queried familiar tasks, the specialist would help four and hurt seven; the conservative router captured three helps and no harms. The zero-threshold route captured 12 shifted helps and no shifted harms, while three familiar helps and three harms canceled. The primary model was too conservative on shifted tasks, not merely unable to identify familiar harm. See `analysis/applicability-failure-diagnostic-20260918.json`.

## Audit, costs and decision

The run generated 26,608 base candidates plus 66,560 extra AST candidates, predicted 745,344 candidate/probe output cells, made 3,840 original E0 candidate scores, 18,958 additional E0 top-100 scores for router features and 2,823 specialist scores on surviving candidates. Router source acquisition included paired effects on 384 tasks, in addition to the specialist's earlier 1,527 survivor labels and E0's historical training. The final research oracle checked **93,168 candidate labels**. The independent replay rebuilt all 192 tasks, 384 source effect records, all frozen model choices and output predictions, and the 93,168 final labels; it passed. See `runs/specialist-applicability-transfer-20260918/audit.json`.

Retain the shifted survivor model as a **scoped specialist** and the protected E0 policy as the general seed. Do not deploy the tested conservative router or claim a positive feedback loop in the improver. The next improver should learn and validate *calibration or acceptance thresholds* on protected mixed feedback, then show that a later improver produces a better child from an identical base and cost budget on another untouched bank. Also test cue-disrupted tasks so routing cannot succeed by memorizing generator artifacts.

Run: `runs/specialist-applicability-transfer-20260918/`. Runner: `specialist_applicability_transfer.py`.
