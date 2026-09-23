# V15 open-ended operator lab

Run: `runs/open-ended-v15d-20260917`.

This experiment combined four mechanisms in one auditable loop: verified
LoRA bootstrap, adapted-model operator proposals, a bounded quality-diversity
composition beam, and separate development/admission gates. The model could
only change the declared arithmetic search configuration; host code applied
and evaluated every proposal. A deterministic schema-and-box projection
repaired malformed model output while recording every repair.

| Quantity | Result |
| --- | ---: |
| Verified bootstrap anchors | 17/24 tasks |
| Valid adapted-model proposals | 3 |
| Total hypotheses evaluated | 12 (3 model, 9 compositions) |
| Hypotheses admitted | 0 |
| Baseline final correctness | 11/16 |
| Best hypothesis final correctness | 11/16 |

All 12 hypotheses lost at least one development or admission task, or tied
without the required strict development improvement. Two composed hypotheses
tied the baseline on the untouched final bank; the remaining candidates scored
9–10/16. The independent archive audit passed: 28 journal events, 400
deterministic selected programs replayed and regraded, and all three valid
model proposals revalidated.

The finding is a null for this open-ended policy-invention protocol. Schema
repair increased usable model output, but bounded search-policy edits did not
survive held-out gates or improve final generalization. This is evidence that
proposal syntax and local development improvement are insufficient for RSI;
the system still lacks unrestricted algorithm invention, broad task transfer,
multiple neural seeds, and independent-host verification.
