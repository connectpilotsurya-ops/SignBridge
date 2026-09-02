"""Spec §10/§11: forensic PDF parsing and the deterministic anti-gaming
detector. No LLM involvement anywhere in this file."""
from __future__ import annotations

import fitz

from app.integrity.detector import analyze_integrity
from app.parsing.pdf_parser import parse_resume_pdf


def _integrity_for(pdf_bytes: bytes):
    parsed = parse_resume_pdf(pdf_bytes)
    return analyze_integrity(parsed.chunks)


def test_clean_resume_is_not_flagged(build_pdf):
    """A normal resume with a typical ~12-term skills list must score
    NORMAL/100 — this is a regression test for a false positive where the
    high-keyword-density check flagged completely ordinary skills lists."""
    pdf = build_pdf([
        ("Jordan Lee", 16, True),
        ("Skills", 12, True),
        ("Python, SQL, PostgreSQL, Docker, AWS, Git, JavaScript, TypeScript, Django, FastAPI, Linux, REST API design", 9.5, False),
    ])
    report = _integrity_for(pdf)
    assert report.category.value == "normal"
    assert report.score == 100
    assert report.flags == []


def test_white_text_is_detected_and_suppressed(build_pdf):
    """Spec §11's flagship case: text colored to match the background is
    invisible to a human reader but present in the raw PDF text layer —
    must be flagged HIGH and its terms suppressed from matching."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((56, 700), "Kubernetes Terraform", fontsize=9, color=(1, 1, 1))
    pdf = doc.tobytes()
    doc.close()

    report = _integrity_for(pdf)
    assert report.category.value == "high_risk"
    assert any(f.type.value == "hidden_text" for f in report.flags)
    assert "kubernetes" in report.suppressed_terms
    assert "terraform" in report.suppressed_terms


def test_tiny_font_is_detected(build_pdf):
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((56, 700), "Azure GCP MongoDB Redis", fontsize=2.5, color=(0, 0, 0))
    pdf = doc.tobytes()
    doc.close()

    report = _integrity_for(pdf)
    assert any(f.type.value == "tiny_font" for f in report.flags)


def test_footer_keyword_stuffing_is_detected(build_pdf):
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    ph = page.rect.height
    page.insert_text((56, ph - 15), "React Angular Java C++", fontsize=8, color=(0.4, 0.4, 0.4))
    pdf = doc.tobytes()
    doc.close()

    report = _integrity_for(pdf)
    assert any(f.type.value == "suspicious_footer" for f in report.flags)


def test_repeated_keyword_stuffed_into_one_line_is_still_counted(build_pdf):
    """Regression test: a term repeated many times within a SINGLE text
    run must be counted by actual occurrence, not just "this chunk
    contains the term at least once" — otherwise cramming a word six
    times into one inserted line only ever counted as one hit."""
    pdf = build_pdf([
        ("Experience", 12, True),
        ("DevOps DevOps DevOps DevOps DevOps DevOps", 9, False),
    ])
    report = _integrity_for(pdf)
    assert any(f.type.value == "repeated_keywords" for f in report.flags)


def test_skills_only_padding_is_detected_but_normal_list_is_not(build_pdf):
    normal = build_pdf([
        ("Skills", 12, True),
        ("Python, SQL, Docker, AWS, Git, Linux", 9.5, False),
    ])
    assert not any(f.type.value == "high_keyword_density" for f in _integrity_for(normal).flags)

    # Split across a few lines rather than one long line — insert_text has
    # no wrapping and silently drops characters that would overflow the
    # page width, which would otherwise truncate the tail of this list.
    padded = build_pdf([
        ("Skills", 12, True),
        ("Elasticsearch, Spark, Hadoop, Scala, Rust, Go", 9.5, False),
        ("Kafka, gRPC, GraphQL, Pulumi, Ansible, Helm", 9.5, False),
        ("CloudFormation, Vue.js, MySQL, NoSQL, Jenkins, Spring", 9.5, False),
    ])
    assert any(f.type.value == "high_keyword_density" for f in _integrity_for(padded).flags)
