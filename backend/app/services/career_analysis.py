"""
Career trajectory + adaptability — spec §18/§19.

Deliberately NOT an LLM call in either mode: this is pure structural
extraction (find year anchors in the experience section, bucket
technologies mentioned after each anchor) plus counting. Spec §18/§19 are
explicit that this must stay strictly descriptive of resume evidence and
never predict future performance or attach a personality label — a
counting function can't accidentally do either of those things, which is
exactly why it's implemented this way instead of asking a model to
"assess adaptability."
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from app.parsing.constants import DISPLAY_NAMES, TECH_VOCAB
from app.schemas.career import AdaptabilityIndicator, CareerTrajectory, TrajectoryPoint

_YEAR_RE = re.compile(r"(19|20)\d{2}")
# Captures a full "2021 - Present" / "2021-2024" style range so an ongoing
# role's real span isn't lost down to just its start year.
_RANGE_RE = re.compile(r"((?:19|20)\d{2})\s*[-–—]\s*(present|current|now|(?:19|20)\d{2})", re.I)
_ROLE_RE = re.compile(r"^([A-Za-z][A-Za-z /&-]{2,60}?)(?:,|\s+at\s+|\s*[-–(])", re.I)


def _display(term: str) -> str:
    return DISPLAY_NAMES.get(term, term.title())


def _current_year() -> int:
    return datetime.now(timezone.utc).year


def parse_year_span(period_label: str) -> tuple[int, int]:
    """Best-effort (start_year, end_year) from a period_label like '2021',
    '2021-2024', or '2021-Present'. 'Present'/'Current'/'Now' resolve to
    this calendar year so an ongoing role's real tenure is counted, not
    just its start. Returns (0, 0) if nothing parseable is found."""
    m = _RANGE_RE.search(period_label)
    if m:
        start = int(m.group(1))
        end_raw = m.group(2).lower()
        end = _current_year() if end_raw in ("present", "current", "now") else int(end_raw)
        return start, end
    year_match = _YEAR_RE.search(period_label)
    if year_match:
        y = int(year_match.group(0))
        return y, y
    return 0, 0


def build_career_trajectory(chunks: list[dict]) -> CareerTrajectory:
    relevant = [c for c in chunks if c.get("section") in ("experience", "summary") and c.get("visibility") == "visible"]
    relevant.sort(key=lambda c: (c["page"], c["y"]))

    points: list[TrajectoryPoint] = []
    current: TrajectoryPoint | None = None

    for chunk in relevant:
        text = chunk["text"]
        range_match = _RANGE_RE.search(text) if chunk["section"] == "experience" else None
        year_match = _YEAR_RE.search(text)
        if (range_match or year_match) and chunk["section"] == "experience":
            role_match = _ROLE_RE.match(text)
            if range_match:
                end_raw = range_match.group(2)
                end_label = "Present" if end_raw.lower() in ("present", "current", "now") else end_raw
                label = f"{range_match.group(1)}-{end_label}"
            else:
                label = year_match.group(0)
            current = TrajectoryPoint(
                period_label=label,
                role=role_match.group(1).strip() if role_match else "",
            )
            points.append(current)

        if current is not None:
            low = text.lower()
            for term in TECH_VOCAB:
                if term in low:
                    disp = _display(term)
                    if disp not in current.technologies:
                        current.technologies.append(disp)

    points.sort(key=lambda p: p.period_label)

    if not points:
        summary = "No dated role history with recognizable technology mentions was found in the experience section."
    else:
        span = f"{points[0].period_label}–{points[-1].period_label}" if len(points) > 1 else points[0].period_label
        summary = (
            f"Resume evidence spans {span} across {len(points)} identifiable period(s), "
            f"referencing {len({t for p in points for t in p.technologies})} distinct technologies."
        )

    return CareerTrajectory(points=points, summary=summary)


def build_adaptability_indicator(trajectory: CareerTrajectory) -> AdaptabilityIndicator:
    if not trajectory.points:
        return AdaptabilityIndicator(
            level="low",
            technology_transitions=0,
            role_transitions=0,
            explanation="Insufficient dated role history was found to assess technology adoption over time.",
        )

    seen: set[str] = set()
    new_tech_after_first = 0
    for i, point in enumerate(trajectory.points):
        for tech in point.technologies:
            if tech not in seen:
                if i > 0:
                    new_tech_after_first += 1
                seen.add(tech)

    role_transitions = max(0, len(trajectory.points) - 1)

    if new_tech_after_first >= 3 and role_transitions >= 1:
        level = "high"
        explanation = (
            "Resume evidence indicates repeated adoption of new technologies "
            f"across successive roles ({new_tech_after_first} new technologies "
            f"introduced over {role_transitions} role transition(s))."
        )
    elif new_tech_after_first >= 1 or role_transitions >= 1:
        level = "moderate"
        explanation = (
            f"Resume evidence shows some technology change over time "
            f"({new_tech_after_first} new technologies across {role_transitions} "
            "role transition(s))."
        )
    else:
        level = "low"
        explanation = (
            "Resume evidence does not show a clear pattern of new-technology "
            "adoption across roles — this may reflect a stable role rather than "
            "limited capability."
        )

    return AdaptabilityIndicator(
        level=level,
        technology_transitions=new_tech_after_first,
        role_transitions=role_transitions,
        explanation=explanation,
    )
