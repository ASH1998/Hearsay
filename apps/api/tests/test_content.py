from __future__ import annotations

import pytest
from pydantic import ValidationError

from hearsay_api.content import GreyhavenContent, load_content


def test_greyhaven_content_references_are_complete() -> None:
    content = load_content()

    assert len(content.locations) == 12
    assert len(content.principals) == 8
    assert len(content.ambients) == 12
    assert len(content.residents) == 20
    assert len(content.endings) == 6
    assert len(content.schedule_templates) == 17
    assert len(content.public_traits) == 6
    assert all(location.neighbors for location in content.locations)
    assert {
        content.scheduled_location(resident.id, day, phase)
        for resident in content.residents
        for day in range(1, 4)
        for phase in ("morning", "afternoon", "evening", "night")
    } <= set(content.locations_by_id)


def test_content_rejects_one_way_waypoint_edge() -> None:
    payload = load_content().model_dump(mode="json")
    square = next(location for location in payload["locations"] if location["id"] == "square")
    square["neighbors"].remove("road")

    with pytest.raises(ValidationError, match="bidirectional"):
        GreyhavenContent.model_validate(payload)


def test_content_rejects_malformed_resident_schedule() -> None:
    payload = load_content().model_dump(mode="json")
    payload["schedule_templates"][0]["days"][0].pop()

    with pytest.raises(ValidationError, match="three days"):
        GreyhavenContent.model_validate(payload)
