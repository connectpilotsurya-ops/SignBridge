"""Spec §29: the adversarial resume simulator. Each of the six attack
variants is a real PDF pushed through the real parser + integrity
detector — this test would fail exactly the same way a genuine gamed
resume would fail to evade detection."""
from __future__ import annotations

from app.services.adversarial import ATTACK_KEYWORDS, run_adversarial_suite
from app.services.sample_resume import build_sample_clean_resume_pdf


def test_clean_baseline_is_not_flagged():
    """The bundled zero-setup base resume must itself score clean —
    otherwise every attack's "before" state is already suspicious and
    the demo proves nothing."""
    from app.integrity.detector import analyze_integrity
    from app.parsing.pdf_parser import parse_resume_pdf

    pdf = build_sample_clean_resume_pdf()
    report = analyze_integrity(parse_resume_pdf(pdf).chunks)
    assert report.category.value == "normal"
    assert report.flags == []


def test_all_six_attack_types_are_detected():
    pdf = build_sample_clean_resume_pdf()
    reports = run_adversarial_suite(pdf)
    assert len(reports) == len(ATTACK_KEYWORDS) == 6
    for r in reports:
        assert r.detected is True, f"{r.attack_type} went undetected"


def test_hidden_injection_attacks_exclude_terms_from_matching():
    pdf = build_sample_clean_resume_pdf()
    reports = {r.attack_type: r for r in run_adversarial_suite(pdf)}
    assert reports["white_text_injection"].matching_impact == "EXCLUDED"
    assert reports["hidden_section_manipulation"].matching_impact == "EXCLUDED"
