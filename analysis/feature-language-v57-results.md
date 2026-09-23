# V57 generated feature-language selection

Status: audited two-seed result. V57 synthesizes a small predicate-language grammar from observed structural primitives, generating raw ordinal intervals, exact character-category predicates, and category-prefix predicates. An admission-gated controller selects the lowest-complexity language that meets the baseline admission criterion, then evaluates the selected language on a disjoint Greek-letter/Arabic-Indic-digit domain.

| Language | Seed 14 final | Seed 15 final |
| --- | ---: | ---: |
| Baseline | 0/24 | 0/24 |
| Generated ordinal interval | 0/24 | 0/24 |
| Generated exact category | 24/24 | 24/24 |
| Generated category prefix | 24/24 | 24/24 |

The controller selected the simpler `category_prefix` language on both seeds. Its development, admission, and final scores were all 24/24 on both banks. The language itself was generated from observed category values; the experiment did not provide semantic names such as letter or digit.

This is a step beyond V56's hand-listed representation menu: the feature-language candidates and their complexity ordering are synthesized by a reusable grammar. It remains bounded meta-search rather than open-ended RSI because the primitive grammar exposes ordinal and Unicode-category operations, and the domain remains synthetic.

Both independent audits passed, replaying 288 evaluation rows and checking 23 sealed artifacts per run.

Artifacts: `runs/feature-language-v57-20260918/` and `runs/feature-language-v57-20260919-seed15/`.
