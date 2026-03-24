"""
Eigentümerabrechnung – DOCX Export Service

Generates an owner billing letter (WEG annual settlement) for a single
Wohnungseinheit as a Word (.docx) document, matching the existing
Abrechnung_*_YYYY-WEXX.docx document format.
"""

from io import BytesIO
from datetime import date as _date

# ─── Static bank balance data per year ────────────────────────────────────────

KONTENENTWICKLUNG = {
    2024: {
        "giro":       [("29.12.2023", 3_527.48), ("30.12.2024", 3_333.80)],
        "geldmarkt":  [("29.12.2023", 8_067.85), ("30.12.2024", 10_274.95)],
    },
    2025: {
        "giro":       [("30.12.2024", 3_333.80), ("30.12.2025", 3_970.48)],
        "geldmarkt":  [("30.12.2024", 10_281.93), ("30.12.2025", 12_677.11)],
    },
}


# ─── Formatting helpers ────────────────────────────────────────────────────────

def _n(val, dec: int = 2) -> str:
    """Format number German-style: 1.234,56"""
    if val is None:
        return "ausstehend"
    try:
        s = f"{float(val):,.{dec}f}"
        return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    except (TypeError, ValueError):
        return "ausstehend"


def _eur(val) -> str:
    """Format as Euro amount: 1.234,56 €"""
    if val is None:
        return "ausstehend"
    return _n(val) + " €"


# ─── DOCX generator ───────────────────────────────────────────────────────────

