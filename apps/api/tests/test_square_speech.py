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


def test_unsupported_candidacy_reaches_humiliation_through_normal_play() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=121))
    act(service, created.run_id, "sleep")
    act(service, created.run_id, "declare_candidacy", "rhea")
    act(service, created.run_id, "sleep")
    result = act(service, created.run_id, "sleep")

    assert result.snapshot.election is not None
    assert result.snapshot.election.ending.key == "humiliation"


def test_square_speech_is_once_daily_and_produces_audited_ten_ten_loss() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=122))
    act(service, created.run_id, "sleep")
    act(service, created.run_id, "declare_candidacy", "rhea")

    speech = act(service, created.run_id, "give_square_speech", "square")
    assert speech.snapshot.player.square_speech_days == [2]
    assert speech.snapshot.player.traits == ["Influential"]
    assert speech.snapshot.recent_events[0].kind == "square_speech"
    assert speech.snapshot.recent_events[1].kind == "ambient_gossip"

    with pytest.raises(InvalidActionError, match="already addressed"):
        act(service, created.run_id, "give_square_speech", "square")

    act(service, created.run_id, "sleep")
    result = act(service, created.run_id, "sleep")
    election = result.snapshot.election
    assert election is not None
    assert election.player_votes == 10
    assert election.rhea_votes == 10
    assert election.tie_favors_rhea is True
    assert election.ending.key == "narrow_loss"
    pip_vote = next(vote for vote in election.votes if vote.voter_id == "pip")
    speech_input = next(
        item
        for item in pip_vote.inputs
        if item.key == "player-square-speech"
    )
    assert speech_input.belief_id is not None
    assert speech_input.contribution == pytest.approx(-0.01)
