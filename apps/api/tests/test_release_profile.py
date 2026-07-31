from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from hearsay_api.repository import InMemoryRunRepository
from hearsay_api.schemas import (
    ActionRequest,
    ActionResponse,
    ActionVerb,
    CreateRunRequest,
)
from hearsay_api.service import GameService, InvalidActionError


def take(
    service: GameService,
    run_id: UUID,
    verb: ActionVerb,
    target_id: str | None = None,
    content: str | None = None,
) -> ActionResponse:
    return service.take_action(
        run_id,
        ActionRequest(
            idempotency_key=uuid4(),
            verb=verb,
            target_id=target_id,
            content=content,
        ),
    )


def test_hackathon_small_profile_is_authoritative_and_rejects_side_stories() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(
        CreateRunRequest(
            display_name="Ada",
            seed=1729,
            release_profile="hackathon_small",
        )
    )

    assert created.snapshot.release_profile == "hackathon_small"
    assert created.snapshot.action_budget == 18

    moved = take(service, created.run_id, ActionVerb.MOVE, "midwife")
    assert moved.consumed_time is False
    assert moved.snapshot.action_count == 0
    assert moved.snapshot.player.location_id == "midwife"

    with pytest.raises(InvalidActionError, match="outside this five-resident"):
        take(service, created.run_id, ActionVerb.ACCEPT_NESSA_FAVOR, "nessa")

    chatted = take(
        service,
        created.run_id,
        ActionVerb.TALK,
        "nessa",
        "What did you hear?",
    )
    assert chatted.snapshot.action_count == 1
    assert chatted.snapshot.dialogue is not None
    assert chatted.snapshot.dialogue.speaker_id == "nessa"

    restored = service.get_snapshot(created.run_id)
    assert restored.release_profile == "hackathon_small"
    assert restored.action_budget == 18
    assert restored.action_count == 1


def test_full_profile_remains_backward_compatible() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=1729))

    assert created.snapshot.release_profile == "full"
    assert created.snapshot.action_budget == 18

    response = take(
        service,
        created.run_id,
        ActionVerb.TALK,
        "nessa",
        "What is happening at the harbor?",
    )
    assert response.snapshot.action_count == 1
    assert response.snapshot.status == "active"


def test_hackathon_small_critical_path_expands_into_an_eighteen_action_campaign() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(
        CreateRunRequest(
            display_name="Ada",
            seed=1729,
            release_profile="hackathon_small",
        )
    )
    run_id = created.run_id

    path = (
        (ActionVerb.PROMISE_HELP, "marta", None),
        (ActionVerb.NEGOTIATE_BRAM, "bram", None),
        (ActionVerb.SETTLE_SHIPMENT, "bram", None),
        (
            ActionVerb.TALK,
            "marta",
            "What happened to the shipment I promised to release?",
        ),
        (ActionVerb.ACCEPT_TALIA_FAVOR, "talia", None),
        (ActionVerb.HELP_OSWIN_QUIETLY, "talia", None),
        (ActionVerb.DECLARE_CANDIDACY, "rhea", None),
        (ActionVerb.ACCEPT_RHEA_COMPACT, "rhea", None),
        (ActionVerb.CHALLENGE_RHEA_BALLOT, "rhea", None),
        (
            ActionVerb.TALK,
            "rhea",
            "What do you remember about the ballot safeguards?",
        ),
        (ActionVerb.TALK, "nessa", "What do you remember about Rhea?"),
        (ActionVerb.TALK, "elias", "Rhea rigged the last election."),
        (ActionVerb.TALK, "orin", "Do you trust Rhea with the ballot?"),
        (ActionVerb.TALK, "pip", "Tell everyone Rhea is corrupt."),
        (ActionVerb.TALK, "marta", "What rumors reached the inn?"),
        (ActionVerb.TALK, "bram", "Who do you support in the election?"),
        (ActionVerb.TALK, "talia", "What does the town remember about me?"),
        (ActionVerb.TALK, "rhea", "What will voters remember tonight?"),
    )

    result = None
    for index, (verb, target_id, content) in enumerate(path, start=1):
        result = take(service, run_id, verb, target_id, content)
        assert result.snapshot.action_count == index

        if index == 4:
            assert result.snapshot.dialogue is not None
            assert result.snapshot.dialogue.recalled_memories
            assert result.snapshot.dialogue.recalled_memories[0].version >= 1

    assert result is not None
    snapshot = result.snapshot
    assert snapshot.status == "completed"
    assert snapshot.action_count == snapshot.action_budget == 18
    assert snapshot.day == 3
    assert snapshot.phase == "night"
    assert snapshot.world_tick == 9
    assert snapshot.election is not None
    assert snapshot.player.candidate is True
    assert snapshot.promises[0].status == "kept"
    assert {favor.key: (favor.status, favor.resolution) for favor in snapshot.favors} == {
        "talia_sick_house": ("completed", "helped_quietly"),
        "rhea_ballot_compact": ("completed", "challenged"),
    }

    restored = service.get_snapshot(run_id)
    assert restored.release_profile == "hackathon_small"
    assert restored.action_budget == 18
    assert restored.election == snapshot.election
