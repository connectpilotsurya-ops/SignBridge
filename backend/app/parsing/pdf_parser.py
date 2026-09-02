"""
PyMuPDF-based resume parser.

Spec §10 is explicit that plain-text extraction is not enough — the whole
anti-gaming story depends on knowing WHERE on the page each run of text
sits, what font/size/color it used, and whether it's actually perceptible.
This module is the only place in the codebase that touches `fitz` directly;
everything downstream works off `TextChunk` objects.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass

import fitz  # PyMuPDF

from app.parsing.color_utils import contrast_ratio, int_to_hex
from app.parsing.constants import SECTION_HEADINGS

TINY_FONT_RATIO = 0.55  # a span under 55% of the doc's median body size is "tiny"
TINY_FONT_ABS_PT = 6.0  # ...or under this absolute size, whichever triggers first
HIDDEN_CONTRAST_MAX = 1.15  # WCAG ratio below this = indistinguishable from bg
LOW_CONTRAST_MAX = 2.2  # below this but above HIDDEN = "near-white", perceptible but faint
FOOTER_BAND_FRACTION = 0.92  # y beyond 92% of page height counts as footer band


class UnreadablePDFError(Exception):
    """Raised for corrupted, empty, or image-only (scanned) PDFs."""


@dataclass
class ParsedResume:
    chunks: list[dict]
    page_count: int
    page_sizes: list[tuple[float, float]]  # (width, height) per page
    raw_text_len: int


def _match_section(line_text: str) -> str | None:
    low = line_text.strip().lower()
    if len(low) > 40:  # heading lines are short
        return None
    for section, aliases in SECTION_HEADINGS.items():
        if low in aliases or any(low.startswith(a) for a in aliases):
            return section
    return None


def parse_resume_pdf(file_bytes: bytes) -> ParsedResume:
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:  # noqa: BLE001 - fitz raises various C-level errors
        raise UnreadablePDFError(f"Could not open PDF: {exc}") from exc

    if doc.page_count == 0:
        raise UnreadablePDFError("PDF has zero pages.")

    all_spans: list[dict] = []
    font_sizes: list[float] = []
    page_sizes: list[tuple[float, float]] = []
    raw_text_len = 0
    current_section = "unknown"

    for page_index in range(doc.page_count):
        page = doc[page_index]
        page_sizes.append((page.rect.width, page.rect.height))

        # Filled rectangles behind text (a common hiding trick: white text on
        # a white *drawn* rectangle rather than relying on the page bg) so we
        # can estimate a real background color instead of assuming #FFFFFF.
        fills: list[tuple[fitz.Rect, str]] = []
        try:
            for d in page.get_drawings():
                if d.get("fill") is not None and d.get("rect") is not None:
                    r, g, b = (int(c * 255) for c in d["fill"])
                    fills.append((fitz.Rect(d["rect"]), f"#{r:02X}{g:02X}{b:02X}"))
        except Exception:  # noqa: BLE001 - drawing extraction is best-effort
            fills = []

        page_dict = page.get_text("dict")
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:  # 0 = text block
                continue
            for line in block.get("lines", []):
                line_text = "".join(s.get("text", "") for s in line.get("spans", []))
                section_hit = _match_section(line_text)
                if section_hit:
                    current_section = section_hit
                    continue  # heading lines aren't evidence content themselves

                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue
                    raw_text_len += len(text)
                    size = float(span.get("size", 0.0))
                    font_sizes.append(size)
                    color_hex = int_to_hex(int(span.get("color", 0)))
                    bbox = span.get("bbox", (0, 0, 0, 0))
                    x0, y0, x1, y1 = bbox

                    bg_hex = "#FFFFFF"
                    span_rect = fitz.Rect(bbox)
                    for rect, fill_hex in fills:
                        if rect.intersects(span_rect):
                            bg_hex = fill_hex
                            break

                    all_spans.append(
                        {
                            "text": text,
                            "page": page_index + 1,
                            "font_size": size,
                            "font_name": span.get("font", ""),
                            "color_hex": color_hex,
                            "bg_color_hex": bg_hex,
                            "x": x0,
                            "y": y0,
                            "width": x1 - x0,
                            "height": y1 - y0,
                            "block_type": "text",
                            "section": current_section,
                            "page_width": page.rect.width,
                            "page_height": page.rect.height,
                        }
                    )

    page_count = doc.page_count
    doc.close()

    if raw_text_len == 0:
        raise UnreadablePDFError(
            "No extractable text found — this looks like a scanned/image-only "
            "PDF. OCR is not enabled in this MVP; ask the candidate for a "
            "text-based PDF."
        )

    median_size = statistics.median(font_sizes) if font_sizes else 10.0
    tiny_threshold = max(TINY_FONT_ABS_PT, median_size * TINY_FONT_RATIO)

    for span in all_spans:
        contrast = contrast_ratio(span["color_hex"], span["bg_color_hex"])
        off_page = (
            span["x"] < 0
            or span["y"] < 0
            or span["x"] > span["page_width"]
            or span["y"] > span["page_height"]
        )
        footer_band = span["y"] > span["page_height"] * FOOTER_BAND_FRACTION

        if off_page:
            visibility = "off_page"
        elif contrast < HIDDEN_CONTRAST_MAX:
            visibility = "hidden"
        elif contrast < LOW_CONTRAST_MAX:
            visibility = "low_contrast"
        else:
            visibility = "visible"

        span["visibility"] = visibility
        span["is_tiny_font"] = span["font_size"] < tiny_threshold
        span["is_footer_band"] = footer_band

    return ParsedResume(
        chunks=all_spans,
        page_count=page_count,
        page_sizes=page_sizes,
        raw_text_len=raw_text_len,
    )
