"""Spec §8/§2: the mock LLM's JD extraction must be evidence-grounded
(never invents requirements not present in the text) and must correctly
classify must-have vs. preferred regardless of whether the JD writes the
header on its own line or inline with the terms."""
from __future__ import annotations

from app.llm.mock import MockLLM


def test_extraction_handles_inline_header_on_its_own_short_line():
    """Regression test: 'Must-have: Python, SQL, Docker, AWS.' as a
    short, self-contained line must not be treated as pure-header noise
    with nothing to extract — a length-only heuristic swallowed exactly
    this common JD format and silently produced zero requirements."""
    jd = (
        "We are hiring a Backend Software Engineer to join our platform team.\n"
        "Must-have: Python, SQL, Docker, AWS.\n"
        "Preferred: Kubernetes, Terraform, React.\n"
        "You will design APIs and own services in production."
    )
    result = MockLLM().extract_requirements(jd, "3+ years of professional backend experience")
    by_name = {r.name: r.importance.value for r in result.requirements}

    assert by_name["Python"] == "must_have"
    assert by_name["SQL"] == "must_have"
    assert by_name["Docker"] == "must_have"
    assert by_name["AWS"] == "must_have"
    assert by_name["Kubernetes"] == "preferred"
    assert by_name["Terraform"] == "preferred"
    assert by_name["React"] == "preferred"
    assert result.experience_years_min == 3.0


def test_extraction_handles_header_embedded_mid_sentence():
    jd = (
        "We are hiring a Backend Software Engineer. Must-have: Python, SQL, Docker, AWS.\n"
        "Preferred: Kubernetes, Terraform, React. Requires 3+ years of experience."
    )
    result = MockLLM().extract_requirements(jd, "")
    by_name = {r.name: r.importance.value for r in result.requirements}
    assert by_name["Python"] == "must_have"
    assert by_name["Kubernetes"] == "preferred"


def test_extraction_never_invents_a_skill_not_in_the_text():
    jd = "We are hiring a Backend Engineer. Must-have: Python."
    result = MockLLM().extract_requirements(jd, "")
    names = {r.name for r in result.requirements}
    assert names == {"Python"}
    assert "AWS" not in names
    assert "Kubernetes" not in names
