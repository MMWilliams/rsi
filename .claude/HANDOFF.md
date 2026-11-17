# HANDOFF: paper-style (started 11-17)

1. Goal: both seed-growth papers (technical seed-growth.tex, plain seed-growth-plain.tex) readable in standard arXiv style (DreamCoder / Darwin Godel Machine cadence), same numbers and claims. Done = reese approves tone, all sections rewritten, PDFs rebuilt, merged into worktree-review002.
2. Files: worktree `.claude/worktrees/paper-style`, branch `paper-style` (off worktree-review002 d557c06). d185fc3: new title, abstract (450 -> ~240 words), introduction (5 paragraphs + contributions list + antecedents) in paper/seed-growth.tex; snapshot paper/seed-growth-style-v1a.pdf.
3. Style norms (from DreamCoder, STOP, DGM): abstract 150-320 words, ~19-word sentences, order problem > approach > numbers > implication; "we"; results as "from A to B"; one-sentence limitations where they apply; no version numbers or lab history in abstract/intro; contributions as a short list.
4. Decisions: tone sample first (abstract + intro), rest after reese's verdict. Title dropped "Ten-Seed Replication and Preregistered Ablations" (now in contributions). Abstract says "29% of the compute" for "29% of the scans".
5. Next step: get reese's verdict on v1a; then rewrite sections 2 onward in the same style (Terms table into prose definitions at first use, protocol chronology to an appendix, split 60-word sentences), then the plain paper.
6. Test: `cd paper && pdflatex -interaction=nonstopmode seed-growth.tex` twice: no `!` errors, no undefined refs (current: 30 pages, clean).
Also: review002 runs finished 11-13 ("all done"); the main HANDOFF.md next step (summarize_arms10 etc.) is still open and independent of this.
