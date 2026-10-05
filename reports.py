"""
reports.py
==========
Intelligence report generation for the
POLICE INTELLIGENCE AND INFORMATION MANAGEMENT SYSTEM (PIIMS).

The report produced here follows the layout prescribed by the project document
exactly:

    NIGERIA POLICE FORCE
    Police Command Oji-River, Oji-River LGA, Enugu State
    COMPUTERIZED INTELLIGENCE REPORT
    ------------------------------------------------------------------
    Name of Suspect: ...          Sex: ...
    Address: ...                  Occupation: ...
    Age: ...                      Height: ...
    Date: ...                     Sign: ...
    ------------------------------------------------------------------
    INTELLIGENCE REPORT
    Material Evidence: ...
    Officer: ...
    Date: ...
    Department: ...

Three output formats are provided:

* ``format_report_as_html``  - styled, print-ready HTML (used on screen and for
  the "Download as HTML" button; the browser's Print dialog can also save it as
  PDF).
* ``format_report_as_pdf``   - a genuine PDF produced by a tiny built-in writer,
  so no third-party PDF library is required (the stack is limited to
  Streamlit / SQLite / Pandas / Pillow).
* ``format_report_as_text``  - the plain ASCII box layout, for the "Download as
  TXT" button and for console inspection.

Public API
----------
generate_intelligence_report(case_id, ...)  -> dict
format_report_as_html(report_data)          -> str
format_report_as_pdf(report_data)           -> bytes
format_report_as_text(report_data)          -> str
default_material_evidence(case_id)          -> str
report_filename(report_data, extension)     -> str
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Optional

from db import fetch_all, fetch_one

# --------------------------------------------------------------------------- #
#  Constant report header - Nigeria Police Force, Oji-River Area Command
# --------------------------------------------------------------------------- #
NPF_LINE_1 = "NIGERIA POLICE FORCE"
NPF_LINE_2 = "Police Command Oji-River, Oji-River LGA, Enugu State"
NPF_LINE_3 = "COMPUTERIZED INTELLIGENCE REPORT"
SECTION_TITLE = "INTELLIGENCE REPORT"

SEX_WORDS = {"M": "Male", "F": "Female"}


# --------------------------------------------------------------------------- #
#  Small formatting helpers
# --------------------------------------------------------------------------- #
def _text(value: Any, fallback: str = "Not Stated") -> str:
    """Return a display-safe string, substituting a fallback for empty values."""
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _long_date(value: Any) -> str:
    """Render an ISO date (or date object) as ``05 October 2026``."""
    if isinstance(value, dt.datetime):
        value = value.date()
    if isinstance(value, dt.date):
        return value.strftime("%d %B %Y")
    try:
        return dt.date.fromisoformat(str(value)[:10]).strftime("%d %B %Y")
    except (ValueError, TypeError):
        return _text(value)


def initials(name: str) -> str:
    """Build a signature/initials string from a full name, e.g. ``C.O.``."""
    parts = [p for p in str(name or "").replace(".", " ").split() if p]
    if not parts:
        return "N/A"
    return ".".join(p[0].upper() for p in parts[:3]) + "."


def case_options() -> list[tuple[int, str]]:
    """
    Return ``(case_id, label)`` pairs for the report dropdown, newest first.

    Example label: ``OR/2026/001 - Armed Robbery (Chinedu Okonkwo)``
    """
    rows = fetch_all(
        """
        SELECT c.case_id,
               c.case_number,
               c.crime_type,
               c.status,
               COALESCE(s.name, 'Suspect not recorded') AS suspect_name
        FROM cases c
        LEFT JOIN suspects s ON s.suspect_id = c.suspect_id
        ORDER BY c.case_number DESC
        """
    )
    return [
        (
            int(r["case_id"]),
            f"{r['case_number']} - {r['crime_type']} ({r['suspect_name']}) [{r['status']}]",
        )
        for r in rows
    ]


def default_material_evidence(case_id: int) -> str:
    """
    Build the default "Material Evidence" text for a case.

    The database schema has no dedicated evidence column, so the case
    description is combined with the notes of every linked arrest record.  The
    investigating officer can overwrite the result in the report page before
    downloading it.
    """
    case = fetch_one("SELECT description, crime_type FROM cases WHERE case_id = ?", (case_id,))
    pieces: list[str] = []
    if case and _text(case["description"], "") and str(case["description"]).strip():
        pieces.append(str(case["description"]).strip())

    arrests = fetch_all(
        """
        SELECT a.arrest_date, a.location, a.notes
        FROM arrests a
        WHERE a.case_id = ?
        ORDER BY a.arrest_date
        """,
        (case_id,),
    )
    for a in arrests:
        note = _text(a["notes"], "").strip()
        if note:
            pieces.append(
                f"Recovered/recorded at {_text(a['location']) } on {_long_date(a['arrest_date'])}: {note}"
            )
        else:
            pieces.append(
                f"Arrest effected at {_text(a['location'])} on {_long_date(a['arrest_date'])}."
            )
    return " ".join(pieces) if pieces else "No material evidence recorded at the time of filing."


# --------------------------------------------------------------------------- #
#  Report data assembly
# --------------------------------------------------------------------------- #
def generate_intelligence_report(
    case_id: int,
    material_evidence: Optional[str] = None,
    report_date: Optional[dt.date] = None,
    sign: Optional[str] = None,
    generated_by: Optional[str] = None,
) -> dict[str, Any]:
    """
    Collect every field required by the intelligence report for ``case_id``.

    Parameters
    ----------
    case_id : int
        Primary key of the case to report on.
    material_evidence : str, optional
        Overrides the automatically assembled evidence text.
    report_date : datetime.date, optional
        Date printed on the report (defaults to today).
    sign : str, optional
        Signature / initials of the officer (defaults to the suspect's initials
        as they appear on the file copy).
    generated_by : str, optional
        Username of the operator generating the report (recorded in the footer).

    Returns
    -------
    dict
        All fields needed by the HTML / PDF / TXT formatters.

    Raises
    ------
    ValueError
        If the case does not exist.
    """
    row = fetch_one(
        """
        SELECT c.case_id, c.case_number, c.crime_type, c.description,
               c.status, c.date_filed,
               s.suspect_id, s.name AS suspect_name, s.sex, s.address,
               s.occupation, s.age, s.height, s.photo_path, s.date_added,
               o.officer_id, o.officer_number, o.name AS officer_name,
               o.rank AS officer_rank, o.department, o.date_joined
        FROM cases c
        LEFT JOIN suspects s ON s.suspect_id = c.suspect_id
        LEFT JOIN officers o ON o.officer_id = c.officer_id
        WHERE c.case_id = ?
        """,
        (case_id,),
    )
    if row is None:
        raise ValueError(f"Case id {case_id} was not found in the database.")

    report_date = report_date or dt.date.today()
    suspect_name = _text(row["suspect_name"], "Suspect not recorded")

    report: dict[str, Any] = {
        # ---- case --------------------------------------------------------- #
        "case_id": int(row["case_id"]),
        "case_number": _text(row["case_number"]),
        "crime_type": _text(row["crime_type"]),
        "status": _text(row["status"]),
        "description": _text(row["description"], "No description recorded."),
        "date_filed": row["date_filed"],
        "date_filed_long": _long_date(row["date_filed"]),
        # ---- suspect ------------------------------------------------------ #
        "suspect_id": row["suspect_id"],
        "suspect_name": suspect_name,
        "sex": _text(row["sex"], "-"),
        "sex_word": SEX_WORDS.get(str(row["sex"]).upper(), "Not Stated"),
        "address": _text(row["address"]),
        "occupation": _text(row["occupation"]),
        "age": _text(row["age"]),
        "height": _text(row["height"]),
        "photo_path": row["photo_path"],
        # ---- officer ------------------------------------------------------ #
        "officer_id": row["officer_id"],
        "officer_name": _text(row["officer_name"], "Officer not recorded"),
        "officer_number": _text(row["officer_number"], "-"),
        "officer_rank": _text(row["officer_rank"], "-"),
        "department": _text(row["department"], "Intelligence"),
        "officer_display": (
            f"{_text(row['officer_rank'], '')} {_text(row['officer_name'], 'Officer not recorded')}"
            f" (No. {_text(row['officer_number'], '-')})"
        ).strip(),
        # ---- report meta -------------------------------------------------- #
        "material_evidence": _text(material_evidence) if material_evidence else default_material_evidence(case_id),
        "report_date": report_date,
        "report_date_long": _long_date(report_date),
        "sign": _text(sign) if sign else initials(suspect_name),
        "generated_by": _text(generated_by, "System"),
        "generated_on": dt.datetime.now().strftime("%d %B %Y, %H:%M"),
        "command": NPF_LINE_2,
    }

    # Linked arrests give useful background in the printed report footer.
    arrests = fetch_all(
        """
        SELECT a.arrest_id, a.arrest_date, a.location, a.notes,
               o.name AS officer_name, o.officer_number
        FROM arrests a
        LEFT JOIN officers o ON o.officer_id = a.officer_id
        WHERE a.case_id = ?
        ORDER BY a.arrest_date
        """,
        (case_id,),
    )
    report["arrests"] = [dict(a) for a in arrests]
    report["arrest_summary"] = (
        "; ".join(
            f"{_long_date(a['arrest_date'])} at {_text(a['location'])}" for a in arrests
        )
        if arrests
        else "No arrest recorded on this case."
    )
    return report


# --------------------------------------------------------------------------- #
#  HTML output
# --------------------------------------------------------------------------- #
def _esc(value: Any) -> str:
    """Minimal HTML escaping for report values."""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def format_report_as_html(report_data: dict[str, Any], standalone: bool = True) -> str:
    """
    Render the intelligence report as clean, print-ready HTML.

    When ``standalone`` is True a complete HTML document (with ``<head>`` and
    print CSS) is returned - that is what the download button exports.  When
    False only the report fragment is returned, which is what gets embedded in
    the Streamlit page.
    """
    r = report_data

    rows = [
        ("Name of Suspect:", r["suspect_name"], "Sex:", f"{r['sex']} ({r['sex_word']})"),
        ("Address:", r["address"], "Occupation:", r["occupation"]),
        ("Age:", r["age"], "Height:", r["height"]),
        ("Date:", _long_date(r["report_date"]), "Sign:", r["sign"]),
    ]
    kv_html = "\n".join(
        f"""      <tr>
        <th>{_esc(l1)}</th><td>{_esc(v1)}</td>
        <th>{_esc(l2)}</th><td>{_esc(v2)}</td>
      </tr>"""
        for l1, v1, l2, v2 in rows
    )

    fragment = f"""
