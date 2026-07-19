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
        "relationships",
        "required_edges",
        "core_contributions",
        "event_kind",
        "player_votes",
        "ending",
    ),
    [
        (
            "challenge_rhea_ballot",
            "challenged",
            ["Reliable", "Troublemaker"],
            {
                "rhea": -35,
                "elias": 25,
                "edda": 25,
                "tob": 20,
                "pip": 15,
                "marta": 10,
                "orin": 10,
                "nessa": 10,
                "lina": 10,
                "kit": 10,
            },
            {
                ("player", "rhea"),
                ("player", "elias"),
                ("elias", "edda"),
                ("edda", "tob"),
                ("tob", "pip"),
                ("tob", "marta"),
                ("edda", "orin"),
                ("elias", "nessa"),
                ("pip", "lina"),
                ("pip", "kit"),
            },
            {
                "rhea": -0.55,
                "elias": 0.55,
                "edda": 0.5,
                "tob": 0.45,
                "pip": 0.4,
                "marta": 0.35,
                "orin": 0.35,
                "nessa": 0.3,
                "lina": 0.3,
                "kit": 0.3,
            },
            "rhea_ballot_challenged",
            12,
            "narrow_win",
        ),
        (
            "deal_with_rhea",
            "made_deal",
            ["Influential"],
            {
                "rhea": 35,
                "bram": 25,
                "hettie": 25,
                "cal": 20,
                "will": 15,
                "kit": 10,
                "pip": -10,
                "elias": -20,
                "edda": -15,
            },
            {
                ("player", "rhea"),
                ("rhea", "bram"),
                ("bram", "hettie"),
                ("hettie", "cal"),
                ("rhea", "will"),
                ("rhea", "kit"),
                ("kit", "pip"),
                ("player", "elias"),
                ("elias", "edda"),
            },
            {
                "rhea": 0.25,
                "bram": 0.5,
                "hettie": 0.55,
                "cal": 0.45,
                "will": 0.35,
                "kit": 0.3,
                "pip": -0.2,
                "elias": -0.3,
                "edda": -0.25,
            },
            "rhea_compact_signed",
            14,
            "landslide",
        ),
    ],
)
def test_rhea_compact_choices_persist_ballot_custody_and_votes(
    verb: str,
    resolution: str,
    traits: list[str],
    relationships: dict[str, int],
    required_edges: set[tuple[str, str]],
    core_contributions: dict[str, float],
    event_kind: str,
    player_votes: int,
    ending: str,
) -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=171))

    act(service, created.run_id, "sleep")
    act(service, created.run_id, "declare_candidacy", "rhea")
    accepted = act(service, created.run_id, "accept_rhea_compact", "rhea")
    favor = accepted.snapshot.favors[0]
    assert favor.key == "rhea_ballot_compact"
    assert favor.status == "active"
    assert favor.resolution is None
    assert accepted.snapshot.recent_events[0].kind == "rhea_compact_offered"
    assert "overwritten totals" in (
        next(npc for npc in accepted.snapshot.npcs if npc.id == "kit").speech or ""
    )

    offered_lineage = service.get_memory_lineage(
        created.run_id,
        "rhea-ballot-custody",
    )
    assert {version.holder_id for version in offered_lineage.versions} == {
        "rhea",
        "player",
    }
    assert {(edge.speaker_id, edge.listener_id) for edge in offered_lineage.transmissions} == {
        ("rhea", "player")
    }

    resolved = act(service, created.run_id, verb, "rhea")
    favor = resolved.snapshot.favors[0]
    assert favor.status == "completed"
    assert favor.resolution == resolution
    assert resolved.snapshot.player.traits == traits
    assert resolved.snapshot.recent_events[0].kind == event_kind
    for resident_id, relationship in relationships.items():
        assert (
            next(npc.relationship for npc in resolved.snapshot.npcs if npc.id == resident_id)
            == relationship
        )

    other_verb = "deal_with_rhea" if verb == "challenge_rhea_ballot" else "challenge_rhea_ballot"
    with pytest.raises(InvalidActionError, match="no unresolved guild ballot compact"):
        act(service, created.run_id, other_verb, "rhea")

    lineage = service.get_memory_lineage(
        created.run_id,
        "rhea-ballot-custody",
    )
    edges = {(edge.speaker_id, edge.listener_id) for edge in lineage.transmissions}
    assert {("rhea", "player"), *required_edges} <= edges
    assert len([version for version in lineage.versions if version.holder_id == "player"]) == 2

    act(service, created.run_id, "sleep")
    election_state = act(service, created.run_id, "sleep").snapshot.election
    assert election_state is not None
    assert election_state.player_votes == player_votes
    assert election_state.ending.key == ending
    compact_inputs = {
        vote.voter_id: vote_input
        for vote in election_state.votes
        for vote_input in vote.inputs
        if vote_input.key == "rhea-ballot-custody"
    }
    assert set(compact_inputs) == set(core_contributions)
    for voter_id, contribution in core_contributions.items():
        vote_input = compact_inputs[voter_id]
        assert vote_input.value == resolution
        assert vote_input.contribution == pytest.approx(contribution)
        assert vote_input.belief_id is not None
        assert vote_input.belief_version is not None


def test_rhea_does_not_offer_ballot_terms_before_candidacy() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=172))

    with pytest.raises(InvalidActionError, match="only to a declared candidate"):
        act(service, created.run_id, "accept_rhea_compact", "rhea")

    act(service, created.run_id, "sleep")
    with pytest.raises(InvalidActionError, match="no unresolved guild ballot compact"):
        act(service, created.run_id, "challenge_rhea_ballot", "rhea")
