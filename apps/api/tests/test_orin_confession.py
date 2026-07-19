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
        "trait",
        "endorsements",
        "relationships",
        "required_edges",
        "contributions",
    ),
    [
        (
            "reveal_orin_confession",
            "revealed",
            "Reliable",
            [],
            {"orin": -30, "elias": 15, "edda": 20, "will": -10},
            {
                ("player", "orin"),
                ("player", "elias"),
                ("player", "edda"),
                ("player", "will"),
                ("player", "pip"),
            },
            {"orin": -0.35, "elias": 0.5, "edda": 0.5, "will": -0.15, "pip": 0.2},
        ),
        (
            "conceal_orin_confession",
            "concealed",
            "Influential",
            ["orin"],
            {"orin": 30, "edda": 15, "will": 20},
            {
                ("player", "orin"),
                ("orin", "edda"),
                ("orin", "will"),
            },
            {"orin": 0.45, "edda": 0.35, "will": 0.5},
        ),
    ],
)
def test_orin_confession_choices_change_elders_and_audited_votes(
    verb: str,
    resolution: str,
    trait: str,
    endorsements: list[str],
    relationships: dict[str, int],
    required_edges: set[tuple[str, str]],
    contributions: dict[str, float],
) -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=131))

    accepted = act(
        service,
        created.run_id,
        "accept_orin_confession",
        "orin",
    )
    favor = accepted.snapshot.favors[0]
    assert favor.key == "orin_election_confession"
    assert favor.status == "active"
    assert favor.resolution is None
    assert accepted.snapshot.recent_events[0].kind == "orin_confession_entrusted"

    entrusted_lineage = service.get_memory_lineage(
        created.run_id,
        "orin-rhea-election-confession",
    )
    assert {version.holder_id for version in entrusted_lineage.versions} == {
        "orin",
        "player",
    }
    assert {(edge.speaker_id, edge.listener_id) for edge in entrusted_lineage.transmissions} == {
        ("orin", "player")
    }

    resolved = act(service, created.run_id, verb, "orin")
    favor = resolved.snapshot.favors[0]
    assert favor.status == "completed"
    assert favor.resolution == resolution
    assert resolved.snapshot.player.traits == [trait]
    assert resolved.snapshot.player.endorsements == endorsements
    assert resolved.snapshot.recent_events[0].kind == f"orin_confession_{resolution}"
    for resident_id, relationship in relationships.items():
        assert (
            next(npc.relationship for npc in resolved.snapshot.npcs if npc.id == resident_id)
            == relationship
        )

    other_verb = (
        "conceal_orin_confession" if verb == "reveal_orin_confession" else "reveal_orin_confession"
    )
    with pytest.raises(InvalidActionError, match="no unresolved confession"):
        act(service, created.run_id, other_verb, "orin")

    lineage = service.get_memory_lineage(
        created.run_id,
        "orin-rhea-election-confession",
    )
    edges = {(edge.speaker_id, edge.listener_id) for edge in lineage.transmissions}
    assert {("orin", "player"), *required_edges} <= edges
    assert len([version for version in lineage.versions if version.holder_id == "player"]) == 2

    act(service, created.run_id, "sleep")
    act(service, created.run_id, "declare_candidacy", "rhea")
    act(service, created.run_id, "sleep")
    election = act(service, created.run_id, "sleep").snapshot.election
    assert election is not None
    assert election.player_votes == 13
    assert election.ending.key == "narrow_win"
    confession_inputs = {
        vote.voter_id: vote_input
        for vote in election.votes
        for vote_input in vote.inputs
        if vote_input.key == "orin-rhea-election-confession" and vote.voter_id in contributions
    }
    assert set(confession_inputs) == set(contributions)
    for voter_id, contribution in contributions.items():
        vote_input = confession_inputs[voter_id]
        assert vote_input.value == resolution
        assert vote_input.contribution == pytest.approx(contribution)
        assert vote_input.belief_id is not None
        assert vote_input.belief_version is not None


def test_confession_cannot_be_resolved_before_orin_entrusts_it() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=133))

    with pytest.raises(InvalidActionError, match="no unresolved confession"):
        act(
            service,
            created.run_id,
            "reveal_orin_confession",
            "orin",
        )
