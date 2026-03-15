"""
PDF Report Generator using ReportLab
Produces a professional, structured meeting report.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing, Rect, String, Circle
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF

# ── Colour palette ────────────────────────────────────────────────────────────
C_NAVY    = colors.HexColor("#0A1628")
C_BLUE    = colors.HexColor("#1A6EE3")
C_LIGHT   = colors.HexColor("#EBF2FD")
C_TEAL    = colors.HexColor("#0F9B76")
C_AMBER   = colors.HexColor("#E8930A")
C_RED     = colors.HexColor("#D63B3B")
C_GRAY    = colors.HexColor("#6B7280")
C_LGRAY   = colors.HexColor("#F3F4F6")
C_WHITE   = colors.white
C_BLACK   = colors.HexColor("#111827")
C_BORDER  = colors.HexColor("#D1D5DB")

PAGE_W, PAGE_H = A4
MARGIN = 1.8 * cm

PRIORITY_COLORS = {"high": C_RED, "medium": C_AMBER, "low": C_TEAL}
SENTIMENT_COLORS = {"positive": C_TEAL, "neutral": C_GRAY, "negative": C_RED, "mixed": C_AMBER}


# ── Style factory ─────────────────────────────────────────────────────────────
def build_styles() -> dict:
    base = getSampleStyleSheet()

    def P(name, **kw) -> ParagraphStyle:
        parent = kw.pop("parent", "Normal")
        return ParagraphStyle(name, parent=base[parent], **kw)

    return {
        "title":       P("RPTitle", fontSize=26, textColor=C_WHITE,
                         fontName="Helvetica-Bold", alignment=TA_LEFT, leading=32),
        "subtitle":    P("RPSub",   fontSize=12, textColor=colors.HexColor("#A5C4F5"),
                         fontName="Helvetica", alignment=TA_LEFT),
        "section":     P("RPSec",   fontSize=13, textColor=C_NAVY,
                         fontName="Helvetica-Bold", spaceBefore=16, spaceAfter=6,
                         borderPadding=(0, 0, 4, 0)),
        "body":        P("RPBody",  fontSize=10, textColor=C_BLACK,
                         fontName="Helvetica", leading=15, alignment=TA_JUSTIFY),
        "bullet":      P("RPBull",  fontSize=10, textColor=C_BLACK,
                         fontName="Helvetica", leading=14, leftIndent=12, bulletIndent=0),
        "small":       P("RPSmall", fontSize=8.5, textColor=C_GRAY,
                         fontName="Helvetica", leading=12),
        "label":       P("RPLabel", fontSize=9, textColor=C_BLUE,
                         fontName="Helvetica-Bold"),
        "card_title":  P("RPCTitle",fontSize=10, textColor=C_NAVY,
                         fontName="Helvetica-Bold"),
        "tag":         P("RPTag",   fontSize=8, textColor=C_BLUE,
                         fontName="Helvetica-Bold"),
        "footer":      P("RPFoot",  fontSize=8, textColor=C_GRAY,
                         fontName="Helvetica", alignment=TA_CENTER),
        "highlight":   P("RPHigh",  fontSize=10, textColor=C_NAVY,
                         fontName="Helvetica-Bold", backColor=C_LIGHT,
                         borderPadding=6, leading=15),
    }


# ── Page frame helpers ────────────────────────────────────────────────────────
def _on_first_page(canvas, doc, session: dict, analysis: dict):
    """Draw the full-bleed header on page 1."""
    canvas.saveState()

    # Dark navy header
    header_h = 72 * mm
    canvas.setFillColor(C_NAVY)
    canvas.rect(0, PAGE_H - header_h, PAGE_W, header_h, fill=1, stroke=0)

    # Blue accent stripe
    canvas.setFillColor(C_BLUE)
    canvas.rect(0, PAGE_H - header_h - 4, PAGE_W, 4, fill=1, stroke=0)

    # Title
    title = session.get("title", "Meeting Report")
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 22)
    canvas.drawString(MARGIN, PAGE_H - 28 * mm, title)

    # Subtitle line
    started = session.get("started_at", "")
    date_str = ""
    if started:
        try:
            dt = datetime.fromisoformat(started)
            date_str = dt.strftime("%B %d, %Y  •  %H:%M UTC")
        except Exception:
            date_str = started

    canvas.setFont("Helvetica", 10)
    canvas.setFillColor(colors.HexColor("#A5C4F5"))
    canvas.drawString(MARGIN, PAGE_H - 38 * mm, date_str)

    # Duration + type badges
    dur = int(session.get("duration_seconds", 0))
    dur_str = f"{dur // 60}m {dur % 60}s" if dur else "—"
    meeting_type = analysis.get("meeting_type", "")
    meta = f"Duration: {dur_str}   ·   Type: {meeting_type}"
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#7BA8E0"))
    canvas.drawString(MARGIN, PAGE_H - 48 * mm, meta)

    # NVIDIA badge (top right)
    canvas.setFillColor(colors.HexColor("#76B900"))
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 12 * mm, "Powered by NVIDIA NIM AI")

    _draw_footer(canvas, 1)
    canvas.restoreState()


def _on_later_pages(canvas, doc):
    canvas.saveState()
    # Thin top bar
    canvas.setFillColor(C_NAVY)
    canvas.rect(0, PAGE_H - 12 * mm, PAGE_W, 12 * mm, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(MARGIN, PAGE_H - 7 * mm, "AI Meeting Intelligence Report")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 7 * mm, f"Page {doc.page}")
    _draw_footer(canvas, doc.page)
    canvas.restoreState()


def _draw_footer(canvas, page_num):
    canvas.setFillColor(C_LGRAY)
    canvas.rect(0, 0, PAGE_W, 10 * mm, fill=1, stroke=0)
    canvas.setFillColor(C_GRAY)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawCentredString(PAGE_W / 2, 3.5 * mm,
        "Generated by AI Meeting Intelligence Agent  ·  NVIDIA NIM APIs  ·  Confidential")


# ── Section helpers ───────────────────────────────────────────────────────────
def _section_header(text: str, styles: dict) -> list:
    return [
        HRFlowable(width="100%", thickness=0.5, color=C_BORDER, spaceAfter=4),
        Paragraph(f"▌  {text}", styles["section"]),
    ]


def _pill_table(items: list[str], color=C_BLUE) -> Table:
    """Render a list of strings as coloured pills in a wrapping table."""
    cells = []
    row = []
    for i, item in enumerate(items):
        cell = Paragraph(
            f'<font color="white"><b>{item}</b></font>',
            ParagraphStyle("pill", fontSize=8, fontName="Helvetica-Bold",
                           alignment=TA_CENTER, leading=10),
        )
        row.append(cell)
        if (i + 1) % 4 == 0:
            cells.append(row)
            row = []
    if row:
        while len(row) < 4:
            row.append(Paragraph("", ParagraphStyle("empty", fontSize=8)))
        cells.append(row)
    if not cells:
        return Spacer(1, 1)

    col_w = (PAGE_W - 2 * MARGIN) / 4
    t = Table(cells, colWidths=[col_w] * 4, rowHeights=18)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("ROUNDEDCORNERS", [4]),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [color]),
        ("GRID", (0, 0), (-1, -1), 0, colors.transparent),
    ]))
    return t


def _kv_table(rows: list[tuple], styles: dict) -> Table:
    data = [[Paragraph(f"<b>{k}</b>", styles["label"]),
             Paragraph(str(v), styles["body"])] for k, v in rows]
    col_w = PAGE_W - 2 * MARGIN
    t = Table(data, colWidths=[col_w * 0.28, col_w * 0.72])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [C_WHITE, C_LGRAY]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, C_BORDER),
    ]))
    return t


def _action_table(items: list[dict], styles: dict) -> Table:
    header = [
        Paragraph("<b>#</b>", styles["label"]),
        Paragraph("<b>Task</b>", styles["label"]),
        Paragraph("<b>Owner</b>", styles["label"]),
        Paragraph("<b>Deadline</b>", styles["label"]),
        Paragraph("<b>Priority</b>", styles["label"]),
    ]
    rows = [header]
    for i, item in enumerate(items, 1):
        priority = item.get("priority", "medium").lower()
        p_color = PRIORITY_COLORS.get(priority, C_GRAY)
        rows.append([
            Paragraph(str(i), styles["small"]),
            Paragraph(item.get("task", ""), styles["body"]),
            Paragraph(item.get("owner", "TBD"), styles["body"]),
            Paragraph(item.get("deadline", "—") or "—", styles["small"]),
            Paragraph(
                f'<font color="white"><b>{priority.upper()}</b></font>',
                ParagraphStyle("pri", fontSize=8, fontName="Helvetica-Bold",
                               alignment=TA_CENTER, backColor=p_color, leading=12),
            ),
        ])

    col_w = PAGE_W - 2 * MARGIN
    t = Table(rows, colWidths=[col_w * 0.05, col_w * 0.42, col_w * 0.18,
                                col_w * 0.18, col_w * 0.17], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_NAVY),
        ("TEXTCOLOR",  (0, 0), (-1, 0), C_WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_LGRAY]),
        ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return t


def _speaker_table(speakers: list[dict], styles: dict) -> Table:
    header = [
        Paragraph("<b>Speaker</b>", styles["label"]),
        Paragraph("<b>Role</b>", styles["label"]),
        Paragraph("<b>Talk %</b>", styles["label"]),
        Paragraph("<b>Key Contributions</b>", styles["label"]),
    ]
    rows = [header]
    for spk in speakers:
        pct = spk.get("estimated_talk_percentage", 0)
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        contributions = "<br/>".join(f"• {c}" for c in spk.get("key_contributions", [])[:3])
        rows.append([
            Paragraph(f"<b>{spk.get('name', 'Unknown')}</b>", styles["body"]),
            Paragraph(spk.get("role_in_meeting", "participant").title(), styles["small"]),
            Paragraph(f"{bar}  {pct}%", ParagraphStyle(
                "bar", fontSize=8, fontName="Courier", textColor=C_BLUE)),
            Paragraph(contributions or "—", styles["small"]),
        ])

    col_w = PAGE_W - 2 * MARGIN
    t = Table(rows, colWidths=[col_w * 0.20, col_w * 0.17, col_w * 0.22, col_w * 0.41], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_NAVY),
        ("TEXTCOLOR",  (0, 0), (-1, 0), C_WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_LGRAY]),
        ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


# ── Main generator ────────────────────────────────────────────────────────────
class ReportGenerator:

    def generate(self, session: dict, analysis: dict, output_path: str) -> str:
        styles = build_styles()

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=76 * mm,   # leave room for header on pg 1
            bottomMargin=18 * mm,
        )

        story = self._build_story(session, analysis, styles)

        doc.build(
            story,
            onFirstPage=lambda c, d: _on_first_page(c, d, session, analysis),
            onLaterPages=_on_later_pages,
        )
        return output_path

    # ── Story sections ────────────────────────────────────────────────────────
    def _build_story(self, session: dict, analysis: dict, styles: dict) -> list:
        story = []

        story += self._section_overview(session, analysis, styles)
        story += self._section_summary(analysis, styles)
        story += self._section_key_points(analysis, styles)
        story += self._section_decisions(analysis, styles)
        story += self._section_action_items(analysis, styles)
        story += self._section_speakers(analysis, styles)
        story += self._section_insights(analysis, styles)
        story += self._section_open_questions(analysis, styles)
        story += self._section_timeline(analysis, styles)
        story.append(PageBreak())
        story += self._section_transcript(session, styles)

        return story

    def _section_overview(self, session: dict, analysis: dict, styles: dict) -> list:
        items = []

        # Meta info grid
        dur = int(session.get("duration_seconds", 0))
        dur_str = f"{dur // 60} min {dur % 60} sec" if dur else "—"
        participants = ", ".join(session.get("participants", [])) or "Not specified"
        sentiment = analysis.get("sentiment", "neutral")
        s_color = SENTIMENT_COLORS.get(sentiment, C_GRAY)
        effectiveness = analysis.get("meeting_effectiveness", "medium")
        word_count = analysis.get("word_count", 0)

        overview_data = [
            ("Duration",        dur_str),
            ("Participants",    participants),
            ("Word count",      f"{word_count:,} words transcribed"),
            ("Sentiment",       sentiment.title()),
            ("Effectiveness",   effectiveness.title()),
            ("Follow-up needed", "Yes" if analysis.get("follow_up_meeting_needed") else "No"),
        ]
        items += _section_header("Meeting Overview", styles)
        items.append(_kv_table(overview_data, styles))

        # Tags
        tags = analysis.get("tags", [])
        if tags:
            items.append(Spacer(1, 8))
            items.append(Paragraph("Topics:", styles["label"]))
            items.append(Spacer(1, 4))
            items.append(_pill_table(tags, C_BLUE))

        items.append(Spacer(1, 12))
        return items

    def _section_summary(self, analysis: dict, styles: dict) -> list:
        items = []
        summary = analysis.get("executive_summary", "")
        if not summary:
            return items
        items += _section_header("Executive Summary", styles)
        items.append(KeepTogether([
            Paragraph(summary, ParagraphStyle(
                "exec", fontSize=11, fontName="Helvetica",
                leading=17, alignment=TA_JUSTIFY,
                backColor=C_LIGHT, borderPadding=10,
                textColor=C_NAVY,
            )),
            Spacer(1, 12),
        ]))

        # Main topics pills
        topics = analysis.get("main_topics", [])
        if topics:
            items.append(Paragraph("Main topics covered:", styles["label"]))
            items.append(Spacer(1, 4))
            items.append(_pill_table(topics, C_TEAL))
            items.append(Spacer(1, 12))
        return items

    def _section_key_points(self, analysis: dict, styles: dict) -> list:
        points = analysis.get("key_discussion_points", [])
        if not points:
            return []
        items = _section_header("Key Discussion Points", styles)
        for pt in points:
            point_text = pt.get("point", str(pt)) if isinstance(pt, dict) else str(pt)
            context = pt.get("context", "") if isinstance(pt, dict) else ""
            speaker = pt.get("speaker", "") if isinstance(pt, dict) else ""
            body = f"<b>{point_text}</b>"
            if context:
                body += f"<br/><font color='#6B7280'>{context}</font>"
            if speaker:
                body += f"<br/><font color='#1A6EE3'>— {speaker}</font>"
            items.append(Paragraph(f"• {body}", styles["bullet"]))
            items.append(Spacer(1, 4))
        items.append(Spacer(1, 8))
        return items

    def _section_decisions(self, analysis: dict, styles: dict) -> list:
        decisions = analysis.get("decisions", [])
        if not decisions:
            return []
        items = _section_header("Decisions Made", styles)
        for i, dec in enumerate(decisions, 1):
            decision_text = dec.get("decision", str(dec)) if isinstance(dec, dict) else str(dec)
            rationale = dec.get("rationale", "") if isinstance(dec, dict) else ""
            decided_by = dec.get("decided_by", "") if isinstance(dec, dict) else ""
            body = f"<b>{i}. {decision_text}</b>"
            if rationale:
                body += f"<br/><font color='#6B7280'>Rationale: {rationale}</font>"
            if decided_by:
                body += f"<br/><font color='#0F9B76'>By: {decided_by}</font>"
            items.append(Paragraph(body, styles["bullet"]))
            items.append(Spacer(1, 6))
        items.append(Spacer(1, 8))
        return items

    def _section_action_items(self, analysis: dict, styles: dict) -> list:
        actions = analysis.get("action_items", [])
        if not actions:
            return []
        items = _section_header("Action Items", styles)
        items.append(_action_table(actions, styles))
        items.append(Spacer(1, 12))
        return items

    def _section_speakers(self, analysis: dict, styles: dict) -> list:
        speakers = analysis.get("speakers", [])
        if not speakers:
            return []
        items = _section_header("Speaker Analysis", styles)

        dynamics = analysis.get("meeting_dynamics", "")
        if dynamics:
            items.append(Paragraph(dynamics, styles["body"]))
            items.append(Spacer(1, 6))

        items.append(_speaker_table(speakers, styles))
        items.append(Spacer(1, 12))
        return items

    def _section_insights(self, analysis: dict, styles: dict) -> list:
        insights = analysis.get("key_insights", [])
        recs = analysis.get("recommendations", [])
        blockers = analysis.get("blockers_identified", [])
        next_steps = analysis.get("next_steps_summary", "")

        if not any([insights, recs, blockers, next_steps]):
            return []

        items = _section_header("Insights & Recommendations", styles)

        if next_steps:
            items.append(Paragraph("Next steps:", styles["label"]))
            items.append(Paragraph(next_steps, styles["highlight"]))
            items.append(Spacer(1, 8))

        if insights:
            items.append(Paragraph("Key insights:", styles["label"]))
            for ins in insights:
                items.append(Paragraph(f"💡 {ins}", styles["bullet"]))
            items.append(Spacer(1, 6))

        if recs:
            items.append(Paragraph("Recommendations:", styles["label"]))
            for rec in recs:
                items.append(Paragraph(f"→ {rec}", styles["bullet"]))
            items.append(Spacer(1, 6))

        if blockers:
            items.append(Paragraph("Blockers identified:", styles["label"]))
            for blk in blockers:
                items.append(Paragraph(
                    f'<font color="#D63B3B">⚠ {blk}</font>', styles["bullet"]))
            items.append(Spacer(1, 6))

        items.append(Spacer(1, 8))
        return items

    def _section_open_questions(self, analysis: dict, styles: dict) -> list:
        questions = analysis.get("open_questions", [])
        risks = analysis.get("risks_concerns", [])
        if not questions and not risks:
            return []
        items = _section_header("Open Questions & Risks", styles)
        for q in questions:
            items.append(Paragraph(f"? {q}", styles["bullet"]))
        for r in risks:
            items.append(Paragraph(f'<font color="#D63B3B">⚠ {r}</font>', styles["bullet"]))
        items.append(Spacer(1, 12))
        return items

    def _section_timeline(self, analysis: dict, styles: dict) -> list:
        timeline = analysis.get("timeline", [])
        if not timeline:
            return []
        items = _section_header("Meeting Timeline", styles)
        for event in timeline:
            ts = event.get("timestamp_hint", "")
            ev = event.get("event", "")
            sig = event.get("significance", "")
            body = f"<b>[{ts}]</b> {ev}"
            if sig:
                body += f"<br/><font color='#6B7280'>{sig}</font>"
            items.append(Paragraph(body, styles["bullet"]))
            items.append(Spacer(1, 4))
        items.append(Spacer(1, 12))
        return items

    def _section_transcript(self, session: dict, styles: dict) -> list:
        transcript = session.get("full_transcript", "")
        if not transcript:
            return []
        items = _section_header("Full Transcript", styles)
        items.append(Paragraph(
            "The complete meeting transcript is provided below for reference.",
            styles["small"],
        ))
        items.append(Spacer(1, 6))

        # Split by speaker chunks if formatted
        chunks = session.get("transcript_chunks", [])
        if chunks:
            for chunk in chunks:
                speaker = chunk.get("speaker", "Speaker")
                text = chunk.get("text", "")
                ts = chunk.get("timestamp", "")
                items.append(Paragraph(
                    f'<font color="#1A6EE3"><b>{speaker}</b></font>  '
                    f'<font color="#9CA3AF">[{ts[:19] if ts else ""}]</font>',
                    styles["small"],
                ))
                items.append(Paragraph(text, styles["body"]))
                items.append(Spacer(1, 6))
        else:
            # Plain transcript
            for line in transcript.split("\n"):
                if line.strip():
                    items.append(Paragraph(line.strip(), styles["body"]))
                    items.append(Spacer(1, 3))

        return items
