#!/usr/bin/env python3
"""Convert LOGBOOK_BUSINESS.md to PDF with Mermaid diagrams, markdown images, and optional raw HTML.

Mermaid blocks are rendered via mermaid-cli. Lines of the form ![alt](figures/...) embed PNGs from the repo.
Fenced blocks with language `html` are passed to fpdf.write_html (e.g. reference tables).

Requires: Node.js (npx) on PATH. First run may download @mermaid-js/mermaid-cli (network).
Optional: Pillow for accurate diagram scaling (pip install pillow).
"""

from __future__ import annotations

import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import TextEmphasis
from fpdf.fonts import FontFace, TextStyle

# System font with wide Unicode coverage (em dash, £, ×, etc.)
_UNICODE_FONT = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
# Bold TTF for headings and <b>…</b> (Helvetica-Bold cannot encode →, £, — inside bold spans).
_UNICODE_FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
_BODY_BD_FAMILY = "BodyBd"

# Mermaid PNG: higher canvas + neutral theme + scale for sharper downscale in PDF
_MERMAID_WIDTH = 1120
_MERMAID_HEIGHT = 630
_MERMAID_SCALE = "1.72"
_MERMAID_THEME = "neutral"

# Flowcharts: slightly taller box than before so labels stay readable
_DIAGRAM_MAX_WIDTH_MM = 168.0
_DIAGRAM_MAX_HEIGHT_MM = 58.0
# First diagram: larger on-page box (within A4 text width with margins).
_DIAGRAM_FIRST_MAX_WIDTH_MM = 179.0
_DIAGRAM_FIRST_MAX_HEIGHT_MM = 84.0
# Sharper raster when the first figure is shown larger.
_MERMAID_FIRST_WIDTH = 1440
_MERMAID_FIRST_HEIGHT = 810
_MERMAID_FIRST_SCALE = "2.0"

# Caption for the first Mermaid (replaces generic "— diagram").
_FIRST_MERMAID_CAPTION = (
    "Figure 1 — Research and inputs, Python modelling loop, generated outputs, "
    "then report writing and presentation"
)

# Logbook entry subtitle: only treat the line after the date as a subtitle when it is
# short and followed by a blank line (otherwise it is normal body text).
_SUBTITLE_MAX_CHARS = 110

# Content width inside default 15 mm side margins on A4
_BODY_IMG_WIDTH_MM = 168.0
# Exported matplotlib tables: allow nearly full page height
_TABLE_IMG_MAX_HEIGHT_MM = 176.0
# Web screenshots: cap height so UI text stays readable (tuned upward vs earlier pass)
_SCREENSHOT_IMG_MAX_HEIGHT_MM = 108.0
# Evidence PNGs (tables, screenshots, etc.)
_MISC_IMG_MAX_HEIGHT_MM = 74.0

# Vertical gap between figure frame bottom and caption (caption is drawn below the image).
_GAP_MM_FRAME_TO_CAPTION = 1.25

_MD_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

_DATE_LINE = re.compile(
    r"^\s*(\d{1,2}(?:st|nd|rd|th)?)\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"(\d{4})\s*$",
    re.IGNORECASE,
)


def iter_segments(raw: str) -> list[tuple[str, str]]:
    """Split markdown into ('text', chunk) and ('mermaid', source) segments."""
    segments: list[tuple[str, str]] = []
    pos = 0
    while True:
        i = raw.find("```", pos)
        if i == -1:
            if pos < len(raw):
                segments.append(("text", raw[pos:]))
            break
        if i > pos:
            segments.append(("text", raw[pos:i]))
        nl = raw.find("\n", i + 3)
        if nl == -1:
            segments.append(("text", raw[i:]))
            break
        lang = raw[i + 3 : nl].strip().lower()
        j = raw.find("```", nl + 1)
        if j == -1:
            segments.append(("text", raw[i:]))
            break
        body = raw[nl + 1 : j].rstrip("\n")
        if lang == "mermaid":
            segments.append(("mermaid", body))
        elif lang == "html":
            segments.append(("rawhtml", body))
        else:
            segments.append(("code", body))
        pos = j + 3
        if pos < len(raw) and raw[pos] == "\n":
            pos += 1
    return segments


