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
            "help_oswin_quietly",
            "helped_quietly",
            ["Generous", "Reliable"],
            ["talia"],
            {"talia": 30, "oswin": 25, "lina": 20, "marta": 10},
            {
                ("player", "talia"),
                ("talia", "oswin"),
                ("talia", "lina"),
                ("talia", "marta"),
            },
            {"talia": 0.45, "oswin": 0.45, "lina": 0.4, "marta": 0.25},
            "talia_sick_house_helped",
            12,
            "narrow_win",
        ),
        (
            "gossip_oswin_illness",
            "gossiped_publicly",
            ["Influential"],
            [],
            {"talia": -30, "oswin": -25, "lina": -15, "pip": 10},
            {
                ("player", "talia"),
                ("player", "oswin"),
                ("player", "lina"),
                ("player", "pip"),
            },
            {"talia": -0.4, "oswin": -0.45, "lina": -0.35, "pip": 0.2},
            "talia_sick_house_gossiped",
            9,
            "narrow_loss",
        ),
    ],
)
def test_talia_sick_house_choices_change_family_memory_and_votes(
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
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=141))

    accepted = act(service, created.run_id, "accept_talia_favor", "talia")
    favor = accepted.snapshot.favors[0]
    assert favor.key == "talia_sick_house"
    assert favor.status == "active"
    assert favor.resolution is None
    assert accepted.snapshot.recent_events[0].kind == "talia_sick_house_entrusted"
    assert "ordinary" in (
        next(npc for npc in accepted.snapshot.npcs if npc.id == "oswin").speech
        or ""
    )

    entrusted_lineage = service.get_memory_lineage(
        created.run_id,
        "talia-oswin-sick-house",
    )
    assert {version.holder_id for version in entrusted_lineage.versions} == {
        "talia",
        "player",
    }
    assert {
        (edge.speaker_id, edge.listener_id)
        for edge in entrusted_lineage.transmissions
    } == {("talia", "player")}

    resolved = act(service, created.run_id, verb, "talia")
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
        "gossip_oswin_illness"
        if verb == "help_oswin_quietly"
        else "help_oswin_quietly"
    )
    with pytest.raises(InvalidActionError, match="no unresolved sick-house"):
        act(service, created.run_id, other_verb, "talia")

    lineage = service.get_memory_lineage(
        created.run_id,
        "talia-oswin-sick-house",
    )
    edges = {
        (edge.speaker_id, edge.listener_id)
        for edge in lineage.transmissions
    }
    assert {("talia", "player"), *required_edges} <= edges
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
    sick_house_inputs = {
        vote.voter_id: vote_input
        for vote in election_state.votes
        for vote_input in vote.inputs
        if vote_input.key == "talia-oswin-sick-house"
        and vote.voter_id in contributions
    }
    assert set(sick_house_inputs) == set(contributions)
    for voter_id, contribution in contributions.items():
        vote_input = sick_house_inputs[voter_id]
        assert vote_input.value == resolution
        assert vote_input.contribution == pytest.approx(contribution)
        assert vote_input.belief_id is not None
        assert vote_input.belief_version is not None


def test_sick_house_favor_cannot_be_resolved_before_talia_offers_it() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=142))

    with pytest.raises(InvalidActionError, match="no unresolved sick-house"):
        act(service, created.run_id, "help_oswin_quietly", "talia")
