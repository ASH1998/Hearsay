from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from hearsay_api.content import load_content
from hearsay_api.election import classify_ending, resolve_election
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
    ("votes", "traits", "candidate", "expected"),
    [
        (15, set(), True, "landslide"),
        (11, set(), True, "narrow_win"),
        (10, set(), True, "narrow_loss"),
        (4, set(), True, "humiliation"),
        (12, {"Dishonest"}, True, "exposed"),
        (15, {"Dangerous", "Troublemaker"}, True, "run_out_of_town"),
        (20, set(), False, "humiliation"),
    ],
)
def test_all_ending_classes_have_deterministic_thresholds(
    votes: int,
    traits: set[str],
    candidate: bool,
    expected: str,
) -> None:
    assert (
        classify_ending(
            player_votes=votes,
            traits=traits,
            candidate=candidate,
        )
        == expected
    )


def test_kept_promise_produces_explainable_winning_election() -> None:
    repository = InMemoryRunRepository()
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=51))
    act(service, created.run_id, "promise_help", "marta")
    act(service, created.run_id, "settle_shipment", "bram")
    act(service, created.run_id, "sleep")
    declaration = act(service, created.run_id, "declare_candidacy", "rhea")
    assert declaration.snapshot.player.candidate is True
    act(service, created.run_id, "sleep")

    result = act(service, created.run_id, "sleep")

    assert result.snapshot.status == "completed"
    election = result.snapshot.election
    assert election is not None
    assert len(election.votes) == 20
    assert election.player_votes == 11
    assert election.rhea_votes == 9
    assert election.winner == "player"
    assert election.ending.key == "narrow_win"
    assert len(election.ending.decisive_voter_ids) == 3
    marta_vote = next(vote for vote in election.votes if vote.voter_id == "marta")
    promise_input = next(
        item
        for item in marta_vote.inputs
        if item.kind == "belief"
        and item.key == "player-promise-marta-shipment"
    )
    assert promise_input.value == "kept"
    assert promise_input.belief_id is not None
    assert promise_input.belief_version == 2
    assert promise_input.explanation
    assert {item.decisive_rank for item in marta_vote.inputs if item.decisive_rank} == {
        1,
        2,
        3,
    }

    restored = service.get_snapshot(created.run_id)
    assert restored.election == election


def test_ten_ten_tie_resolves_to_rhea_and_is_replay_stable() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=52))
    snapshot = created.snapshot
    snapshot.player.candidate = True
    for voter_id in ("marta", "elias", "orin", "nessa", "pip", "mae"):
        next(npc for npc in snapshot.npcs if npc.id == voter_id).relationship = 100
    lineage = service.get_memory_lineage(created.run_id)

    first = resolve_election(snapshot, load_content(), lineage)
    second = resolve_election(snapshot, load_content(), lineage)

    assert first == second
    assert first.player_votes == 10
    assert first.rhea_votes == 10
    assert first.winner == "rhea"
    assert first.tie_favors_rhea is True
    assert first.ending.key == "narrow_loss"


def test_candidacy_cannot_be_declared_before_day_two() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=53))

    with pytest.raises(InvalidActionError, match="before day two"):
        act(service, created.run_id, "declare_candidacy", "rhea")
