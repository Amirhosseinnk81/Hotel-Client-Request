"""
The printed phone list — the one that ends up taped next to a desk.

The layout is the Flask app's, kept on purpose because it was designed
around printing: landscape A4 in two columns, each department's name in
a single cell merged down beside all of its own numbers, and the next
department starting immediately after with no header band and no gap, so
the whole hotel fits on as few sheets as possible.

Two things differ from there. The font is the project's Vazirmatn rather
than Tahoma (`apps/tickets/pdf.py` owns that plumbing — the full TTF,
not the "Non-Latin" build, which has no Latin or ASCII digit glyphs; see
CLAUDE.md). And platypus does the work here, not raw canvas, because
merged cells that flow across two frames are what platypus is for.

The rows handed in are already filtered and sorted by the caller, so the
print-out matches whatever the person was looking at on screen.
"""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Table, TableStyle

from apps.tickets.labels import fa_digits
from apps.tickets.pdf import FONT_BOLD, FONT_REGULAR, register_fonts, shape

NO_DEPARTMENT = "بدون واحد"


def _p(text, style):
    return Paragraph(shape(str(text or "—")), style)


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "DirTitle",
            parent=base["Title"],
            fontName=FONT_BOLD,
            fontSize=13,
            leading=18,
            alignment=TA_CENTER,
            textColor=colors.white,
        ),
        "department": ParagraphStyle(
            "DirDept",
            parent=base["Normal"],
            fontName=FONT_BOLD,
            fontSize=9.3,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#4d4d4d"),
        ),
        "cell": ParagraphStyle(
            "DirCell",
            parent=base["Normal"],
            fontName=FONT_REGULAR,
            fontSize=9,
            leading=12,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#4d4d4d"),
        ),
        "number": ParagraphStyle(
            "DirNumber",
            parent=base["Normal"],
            fontName=FONT_BOLD,
            fontSize=9.5,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#7c5f47"),
        ),
        "empty": ParagraphStyle(
            "DirEmpty",
            parent=base["Normal"],
            fontName=FONT_REGULAR,
            fontSize=10,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#9a948b"),
        ),
    }


def _grouped(extensions):
    """Department name -> its rows, in the order the caller gave them."""
    groups: dict[str, list] = {}
    for item in extensions:
        name = item.department.name if item.department_id else NO_DEPARTMENT
        groups.setdefault(name, []).append(item)
    return groups


def _department_block(name, rows, styles, column_width):
    """
    One department as a single table: its name merged down the first
    column (RTL, so "first" is the rightmost), one line per number.
    """
    data = []
    for index, item in enumerate(rows):
        person = item.person_name or ""
        detail = item.title if not person else f"{item.title} — {person}"
        if not item.is_active:
            detail = f"{detail} (غیرفعال)"
        data.append(
            [
                _p(name, styles["department"]) if index == 0 else "",
                _p(detail, styles["cell"]),
                _p(fa_digits(item.extension), styles["number"]),
            ]
        )

    # Right-to-left: department, then what the number is, then the number.
    widths = [column_width * 0.26, column_width * 0.56, column_width * 0.18]
    table = Table(data, colWidths=widths, hAlign="RIGHT")
    table.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (0, len(data) - 1)),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d9d4cd")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f5f2ee")),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def build_extensions_pdf(extensions, title="فهرست داخلی‌های هتل") -> bytes:
    register_fonts()
    styles = _styles()

    page_width, page_height = landscape(A4)
    margin = 1 * cm
    gutter = 0.7 * cm
    column_width = (page_width - 2 * margin - gutter) / 2

    buffer = BytesIO()
    document = BaseDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=margin,
        leftMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
        title=title,
    )
    # Right column first: on an RTL page the eye starts there.
    right = Frame(page_width - margin - column_width, margin, column_width, page_height - 2 * margin, id="right")
    left = Frame(margin, margin, column_width, page_height - 2 * margin, id="left")
    document.addPageTemplates([PageTemplate(id="two-col", frames=[right, left])])

    heading = Table(
        [[_p(title, styles["title"])]],
        colWidths=[column_width],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#4d4d4d")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        ),
    )

    story = [heading]
    groups = _grouped(extensions)
    if not groups:
        story.append(_p("داخلی‌ای برای نمایش نیست.", styles["empty"]))
    for name, rows in groups.items():
        story.append(_department_block(name, rows, styles, column_width))

    document.build(story)
    return buffer.getvalue()