<div class="npf-report">
  <div class="npf-head">
    <div class="npf-line1">{_esc(NPF_LINE_1)}</div>
    <div class="npf-line2">{_esc(NPF_LINE_2)}</div>
    <div class="npf-line3">{_esc(NPF_LINE_3)}</div>
  </div>

  <table class="npf-kv">
    {kv_html}
  </table>

  <div class="npf-section">{_esc(SECTION_TITLE)}</div>

  <table class="npf-body">
    <tr><th>Material Evidence:</th><td>{_esc(r['material_evidence'])}</td></tr>
    <tr><th>Officer:</th><td>{_esc(r['officer_display'])}</td></tr>
    <tr><th>Date:</th><td>{_esc(_long_date(r['report_date']))}</td></tr>
    <tr><th>Department:</th><td>{_esc(r['department'])}</td></tr>
  </table>

  <div class="npf-foot">
    Case Reference: <strong>{_esc(r['case_number'])}</strong> &nbsp;|&nbsp;
    Offence: <strong>{_esc(r['crime_type'])}</strong> &nbsp;|&nbsp;
    Case Status: <strong>{_esc(r['status'])}</strong> &nbsp;|&nbsp;
    Date Filed: <strong>{_esc(r['date_filed_long'])}</strong><br/>
    Arrest Record: {_esc(r['arrest_summary'])}<br/>
    Generated by {_esc(r['generated_by'])} on {_esc(r['generated_on'])} - PIIMS, Oji-River Area Command.
  </div>
