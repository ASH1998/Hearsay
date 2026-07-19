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
) -> ActionResponse:
    return service.take_action(
        run_id,
        ActionRequest(
            idempotency_key=uuid4(),
            verb=verb,
            target_id=target_id,
        ),
    )


def reach_argument(service: GameService, run_id: UUID) -> ActionResponse:
    act(service, run_id, "sleep")
    act(service, run_id, "declare_candidacy", "rhea")
    return act(service, run_id, "talk", "pip")


def test_public_argument_stages_square_damages_factions_and_clears() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=101))

    started = reach_argument(service, created.run_id)

    event = next(event for event in started.snapshot.town_events if event.key == "public_argument")
    assert event.status == "active"
    assert started.snapshot.day == 2
    assert started.snapshot.phase == "afternoon"
    assert {npc.location_id for npc in started.snapshot.npcs} == {"square"}
    assert started.snapshot.recent_events[1].kind == "public_argument_begins"
    assert "drowned sailors" in (
        next(npc for npc in started.snapshot.npcs if npc.id == "pip").speech or ""
    )

    calmed = act(service, created.run_id, "calm_argument")
    assert calmed.snapshot.player.argument_choice == "calm_argument"
    assert calmed.snapshot.player.traits == ["Influential"]
    assert calmed.snapshot.recent_events[0].kind == "argument_calmed"
    assert next(npc.relationship for npc in calmed.snapshot.npcs if npc.id == "bram") == 10
    assert next(npc.relationship for npc in calmed.snapshot.npcs if npc.id == "nessa") == 10

    lineage = service.get_memory_lineage(
        created.run_id,
        "public-argument-player-intervention",
    )
    assert {version.holder_id for version in lineage.versions} == {
        "bram",
        "nessa",
        "pip",
    }
    assert {version.normalized_position["choice"] for version in lineage.versions} == {
        "calm_argument"
    }

    with pytest.raises(InvalidActionError, match="already chose"):
        act(service, created.run_id, "side_with_bram")

    cleared = act(service, created.run_id, "sleep")
    argument = next(
        event for event in cleared.snapshot.town_events if event.key == "public_argument"
    )
    assert argument.status == "resolved"
    assert cleared.snapshot.day == 3
    assert cleared.snapshot.phase == "morning"
    assert {npc.location_id for npc in cleared.snapshot.npcs} != {"square"}
    assert cleared.snapshot.recent_events[1].kind == "public_argument_clears"


@pytest.mark.parametrize(
    ("verb", "bram_standing", "nessa_standing", "traits"),
    [
        ("side_with_bram", 25, -30, []),
        ("side_with_nessa", -30, 25, ["Generous"]),
        ("calm_argument", 10, 10, ["Influential"]),
    ],
)
def test_each_argument_choice_changes_standing_and_vote_memory(
    verb: str,
    bram_standing: int,
    nessa_standing: int,
    traits: list[str],
) -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=102))
    reach_argument(service, created.run_id)

    chosen = act(service, created.run_id, verb)

    assert chosen.snapshot.player.traits == traits
    assert (
        next(npc.relationship for npc in chosen.snapshot.npcs if npc.id == "bram") == bram_standing
    )
    assert (
        next(npc.relationship for npc in chosen.snapshot.npcs if npc.id == "nessa")
        == nessa_standing
    )

    act(service, created.run_id, "sleep")
    election_result = act(service, created.run_id, "sleep")
    assert election_result.snapshot.election is not None
    if verb == "calm_argument":
        assert election_result.snapshot.election.player_votes == 11
        assert election_result.snapshot.election.rhea_votes == 9
    argument_inputs = [
        vote_input
        for vote in election_result.snapshot.election.votes
        for vote_input in vote.inputs
        if vote_input.key == "public-argument-player-intervention"
    ]
    assert len(argument_inputs) == 3
    assert {vote_input.value for vote_input in argument_inputs} == {verb}
    assert all(vote_input.belief_id is not None for vote_input in argument_inputs)
