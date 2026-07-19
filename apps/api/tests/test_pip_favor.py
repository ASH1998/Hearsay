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
        "core_contributions",
        "event_kind",
        "player_votes",
        "ending",
    ),
    [
        (
            "verify_pip_source",
            "verified_source",
            ["Reliable", "Influential"],
            ["pip"],
            {"pip": 25, "kit": 20, "edda": 20, "tob": 10},
            {
                ("player", "kit"),
                ("kit", "pip"),
                ("kit", "edda"),
                ("pip", "tob"),
            },
            {"kit": 0.45, "pip": 0.4, "edda": 0.4, "tob": 0.25},
            "pip_source_verified",
            15,
            "landslide",
        ),
        (
            "embellish_pip_rumor",
            "embellished",
            ["Influential", "Troublemaker"],
            [],
            {
                "pip": 30,
                "tob": 15,
                "marta": -20,
                "kit": -25,
                "hettie": 10,
                "cal": 10,
                "del": 10,
            },
            {
                ("player", "pip"),
                ("pip", "tob"),
                ("tob", "marta"),
                ("pip", "hettie"),
                ("hettie", "cal"),
                ("tob", "del"),
                ("player", "kit"),
            },
            {
                "pip": 0.45,
                "tob": 0.3,
                "marta": -0.35,
                "hettie": 0.5,
                "cal": 0.4,
                "kit": -0.45,
            },
            "pip_rumor_embellished",
            8,
            "narrow_loss",
        ),
    ],
)
def test_pip_source_choices_create_traceable_mutation_and_votes(
    verb: str,
    resolution: str,
    traits: list[str],
    endorsements: list[str],
    relationships: dict[str, int],
    required_edges: set[tuple[str, str]],
    core_contributions: dict[str, float],
    event_kind: str,
    player_votes: int,
    ending: str,
) -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=161))

    accepted = act(service, created.run_id, "accept_pip_favor", "pip")
    favor = accepted.snapshot.favors[0]
    assert favor.key == "pip_ballot_source"
    assert favor.status == "active"
    assert favor.resolution is None
    assert accepted.snapshot.recent_events[0].kind == "pip_source_entrusted"
    assert "receipt" in (
        next(npc for npc in accepted.snapshot.npcs if npc.id == "kit").speech or ""
    )

    entrusted_lineage = service.get_memory_lineage(
        created.run_id,
        "pip-rhea-ballot-source",
    )
    assert {version.holder_id for version in entrusted_lineage.versions} == {
        "pip",
        "player",
    }
    assert {(edge.speaker_id, edge.listener_id) for edge in entrusted_lineage.transmissions} == {
        ("pip", "player")
    }

    resolved = act(service, created.run_id, verb, "pip")
    favor = resolved.snapshot.favors[0]
    assert favor.status == "completed"
    assert favor.resolution == resolution
    assert resolved.snapshot.player.traits == traits
    assert resolved.snapshot.player.endorsements == endorsements
    assert resolved.snapshot.recent_events[0].kind == event_kind
    assert resolved.snapshot.recent_events[1].kind == "ambient_gossip"
    for resident_id, relationship in relationships.items():
        assert (
            next(npc.relationship for npc in resolved.snapshot.npcs if npc.id == resident_id)
            == relationship
        )

    other_verb = "embellish_pip_rumor" if verb == "verify_pip_source" else "verify_pip_source"
    with pytest.raises(InvalidActionError, match="no unresolved ballot-source"):
        act(service, created.run_id, other_verb, "pip")

    lineage = service.get_memory_lineage(
        created.run_id,
        "pip-rhea-ballot-source",
    )
    edges = {(edge.speaker_id, edge.listener_id) for edge in lineage.transmissions}
    assert {("pip", "player"), *required_edges} <= edges
    assert any(
        speaker_id == "pip" and listener_id not in {"player", "tob", "hettie"}
        for speaker_id, listener_id in edges
    )
    assert len([version for version in lineage.versions if version.holder_id == "player"]) == 2

    act(service, created.run_id, "sleep")
    act(service, created.run_id, "declare_candidacy", "rhea")
    act(service, created.run_id, "sleep")
    election_state = act(service, created.run_id, "sleep").snapshot.election
    assert election_state is not None
    assert election_state.player_votes == player_votes
    assert election_state.ending.key == ending
    source_inputs = {
        vote.voter_id: vote_input
        for vote in election_state.votes
        for vote_input in vote.inputs
        if vote_input.key == "pip-rhea-ballot-source" and vote.voter_id in core_contributions
    }
    assert set(source_inputs) == set(core_contributions)
    for voter_id, contribution in core_contributions.items():
        vote_input = source_inputs[voter_id]
        assert vote_input.value == resolution
        assert vote_input.contribution == pytest.approx(contribution)
        assert vote_input.belief_id is not None
        assert vote_input.belief_version is not None


def test_ballot_source_cannot_be_resolved_before_pip_offers_it() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=162))

    with pytest.raises(InvalidActionError, match="no unresolved ballot-source"):
        act(service, created.run_id, "verify_pip_source", "pip")
