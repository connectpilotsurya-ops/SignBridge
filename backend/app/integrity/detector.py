"""
Deterministic anti-gaming / document-integrity engine — spec §11.

No LLM call happens in this file. Every flag here is derived purely from
the forensic metadata PyMuPDF gives us (color, size, position). We never
delete suspicious content; we flag it and hand `suppressed_terms` to the
scoring layer so it can zero (or heavily reduce) matching weight instead.
"""
from __future__ import annotations

import re
from collections import defaultdict

from app.parsing.constants import TECH_VOCAB
from app.schemas.enums import IntegrityCategory, IntegrityFlagType, IntegritySeverity
from app.schemas.integrity import IntegrityFlag, IntegrityReport

SEVERITY_WEIGHT = {
    IntegritySeverity.LOW: 5,
    IntegritySeverity.MEDIUM: 15,
    IntegritySeverity.HIGH: 35,
}

CONTACT_PATTERNS = [
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),  # email
    re.compile(r"\+?\d[\d\s().-]{7,}\d"),  # phone-ish
    re.compile(r"https?://|www\.", re.I),  # url
    re.compile(r"^\s*page\s*\d+\s*(of\s*\d+)?\s*$", re.I),  # "Page 2 of 3"
]

REPEATED_KEYWORD_THRESHOLD = 4
# A normal, honest resume very often lists 10-15 technologies tersely in its
# skills section — that alone must not read as manipulation. This threshold
# is tuned to catch deliberate buzzword-padding (skills lists that run well
# past what a genuine, evidence-backed skillset looks like) without flagging
# an ordinary comma-separated list.
SKILLS_DENSITY_MIN_HITS = 18
SKILLS_DENSITY_RATIO = 0.55


def _find_vocab_hits(text: str) -> list[str]:
    low = text.lower()
    return [term for term in TECH_VOCAB if term in low]


def _looks_like_contact_info(text: str) -> bool:
    return any(p.search(text) for p in CONTACT_PATTERNS)


def _group_by_page(chunks: list[dict], predicate) -> dict[int, list[dict]]:
    grouped: dict[int, list[dict]] = defaultdict(list)
    for c in chunks:
        if predicate(c):
            grouped[c["page"]].append(c)
    return grouped


def analyze_integrity(chunks: list[dict]) -> IntegrityReport:
    flags: list[IntegrityFlag] = []
    suppressed: set[str] = set()
    clean_terms: set[str] = set()  # terms seen in a normal, visible, non-footer chunk

    # ---- 1 & 2: hidden / near-white text -----------------------------------
    hidden_by_page = _group_by_page(chunks, lambda c: c["visibility"] == "hidden")
    for page, page_chunks in hidden_by_page.items():
        sample = " ".join(c["text"] for c in page_chunks)[:200]
        hits = set()
        for c in page_chunks:
            hits.update(_find_vocab_hits(c["text"]))
        flags.append(
            IntegrityFlag(
                type=IntegrityFlagType.HIDDEN_TEXT,
                severity=IntegritySeverity.HIGH,
                description=(
                    f"Text with near-zero contrast against its background "
                    f"detected on page {page} ({len(page_chunks)} run(s)) — "
                    "indistinguishable from the page to a human reader."
                ),
                page=page,
                evidence_text=sample,
                confidence=min(0.99, 0.85 + 0.02 * len(page_chunks)),
            )
        )
        suppressed |= hits

    low_contrast_by_page = _group_by_page(chunks, lambda c: c["visibility"] == "low_contrast")
    for page, page_chunks in low_contrast_by_page.items():
        sample = " ".join(c["text"] for c in page_chunks)[:200]
        hits = set()
        for c in page_chunks:
            hits.update(_find_vocab_hits(c["text"]))
        flags.append(
            IntegrityFlag(
                type=IntegrityFlagType.NEAR_WHITE_TEXT,
                severity=IntegritySeverity.MEDIUM,
                description=(
                    f"Low-contrast text detected on page {page} — faint but "
                    "technically visible; unusual for genuine resume content."
                ),
                page=page,
                evidence_text=sample,
                confidence=min(0.9, 0.6 + 0.03 * len(page_chunks)),
            )
        )
        suppressed |= hits

    # ---- 3: tiny fonts ------------------------------------------------------
    tiny_by_page = _group_by_page(chunks, lambda c: c.get("is_tiny_font") and c["visibility"] == "visible")
    for page, page_chunks in tiny_by_page.items():
        avg_size = sum(c["font_size"] for c in page_chunks) / len(page_chunks)
        sample = " ".join(c["text"] for c in page_chunks)[:200]
        severity = IntegritySeverity.HIGH if avg_size < 4 else IntegritySeverity.MEDIUM
        flags.append(
            IntegrityFlag(
                type=IntegrityFlagType.TINY_FONT,
                severity=severity,
                description=(
                    f"Font size averaging {avg_size:.1f}pt on page {page} — well "
                    "below normal body text, likely unreadable at normal zoom."
                ),
                page=page,
                evidence_text=sample,
                confidence=0.8,
            )
        )
        hits = set()
        for c in page_chunks:
            hits.update(_find_vocab_hits(c["text"]))
        if severity == IntegritySeverity.HIGH:
            suppressed |= hits

    # ---- 4: off-page text -----------------------------------------------
    off_by_page = _group_by_page(chunks, lambda c: c["visibility"] == "off_page")
    for page, page_chunks in off_by_page.items():
        sample = " ".join(c["text"] for c in page_chunks)[:200]
        hits = set()
        for c in page_chunks:
            hits.update(_find_vocab_hits(c["text"]))
        flags.append(
            IntegrityFlag(
                type=IntegrityFlagType.OFF_PAGE_TEXT,
                severity=IntegritySeverity.HIGH,
                description=f"Text positioned outside the visible page area on page {page}.",
                page=page,
                evidence_text=sample,
                confidence=0.95,
            )
        )
        suppressed |= hits

    # ---- 5: suspicious footer content ---------------------------------------
    footer_chunks = [
        c for c in chunks
        if c.get("is_footer_band") and c["visibility"] == "visible" and not _looks_like_contact_info(c["text"])
    ]
    footer_by_page = _group_by_page(footer_chunks, lambda c: True)
    for page, page_chunks in footer_by_page.items():
        hits = set()
        for c in page_chunks:
            hits.update(_find_vocab_hits(c["text"]))
        if len(hits) >= 2:
            flags.append(
                IntegrityFlag(
                    type=IntegrityFlagType.SUSPICIOUS_FOOTER,
                    severity=IntegritySeverity.HIGH,
                    description=(
                        f"Footer region on page {page} contains {len(hits)} distinct "
                        "technical keywords with no surrounding contact-info context — "
                        "a common keyword-stuffing pattern."
                    ),
                    page=page,
                    evidence_text=", ".join(sorted(hits)),
                    confidence=0.75,
                )
            )
            suppressed |= hits

    # ---- 6 & 7: density + repetition (computed over ALL visible text) -------
    visible_normal = [
        c for c in chunks
        if c["visibility"] == "visible" and not c.get("is_footer_band")
    ]
    # Count real occurrences per chunk, not just chunk presence — a term
    # crammed several times into a single inserted line (a common stuffing
    # trick) must not be undercounted as "one hit" just because it landed
    # in one text run.
    term_counts: dict[str, int] = defaultdict(int)
    for c in visible_normal:
        low = c["text"].lower()
        for term in TECH_VOCAB:
            occurrences = low.count(term)
            if occurrences:
                term_counts[term] += occurrences
                clean_terms.add(term)

        # skills-section density
    skills_chunks = [c for c in visible_normal if c["section"] == "skills"]
    if skills_chunks:
        skills_text = " ".join(c["text"] for c in skills_chunks)
        skill_hits = _find_vocab_hits(skills_text)
        total_tokens = max(1, len(skills_text.split()))
        ratio = len(skill_hits) / total_tokens
        if len(skill_hits) >= SKILLS_DENSITY_MIN_HITS and ratio >= SKILLS_DENSITY_RATIO:
            flags.append(
                IntegrityFlag(
                    type=IntegrityFlagType.HIGH_KEYWORD_DENSITY,
                    severity=IntegritySeverity.MEDIUM,
                    description=(
                        f"Skills section lists {len(skill_hits)} recognized technical "
                        f"terms in {total_tokens} words ({ratio:.0%} density) with no "
                        "narrative content — consistent with a padded skills list."
                    ),
                    page=skills_chunks[0]["page"],
                    evidence_text=", ".join(sorted(set(skill_hits))[:15]),
                    confidence=0.6,
                )
            )

    for term, count in term_counts.items():
        if count > REPEATED_KEYWORD_THRESHOLD:
            flags.append(
                IntegrityFlag(
                    type=IntegrityFlagType.REPEATED_KEYWORDS,
                    severity=IntegritySeverity.LOW,
                    description=(
                        f"'{term}' appears {count} times across the document — "
                        "unusual repetition for a single resume."
                    ),
                    page=0,
                    evidence_text=term,
                    confidence=0.5,
                )
            )

    # A term only ever seen in a suspicious region stays suppressed even if it
    # also happens to appear in, say, a repeated-keyword footer echo.
    suppressed -= clean_terms

    # ---- roll up ------------------------------------------------------------
    penalty = sum(SEVERITY_WEIGHT[f.severity] for f in flags)
    score = max(0, 100 - penalty)

    has_high = any(f.severity == IntegritySeverity.HIGH for f in flags)
    has_medium = any(f.severity == IntegritySeverity.MEDIUM for f in flags)
    if has_high or score < 50:
        category = IntegrityCategory.HIGH_RISK
    elif has_medium or flags:
        category = IntegrityCategory.SUSPICIOUS
    else:
        category = IntegrityCategory.NORMAL

    return IntegrityReport(
        category=category,
        score=score,
        flags=flags,
        suppressed_terms=sorted(suppressed),
    )
