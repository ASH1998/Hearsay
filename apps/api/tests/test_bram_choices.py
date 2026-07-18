from __future__ import annotations

from uuid import UUID, uuid4

import pytest

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


@pytest.mark.parametrize(
    ("verb", "relationship", "traits", "rumor_fragment"),
    [
        (
            "threaten_bram",
            -25,
            ["Dangerous", "Troublemaker"],
            "threatened to ruin Bram",
        ),
        ("flatter_bram", 15, [], "only honest merchant"),
        ("negotiate_bram", -5, [], "tried to ruin Bram"),
        ("lie_to_bram", -15, ["Dishonest"], "forged Elias's authority"),
    ],
)
def test_bram_approaches_have_distinct_visible_and_memory_consequences(
    verb: str,
    relationship: int,
    traits: list[str],
    rumor_fragment: str,
) -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=81))

    result = act(service, created.run_id, verb, "bram")

    bram = next(npc for npc in result.snapshot.npcs if npc.id == "bram")
    pip = next(npc for npc in result.snapshot.npcs if npc.id == "pip")
    assert bram.relationship == relationship
    assert result.snapshot.player.traits == traits
    assert rumor_fragment in (pip.speech or "")
    assert result.snapshot.recent_events[0].kind == (
        service.content.bram_approaches_by_verb[verb].event_kind
    )

    lineage = service.get_memory_lineage(
        created.run_id,
        "bram-price-confrontation",
    )
    assert len(lineage.versions) == 2
    assert len(lineage.transmissions) == 1
    assert {
        version.normalized_position["approach"]
        for version in lineage.versions
    } == {verb}
    assert next(
        version
        for version in lineage.versions
        if version.holder_id == "pip"
    ).narrative_text.find(rumor_fragment) >= 0


@pytest.mark.parametrize(
    ("verb", "ending"),
    [
        ("threaten_bram", "run_out_of_town"),
        ("lie_to_bram", "exposed"),
    ],
)
def test_dangerous_and_dishonest_choices_reach_seeded_playable_endings(
    verb: str,
    ending: str,
) -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=82))

    act(service, created.run_id, verb, "bram")
    act(service, created.run_id, "sleep")
    act(service, created.run_id, "declare_candidacy", "rhea")
    act(service, created.run_id, "sleep")
    result = act(service, created.run_id, "sleep")

    assert result.snapshot.election is not None
    assert result.snapshot.election.ending.key == ending
    assert any(
        vote_input.key == "bram-price-confrontation"
        and vote_input.value == verb
        and vote_input.belief_id is not None
        for vote in result.snapshot.election.votes
        for vote_input in vote.inputs
    )
