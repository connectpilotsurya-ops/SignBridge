"""Generates a genuinely clean, realistic one-page resume PDF with real
PyMuPDF text (not scanned/image), used as:

  1. the zero-setup base document for POST /api/adversarial/test (spec §29)
     when the caller doesn't upload their own PDF, and
  2. the demo candidate resume seeded by Task #13's sample-data script.

Its genuine skills content deliberately avoids the exact keywords injected
by app/services/adversarial.py's six attack types, so a fresh adversarial
run against it demonstrates a clean signal: a term that ONLY ever appears
in a hidden/suspicious region gets excluded from matching, rather than
being rescued by a legitimate mention elsewhere on the page.
"""
from __future__ import annotations

import fitz

_LINES = [
    ("Dana Whitfield", 16, True),
    ("Backend Software Engineer  |  dana.whitfield@example.com  |  +1 (555) 019-2244", 9.5, False),
    ("", 6, False),
    ("Summary", 12, True),
    (
        "Backend engineer with 5 years building and operating production APIs "
        "and data pipelines. Comfortable owning a service from design through "
        "on-call.",
        9.5,
        False,
    ),
    ("", 6, False),
    ("Experience", 12, True),
    ("2022 - Present: Software Engineer, Northwind Analytics", 10, True),
    ("Built and maintained internal REST APIs serving product and billing data.", 9.5, False),
    ("Migrated a batch ETL job to an event-driven pipeline, cutting latency from hours to minutes.", 9.5, False),
    ("Owned the on-call rotation for the payments service for two years.", 9.5, False),
    ("2020 - 2022: Software Engineer, Bluecrest Systems", 10, True),
    ("Developed a customer-facing dashboard and its supporting API layer.", 9.5, False),
    ("Wrote integration tests that cut production regressions by roughly a third.", 9.5, False),
    ("", 6, False),
    ("Skills", 12, True),
    ("Python, SQL, PostgreSQL, Docker, AWS, Git, JavaScript, TypeScript, Django, FastAPI, Linux, REST API design", 9.5, False),
    ("", 6, False),
    ("Education", 12, True),
    ("B.S. Computer Science, Riverton State University, 2020", 9.5, False),
]


def build_sample_clean_resume_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)  # US Letter
    x = 56.0
    y = 56.0
    for text, size, bold in _LINES:
        if text:
            page.insert_text(
                (x, y),
                text,
                fontsize=size,
                fontname="helv" if not bold else "hebo",
                color=(0.1, 0.1, 0.1),
            )
        y += size + 8
    buf = doc.tobytes()
    doc.close()
    return buf