def generate_owner_docx(owner: dict, year: int) -> BytesIO:
    """Generate a single Eigentümerabrechnung DOCX for `owner` and `year`."""
    from docx import Document
    from docx.shared import Pt, Cm, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    PRIMARY_HEX = "1A7A5E"
    PRIMARY_RGB = RGBColor(0x1A, 0x7A, 0x5E)
    WHITE_RGB   = RGBColor(0xFF, 0xFF, 0xFF)
    LIGHT_HEX   = "E6F4EF"

    doc = Document()

    # ── Page setup: A4, 2.5 cm margins ────────────────────────────────────────
    sec = doc.sections[0]
    sec.page_width  = Cm(21)
    sec.page_height = Cm(29.7)
    for attr in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, attr, Cm(2.5))

    # ── Helpers ────────────────────────────────────────────────────────────────

    def set_cell_bg(cell, hex_color: str):
        tcPr = cell._tc.get_or_add_tcPr()
        for existing in tcPr.findall(qn("w:shd")):
            tcPr.remove(existing)
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"),   "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"),  hex_color)
        tcPr.append(shd)

    def para(text="", bold=False, size_pt=10, align=None, color_rgb=None,
             space_before=0, space_after=0):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after  = Pt(space_after)
        if align:
            p.alignment = align
        if text:
            r = p.add_run(text)
            r.bold = bold
            r.font.size = Pt(size_pt)
            if color_rgb:
                r.font.color.rgb = color_rgb
        return p

    def cell_text(cell, text="", bold=False, size_pt=9,
                  align=WD_ALIGN_PARAGRAPH.LEFT, color_rgb=None):
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = align
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after  = Pt(0)
        if text:
            r = p.add_run(text)
            r.bold = bold
            r.font.size = Pt(size_pt)
            if color_rgb:
                r.font.color.rgb = color_rgb

    # ── Sender header ──────────────────────────────────────────────────────────
    p_sender = doc.add_paragraph()
    r = p_sender.add_run("WEG Tulpenstr. 31  •  86567 Hilgertshausen")
    r.font.size = Pt(8)
    r.font.color.rgb = RGBColor(0x80, 0x80, 0x80)
    # underline-separator using border on paragraph bottom
    pPr  = p_sender._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bot  = OxmlElement("w:bottom")
    bot.set(qn("w:val"),  "single")
    bot.set(qn("w:sz"),   "4")
    bot.set(qn("w:space"), "2")
    bot.set(qn("w:color"), "1A7A5E")
    pBdr.append(bot)
    pPr.append(pBdr)

    doc.add_paragraph()  # spacer

    # ── Recipient address ──────────────────────────────────────────────────────
    para(owner.get("name", ""), size_pt=11)
    para(owner.get("address1", ""), size_pt=10)
    para(owner.get("city", ""), size_pt=10)

    doc.add_paragraph()  # spacer

    # ── Date (right-aligned) ───────────────────────────────────────────────────
    today = _date.today().strftime("%d.%m.%Y")
    p_date = doc.add_paragraph()
    p_date.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_date.add_run(today)
    r.font.size = Pt(10)
    r.italic = True

    doc.add_paragraph()  # spacer

    # ── Subject ────────────────────────────────────────────────────────────────
    p_sub = doc.add_paragraph()
    r = p_sub.add_run(f"Allgemeine Jahresabrechnung {owner.get('unit_id', '')} – {year}")
    r.bold = True
    r.font.size = Pt(12)
    r.font.color.rgb = PRIMARY_RGB
    # Bottom border
    pPr2  = p_sub._p.get_or_add_pPr()
    pBdr2 = OxmlElement("w:pBdr")
    bot2  = OxmlElement("w:bottom")
    bot2.set(qn("w:val"),  "single")
    bot2.set(qn("w:sz"),   "4")
    bot2.set(qn("w:space"), "2")
    bot2.set(qn("w:color"), "1A7A5E")
    pBdr2.append(bot2)
    pPr2.append(pBdr2)

    doc.add_paragraph()  # spacer

    # ── "Ausgaben:" label ──────────────────────────────────────────────────────
    para("Ausgaben:", bold=True, size_pt=10, space_after=4)

    # ── Cost table ─────────────────────────────────────────────────────────────
    col_widths = [Cm(6), Cm(4), Cm(2.2), Cm(2.5), Cm(2.5)]
    tbl = doc.add_table(rows=0, cols=5)
    tbl.style = "Table Grid"

    def add_row(cells_data, bg=None, bold=False):
        row = tbl.add_row()
        for ci, (width, text) in enumerate(zip(col_widths, cells_data)):
            row.cells[ci].width = width
            align = WD_ALIGN_PARAGRAPH.RIGHT if ci >= 2 else WD_ALIGN_PARAGRAPH.LEFT
            cell_text(row.cells[ci], text,
                      bold=bold, size_pt=9, align=align,
                      color_rgb=WHITE_RGB if bg == PRIMARY_HEX else None)
            if bg:
                set_cell_bg(row.cells[ci], bg)

    # Header row
    add_row([
        "Kostenkonto", "Umlageart",
        "Umlage\nanteilig", "Ges. Betrag", "Betrag ant.",
    ], bg=PRIMARY_HEX, bold=True)

    # Data rows
    positionen = owner.get("positionen", [])
    for alt_idx, pos in enumerate(positionen):
        mea = pos.get("umlage_anteilig")
        mea_str = _n(mea) if mea is not None else ""
        add_row([
            pos.get("kostenkonto", ""),
            pos.get("umlageart", ""),
            mea_str,
            _n(pos.get("ges_betrag")),
            _eur(pos.get("betrag_ant")),
        ], bg=LIGHT_HEX if alt_idx % 2 == 1 else None)

    # Empty separator row
    add_row(["", "", "", "", ""])

    # Gesamt row
    gesamt_ges = None
    try:
        gesamt_ges = sum(
            p["ges_betrag"] for p in positionen if p.get("ges_betrag") is not None
        )
        if any(p.get("ges_betrag") is None for p in positionen):
            gesamt_ges = None  # BKA-1 still pending
    except Exception:
        gesamt_ges = None
    add_row([
        "Gesamt", "", "",
        _n(gesamt_ges),
        _eur(owner.get("gesamt")),
    ], bold=True)

    # Vorauszahlung row
    add_row([
        "Abzüglich Vorauszahlung", "", "", "",
        _eur(owner.get("vorauszahlung")),
    ])

    # Empty row
    add_row(["", "", "", "", ""])

    # Nachzahlung/Rückzahlung row
    nachzahlung = owner.get("nachzahlung")
    nz_label = "Nachzahlung" if nachzahlung is None or nachzahlung >= 0 else "Rückzahlung"
    add_row([
        "", "", nz_label, nz_label,
        _eur(nachzahlung),
    ], bg=LIGHT_HEX, bold=True)

    doc.add_paragraph()  # spacer

    # ── Footnote ───────────────────────────────────────────────────────────────
    p_fn = doc.add_paragraph()
    r_fn = p_fn.add_run(
        "¹ Weitere Details sind aus der Heiz- und Nebenkostenabrechnung "
        "der Fa. Witter zu entnehmen."
    )
    r_fn.font.size = Pt(8)
    r_fn.font.color.rgb = RGBColor(0x60, 0x60, 0x60)

    doc.add_paragraph()  # spacer

    # ── Kontenentwicklung ──────────────────────────────────────────────────────
    ke = KONTENENTWICKLUNG.get(year)
    if ke:
        para("Kontenentwicklung:", bold=True, size_pt=10)
        doc.add_paragraph()

        for datum, val in ke["giro"]:
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after  = Pt(0)
            r = p.add_run(f"Girokonto Stand:  {datum}  {_n(val)}  Euro")
            r.font.size = Pt(10)

        doc.add_paragraph()

        for datum, val in ke["geldmarkt"]:
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after  = Pt(0)
            r = p.add_run(f"Geldmarktkonto:  {datum}  {_n(val)}  Euro")
            r.font.size = Pt(10)

    doc.add_paragraph()  # spacer

    # ── Closing / Anlagen ──────────────────────────────────────────────────────
    p_cl = doc.add_paragraph()
    r_cl = p_cl.add_run("Anlagen:\nWitter  Heiz- und Nebenkostenabrechnung")
    r_cl.font.size = Pt(10)

    # ── Write to buffer ────────────────────────────────────────────────────────
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf
