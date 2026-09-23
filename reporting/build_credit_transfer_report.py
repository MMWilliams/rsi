"""Build the audited V12 credit-transfer result PDF."""
from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "credit-transfer-20260917-v12"
OUT = ROOT / "output" / "pdf" / "credit-transfer-results-2026-09-17.pdf"


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#536377"))
    canvas.drawString(0.65 * inch, 0.4 * inch, "RSI research | V12 credit-transfer result | No RSI claim")
    canvas.drawRightString(7.85 * inch, 0.4 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build():
    result = json.loads((RUN / "results.json").read_text(encoding="utf-8"))
    audit = json.loads((RUN / "audit.json").read_text(encoding="utf-8"))
    seeds = [347, 359, 373, 389, 401, 419]
    conditions = ["immediate_only", "observational_descendant", "paired_credit", "scrambled_paired", "empty", "random"]
    styles = getSampleStyleSheet()
    title = ParagraphStyle("title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=25, leading=30, textColor=colors.HexColor("#16263D"), spaceAfter=12)
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=colors.HexColor("#16263D"), spaceBefore=10, spaceAfter=8)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=colors.HexColor("#205FC3"), spaceBefore=8, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.5, leading=14, textColor=colors.HexColor("#16263D"), spaceAfter=7)
    small = ParagraphStyle("small", parent=body, fontSize=8, leading=11, textColor=colors.HexColor("#536377"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUT), pagesize=letter, rightMargin=0.65 * inch, leftMargin=0.65 * inch, topMargin=0.65 * inch, bottomMargin=0.65 * inch, title="V12 credit-transfer result")
    story = [Paragraph("V12 inherited-credit transfer", title), Paragraph("Audited result for the RSI improver-selection component", h2),
             Paragraph("This study tested whether inherited effect estimates help a bounded improver choose edits on new tasks. Six conditions shared the same V10 source evidence, six source groups, matched development and admission opportunities, and a common 256-task final bank.", body)]
    story += [Paragraph("Conclusion", h1), Paragraph("The declared selector screen failed. Observational-descendant and paired later-improvement credit tied immediate-only in all six source groups. Scrambled and random controls were worse. This is a validated negative component result; it does not establish recursive self-improvement.", body)]
    story += [Paragraph("Audit and integrity", h1), Paragraph(f"Independent audit status: {audit['status']}. It regenerated {audit['tasks_regenerated']} tasks, reexecuted {audit['unique_batches_reexecuted']} unique worker batches and their exact replays, and regraded {audit['evaluation_task_rows_regraded']} task rows with the strict host oracle. The journal contains {audit['journal_events']} events. The run recorded zero runtime incidents.", body), Paragraph("The audit reports post-run workspace drift in two unrelated modules and in the auditor script. The sealed source snapshot has no internal hash mismatches, and the runner's start/end integrity check passed.", small)]
    story += [Paragraph("Final scores", h1)]
    table = [["Condition", *[str(s) for s in seeds], "Mean"], ["Immediate-only", *[f"{result['scores'][f'final/immediate_only/s{s}']['accuracy']:.1%}" for s in seeds], f"{sum(result['scores'][f'final/immediate_only/s{s}']['accuracy'] for s in seeds)/6:.1%}"]]
    for c in conditions[1:]:
        vals = [result["scores"][f"final/{c}/s{s}"]["accuracy"] for s in seeds]
        table.append([c.replace("_", " "), *[f"{v:.1%}" for v in vals], f"{sum(vals)/6:.1%}"])
    t = Table(table, colWidths=[1.45 * inch] + [0.67 * inch] * 6 + [0.67 * inch], repeatRows=2)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16263D")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#E8F5F2")), ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D8E0E9")), ("FONTNAME", (0, 1), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 7.5), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story += [t, Spacer(1, 10), Paragraph("Paired mean differences versus immediate-only: observational descendant 0.00 pp; paired credit 0.00 pp; scrambled paired -0.78 pp; empty -0.39 pp; random -0.78 pp.", body)]
    story += [Paragraph("Compute and next decision", h1), Paragraph(f"The run charged {result['cost']['worker_batches']:,} worker batches, including {result['cost']['replay_batches']:,} replay batches, {result['cost']['search_expansions']:,} search expansions, {result['cost']['primitive_executions']:,} primitive executions, and {result['cost']['oracle_string_executions']:,} strict-oracle string checks.", body), Paragraph("Do not promote the current credit selector into the recursive loop. The next useful test is a calibrated estimator on larger independent source banks, or a different measured bottleneck. The DSL, edit catalog, and task generator remain bounded and researcher-authored.", body), Paragraph("Archive: runs/credit-transfer-20260917-v12. Full narrative: credit-transfer-results-2026-09-17.md.", small)]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return OUT


if __name__ == "__main__":
    print(build())
