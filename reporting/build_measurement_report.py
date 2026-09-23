"""Build the dated RSI measurement report from sealed local evidence."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    HRFlowable,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "rsi-improvement-measurement-report-2026-09-16.pdf"
RUN = ROOT / "runs" / "paired-credit-20260916-v10"

INK = colors.HexColor("#16263D")
MUTED = colors.HexColor("#536377")
BLUE = colors.HexColor("#205FC3")
TEAL = colors.HexColor("#0D827C")
PALE = colors.HexColor("#EDF3FB")
PALE_TEAL = colors.HexColor("#E8F5F2")
AMBER = colors.HexColor("#9B5A12")
PALE_AMBER = colors.HexColor("#FFF4E6")
RULE = colors.HexColor("#D8E0E9")
WHITE = colors.white


def register_fonts():
    font_dir = Path("C:/Windows/Fonts")
    pdfmetrics.registerFont(TTFont("ArialR", str(font_dir / "arial.ttf")))
    pdfmetrics.registerFont(TTFont("ArialB", str(font_dir / "arialbd.ttf")))
    pdfmetrics.registerFontFamily("ArialR", normal="ArialR", bold="ArialB")


def styles():
    return {
        "eyebrow": ParagraphStyle("eyebrow", fontName="ArialB", fontSize=8, leading=11, textColor=TEAL, spaceAfter=8),
        "title": ParagraphStyle("title", fontName="ArialB", fontSize=29, leading=33, textColor=INK, spaceAfter=11),
        "subtitle": ParagraphStyle("subtitle", fontName="ArialR", fontSize=12.5, leading=18, textColor=MUTED, spaceAfter=17),
        "h1": ParagraphStyle("h1", fontName="ArialB", fontSize=17, leading=22, textColor=INK, spaceBefore=0, spaceAfter=10),
        "h2": ParagraphStyle("h2", fontName="ArialB", fontSize=11.7, leading=16, textColor=INK, spaceBefore=12, spaceAfter=5),
        "body": ParagraphStyle("body", fontName="ArialR", fontSize=9.3, leading=14, textColor=INK, spaceAfter=7),
        "small": ParagraphStyle("small", fontName="ArialR", fontSize=8, leading=11.8, textColor=MUTED, spaceAfter=5),
        "table": ParagraphStyle("table", fontName="ArialR", fontSize=8.3, leading=12, textColor=INK),
        "table_head": ParagraphStyle("table_head", fontName="ArialB", fontSize=8, leading=11, textColor=WHITE),
        "callout": ParagraphStyle("callout", fontName="ArialB", fontSize=12.2, leading=18, textColor=INK),
        "metric": ParagraphStyle("metric", fontName="ArialB", fontSize=17, leading=21, textColor=BLUE, alignment=TA_CENTER),
        "metric_label": ParagraphStyle("metric_label", fontName="ArialR", fontSize=7.8, leading=11, textColor=MUTED, alignment=TA_CENTER),
        "source": ParagraphStyle("source", fontName="ArialR", fontSize=7.9, leading=11.6, textColor=INK, spaceAfter=5),
    }


def p(text, style):
    return Paragraph(text, style)


def box(text, style, bg=PALE, border=BLUE, width=511):
    tab = Table([[p(text, style)]], colWidths=[width])
    tab.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.6, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 13),
        ("RIGHTPADDING", (0, 0), (-1, -1), 13),
        ("TOPPADDING", (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
    ]))
    return tab


def grid(rows, widths, head=True, padding=7):
    tab = Table(rows, colWidths=widths, repeatRows=1 if head else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), padding),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding),
        ("TOPPADDING", (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
        ("LINEBELOW", (0, -1), (-1, -1), 0.6, RULE),
    ]
    if head:
        commands += [("BACKGROUND", (0, 0), (-1, 0), INK)]
        if len(rows) > 1:
            commands += [("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F8FAFD")])]
    else:
        commands += [("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, colors.HexColor("#F8FAFD")])]
    tab.setStyle(TableStyle(commands))
    return tab


class SearchBars(Flowable):
    def __init__(self):
        super().__init__()
        self.width = 508
        self.height = 90

    def draw(self):
        c = self.canv
        bar_x, max_w = 224, 228
        c.setFont("ArialR", 7.5)
        c.setFillColor(MUTED)
        c.roundRect(224, 84, 8, 8, 2, fill=1, stroke=0)
        c.drawString(236, 85, "Original")
        c.setFillColor(TEAL)
        c.roundRect(307, 84, 8, 8, 2, fill=1, stroke=0)
        c.drawString(319, 85, "Corrected")
        for i, (label, old, new) in enumerate([
            ("First-choice correct", 332, 377),
            ("Deterministic coverage@64", 374, 438),
        ]):
            y = 70 - 41 * i
            c.setFont("ArialB", 8.5)
            c.setFillColor(INK)
            c.drawString(0, y + 6, label)
            c.setFillColor(RULE)
            c.roundRect(bar_x, y + 1, max_w, 11, 4, fill=1, stroke=0)
            c.setFillColor(MUTED)
            c.roundRect(bar_x, y + 1, max_w * old / 576, 11, 4, fill=1, stroke=0)
            c.setFillColor(TEAL)
            c.roundRect(bar_x, y - 13, max_w * new / 576, 11, 4, fill=1, stroke=0)
            c.setFont("ArialR", 7.5)
            c.setFillColor(MUTED)
            c.drawRightString(505, y + 2, f"{old}/576")
            c.setFillColor(TEAL)
            c.drawRightString(505, y - 13, f"{new}/576")


def page_footer(canvas, doc):
    canvas.saveState()
    width, height = letter
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(50, height - 48, width - 50, height - 48)
    canvas.setFont("ArialB", 7.4)
    canvas.setFillColor(TEAL)
    canvas.drawString(50, height - 38, "RSI RESEARCH  /  MEASUREMENT REPORT")
    canvas.setFont("ArialR", 7.4)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(width - 50, height - 38, "16 SEPTEMBER 2026")
    canvas.line(50, 43, width - 50, 43)
    canvas.drawString(50, 30, "Local evidence review  |  No RSI claim")
    canvas.drawRightString(width - 50, 30, f"Page {doc.page}")
    canvas.restoreState()


def h1(story, text, s):
    story.append(p(text, s["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.7, color=RULE, spaceAfter=10))


def build():
    register_fonts()
    s = styles()
    result = json.loads((RUN / "results.json").read_text(encoding="utf-8"))
    audit = json.loads((RUN / "audit.json").read_text(encoding="utf-8"))
    assert audit["status"] == "passed"
    assert audit["paired_effects_recomputed"] == len(result["pairs"]) == 72
    counts = {name: Counter((row[name] > 0) - (row[name] < 0) for row in result["pairs"])
              for name in ("immediate", "total_descendant", "later_improvement")}
    assert counts["later_improvement"] == Counter({0: 62, 1: 8, -1: 2})
    assert result["headroom_observed"] is True

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(str(OUTPUT), pagesize=letter, leftMargin=50, rightMargin=50,
                          topMargin=62, bottomMargin=58, title="RSI: Defining and Measuring Improvement",
                          author="RSI research project", subject="Audited component findings and open RSI criteria")
    frame = Frame(50, 58, 512, 672, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id="report", frames=frame, onPage=page_footer))
    story = []

    # Page 1 - claim and navigation.
    story += [Spacer(1, 40), p("RESEARCH STATUS / EVIDENCE BRIEF", s["eyebrow"]),
              p("What counts as<br/>improvement?", s["title"]),
              p("Definitions, measurements, findings, and how they change the RSI program", s["subtitle"]),
              box("<b>Current conclusion.</b> A corrected searcher reaches more verified solutions on fresh string-DSL tasks. The tested model and inherited improver have not shown durable, compounding improvement. No result yet supports an RSI or mission-domain capability claim.", s["callout"]),
              Spacer(1, 22)]
    metrics = Table([
        [p("+11.11 pp", s["metric"]), p("10 / 72", s["metric"]), p("0", s["metric"])],
        [p("fresh-task search coverage@64<br/>at ceiling 128 [S1]", s["metric_label"]),
         p("paired edits with a nonzero effect<br/>on later improvement [S4]", s["metric_label"]),
         p("replicated inherited-improver<br/>advantages established [S3]", s["metric_label"])],
    ], colWidths=[170, 170, 170])
    metrics.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                 ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F9FC")),
                                 ("BOX", (0, 0), (-1, -1), 0.5, RULE),
                                 ("INNERGRID", (0, 0), (-1, -1), 0.4, RULE),
                                 ("TOPPADDING", (0, 0), (-1, 0), 12),
                                 ("BOTTOMPADDING", (0, -1), (-1, -1), 12)]))
    story += [metrics, Spacer(1, 24), p("The system under test", s["h2"]),
              p("The proposed loop amplifies a pinned local model with bounded program search, verifies trajectories with an external oracle, distills verified solutions into model weights, and edits the amplifier. Its eventual target is improved capacity to improve itself. The proposed applications are research, defensive cybersecurity, social good, and policy; none has yet been evaluated by these DSL studies.", s["body"]),
              p("This report separates five things often conflated: a better selected answer, broader search coverage, better sampled model behavior, a better improver, and application value. Only the first two have a positive audited component result.", s["body"]),
              Spacer(1, 7), p("Evidence cutoff: completed local archives available on 17 September 2026. V10 passed independent audit. V9b failed its publication audit; V11 completed under the repaired contract and failed its advancement screen [S5, S7].", s["small"]),
              PageBreak()]

    # Page 2 - definitions.
    h1(story, "1. Four measurement levels", s)
    levels = [
        [p("Level", s["table_head"]), p("Operational definition", s["table_head"]), p("What would count as improvement", s["table_head"])],
        [p("Answer", s["table"]), p("A selected program is correct when the host oracle matches all specified visible and hidden examples on a fresh task.", s["table"]), p("A higher paired fraction of tasks solved, with losses and actual cost reported.", s["table"])],
        [p("Searcher", s["table"]), p("The first candidate's correctness and deterministic coverage@k: at least one verified program among the first k cost-ordered candidates.", s["table"]), p("More verified tasks at the declared budget; assess the full budget/cost curve, not only an equal ceiling.", s["table"])],
        [p("Model", s["table"]), p("Raw pass@k from n independent model samples per task, graded by the oracle. Report k=1, 4, 8, 16, 32, 64 by checkpoint.", s["table"]), p("Large-k coverage rises above the same frozen base and remains higher after later generations, without unacceptable task losses.", s["table"])],
        [p("Improver", s["table"]), p("Restart older and newer edit policies from the same frozen ancestor; compare the gain each produces with equal opportunities on fresh tasks.", s["table"]), p("Later inherited improvers outperform empty, scrambled, random, and fixed-policy controls at matched acquisition and downstream compute.", s["table"])],
    ]
    story += [grid(levels, [73, 224, 215]), Spacer(1, 13),
              box("<b>One necessary separation:</b> search coverage@64 is a deterministic property of a correlated candidate list. Neural pass@64 is an estimate from sampled model outputs. Their percentages are not interchangeable.", s["body"], PALE_TEAL, TEAL),
              Spacer(1, 14), p("Application value is a fifth, later level", s["h2"]),
              p("Success on the string-transformation DSL is a controlled mechanism test. Before claiming value in research, defensive security, social good, or policy, each domain needs its own authorized tasks, outcome measures, failure analysis, human review, and cost accounting. A DSL gain is not a proxy for those outcomes.", s["body"]),
              PageBreak()]

    # Page 3 - measurement protocol.
    h1(story, "2. How scores are produced and checked", s)
    story += [p("Tasks are split before experiments into development, admission, and final banks. Search sees task IDs and visible examples. Hidden examples are held by the host oracle. The final bank is kept out of edit selection and checkpoint decisions. In the DSL studies a task has three visible and thirteen hidden examples; finite examples are evidence of tested behavior, not an all-input proof [S1, S4].", s["body"]),
              p("Neural pass@k", s["h2"]),
              box("For n saved model samples with c correct outputs on a task: <b>pass@k = 1 - C(n-c,k) / C(n,k)</b>. Average the per-task values. With n=k=64, a task contributes 1 if any of its 64 samples is correct, otherwise 0. Report per-task counts and the full curve, not only pass@1 [S2].", s["body"]),
              p("Candidate gates and final evaluation", s["h2"]),
              p("A search edit is considered on development tasks and admitted only after a separate nonregression check. The V9 neural gate retains a checkpoint only if no previously solved admission task is lost, pass@1 and pass@64 do not fall, and at least one improves. These are finite-sample decisions; the final bank later checks whether admission was right. Earlier replay work preserved diversity but still lost final coverage, showing why a gate is not a guarantee [S2, S6].", s["body"]),
              p("Integrity and cost", s["h2"]),
              p("Every candidate request, score, decision, source version and run artifact is journaled. Search requests are replayed bit-exactly, and the host recomputes program behavior independently. A separate auditor reconstructs tasks, grades, branches and effects before results are used. We charge physical search, replay, training, sampling, oracle checks and audit separately. Local hashes help detect accidental alteration, but do not authenticate against a compromised host [S4, S6].", s["body"]),
              box("<b>Important current boundary:</b> a posthoc scan found 106 visible-behavior disagreements in V9b's saved samples, including the <b>M(WORD,1,End)</b> case, plus 3 trailing-comma programs accepted by Python AST but rejected by the published grammar. The detailed neural result remains withheld; the strict oracle now rejects trailing commas and a fresh rerun is required [S5].", s["body"], PALE_AMBER, AMBER),
              PageBreak()]

    # Page 4 - audited results.
    h1(story, "3. What the completed studies found", s)
    story += [p("Search repair: positive component evidence [S1]", s["h2"]),
              p("On 576 fresh tasks at expansion ceiling 128, allowing program pieces that are empty on some visible examples improved first-choice correctness from 332 to 377 (+7.81 percentage points) and coverage@64 from 374 to 438 (+11.11 points). Both gains were positive in five of six source groups. The repair was human-directed; it did not modify model weights or the improver.", s["body"]),
              SearchBars(),
              p("Actual expansions rose from 38,143 to 57,724 and primitive executions from 2.69 million to 4.41 million. Equal expansion ceilings did not produce equal compute. Seventeen first-choice tasks regressed, so the gain is not universal.", s["small"]),
              p("Model and inheritance: prior negative results [S2, S3]", s["h2"]),
              p("In the controlled V2 pilot, tasks reached by raw neural sampling at k=64 went 7/24 -> 8/24 -> 5/24 over the initial checkpoint and two adaptive rounds. A separate fresh replication of inherited edit statistics failed its declared screen: the generation-6 table averaged 58.72% solved, below the empty table's 58.92% and random edits' 59.05% on the shared 256-task final bank. These are narrow negative results, not a proof that RSI is impossible.", s["body"]),
              p("Paired later-improvement probe: audited headroom [S4]", s["h2"]),
              p("V10 applied each of twelve numeric initial edits and a no-edit branch in six source groups, then ran the same fixed two-round downstream improver in each branch. Each group's edits share its 16 measurement tasks and baseline. The independent auditor reconstructed all 78 branches and 72 paired effects.", s["body"])]
    signs = [[p("Paired effect", s["table_head"]), p("Positive", s["table_head"]), p("Zero", s["table_head"]), p("Negative", s["table_head"])]]
    for name, label in (("immediate", "Initial edit"), ("total_descendant", "Terminal quality"), ("later_improvement", "Later improvement")):
        ct = counts[name]
        signs.append([p(label, s["table"]), p(str(ct[1]), s["table"]), p(str(ct[0]), s["table"]), p(str(ct[-1]), s["table"])])
    story += [grid(signs, [220, 97, 97, 98]), Spacer(1, 9),
              p("The declared nonzero headroom check passed: 8 positive and 2 negative later-improvement effects, with 62 zero. This supports measuring that quantity, not a claim that a predictor can select it. The 72 pairs are dependent, not 72 independent replications.", s["small"]),
              p("Here Q is the count of correct first-choice programs on each group's 16 common measurement tasks. In one paired branch (seed 373, case_cost_down), the initial edit scored -2 tasks, the terminal branch scored +1, and the difference in later improvement was +3. This illustrates the distinction; it is not an estimate of that edit's general effect.", s["small"]),
              p("V10 cost: 7,376 physical searches and 7,376 exact replays; 1.46 million charged expansions and 112.91 million primitive executions. Its independent audit added separate work [S4].", s["small"]),
              PageBreak()]

    # Page 5 - use of evidence.
    h1(story, "4. How findings change the next experiment", s)
    applications = [
        [p("Finding", s["table_head"]), p("Action already taken", s["table_head"]), p("Next decision", s["table_head"])],
        [p("Remembered fragments did not improve correctness [S6].", s["table"]), p("Diagnosed search reachability; repaired the partial-empty filter; prospectively validated it on fresh tasks [S1].", s["table"]), p("Test whether its larger verified frontier improves sampled model coverage after distillation.", s["table"])],
        [p("Training gains faded in V2; replay alone did not retain coverage [S2, S6].", s["table"]), p("Added task-balanced cumulative verified examples, anchor examples, checkpoint admission and rollback to V9b.", s["table"]), p("V11 completed under the repaired contract and passed audit, but failed the advancement screen; preserve it as a negative transfer result.", s["table"])],
        [p("Inherited descendant credit was sparse and mostly observational [S3, S6].", s["table"]), p("Executed the matched paired-branch V10 source probe; it passed audit and found sparse nonzero later-improvement effects [S4].", s["table"]), p("Compare immediate-only, observational-credit and paired-credit selectors from a common ancestor at matched total compute.", s["table"])],
        [p("A report renderer could trust stale evidence [S6].", s["table"]), p("Changed publication to rerun the independent audit over all declared artifacts. It blocked V9b reporting on a real mismatch.", s["table"]), p("Version the oracle and auditor with a regression test; retain the failed run and full incident trail.", s["table"])],
    ]
    story += [grid(applications, [147, 186, 179]), Spacer(1, 13),
              box("<b>Promotion rule:</b> do not move a component into the flagship loop because its code runs or one local score rose. Require a declared fresh-task improvement, independent audit, cost comparison, and evidence that the gain survives the next stage of the loop.", s["body"], PALE_TEAL, TEAL),
              Spacer(1, 13), p("The RSI test still ahead", s["h2"]),
              p("The decisive claim requires sustained large-k model coverage above the frozen base across generations; later improvers producing larger gains than generation 0 when restarted from the same ancestor; inheritance beating empty, scrambled and random controls; and a fixed external improver and self-training-only baseline at matched total compute. New edit types must make verified contributions, not merely enter a catalog. No completed study has met this package of criteria [S2, S3, S6].", s["body"]),
              PageBreak()]

    # Page 6 - limits and source ledger.
    h1(story, "5. What the evidence does not yet show", s)
    story += [p("The current task generator is a narrow string-transformation DSL. Its hidden tests are finite, its source groups share design choices, and its scores do not establish all-input equivalence or transfer to open-ended programming. V10's shared baselines make the 72 pair rows dependent. V8 compares equal ceilings and reports actual costs; it is not a fully matched-total-compute RSI test. V9b's completed runner cannot be interpreted as a verified neural result until the oracle/auditor mismatch is resolved [S1-S5].", s["body"]),
              p("The proposed mission needs separate evidence", s["h2"]),
              p("Research: novelty, reproducibility, and expert review. Defensive cybersecurity: authorized scopes, validated findings, and false-positive/false-negative costs. Social good: beneficiary-defined outcomes and distributional harms. Policy: traceable sources, uncertainty, stakeholder review, and correction processes. These are evaluation requirements, not current measured capabilities.", s["body"]),
              p("Source ledger", s["h2"]),
              p("Paths below are relative to C:/Users/reese/projects/rsi/.", s["small"])]
    sources = [
        ("S1", "Audited V8 search validation", "search-validation-results-2026-09-16.md; runs/search-validation-20260916-v8/audit.json"),
        ("S2", "Audited V2 controlled pilot", "pilot-results-2026-09-16.md; runs/pilot-20260916-v2-complete/audit.json"),
        ("S3", "Audited V5 inheritance replication", "inheritance-replication-results-2026-09-16.md; runs/inheritance-20260916-v5/audit.json"),
        ("S4", "Audited V10 paired source probe", "EXPERIMENT-v10-paired-credit-probe.md; runs/paired-credit-20260916-v10/results.json and audit.json"),
        ("S5", "V9b publication-audit incident and mismatch characterization", "EXPERIMENT-v9b-resource-recovery.md; analysis/v9b-semantic-mismatch-20260916.md and .json; runs/frontier-distillation-20260916-v9b/; CHANGE-REGISTER.md, C023"),
        ("S6", "Change history and design requirements", "CHANGE-REGISTER.md; NEXT-IMPROVER-CREDIT-STUDY.md; GAP-COVERAGE.md"),
        ("S7", "V11 audited fresh rerun", "EXPERIMENT-v11-frontier-contract-repair.md; configs/frontier-v11.json; frontier-distillation-results-2026-09-17.md; runs/frontier-distillation-20260916-v11/"),
    ]
    for key, title, paths in sources:
        story.append(p(f"<b>[{key}] {title}.</b> {paths}", s["source"]))
    story += [Spacer(1, 13), box("<b>Decision at this cutoff:</b> retain the corrected search repair as a validated source component; preserve V11 as a negative transfer result; use V10 only to design a prospective credit-selector test; withhold V9b neural conclusions; and keep RSI and mission-domain claims open.", s["body"]),
              Spacer(1, 15), p("Report generated from the local project archive. The V10 builder checks that the independent audit passed and that all 72 paired effects have the stated sign counts. Detailed records remain in the cited run directory.", s["small"])]

    doc.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    build()
