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
    assert len(content.bram_approaches) == 4
    assert {event.id for event in content.town_events} == {
        "storm",
        "public_argument",
    }
    assert len(content.argument_choices) == 3
    assert {favor.id for favor in content.favors} == {
        "nessa_harbor_log",
        "orin_election_confession",
        "talia_sick_house",
        "elias_wrongful_arrest",
        "pip_ballot_source",
    }
    assert {choice.action_verb for choice in content.favor_choices} == {
        "reveal_orin_confession",
        "conceal_orin_confession",
        "help_oswin_quietly",
        "gossip_oswin_illness",
        "investigate_elias_arrest",
        "cover_elias_arrest",
        "verify_pip_source",
        "embellish_pip_rumor",
    }
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


def test_content_requires_every_authored_bram_approach() -> None:
    payload = load_content().model_dump(mode="json")
    payload["bram_approaches"].pop()

    with pytest.raises(ValidationError, match="threaten, flatter, negotiate, and lie"):
        GreyhavenContent.model_validate(payload)


def test_content_requires_never_cut_storm() -> None:
    payload = load_content().model_dump(mode="json")
    payload["town_events"] = [event for event in payload["town_events"] if event["id"] != "storm"]

    with pytest.raises(ValidationError, match="never-cut storm"):
        GreyhavenContent.model_validate(payload)


def test_content_requires_all_public_argument_choices() -> None:
    payload = load_content().model_dump(mode="json")
    payload["argument_choices"].pop()

    with pytest.raises(ValidationError, match="Bram, Nessa, and calm"):
        GreyhavenContent.model_validate(payload)


def test_content_requires_all_authored_favor_choices() -> None:
    payload = load_content().model_dump(mode="json")
    payload["favor_choices"].pop()

    with pytest.raises(ValidationError, match="reveal/conceal"):
        GreyhavenContent.model_validate(payload)


def test_favor_choice_rejects_missing_or_forward_parent_route() -> None:
    payload = load_content().model_dump(mode="json")
    choice = next(
        item
        for item in payload["favor_choices"]
        if item["action_verb"] == "investigate_elias_arrest"
    )
    choice["transmission_parents"]["tob"] = "marta"

    with pytest.raises(ValidationError, match="invalid references"):
        GreyhavenContent.model_validate(payload)
