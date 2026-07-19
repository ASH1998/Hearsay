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


@pytest.mark.parametrize(
    (
        "verb",
        "resolution",
        "traits",
        "endorsements",
        "relationships",
        "required_edges",
        "contributions",
        "event_kind",
        "player_votes",
        "ending",
    ),
    [
        (
            "investigate_elias_arrest",
            "investigated",
            ["Reliable", "Influential"],
            ["elias"],
            {"elias": 20, "tob": 30, "marta": 15, "edda": 15},
            {
                ("player", "elias"),
                ("elias", "tob"),
                ("tob", "marta"),
                ("elias", "edda"),
                ("tob", "pip"),
            },
            {"elias": 0.5, "tob": 0.45, "marta": 0.3, "edda": 0.3, "pip": 0.2},
            "elias_arrest_investigated",
            16,
            "landslide",
        ),
        (
            "cover_elias_arrest",
            "covered_up",
            ["Dishonest"],
            [],
            {"elias": 30, "tob": -30, "marta": -20, "will": 15},
            {
                ("player", "elias"),
                ("player", "tob"),
                ("tob", "marta"),
                ("tob", "pip"),
                ("elias", "will"),
            },
            {"elias": 0.45, "tob": -0.5, "marta": -0.35, "pip": -0.25, "will": 0.25},
            "elias_arrest_covered",
            0,
            "exposed",
        ),
    ],
)
def test_elias_wrongful_arrest_choices_change_legitimacy_and_votes(
    verb: str,
    resolution: str,
    traits: list[str],
    endorsements: list[str],
    relationships: dict[str, int],
    required_edges: set[tuple[str, str]],
    contributions: dict[str, float],
    event_kind: str,
    player_votes: int,
    ending: str,
) -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=151))

    accepted = act(service, created.run_id, "accept_elias_favor", "elias")
    favor = accepted.snapshot.favors[0]
    assert favor.key == "elias_wrongful_arrest"
    assert favor.status == "active"
    assert favor.resolution is None
    assert accepted.snapshot.recent_events[0].kind == (
        "elias_wrongful_arrest_entrusted"
    )
    assert "innocent" in (
        next(npc for npc in accepted.snapshot.npcs if npc.id == "tob").speech
        or ""
    )

    entrusted_lineage = service.get_memory_lineage(
        created.run_id,
        "elias-tob-wrongful-arrest",
    )
    assert {version.holder_id for version in entrusted_lineage.versions} == {
        "elias",
        "player",
    }
    assert {
        (edge.speaker_id, edge.listener_id)
        for edge in entrusted_lineage.transmissions
    } == {("elias", "player")}

    resolved = act(service, created.run_id, verb, "elias")
    favor = resolved.snapshot.favors[0]
    assert favor.status == "completed"
    assert favor.resolution == resolution
    assert resolved.snapshot.player.traits == traits
    assert resolved.snapshot.player.endorsements == endorsements
    assert resolved.snapshot.recent_events[0].kind == event_kind
    for resident_id, relationship in relationships.items():
        assert next(
            npc.relationship
            for npc in resolved.snapshot.npcs
            if npc.id == resident_id
        ) == relationship

    other_verb = (
        "cover_elias_arrest"
        if verb == "investigate_elias_arrest"
        else "investigate_elias_arrest"
    )
    with pytest.raises(InvalidActionError, match="no unresolved wrongful-arrest"):
        act(service, created.run_id, other_verb, "elias")

    lineage = service.get_memory_lineage(
        created.run_id,
        "elias-tob-wrongful-arrest",
    )
    edges = {
        (edge.speaker_id, edge.listener_id)
        for edge in lineage.transmissions
    }
    assert {("elias", "player"), *required_edges} <= edges
    assert len(
        [
            version
            for version in lineage.versions
            if version.holder_id == "player"
        ]
    ) == 2

    act(service, created.run_id, "sleep")
    act(service, created.run_id, "declare_candidacy", "rhea")
    act(service, created.run_id, "sleep")
    election_state = act(service, created.run_id, "sleep").snapshot.election
    assert election_state is not None
    assert election_state.player_votes == player_votes
    assert election_state.ending.key == ending
    arrest_inputs = {
        vote.voter_id: vote_input
        for vote in election_state.votes
        for vote_input in vote.inputs
        if vote_input.key == "elias-tob-wrongful-arrest"
        and vote.voter_id in contributions
    }
    assert set(arrest_inputs) == set(contributions)
    for voter_id, contribution in contributions.items():
        vote_input = arrest_inputs[voter_id]
        assert vote_input.value == resolution
        assert vote_input.contribution == pytest.approx(contribution)
        assert vote_input.belief_id is not None
        assert vote_input.belief_version is not None


def test_wrongful_arrest_cannot_be_resolved_before_elias_offers_it() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=152))

    with pytest.raises(InvalidActionError, match="no unresolved wrongful-arrest"):
        act(service, created.run_id, "investigate_elias_arrest", "elias")