def iter_text_and_images(md_chunk: str) -> list[tuple[str, str, str]]:
    """Split a text segment into ordered pieces: ('text', body, '') or ('image', alt, path)."""
    pieces: list[tuple[str, str, str]] = []
    pos = 0
    for m in _MD_IMAGE.finditer(md_chunk):
        before = md_chunk[pos : m.start()]
        if before:
            pieces.append(("text", before, ""))
        pieces.append(("image", m.group(1).strip(), m.group(2).strip()))
        pos = m.end()
    tail = md_chunk[pos:]
    if tail:
        pieces.append(("text", tail, ""))
    return pieces


def _body_font_family(use_unicode: bool) -> str:
    return "Body" if use_unicode else "Helvetica"


def _html_tag_styles_body(body_family: str, *, bold_face_name: str) -> dict[str, FontFace | TextStyle]:
    """Typography for narrative blocks (document title, dates, optional subtitles, body).

    ``body_family`` carries normal-weight Unicode text. Headings and ``<b>`` use
    ``bold_face_name``: either the registered ``BodyBd`` (Arial Bold TTF) so arrows and
    currency in bold spans render, or ``Helvetica`` with synthetic bold (ASCII-only safe).
    """
    ink = (26, 28, 34)
    date_ink = (28, 36, 52)
    subtitle_ink = (38, 48, 62)
    title_ink = (22, 28, 44)
    use_ttf_bold = bold_face_name == _BODY_BD_FAMILY

    def _head(sz: float, color: tuple[int, int, int], t_m: float, b_m: float) -> TextStyle:
        return TextStyle(
            font_family=bold_face_name,
            font_style="" if use_ttf_bold else "B",
            font_size_pt=sz,
            color=color,
            t_margin=t_m,
            b_margin=b_m,
            l_margin=0,
        )

    b_tag = (
        FontFace(family=bold_face_name, color=ink)
        if use_ttf_bold
        else FontFace(family=bold_face_name, emphasis=TextEmphasis.B, color=ink)
    )
    return {
        "h1": _head(15.5, title_ink, 1.2, 2.0),
        "h2": _head(12.0, date_ink, 2.2, 1.2),
        "h3": _head(10.75, subtitle_ink, 0.1, 1.6),
        "p": TextStyle(
            font_family=body_family,
            font_style="",
            font_size_pt=9.0,
            color=ink,
            t_margin=0.35,
            b_margin=1.85,
            l_margin=0,
        ),
        "ul": TextStyle(
            font_family=body_family,
            font_style="",
            font_size_pt=9.0,
            color=ink,
            t_margin=0.85,
            b_margin=1.5,
            l_margin=4.0,
        ),
        "li": TextStyle(
            font_family=body_family,
            font_style="",
            font_size_pt=9.0,
            color=ink,
            t_margin=0.15,
            b_margin=0.85,
            l_margin=5.2,
        ),
        "b": b_tag,
        "i": FontFace(family=body_family, emphasis=TextEmphasis.I, color=ink),
    }


