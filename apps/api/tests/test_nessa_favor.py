from __future__ import annotations

from uuid import UUID, uuid4

from hearsay_api.repository import InMemoryRunRepository
from hearsay_api.schemas import ActionRequest, ActionResponse, CreateRunRequest
from hearsay_api.service import GameService


def act(
    service: GameService,
    run_id: UUID,
    verb: str,
    target_id: str | None = None,
) -> ActionResponse:
    return service.take_action(
        run_id,
        ActionRequest(
            idempotency_key=uuid4(),
            verb=verb,
            target_id=target_id,
        ),
    )


def test_nessa_harbor_log_becomes_correction_endorsement_and_vote_evidence() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=111))
    act(service, created.run_id, "sleep")

    accepted = act(service, created.run_id, "accept_nessa_favor", "nessa")
    assert accepted.snapshot.favors[0].status == "active"
    assert accepted.snapshot.recent_events[0].kind == "nessa_favor_accepted"

    delivered = act(service, created.run_id, "deliver_harbor_log", "elias")
    assert delivered.snapshot.favors[0].status == "completed"
    assert delivered.snapshot.player.traits == ["Reliable"]
    assert next(npc.relationship for npc in delivered.snapshot.npcs if npc.id == "nessa") == 25
    assert next(npc.relationship for npc in delivered.snapshot.npcs if npc.id == "elias") == 10

    corrected = act(service, created.run_id, "correct_storm_rumor", "pip")
    assert corrected.snapshot.favors[0].corrected_publicly is True
    assert corrected.snapshot.recent_events[0].kind == "storm_rumor_corrected"
    assert (
        "harbor log proves"
        in (next(npc for npc in corrected.snapshot.npcs if npc.id == "pip").speech or "").lower()
    )

    endorsed = act(service, created.run_id, "ask_nessa_endorsement", "nessa")
    assert endorsed.snapshot.player.endorsements == ["nessa"]
    assert endorsed.snapshot.player.traits == ["Reliable", "Influential"]
    assert endorsed.snapshot.recent_events[0].kind == "nessa_endorsement"

    lineage = service.get_memory_lineage(
        created.run_id,
        "nessa-storm-harbor-log",
    )
    assert {version.holder_id for version in lineage.versions} == {
        "nessa",
        "elias",
        "pip",
        "jonas",
        "mae",
    }
    assert len([version for version in lineage.versions if version.holder_id == "nessa"]) == 3
    assert {(edge.speaker_id, edge.listener_id) for edge in lineage.transmissions} == {
        ("elias", "pip"),
        ("nessa", "jonas"),
        ("nessa", "mae"),
    }

    act(service, created.run_id, "declare_candidacy", "rhea")
    act(service, created.run_id, "sleep")
    election = act(service, created.run_id, "sleep").snapshot.election
    assert election is not None
    assert election.ending.key == "landslide"
    favor_inputs = [
        vote_input
        for vote in election.votes
        for vote_input in vote.inputs
        if vote_input.key == "nessa-storm-harbor-log"
    ]
    assert len(favor_inputs) == 5
    assert all(vote_input.belief_id is not None for vote_input in favor_inputs)
