# RSI criteria: September 2026 primary-source check

Checked during the retention experiment. No experimental settings were changed in response to this review.

[Generalized Agent Iteration, September 11, v1](https://arxiv.org/html/2609.13406v1), abstract and introduction inspected, separates whether the improvement mechanism itself is modifiable from whether evaluation remains externally grounded. This is useful vocabulary for our architecture: changing solver weights under a fixed training rule is insufficient evidence that the improvement mechanism became better. Its conceptual framework does not establish convergence or empirical success for our system.

[The Last AI Built by Humans, September 15, v2](https://arxiv.org/abs/2609.11873v2), abstract inspected and full HTML located, distinguishes several kinds of autonomy and recursive meta-improvement. Treat this as a recent roadmap and related-work lead, not evidence of achieved RSI or a validated recipe. Detailed empirical claims and its headroom index have not been audited here.

[The Generic Holdout, 2018](https://arxiv.org/abs/1809.05596), abstract checked, addresses false discoveries under adaptive reuse of evaluation data. Our current response is fresh per-round admission tasks and a separately closed final evaluation. We have not implemented the paper's statistical mechanism and cannot claim its guarantees.

## Consequences for the next system experiment

1. Record the entire inheritable system state: weights, macros, search configuration, edit catalog, effect table, and update policy. Identify exactly which component each intervention changes.
2. Keep oracle semantics and final scoring outside the editable proposal interface. Test the stated boundary; do not call a same-user process an OS sandbox.
3. Apply generation-0/3/6 improvers to a common ancestor. Record all attempted edits and their cost, including rejection and later descendant outcomes. Better successor scores alone cannot establish a better improver.
4. Transplant one component at a time. Effect-table experiments freeze weights, macros and code. Weight retention experiments freeze harvested trajectories and edit policy. Recombine components only after interpreting these controls.
5. Require later use of a changed improvement rule and a controlled gain from that use before calling it recursive meta-improvement. Preserve negative results and uncertainty.

These criteria support the existing project objective. The current bounded numeric edit catalog, single-seed neural pilot and unmatched total compute remain limitations. A working retention gate is a prerequisite for a more informative next loop, not completion of RSI.
