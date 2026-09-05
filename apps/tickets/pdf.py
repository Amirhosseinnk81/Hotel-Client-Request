"""
Stage 2.7 — PDF export of a single ticket, for the hotel's physical
archive.

reportlab has no built-in complex-text-layout support, so plain Persian
text drawn with drawString comes out as disconnected, left-to-right
letter forms. Two extra libraries fix that:
  - arabic_reshaper: joins letters into their correct contextual forms
    (isolated/initial/medial/final) — Persian shares its script shaping
    rules with Arabic.
  - python-bidi: reorders the shaped text into visual (right-to-left)
    order, since reportlab always draws left-to-right.

Word-wrapping has to happen on the *unshaped* text (wrapping shaped text
would put word-joining glyphs in the wrong place at line breaks), so
`_wrap_and_shape` measures/wraps first and only shapes each finished
line right before drawing it.
"""

import os
from io import BytesIO

import arabic_reshaper
import jdatetime
from bidi.algorithm import get_display
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdf_canvas

FONT_DIR = os.path.join(os.path.dirname(__file__), "assets", "fonts")
FONT_REGULAR = "Vazirmatn"
FONT_BOLD = "Vazirmatn-Bold"

_fonts_registered = False


def _register_fonts():
    global _fonts_registered
    if _fonts_registered:
        return
    pdfmetrics.registerFont(TTFont(FONT_REGULAR, os.path.join(FONT_DIR, "Vazirmatn-Regular.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, os.path.join(FONT_DIR, "Vazirmatn-Bold.ttf")))
    _fonts_registered = True


_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

_STATUS_LABELS_FA = {
    "OPEN": "باز",
    "IN_PROGRESS": "در حال انجام",
    "RESOLVED": "حل‌شده",
    "CANCELLED": "لغوشده",
}

_PRIORITY_LABELS_FA = {
    "LOW": "کم",
    "NORMAL": "عادی",
    "HIGH": "بالا",
    "URGENT": "فوری",
}

jdatetime.set_locale("fa_IR")


def _fa_digits(text: str) -> str:
    return text.translate(_PERSIAN_DIGITS)


def _format_jalali(dt) -> str:
    """e.g. '۱۲ شهریور ۱۴۰۵ ساعت ۱۴:۳۰' — mirrors the frontend's fa-IR
    Intl.DateTimeFormat output, since browsers render fa-IR dates on the
    Jalali calendar and this report should read the same way."""
    if dt is None:
        return "—"
    local_dt = dt if dt.tzinfo is None else dt.astimezone()
    jd = jdatetime.datetime.fromgregorian(datetime=local_dt)
    return _fa_digits(jd.strftime("%d %B %Y ساعت %H:%M"))


def _shape(text: str) -> str:
    """Reshape + bidi-reorder one already line-wrapped chunk of text so
    it draws correctly with reportlab's plain drawString/drawRightString."""
    return get_display(arabic_reshaper.reshape(text))


def _wrap_lines(canvas_obj: pdf_canvas.Canvas, text: str, font: str, size: int, max_width: float):
    """Greedy word-wrap on *unshaped* text, respecting explicit newlines
    in the source text. Returns a list of unshaped lines ready for
    `_shape` + drawRightString."""
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        words = paragraph.split(" ")
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if canvas_obj.stringWidth(_shape(candidate), font, size) <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 20 * mm
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN


def generate_ticket_pdf(ticket) -> bytes:
    """Renders a one-ticket summary report and returns it as PDF bytes."""
    _register_fonts()

    buffer = BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=A4)
    right_edge = PAGE_WIDTH - MARGIN
    y = PAGE_HEIGHT - MARGIN

    def right_text(text, size, font=FONT_REGULAR, gap=7 * mm, color=colors.black):
        nonlocal y
        c.setFont(font, size)
        c.setFillColor(color)
        c.drawRightString(right_edge, y, _shape(text))
        y -= gap

    def rule():
        nonlocal y
        y -= 2 * mm
        c.setStrokeColor(colors.HexColor("#d8d8d2"))
        c.line(MARGIN, y, right_edge, y)
        y -= 6 * mm

    def wrapped_paragraph(text, size=10.5, font=FONT_REGULAR, line_gap=5.5 * mm):
        nonlocal y
        c.setFont(font, size)
        c.setFillColor(colors.black)
        for line in _wrap_lines(c, text, font, size, CONTENT_WIDTH):
            if y < MARGIN + 15 * mm:
                c.showPage()
                y = PAGE_HEIGHT - MARGIN
                c.setFont(font, size)
            c.drawRightString(right_edge, y, _shape(line))
            y -= line_gap

    # --- Header ---------------------------------------------------------
    right_text("سامانه مدیریت درخواست‌های مهمان هتل", 10, color=colors.HexColor("#6b6f6a"), gap=8 * mm)
    right_text(f"گزارش درخواست شمارهٔ {_fa_digits(str(ticket.pk))}", 16, font=FONT_BOLD, gap=9 * mm)
    right_text(ticket.title, 12.5, font=FONT_BOLD, gap=8 * mm)
    rule()

    # --- Meta grid (one label: value per line) --------------------------
    meta_rows = [
        ("شماره اتاق", ticket.room.number),
        ("واحد", ticket.department.name),
        ("دسته", ticket.category.name),
        ("وضعیت", _STATUS_LABELS_FA.get(ticket.status, ticket.status)),
        ("اولویت", _PRIORITY_LABELS_FA.get(ticket.priority, ticket.priority)),
        (
            "اپراتور مسئول",
            ticket.assigned_to.username if ticket.assigned_to else "اختصاص‌نیافته",
        ),
        ("تاریخ ثبت", _format_jalali(ticket.created_at)),
        ("آخرین به‌روزرسانی", _format_jalali(ticket.updated_at)),
    ]
    if ticket.resolved_at:
        meta_rows.append(("تاریخ حل", _format_jalali(ticket.resolved_at)))
    if ticket.guest_rating:
        meta_rows.append(("امتیاز مهمان", _fa_digits(f"{ticket.guest_rating} از ۵")))

    for label, value in meta_rows:
        c.setFont(FONT_BOLD, 10.5)
        c.setFillColor(colors.HexColor("#3d413c"))
        c.drawRightString(right_edge, y, _shape(f"{label}:"))
        c.setFont(FONT_REGULAR, 10.5)
        c.setFillColor(colors.black)
        label_width = c.stringWidth(_shape(f"{label}: "), FONT_BOLD, 10.5)
        c.drawRightString(right_edge - label_width, y, _shape(str(value)))
        y -= 7 * mm

    rule()

    # --- Description ------------------------------------------------------
    right_text("شرح درخواست", 12, font=FONT_BOLD, gap=7 * mm)
    wrapped_paragraph(ticket.description or "—")
    y -= 4 * mm

    # --- Resolution (only if present) -------------------------------------
    if ticket.resolution:
        rule()
        right_text("نتیجهٔ رسیدگی", 12, font=FONT_BOLD, gap=7 * mm)
        wrapped_paragraph(ticket.resolution)
        y -= 4 * mm

    # --- Guest feedback (only if present) ---------------------------------
    if ticket.guest_feedback:
        rule()
        right_text("بازخورد مهمان", 12, font=FONT_BOLD, gap=7 * mm)
        wrapped_paragraph(ticket.guest_feedback)

    # --- Footer -------------------------------------------------------
    c.setFont(FONT_REGULAR, 8)
    c.setFillColor(colors.HexColor("#8a8d87"))
    generated_at = _format_jalali(timezone.now())
    c.drawCentredString(
        PAGE_WIDTH / 2,
        MARGIN / 2,
        _shape(f"تاریخ تولید گزارش: {generated_at}"),
    )

    c.showPage()
    c.save()
    return buffer.getvalue()