def _style_reference_table_html(html: str) -> str:
    """Presentation tweaks fpdf2 can render without custom tag_styles.

    fpdf2 only allows ``tag_styles`` for tags in its built-in default set; ``<table>``,
    ``<th>``, and ``<td>`` are not included, so styling uses cellpadding and ``bgcolor``.
    """
    s = html.strip()
    m = re.match(r"(?is)(<table)(\s[^>]*)(>)", s)
    if m:
        attrs = m.group(2)
        if not re.search(r"(?i)\scellpadding\s*=", attrs):
            insert = ' cellpadding="1.85" cellspacing="0"'
            s = f"{m.group(1)}{insert}{m.group(2)}{m.group(3)}" + s[m.end() :]

    def _th_bg(m: re.Match[str]) -> str:
        inner, end = m.group(1), m.group(2)
        if re.search(r"(?i)\sbgcolor\s*=", inner):
            return m.group(0)
        # Pale header band; body text stays dark (fpdf uses current text colour in cells).
        return f'<th{inner} bgcolor="#E4E8F0"{end}'

    return re.sub(r"(?is)<th(\s[^>]*?)(>)", _th_bg, s)


def _escape_html(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


_CODE_SINGLE = re.compile(r"`([^`]+)`")
_BULLET_LINE = re.compile(r"^\s*-\s+(.*)$")


def _apply_inline_md_to_html(s: str) -> str:
    """Escape user text, apply **bold** / *italic*, and `inline code` (no raw HTML in input)."""
    stash: list[str] = []

    def _stash_code(m: re.Match[str]) -> str:
        stash.append(m.group(1))
        return f"\x7fCODE{len(stash) - 1}\x7f"

    s2 = _CODE_SINGLE.sub(_stash_code, s)
    parts: list[str] = []
    pos = 0
    for m in re.finditer(r"\*\*(.+?)\*\*", s2):
        parts.append(_escape_html(s2[pos : m.start()]))
        parts.append("<b>" + _escape_html(m.group(1)) + "</b>")
        pos = m.end()
    parts.append(_escape_html(s2[pos:]))
    body = "".join(parts)
    body2: list[str] = []
    pos = 0
    for m in re.finditer(r"(?<!\*)\*([^*]+?)\*(?!\*)", body):
        body2.append(body[pos : m.start()])
        body2.append("<i>" + m.group(1) + "</i>")
        pos = m.end()
    body2.append(body[pos:])
    out = "".join(body2)
    for i, chunk in enumerate(stash):
        out = out.replace(f"\x7fCODE{i}\x7f", "<code>" + _escape_html(chunk) + "</code>")
    return out


def _block_lines_to_html(text: str) -> str:
    """Turn one markdown block into <p> / <ul> HTML (newlines → <br/> only inside paragraphs)."""
    lines = [ln.rstrip() for ln in text.split("\n")]
    i = 0
    n = len(lines)
    chunks: list[str] = []
    while i < n:
        while i < n and not lines[i].strip():
            i += 1
        if i >= n:
            break
        if _BULLET_LINE.match(lines[i]):
            items: list[str] = []
            while i < n and _BULLET_LINE.match(lines[i]):
                m = _BULLET_LINE.match(lines[i])
                assert m is not None
                items.append(m.group(1).strip())
                i += 1
            lis = "".join(f"<li>{_apply_inline_md_to_html(it)}</li>" for it in items)
            chunks.append(
                '<ul style="line-height: 1.42;">' + lis + "</ul>"
            )
            continue
        buf: list[str] = []
        while i < n:
            if not lines[i].strip():
                break
            if _BULLET_LINE.match(lines[i]):
                break
            buf.append(lines[i])
            i += 1
        para = "\n".join(buf).strip()
        if para:
            inner = _apply_inline_md_to_html(para).replace("\n", "<br/>")
            chunks.append(f"<p>{inner}</p>")
    return "".join(chunks)


def _paragraph_block_to_html(block: str) -> list[str]:
    """One logbook entry → HTML fragments: ``<h2>`` alone, then body ``<p>``/``<ul>`` in a second fragment.

    Splitting heading and body avoids ``fpdf2`` keeping the heading's bold graphics state for
    paragraphs in the same ``write_html`` feed.

    When a subtitle is detected (short line after the date, followed by a blank line), the
    heading is ``<h2>DATE: subtitle</h2>`` (BodyBd). Otherwise ``<h2>DATE</h2>`` only.
    """
    block = block.strip()
    if not block:
        return []
    lines = block.split("\n")
    first = lines[0].strip()
    m = _DATE_LINE.match(first)
    if not m:
        h = _block_lines_to_html(block)
        return [h] if h.strip() else []

    i = 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines):
        return [f"<h2>{_escape_html(first)}</h2>"]

    cand = lines[i].strip()
    if _DATE_LINE.match(cand):
        rest = "\n".join(lines[i:]).strip()
        frags: list[str] = [f"<h2>{_escape_html(first)}</h2>"]
        if rest:
            b = _block_lines_to_html(rest)
            if b.strip():
                frags.append(b)
        return frags

    next_is_blank = i + 1 < len(lines) and not lines[i + 1].strip()
    is_subtitle = next_is_blank and len(cand) <= _SUBTITLE_MAX_CHARS
    if is_subtitle:
        combined = f"{_escape_html(first)}: {_apply_inline_md_to_html(cand)}"
        frags = [f"<h2>{combined}</h2>"]
        i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
    else:
        frags = [f"<h2>{_escape_html(first)}</h2>"]

    rest_lines = lines[i:]
    rest = "\n".join(rest_lines).strip()
    if rest:
        b = _block_lines_to_html(rest)
        if b.strip():
            frags.append(b)
    return frags