</div>
"""

    css = """
    .npf-report {
      font-family: "Times New Roman", Georgia, serif;
      color: #111111;
      background: #ffffff;
      border: 2px solid #0b2545;
      border-radius: 4px;
      padding: 18px 22px 14px 22px;
      max-width: 820px;
      margin: 0 auto;
    }
    .npf-head { text-align: center; border-bottom: 2px solid #0b2545; padding-bottom: 8px; }
    .npf-line1 { font-size: 20px; font-weight: 700; letter-spacing: 2px; color: #0b2545; }
    .npf-line2 { font-size: 13px; margin-top: 2px; }
    .npf-line3 { font-size: 15px; font-weight: 700; letter-spacing: 1px; margin-top: 6px;
                 text-decoration: underline; }
    table.npf-kv, table.npf-body { width: 100%; border-collapse: collapse; margin-top: 10px; }
    table.npf-kv th, table.npf-body th {
      text-align: left; font-size: 13px; font-weight: 700; width: 150px;
      padding: 5px 6px 5px 0; vertical-align: top; white-space: nowrap;
    }
    table.npf-kv td, table.npf-body td {
      font-size: 13px; padding: 5px 18px 5px 0; border-bottom: 1px dotted #9aa5b1;
      vertical-align: top; width: 34%;
    }
    table.npf-body td { width: auto; }
    .npf-section {
      margin-top: 14px; padding: 5px 8px; background: #eef2f7; color: #0b2545;
      font-weight: 700; letter-spacing: 1px; font-size: 14px;
      border-left: 5px solid #046a38;
    }
    .npf-foot {
      margin-top: 16px; padding-top: 8px; border-top: 1px solid #0b2545;
      font-size: 11px; color: #333333; line-height: 1.5;
    }
    @media print {
      @page { size: A4; margin: 14mm; }
      body { margin: 0; }
      .npf-report { border: 2px solid #000; max-width: 100%; page-break-inside: avoid; }
      .npf-no-print { display: none !important; }
    }
    """

    if not standalone:
        return f"<style>{css}</style>\n{fragment}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Intelligence Report - {_esc(r['case_number'])}</title>
<style>
  body {{ background: #f4f6f8; padding: 24px 12px; font-family: "Times New Roman", Georgia, serif; }}
  {css}
</style>
</head>
<body>
{fragment}
</body>
</html>
"""


# --------------------------------------------------------------------------- #
#  Plain text output (the exact boxed layout from the project document)
# --------------------------------------------------------------------------- #
_BOX_INNER = 61


def _box(text: str = "") -> str:
    """Return one padded line of the ASCII report box."""
    content = (" " + text)[:_BOX_INNER]
    return "│" + content.ljust(_BOX_INNER) + "│"


def _box_kv(label_left: str, value_left: str, label_right: str = "", value_right: str = "") -> str:
    """Return a two-column key/value line inside the ASCII report box."""
    left = f"{label_left} {value_left}"[:31].ljust(31)
    if not label_right:
        return _box(left.rstrip())
    right = f"{label_right} {value_right}"[:30]
    return _box((left + right).rstrip())


def format_report_as_text(report_data: dict[str, Any]) -> str:
    """Render the report in the exact boxed layout used in the project document."""
    r = report_data
    heavy = "─" * _BOX_INNER
    lines = [
        "┌" + heavy + "┐",
        _box(NPF_LINE_1),
        _box(NPF_LINE_2),
        _box(NPF_LINE_3),
        "├" + heavy + "┤",
        _box_kv("Name of Suspect:", r["suspect_name"], "Sex:", f"{r['sex']}"),
        _box_kv("Address:", r["address"], "Occupation:", r["occupation"]),
        _box_kv("Age:", str(r["age"]), "Height:", str(r["height"])),
        _box_kv("Date:", _long_date(r["report_date"]), "Sign:", r["sign"]),
        "├" + heavy + "┤",
        _box(SECTION_TITLE),
        _box_kv("Material Evidence:", ""),
        _box("   " + r["material_evidence"]),
        _box_kv("Officer:", r["officer_display"]),
        _box_kv("Date:", _long_date(r["report_date"])),
        _box_kv("Department:", r["department"]),
        "└" + heavy + "┘",
        "",
        f"Case Reference : {r['case_number']} ({r['crime_type']}) - {r['status']}",
        f"Date Filed     : {r['date_filed_long']}",
        f"Arrest Record  : {r['arrest_summary']}",
        f"Generated by   : {r['generated_by']} on {r['generated_on']}",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
#  Minimal built-in PDF writer
# --------------------------------------------------------------------------- #
#  PDF is a plain-text container format, so a valid document can be written with
#  no third-party library at all.  Only the two standard PDF base-14 fonts
#  (Helvetica and Helvetica-Bold) are used here, which every PDF reader ships
#  with, and WinAnsiEncoding covers the Latin-1 characters in this report.
# --------------------------------------------------------------------------- #
_PAGE_W = 595.28   # A4 width  in points
_PAGE_H = 841.89   # A4 height in points
_MARGIN = 46.0


def _pdf_escape(text: str) -> str:
    """Sanitise and escape a string for use inside a PDF literal string."""
    safe = (
        str(text)
        .replace("₦", "NGN ")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )
    safe = safe.encode("latin-1", "replace").decode("latin-1")
    return safe.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _text_width(text: str, size: float, bold: bool) -> float:
    """Approximate rendered width of ``text`` in points (Helvetica metrics)."""
    factor = 0.553 if bold else 0.503
    return len(str(text)) * size * factor


class _PdfCanvas:
    """Very small content-stream builder with automatic page breaks."""

    def __init__(self) -> None:
        self.pages: list[list[str]] = []
        self._ops: list[str] = []
        self.y: float = _PAGE_H - _MARGIN

    # -- internals --------------------------------------------------------- #
    def _flush(self) -> None:
        if self._ops:
            self.pages.append(self._ops)
            self._ops = []

    def _new_page(self) -> None:
        self._flush()
        self.y = _PAGE_H - _MARGIN

    def _need(self, height: float) -> None:
        if self.y - height < _MARGIN:
            self._new_page()

    # -- drawing ----------------------------------------------------------- #
    def text(
        self,
        value: str,
        x: Optional[float] = None,
        size: float = 10.0,
        bold: bool = False,
        align: str = "left",
        leading: float = 14.0,
        colour: tuple[float, float, float] = (0.07, 0.15, 0.27),
    ) -> None:
        """Draw one line of text and advance the cursor downwards."""
        self._need(leading)
        s = _pdf_escape(value)
        font = "F2" if bold else "F1"
        if align == "center":
            x = (_PAGE_W - _text_width(s, size, bold)) / 2.0
        elif align == "right":
            x = _PAGE_W - _MARGIN - _text_width(s, size, bold)
        if x is None:
            x = _MARGIN
        r, g, b = colour
        self._ops.append(f"{r:.3f} {g:.3f} {b:.3f} rg")
        self._ops.append(
            f"BT /{font} {size:.2f} Tf {x:.2f} {self.y:.2f} Td ({s}) Tj ET"
        )
        self.y -= leading

    def paragraph(
        self,
        value: str,
        size: float = 10.0,
        bold: bool = False,
        x: float = _MARGIN,
        max_width: float = _PAGE_W - 2 * _MARGIN,
        leading: float = 14.0,
    ) -> None:
        """Word-wrap ``value`` and draw it as one or more lines."""
        words = str(value).split()
        if not words:
            self.text("", x=x, size=size, bold=bold, leading=leading)
            return
        line = ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if _text_width(candidate, size, bold) > max_width and line:
                self.text(line, x=x, size=size, bold=bold, leading=leading)
                line = word
            else:
                line = candidate
        if line:
            self.text(line, x=x, size=size, bold=bold, leading=leading)

    def rule(self, width: float = 1.2, lead: float = 10.0, grey: bool = False) -> None:
        """Draw a horizontal rule across the text area."""
        self._need(lead + 4)
        colour = "0.600 0.640 0.700" if grey else "0.070 0.150 0.270"
        self._ops.append(f"{colour} RG {width:.2f} w")
        self._ops.append(f"{_MARGIN:.2f} {self.y:.2f} m {_PAGE_W - _MARGIN:.2f} {self.y:.2f} l S")
        self.y -= lead

    def space(self, amount: float = 8.0) -> None:
        """Advance the cursor without drawing anything."""
        self._need(amount)
        self.y -= amount

    def kv_row(
        self,
        pairs: list[tuple[str, str]],
        size: float = 10.0,
        leading: float = 15.0,
    ) -> None:
        """Draw a row of ``Label: value`` pairs laid out in two columns."""
        self._need(leading)
        column_x = [_MARGIN, _MARGIN + 290.0]
        for index, (label, value) in enumerate(pairs[:2]):
            x = column_x[index]
            self._ops.append("0.070 0.150 0.270 rg")
            self._ops.append(
                f"BT /F2 {size:.2f} Tf {x:.2f} {self.y:.2f} Td ({_pdf_escape(label)}) Tj ET"
            )
            label_w = _text_width(label + " ", size, True)
            self._ops.append(
                f"BT /F1 {size:.2f} Tf {x + label_w:.2f} {self.y:.2f} Td "
                f"({_pdf_escape(value)}) Tj ET"
            )
        self.y -= leading

    def stream(self) -> bytes:
        """Return the content stream of the current (last) page."""
        return "\n".join(self._ops).encode("latin-1", "replace")

    def finish(self) -> list[bytes]:
        """
        Close the document and return one content stream per page.

        Any ops still buffered belong to the final page, so they are flushed
        before the list is returned.  ``format_report_as_pdf`` must call this
        (or no page content would ever reach the PDF body).
        """
        self._flush()
        return [page for page in self.pages if page] or [[""]]


def _build_pdf(page_streams: list[bytes], title: str = "Intelligence Report") -> bytes:
    """
    Assemble a valid PDF 1.4 document from a list of content streams.

    Object layout
    -------------
    1 = Catalog, 2 = Pages, 3 = Helvetica, 4 = Helvetica-Bold,
    5..N = page / content pairs, last = Document Info.
    """
    n_pages = max(1, len(page_streams))
    if not page_streams:
        page_streams = [b""]

    page_ids = [5 + i * 2 for i in range(n_pages)]
    content_ids = [6 + i * 2 for i in range(n_pages)]
    info_id = 5 + n_pages * 2

    objects: dict[int, bytes] = {}
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode("latin-1")
    objects[3] = (
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
        b"/Encoding /WinAnsiEncoding >>"
    )
    objects[4] = (
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
        b"/Encoding /WinAnsiEncoding >>"
    )

    for i, content in enumerate(page_streams):
        objects[page_ids[i]] = (
            f"<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 {_PAGE_W:.2f} {_PAGE_H:.2f}] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
            f"/Contents {content_ids[i]} 0 R >>"
        ).encode("latin-1")
        objects[content_ids[i]] = (
            f"<< /Length {len(content)} >>\nstream\n".encode("latin-1")
            + content
            + b"\nendstream"
        )

    stamp = dt.datetime.now().strftime("D:%Y%m%d%H%M%S")
    objects[info_id] = (
        f"<< /Title ({_pdf_escape(title)}) /Author (Nigeria Police Force - Oji-River Area Command) "
        f"/Subject (Computerized Intelligence Report) /Creator (PIIMS) "
        f"/Producer (PIIMS Python PDF writer) /CreationDate ({stamp}) >>"
    ).encode("latin-1")

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: dict[int, int] = {}
    for number in sorted(objects):
        offsets[number] = len(out)
        out += f"{number} 0 obj\n".encode("latin-1")
        out += objects[number]
        out += b"\nendobj\n"

    max_object = max(objects)
    xref_offset = len(out)
    out += f"xref\n0 {max_object + 1}\n".encode("latin-1")
    out += b"0000000000 65535 f \n"
    for number in range(1, max_object + 1):
        if number in offsets:
            out += f"{offsets[number]:010d} 00000 n \n".encode("latin-1")
        else:  # pragma: no cover - defensive, object numbers are contiguous
            out += b"0000000000 65535 f \n"
    out += (
        f"trailer\n<< /Size {max_object + 1} /Root 1 0 R /Info {info_id} 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("latin-1")

    return bytes(out)


def format_report_as_pdf(report_data: dict[str, Any]) -> bytes:
    """
    Render the intelligence report as a printable A4 PDF document.

    Returns the raw PDF bytes, ready for ``st.download_button``.
    """
    r = report_data
    canvas = _PdfCanvas()

    # ---- masthead -------------------------------------------------------- #
    canvas.text(NPF_LINE_1, size=17, bold=True, align="center", leading=22)
    canvas.text(NPF_LINE_2, size=10.5, align="center", leading=16)
    canvas.text(NPF_LINE_3, size=12, bold=True, align="center", leading=18)
    canvas.rule(width=1.6, lead=14)

    # ---- suspect block --------------------------------------------------- #
    canvas.kv_row([("Name of Suspect:", r["suspect_name"]), ("Sex:", str(r["sex"]))])
    canvas.kv_row([("Address:", r["address"]), ("Occupation:", r["occupation"])])
    canvas.kv_row([("Age:", str(r["age"])), ("Height:", str(r["height"]))])
    canvas.kv_row([("Date:", _long_date(r["report_date"])), ("Sign:", r["sign"])])
    canvas.rule(width=0.7, lead=12, grey=True)

    # ---- intelligence report section ------------------------------------- #
    canvas.text(SECTION_TITLE, size=12, bold=True, leading=18)
    canvas.text("Material Evidence:", size=10, bold=True, leading=13)
    canvas.paragraph(r["material_evidence"], size=10, leading=14)
    canvas.space(6)
    canvas.text(f"Officer:          {r['officer_display']}", size=10, leading=15)
    canvas.text(f"Date:             {_long_date(r['report_date'])}", size=10, leading=15)
    canvas.text(f"Department:       {r['department']}", size=10, leading=15)
    canvas.space(4)
    canvas.rule(width=0.7, lead=12, grey=True)

    # ---- footer ---------------------------------------------------------- #
    canvas.text(f"Case Reference: {r['case_number']}  |  Offence: {r['crime_type']}  |  Status: {r['status']}", size=9, leading=13)
    canvas.text(f"Date Filed: {r['date_filed_long']}", size=9, leading=13)
    canvas.paragraph(f"Arrest Record: {r['arrest_summary']}", size=9, leading=13)
    canvas.space(4)
    canvas.text(
        f"Generated by {r['generated_by']} on {r['generated_on']}  -  PIIMS, Oji-River Area Command.",
        size=8.5,
        leading=12,
        colour=(0.35, 0.38, 0.42),
    )

    # ---- assemble the document ------------------------------------------- #
    page_streams = [
        "\n".join(page_ops).encode("latin-1", "replace")
        for page_ops in canvas.finish()
    ]
    return _build_pdf(page_streams, title=f"Intelligence Report {r['case_number']}")


def report_filename(report_data: dict[str, Any], extension: str) -> str:
    """Build a filesystem-safe download filename, e.g. ``NPF_Report_OR_2026_001.pdf``."""
    raw = f"NPF_Report_{report_data.get('case_number', 'case')}"
    safe = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in raw)
    return f"{safe}.{extension.lstrip('.')}"


if __name__ == "__main__":  # pragma: no cover - manual inspection helper
    import sys

    # The box-drawing characters used by the text report are outside the default
    # Windows console code page, so switch the stream to UTF-8 where possible.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    options = case_options()
    if not options:
        print("No cases in the database. Run: python setup_db.py")
    else:
        data = generate_intelligence_report(options[0][0], generated_by="cli")
        print(format_report_as_text(data))
        pdf_bytes = format_report_as_pdf(data)
        target = report_filename(data, "pdf")
        with open(target, "wb") as fh:
            fh.write(pdf_bytes)
        print(f"\n[reports] PDF written: {target} ({len(pdf_bytes)} bytes)")
