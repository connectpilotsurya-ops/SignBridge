"""HTTP-level tests for the ranking dashboard and recruiter-selection
endpoints — spec update "ranking, not shortlisting". Confirms every
uploaded candidate is ranked (never filtered to a shortlist), the sort
order matches match_score/evidence_confidence/document_integrity, the
forbidden field name never appears, and that selecting a candidate for
the next stage never mutates their AI rank or score."""
from __future__ import annotations

JD = (
    "We are hiring a Backend Software Engineer to join our platform team.\n"
    "Must-have: Python, SQL, Docker, AWS.\n"
    "Preferred: Kubernetes, Terraform, React.\n"
    "You will design APIs and own services in production."
)


def _create_analyzed_job(client, headers):
    job = client.post(
        "/api/jobs", headers=headers,
        json={"title": "Backend Software Engineer", "description": JD, "experience_requirement": "3+ years"},
    ).json()
    return client.post(f"/api/jobs/{job['id']}/analyze", headers=headers).json()


def _upload(client, headers, job_id, filename, pdf_bytes):
    upload = client.post(
        "/api/resumes/upload", headers=headers, data={"job_id": job_id},
        files=[("files", (filename, pdf_bytes, "application/pdf"))],
    ).json()
    assert "error" not in upload["results"][0], upload
    return upload["results"][0]["application_id"]


def _strong_pdf(build_pdf, name):
    return build_pdf([
        (name, 16, True),
        ("Experience", 12, True),
        ("2021 - Present: Senior Software Engineer, Fairbank Systems", 10, True),
        ("Built a Python/FastAPI billing service running in AWS with a PostgreSQL/SQL backend.", 9.5, False),
        ("Containerized all services with Docker and led the migration to Kubernetes.", 9.5, False),
        ("Skills", 12, True),
        ("Python, SQL, Docker, AWS, Kubernetes", 9.5, False),
    ])


def _weak_pdf(build_pdf, name):
    return build_pdf([
        (name, 16, True),
        ("Experience", 12, True),
        ("2023 - Present: Junior Analyst, Some Company", 10, True),
        ("Helped with spreadsheets and reports.", 9.5, False),
    ])


def test_ranking_includes_every_candidate_never_a_shortlist(client, auth_headers, build_pdf):
    job = _create_analyzed_job(client, auth_headers)
    strong_id = _upload(client, auth_headers, job["id"], "strong.pdf", _strong_pdf(build_pdf, "Priya Natarajan"))
    weak_id = _upload(client, auth_headers, job["id"], "weak.pdf", _weak_pdf(build_pdf, "Sam Rivera"))

    resp = client.get(f"/api/jobs/{job['id']}/ranking", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    ranked_ids = {row["application_id"] for row in data["ranking"]}
    assert ranked_ids == {strong_id, weak_id}
    assert data["summary"]["candidates_analyzed"] == 2

    # The forbidden field must never appear anywhere in the payload.
    assert "ai_shortlisted" not in resp.text


def test_ranking_sorted_by_match_score_descending_with_rank_field(client, auth_headers, build_pdf):
    job = _create_analyzed_job(client, auth_headers)
    strong_id = _upload(client, auth_headers, job["id"], "strong.pdf", _strong_pdf(build_pdf, "Priya Natarajan"))
    weak_id = _upload(client, auth_headers, job["id"], "weak.pdf", _weak_pdf(build_pdf, "Sam Rivera"))

    data = client.get(f"/api/jobs/{job['id']}/ranking", headers=auth_headers).json()
    ranking = data["ranking"]

    scores = [row["match_score"] for row in ranking]
    assert scores == sorted(scores, reverse=True)
    assert [row["rank"] for row in ranking] == list(range(1, len(ranking) + 1))
    # The stronger, fully-evidenced resume must outrank the thin one.
    by_id = {row["application_id"]: row for row in ranking}
    assert by_id[strong_id]["rank"] < by_id[weak_id]["rank"]

    for row in ranking:
        assert row["ranking_status"] in (
            "top_match", "strong_match", "potential_match", "lower_match", "human_review_required",
        )


def test_selection_for_next_stage_never_mutates_ai_rank_or_score(client, auth_headers, build_pdf):
    """Spec §11: a lower-ranked candidate can still be manually selected —
    intentional human oversight, and it must never touch the AI's own
    rank/score. Explicitly not the same concept as candidate status."""
    job = _create_analyzed_job(client, auth_headers)
    strong_id = _upload(client, auth_headers, job["id"], "strong.pdf", _strong_pdf(build_pdf, "Priya Natarajan"))
    weak_id = _upload(client, auth_headers, job["id"], "weak.pdf", _weak_pdf(build_pdf, "Sam Rivera"))

    before = client.get(f"/api/jobs/{job['id']}/ranking", headers=auth_headers).json()
    weak_before = next(r for r in before["ranking"] if r["application_id"] == weak_id)
    assert weak_before["selection_status"] is None

    sel = client.post(
        f"/api/applications/{weak_id}/selection", headers=auth_headers,
        json={"selection_status": "selected", "selection_reason": "Strong culture-add signal from interview."},
    )
    assert sel.status_code == 200
    assert sel.json()["selection_status"] == "selected"

    after = client.get(f"/api/jobs/{job['id']}/ranking", headers=auth_headers).json()
    weak_after = next(r for r in after["ranking"] if r["application_id"] == weak_id)
    strong_after = next(r for r in after["ranking"] if r["application_id"] == strong_id)

    # Rank/score untouched by the selection write.
    assert weak_after["rank"] == weak_before["rank"]
    assert weak_after["match_score"] == weak_before["match_score"]
    assert weak_after["ranking_status"] == weak_before["ranking_status"]
    # The selection is now visible alongside the unchanged AI assessment.
    assert weak_after["selection_status"] == "selected"
    # The higher-ranked candidate was never auto-selected and stays untouched.
    assert strong_after["selection_status"] is None
    assert weak_after["rank"] > strong_after["rank"]


def test_ranking_history_preserves_snapshots_across_reanalysis(client, auth_headers, build_pdf):
    job = _create_analyzed_job(client, auth_headers)
    _upload(client, auth_headers, job["id"], "strong.pdf", _strong_pdf(build_pdf, "Priya Natarajan"))

    # _create_analyzed_job already called /analyze once, bumping the
    # version off its default of 1.
    v1 = client.get(f"/api/jobs/{job['id']}/ranking", headers=auth_headers).json()
    first_version = v1["ranking_version"]
    assert first_version >= 2

    # Re-running requirement extraction bumps the ranking model version again.
    client.post(f"/api/jobs/{job['id']}/analyze", headers=auth_headers)
    v2 = client.get(f"/api/jobs/{job['id']}/ranking", headers=auth_headers).json()
    assert v2["ranking_version"] == first_version + 1

    history = client.get(f"/api/jobs/{job['id']}/ranking/history", headers=auth_headers).json()
    versions_present = {row["ranking_version"] for row in history}
    assert {first_version, first_version + 1}.issubset(versions_present)
