from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from hearsay_api.repository import InMemoryRunRepository
from hearsay_api.schemas import ActionRequest, ActionResponse, CreateRunRequest
from hearsay_api.service import GameService, InvalidActionError


def act(
    service: GameService,
    run_id: UUID,
    verb: str,
    target_id: str | None = None,
    content: str | None = None,
) -> ActionResponse:
    return service.take_action(
        run_id,
        ActionRequest(
            idempotency_key=uuid4(),
            verb=verb,
            target_id=target_id,
            content=content,
        ),
    )


def test_settling_shipment_keeps_promise_spreads_memory_and_changes_treatment() -> None:
    repository = InMemoryRunRepository()
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=42))
    act(service, created.run_id, "promise_help", "marta")

    kept = act(service, created.run_id, "settle_shipment", "bram")

    promise = kept.snapshot.promises[0]
    assert promise.status == "kept"
    assert kept.snapshot.player.traits == ["Reliable", "Generous"]
    assert kept.snapshot.recent_events[0].kind == "promise_kept"
    pip = next(npc for npc in kept.snapshot.npcs if npc.id == "pip")
    assert "crates are moving" in (pip.speech or "")

    lineage = service.get_memory_lineage(
        created.run_id,
        "player-promise-marta-shipment",
    )
    marta_versions = [
        version
        for version in lineage.versions
        if version.holder_id == "marta"
    ]
    assert [version.version for version in marta_versions] == [1, 2]
    assert [version.active for version in marta_versions] == [False, True]
    assert marta_versions[-1].normalized_position["promise_status"] == "kept"
    assert any(version.holder_id == "pip" for version in lineage.versions)
    assert len(
        [
            transmission
            for transmission in lineage.transmissions
            if transmission.speaker_id == "marta"
        ]
    ) == 1
    ambient_transmissions = [
        transmission
        for transmission in lineage.transmissions
        if transmission.speaker_id == "pip"
    ]
    assert 2 <= len(ambient_transmissions) <= 4

    response = act(
        service,
        created.run_id,
        "talk",
        "marta",
        "Did I keep my promise to you?",
    )
    assert response.snapshot.dialogue is not None
    assert response.snapshot.dialogue.treatment_cue.startswith("Grateful:")
    assert {choice.id for choice in response.snapshot.dialogue.available_choices} == {
        "ask_for_endorsement",
        "call_in_goodwill",
    }
    marta = next(npc for npc in response.snapshot.npcs if npc.id == "marta")
    assert marta.relationship == 20


def test_evening_breaks_active_promise_and_marks_public_reputation() -> None:
    repository = InMemoryRunRepository()
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=43))
    act(service, created.run_id, "promise_help", "marta")
    act(service, created.run_id, "talk", "bram")
    act(service, created.run_id, "talk", "pip")

    broken = act(service, created.run_id, "talk", "rhea")

    assert broken.snapshot.phase == "evening"
    assert broken.snapshot.promises[0].status == "broken"
    assert broken.snapshot.player.traits == ["Dishonest", "Troublemaker"]
    assert broken.snapshot.recent_events[0].kind == "promise_broken"
    assert broken.snapshot.recent_events[1].kind == "ambient_gossip"
    assert broken.snapshot.recent_events[2].kind == "conversation"
    pip = next(npc for npc in broken.snapshot.npcs if npc.id == "pip")
    assert "empty word" in (pip.speech or "")

    notice = act(service, created.run_id, "read_notice_board")
    assert notice.consumed_time is False
    assert "Dishonest, Troublemaker" in notice.snapshot.recent_events[0].text

    response = act(
        service,
        created.run_id,
        "talk",
        "marta",
        "What happened to the shipment I promised to release?",
    )
    assert response.snapshot.dialogue is not None
    assert response.snapshot.dialogue.treatment_cue.startswith("Bitter:")
    assert {choice.id for choice in response.snapshot.dialogue.available_choices} == {
        "apologize_for_broken_promise",
        "ask_to_rebuild_trust",
    }
    marta = next(npc for npc in response.snapshot.npcs if npc.id == "marta")
    assert marta.relationship == -20


def test_shipment_cannot_be_settled_without_an_active_promise() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=44))

    with pytest.raises(InvalidActionError, match="no active shipment promise"):
        act(service, created.run_id, "settle_shipment", "bram")
