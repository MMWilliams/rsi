# Frozen familiar AST zero-query feedback transfer (2026-09-18)

## Question

Can a familiar-AST-specific top-100 ranker trained on verified candidate labels improve first-choice correctness on untouched familiar banks? Does a later checkpoint trained on 96 more familiar tasks improve over its earlier parent, scrambled new labels and duplicate history?

## Frozen bank and comparison

Generate 24 fresh familiar `ast_transition` banks, seeds 903800–903823, eight tasks per bank, one visible and 23 hidden examples. Use the same V67/V73 widened candidate pools and old/E0 ranking pipeline for every policy. Primary outcome: final correctness of the first program with **zero external output calls**. Compare E0, shifted AB, pooled, familiar early, familiar later, scrambled-later and duplicate-history models. All familiar models score old-order top 100 with stable old-rank ties. The source models were fitted before target generation from 192 familiar AST tasks for early and 288 for later; the new 96-task labels are scrambled within task for one control. Source candidate-label counts and inference cost are recorded. No target hidden output or probe answer enters a choice.

The component gate requires early familiar to beat E0 and pooled each by at least 20/192, improve at least 12/24 banks against both, and have strictly positive paired bank intervals against both. The incremental checkpoint gate requires later to beat early, scrambled-later and duplicate history each by at least five tasks, improve at least eight banks over early, and have strictly positive paired intervals against all three. Report failed criteria individually. This test establishes a familiar specialist at most; mixing it with the shifted specialist needs a separate public-evidence applicability test.

Freeze protocol, script, model and target-public-artifact hashes before scoring. Rebuild target tasks, pools, candidate predictions, choices and final labels in a separate audit command. A failed audit invalidates the result. Equal output-call count is not equal total source acquisition or inference cost.