def md_text_to_html_chunks(text: str, *, lead_is_doc_title: bool = False) -> list[str]:
    """Build HTML fragments for ``write_html`` (one fragment per preamble / dated entry / orphan).

    Each dated entry uses **separate** ``write_html`` fragments: the ``<h2>`` (and ``<h1>``)
    alone, then body HTML, so ``fpdf2`` does not draw normal paragraphs with the heading's
    bold weight after a ``BodyBd`` title.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    n = len(lines)
    i = 0
    parts: list[str] = []

    while i < n and not lines[i].strip():
        i += 1

    preamble_end = i
    while preamble_end < n:
        s = lines[preamble_end].strip()
        if s and _DATE_LINE.match(s):
            break
        preamble_end += 1

    pre_lines = lines[i:preamble_end]
    i = preamble_end
    pre = "\n".join(pre_lines).strip()
    if pre:
        fl = pre.split("\n", 1)[0].strip()
        if not _DATE_LINE.match(fl):
            if lead_is_doc_title:
                title_inner = "<br/>".join(
                    _escape_html(x.strip()) for x in pre.split("\n") if x.strip()
                )
                parts.append(f"<h1>{title_inner}</h1>")
            else:
                parts.append(_block_lines_to_html(pre))
        else:
            parts.extend(_paragraph_block_to_html(pre))

    while i < n:
        while i < n and not lines[i].strip():
            i += 1
        if i >= n:
            break
        s0 = lines[i].strip()
        if not _DATE_LINE.match(s0):
            start_orphan = i
            while i < n:
                s = lines[i].strip()
                if s and _DATE_LINE.match(s):
                    break
                i += 1
            orphan = "\n".join(lines[start_orphan:i]).strip()
            if orphan:
                parts.append(_block_lines_to_html(orphan))
            continue
        start = i
        i += 1
        while i < n:
            s = lines[i].strip()
            if s and _DATE_LINE.match(s):
                break
            i += 1
        entry = "\n".join(lines[start:i]).strip()
        if entry:
            parts.extend(_paragraph_block_to_html(entry))

    return parts


def render_mermaid(
    source: str,
    out_png: Path,
    mmd_path: Path,
    *,
    width: int | None = None,
    height: int | None = None,
    scale: str | None = None,
) -> None:
    mmd_path.write_text(source.strip() + "\n", encoding="utf-8")
    npx = shutil.which("npx")
    if not npx:
        raise RuntimeError("npx not found; install Node.js to render Mermaid diagrams.")
    w = int(width or _MERMAID_WIDTH)
    h = int(height or _MERMAID_HEIGHT)
    s = scale or _MERMAID_SCALE
    cmd = [
        npx,
        "--yes",
        "@mermaid-js/mermaid-cli",
        "-i",
        str(mmd_path),
        "-o",
        str(out_png),
        "-b",
        "white",
        "-t",
        _MERMAID_THEME,
        "-w",
        str(w),
        "-H",
        str(h),
        "-s",
        s,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=180, cwd=str(out_png.parent))


def _diagram_display_mm(
    png_path: Path,
    max_w_mm: float,
    max_h_mm: float,
) -> tuple[float, float]:
    """Return (width_mm, height_mm) to fit image inside box, uniform scale, never upscale."""
    try:
        from PIL import Image

        with Image.open(png_path) as im:
            pw, ph = im.size
    except Exception:
        pw, ph = _MERMAID_WIDTH, _MERMAID_HEIGHT
    if pw <= 0 or ph <= 0:
        return max_w_mm * 0.9, max_h_mm * 0.9
    aspect = ph / pw
    w_at_full = max_w_mm
    h_at_full = w_at_full * aspect
    if h_at_full <= max_h_mm:
        return w_at_full, h_at_full
    h = max_h_mm
    w = h / aspect
    return w, h


def _markdown_image_max_dims(rel_path: str) -> tuple[float, float]:
    """Return (max_w_mm, max_h_mm) tuned by asset type (screenshot vs data table)."""
    name = Path(rel_path).name.lower()
    w = _BODY_IMG_WIDTH_MM
    if name.startswith("ss_"):
        return w, _SCREENSHOT_IMG_MAX_HEIGHT_MM
    if name.startswith("table_"):
        return w, _TABLE_IMG_MAX_HEIGHT_MM
    return w, _MISC_IMG_MAX_HEIGHT_MM


def _markdown_image_frame_params(rel_path: str) -> tuple[float, float, float, tuple[int, int, int] | None, tuple[int, int, int]]:
    """Figure chrome: (tail_after_caption_mm, pad_mm, line_w_mm, frame_fill or None, frame_edge RGB).

    ``tail_after_caption_mm`` is extra vertical space after the caption ``multi_cell`` (caption sits
    below the figure; see ``_GAP_MM_FRAME_TO_CAPTION``).
    """
    name = Path(rel_path).name.lower()
    if name.startswith("table_"):
        return (5.5, 1.35, 0.14, (246, 249, 253), (186, 194, 206))
    if name.startswith("ss_"):
        return (4.25, 0.85, 0.10, None, (200, 206, 216))
    return (4.65, 1.12, 0.11, (252, 253, 255), (210, 217, 228))


def _ensure_vertical_room(pdf: FPDF, needed_mm: float) -> None:
    if pdf.get_y() + needed_mm > pdf.h - pdf.b_margin - 1.0:
        pdf.add_page()


def _approx_caption_height_mm(
    pdf: FPDF,
    family: str,
    text: str,
    width_mm: float,
    font_pt: float,
    line_h_mm: float,
) -> float:
    """Rough height for a wrapped caption (avoids clipping when reserving page space)."""
    pdf.set_font(family, size=font_pt)
    usable = max(25.0, width_mm - 1.0)
    sw = pdf.get_string_width(text.replace("\n", " "))
    # Word wrap usually needs more lines than monotonic width / page width.
    lines = max(1, math.ceil(1.12 * sw / usable) + text.count("\n"))
    return lines * line_h_mm + 1.5


def _emit_fitted_png(
    pdf: FPDF,
    png_path: Path,
    max_w_mm: float,
    max_h_mm: float,
    *,
    draw_frame: bool,
    gap_after_mm: float,
    frame_fill: tuple[int, int, int] | None = None,
    frame_edge: tuple[int, int, int] = (200, 205, 214),
    line_w_mm: float = 0.15,
    pad_mm: float = 1.1,
) -> None:
    w_mm, h_mm = _diagram_display_mm(png_path, max_w_mm, max_h_mm)
    x0 = pdf.l_margin
    y0 = pdf.get_y()
    pad = pad_mm
    outer_w = w_mm + 2 * pad
    outer_h = h_mm + 2 * pad
    apb = pdf.auto_page_break
    bm = pdf.b_margin
    pdf.set_auto_page_break(False)
    try:
        if draw_frame:
            pdf.set_line_width(line_w_mm)
            pdf.set_draw_color(*frame_edge)
            if frame_fill is not None:
                pdf.set_fill_color(*frame_fill)
                pdf.rect(x0 - pad, y0 - pad, outer_w, outer_h, style="FD")
            else:
                pdf.rect(x0 - pad, y0 - pad, outer_w, outer_h, style="D")
        pdf.image(str(png_path), x=x0, y=y0, w=w_mm, h=h_mm)
    finally:
        pdf.set_auto_page_break(apb, margin=bm)
    pdf.set_y(y0 + outer_h + gap_after_mm)


def _emit_diagram(
    pdf: FPDF,
    png_path: Path,
    *,
    max_w_mm: float = _DIAGRAM_MAX_WIDTH_MM,
    max_h_mm: float = _DIAGRAM_MAX_HEIGHT_MM,
    pad_mm: float = 2.0,
) -> None:
    """Draw Mermaid PNG. Caller draws the caption below the figure."""
    _emit_fitted_png(
        pdf,
        png_path,
        max_w_mm,
        max_h_mm,
        draw_frame=True,
        gap_after_mm=_GAP_MM_FRAME_TO_CAPTION,
        frame_fill=(247, 249, 252),
        frame_edge=(188, 196, 208),
        line_w_mm=0.13,
        pad_mm=pad_mm,
    )


def _emit_markdown_image(pdf: FPDF, png_path: Path, rel_for_sizing: str) -> None:
    """Draw markdown image (frame + bitmap). Caption is drawn by the caller, below the figure."""
    max_w, max_h = _markdown_image_max_dims(rel_for_sizing)
    _, pad_mm, line_w, fill, edge = _markdown_image_frame_params(rel_for_sizing)
    _emit_fitted_png(
        pdf,
        png_path,
        max_w,
        max_h,
        draw_frame=True,
        gap_after_mm=_GAP_MM_FRAME_TO_CAPTION,
        frame_fill=fill,
        frame_edge=edge,
        line_w_mm=line_w,
        pad_mm=pad_mm,
    )


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    if len(sys.argv) > 1:
        src_arg = Path(sys.argv[1])
        md_path = src_arg if src_arg.is_absolute() else root / src_arg
    else:
        md_path = root / "LOGBOOK_BUSINESS.md"
    out_path = root / "figures" / f"{md_path.stem}.pdf"
    if not md_path.is_file():
        print(f"Missing {md_path}", file=sys.stderr)
        return 1

    raw = md_path.read_text(encoding="utf-8")
    segments = iter_segments(raw)

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    use_unicode = Path(_UNICODE_FONT).is_file()
    body_font = _body_font_family(use_unicode)
    if use_unicode:
        pdf.add_font("Body", "", _UNICODE_FONT)
        pdf.add_font("Body", "B", _UNICODE_FONT)
        pdf.add_font("Body", "I", _UNICODE_FONT)
        pdf.set_font("Body", size=9)
    else:
        pdf.set_font("Helvetica", size=9)

    bold_face = "Helvetica"
    if use_unicode and Path(_UNICODE_FONT_BOLD).is_file():
        pdf.add_font(_BODY_BD_FAMILY, "", _UNICODE_FONT_BOLD)
        bold_face = _BODY_BD_FAMILY

    tag_styles_body = _html_tag_styles_body(body_font, bold_face_name=bold_face)

    pdf.set_margins(left=15, top=18, right=15)
    pdf.add_page()
    mermaid_idx = 0
    first_md_slice = True

    with tempfile.TemporaryDirectory(prefix="logbook_mermaid_") as tmp:
        tmp_path = Path(tmp)
        for kind, chunk in segments:
            if kind == "text":
                for piece_kind, a, b in iter_text_and_images(chunk):
                    if piece_kind == "text":
                        if not a.strip():
                            continue
                        frags = md_text_to_html_chunks(a, lead_is_doc_title=first_md_slice)
                        first_md_slice = False
                        for frag in frags:
                            if not frag.strip():
                                continue
                            try:
                                pdf.set_font(body_font, size=9)
                                pdf.write_html(
                                    frag,
                                    tag_styles=tag_styles_body,
                                    ul_bullet_char="disc",
                                    li_prefix_color=(78, 86, 100),
                                )
                            except Exception as exc:
                                if pdf.page_no() == 0:
                                    pdf.add_page()
                                pdf.set_text_color(0, 0, 0)
                                pdf.set_font(body_font, size=9)
                                pdf.multi_cell(
                                    0, 5, f"[HTML render error: {exc}]", new_x="LMARGIN", new_y="NEXT"
                                )
                    else:
                        alt, rel = a, b
                        img_path = Path(rel)
                        if not img_path.is_absolute():
                            img_path = (root / img_path).resolve()
                        if not img_path.is_file():
                            pdf.set_font(body_font, size=9)
                            pdf.set_text_color(180, 0, 0)
                            pdf.multi_cell(
                                0,
                                5,
                                f"[Missing image file: {img_path}]",
                                new_x="LMARGIN",
                                new_y="NEXT",
                            )
                            pdf.set_text_color(0, 0, 0)
                            continue
                        cap = alt if alt else str(img_path.name)
                        max_w, max_h = _markdown_image_max_dims(rel)
                        w_mm, h_mm = _diagram_display_mm(img_path, max_w, max_h)
                        tail_i, pad_i, _, _, _ = _markdown_image_frame_params(rel)
                        outer_i = h_mm + 2 * pad_i + _GAP_MM_FRAME_TO_CAPTION
                        epw = pdf.w - pdf.l_margin - pdf.r_margin
                        pdf.set_font(body_font, size=8.2)
                        cap_h = _approx_caption_height_mm(pdf, body_font, cap, epw, 8.2, 4.35)
                        _ensure_vertical_room(pdf, 2.0 + outer_i + cap_h + tail_i + 2.0)
                        pdf.ln(1.0)
                        try:
                            _emit_markdown_image(pdf, img_path, rel)
                            pdf.set_font(body_font, size=8.2)
                            pdf.set_text_color(62, 68, 82)
                            pdf.multi_cell(0, 4.35, cap, new_x="LMARGIN", new_y="NEXT")
                            pdf.set_text_color(0, 0, 0)
                            pdf.set_font(body_font, size=9)
                            pdf.ln(tail_i)
                        except Exception as exc:
                            pdf.set_font(body_font, size=9)
                            pdf.multi_cell(
                                0,
                                5,
                                f"[Image render error ({img_path.name}): {exc}]",
                                new_x="LMARGIN",
                                new_y="NEXT",
                            )
            elif kind == "mermaid":
                mermaid_idx += 1
                mmd = tmp_path / f"diagram_{mermaid_idx}.mmd"
                png = tmp_path / f"diagram_{mermaid_idx}.png"
                is_first_diagram = mermaid_idx == 1
                try:
                    if is_first_diagram:
                        render_mermaid(
                            chunk,
                            png,
                            mmd,
                            width=_MERMAID_FIRST_WIDTH,
                            height=_MERMAID_FIRST_HEIGHT,
                            scale=_MERMAID_FIRST_SCALE,
                        )
                    else:
                        render_mermaid(chunk, png, mmd)
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, RuntimeError) as exc:
                    err = getattr(exc, "stderr", None) or getattr(exc, "stdout", None) or str(exc)
                    pdf.set_font(body_font, size=9)
                    pdf.multi_cell(
                        0,
                        5,
                        f"[Mermaid diagram {mermaid_idx} failed to render: {err[:500]}]",
                        new_x="LMARGIN",
                        new_y="NEXT",
                    )
                    continue
                cap = _FIRST_MERMAID_CAPTION if is_first_diagram else f"Figure {mermaid_idx} — diagram"
                tail_d = 4.8
                if is_first_diagram:
                    w_max, h_max = _DIAGRAM_FIRST_MAX_WIDTH_MM, _DIAGRAM_FIRST_MAX_HEIGHT_MM
                    pad_d = 2.15
                else:
                    w_max, h_max = _DIAGRAM_MAX_WIDTH_MM, _DIAGRAM_MAX_HEIGHT_MM
                    pad_d = 2.0
                w_mm, h_mm = _diagram_display_mm(png, w_max, h_max)
                outer_d = h_mm + 2 * pad_d + _GAP_MM_FRAME_TO_CAPTION
                epw = pdf.w - pdf.l_margin - pdf.r_margin
                pdf.set_font(body_font, size=8.1)
                cap_h = _approx_caption_height_mm(pdf, body_font, cap, epw, 8.1, 4.25)
                _ensure_vertical_room(pdf, 2.5 + outer_d + cap_h + tail_d + 2.0)
                pdf.ln(2.0)
                _emit_diagram(pdf, png, max_w_mm=w_max, max_h_mm=h_max, pad_mm=pad_d)
                pdf.set_font(body_font, size=8.1)
                pdf.set_text_color(62, 68, 82)
                pdf.multi_cell(0, 4.25, cap, new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(0, 0, 0)
                pdf.set_font(body_font, size=9)
                pdf.ln(tail_d)
            elif kind == "rawhtml":
                html_body = _style_reference_table_html(chunk.strip())
                if html_body:
                    try:
                        _ensure_vertical_room(pdf, 98.0)
                        pdf.ln(3.2)
                        pdf.set_font(body_font, size=7.5)
                        pdf.set_text_color(26, 28, 36)
                        pdf.write_html(html_body, table_line_separators=True)
                        pdf.set_text_color(0, 0, 0)
                        pdf.ln(4.5)
                        pdf.set_font(body_font, size=9)
                    except Exception as exc:
                        pdf.set_font(body_font, size=9)
                        pdf.multi_cell(
                            0,
                            5,
                            f"[HTML block render error: {exc}]",
                            new_x="LMARGIN",
                            new_y="NEXT",
                        )
            elif kind == "code":
                pdf.set_font(body_font, size=8)
                safe = _escape_html(chunk[:4000])
                pdf.set_fill_color(247, 248, 250)
                pdf.set_draw_color(220, 224, 230)
                pdf.set_line_width(0.2)
                pdf.write_html(f"<pre>{safe}</pre>")
                pdf.ln(2)
                pdf.set_font(body_font, size=9)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out_path))
    print(
        f"Wrote {out_path} ({pdf.page_no()} pages, {mermaid_idx} Mermaid diagram(s)); "
        f"default Mermaid canvas {_MERMAID_WIDTH}x{_MERMAID_HEIGHT} @ {_MERMAID_SCALE!r}, "
        f"first diagram {_MERMAID_FIRST_WIDTH}x{_MERMAID_FIRST_HEIGHT} @ {_MERMAID_FIRST_SCALE!r}, "
        f"theme {_MERMAID_THEME!r}; diagram box max "
        f"{_DIAGRAM_FIRST_MAX_WIDTH_MM}x{_DIAGRAM_FIRST_MAX_HEIGHT_MM} mm (fig 1) / "
        f"{_DIAGRAM_MAX_WIDTH_MM}x{_DIAGRAM_MAX_HEIGHT_MM} mm (others)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
