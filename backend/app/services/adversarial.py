"""
Adversarial resume simulator — spec §29. Takes a clean base resume PDF and
produces six attack variants, one per manipulation technique, using
PyMuPDF to actually inject the manipulation (not a simulated/fake report
— the same parser and integrity detector used on every real upload runs
against these variants). This is primarily a product-demonstration and
regression-testing feature, exactly as spec §29 frames it.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

import fitz

from app.integrity.detector import analyze_integrity
from app.parsing.constants import DISPLAY_NAMES
from app.parsing.pdf_parser import parse_resume_pdf

ATTACK_KEYWORDS = {
    "white_text_injection": ["kubernetes", "terraform"],
    "tiny_text_injection": ["azure", "gcp"],
    "footer_keyword_stuffing": ["react", "angular", "java", "c++"],
    "repeated_keywords": ["devops"],
    "skills_only_manipulation": [
        "elasticsearch", "spark", "hadoop", "scala", "rust", "golang", "kafka",
        "grpc", "graphql", "pulumi", "ansible", "helm", "cloudformation", "vue.js",
        "mysql", "nosql", "jenkins", "spring",
    ],
    "hidden_section_manipulation": ["mongodb", "redis"],
}

ATTACK_LABELS = {
    "white_text_injection": "White text injection",
    "tiny_text_injection": "Tiny text injection",
    "footer_keyword_stuffing": "Footer keyword stuffing",
    "repeated_keywords": "Repeated keywords",
    "skills_only_manipulation": "Skills-only manipulation",
    "hidden_section_manipulation": "Hidden section manipulation",
}


def _display(term: str) -> str:
    return DISPLAY_NAMES.get(term, term.title())


def _open_copy(base_pdf: bytes) -> fitz.Document:
    return fitz.open(stream=base_pdf, filetype="pdf")


def _save(doc: fitz.Document) -> bytes:
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def build_attack_variant(base_pdf: bytes, attack: str) -> bytes:
    doc = _open_copy(base_pdf)
    page = doc[-1]
    ph = page.rect.height
    words = " ".join(_display(k) for k in ATTACK_KEYWORDS[attack])

    if attack == "white_text_injection":
        page.insert_text((72, ph - 40), words, fontsize=9, color=(1, 1, 1))

    elif attack == "tiny_text_injection":
        page.insert_text((72, ph - 60), words, fontsize=3, color=(0, 0, 0))

    elif attack == "footer_keyword_stuffing":
        page.insert_text((72, ph - 18), words, fontsize=8, color=(0.4, 0.4, 0.4))

    elif attack == "repeated_keywords":
        term = _display(ATTACK_KEYWORDS[attack][0])
        line = " ".join([term] * 6)
        page.insert_text((72, ph - 80), line, fontsize=9, color=(0, 0, 0))

    elif attack == "skills_only_manipulation":
        # A single comma-joined line this long silently overflows the page
        # width — PyMuPDF's insert_text has no wrapping and drops
        # characters past the right edge rather than erroring, which was
        # quietly truncating the tail of the list. Wrapping across a few
        # lines (as a real padded skills section usually looks anyway)
        # keeps every injected term intact and detectable regardless of
        # what else is on the page.
        page.insert_text((72, ph - 100), "Skills", fontsize=11, color=(0, 0, 0))
        terms = [_display(k) for k in ATTACK_KEYWORDS[attack]]
        chunk_size = 6
        for i in range(0, len(terms), chunk_size):
            row = ", ".join(terms[i : i + chunk_size])
            page.insert_text((72, ph - 118 - 14 * (i // chunk_size)), row, fontsize=9, color=(0, 0, 0))

    elif attack == "hidden_section_manipulation":
        rect = fitz.Rect(72, ph - 140, 300, ph - 120)
        page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
        page.insert_text((74, ph - 128), words, fontsize=9, color=(1, 1, 1))

    else:
        raise ValueError(f"Unknown attack type: {attack}")

    return _save(doc)


@dataclass
class AttackReport:
    attack_type: str
    label: str
    injected_keywords: list[str]
    detected: bool
    matching_impact: str
    integrity_impact: str
    flags_triggered: list[str]


def run_adversarial_suite(base_pdf: bytes) -> list[AttackReport]:
    reports: list[AttackReport] = []
    for attack, keywords in ATTACK_KEYWORDS.items():
        variant = build_attack_variant(base_pdf, attack)
        parsed = parse_resume_pdf(variant)
        integrity = analyze_integrity(parsed.chunks)

        suppressed = set(integrity.suppressed_terms)
        injected = set(keywords)
        excluded = bool(injected & suppressed)

        relevant_flags = [
            f for f in integrity.flags
            if any(kw in f.evidence_text.lower() for kw in keywords) or attack.replace("_", " ") in f.description.lower()
        ]
        # skills_only_manipulation and repeated_keywords may not suppress
        # terms outright (they're not hidden), but should still raise a flag.
        detected = excluded or bool(relevant_flags)

        severities = [f.severity.value for f in relevant_flags]
        if "high" in severities:
            integrity_impact = "HIGH"
        elif "medium" in severities:
            integrity_impact = "MEDIUM"
        elif severities:
            integrity_impact = "LOW"
        else:
            integrity_impact = "NONE"

        reports.append(
            AttackReport(
                attack_type=attack,
                label=ATTACK_LABELS[attack],
                injected_keywords=[_display(k) for k in keywords],
                detected=detected,
                matching_impact="EXCLUDED" if excluded else ("FLAGGED, NOT EXCLUDED" if detected else "INCLUDED (undetected)"),
                integrity_impact=integrity_impact,
                flags_triggered=[f.type.value for f in relevant_flags],
            )
        )
    return reports
