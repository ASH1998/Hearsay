from __future__ import annotations

from uuid import UUID, uuid4

from hearsay_api.memory import chat_standing_deltas
from hearsay_api.repository import InMemoryRunRepository
from hearsay_api.schemas import (
    ActionRequest,
    ActionResponse,
    ActionVerb,
    CreateRunRequest,
    CreateRunResponse,
    RunSnapshot,
)
from hearsay_api.service import GameService


def talk(
    service: GameService,
    run_id: UUID,
    npc_id: str,
    message: str,
    *,
    public: bool = False,
) -> ActionResponse:
    return service.take_action(
        run_id,
        ActionRequest(
            idempotency_key=uuid4(),
            verb=ActionVerb.TALK,
            target_id=npc_id,
            content=message,
            public_statement=public,
        ),
    )


def new_run(service: GameService) -> CreateRunResponse:
    return service.create_run(
        CreateRunRequest(
            display_name="Ada",
            seed=1729,
            release_profile="hackathon_small",
        )
    )


def standing(snapshot: RunSnapshot, npc_id: str) -> int:
    npc = next(npc for npc in snapshot.npcs if npc.id == npc_id)
    return int(npc.relationship)


def test_private_extortion_only_moves_the_resident_who_heard_it() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = new_run(service)
    assert standing(created.snapshot, "nessa") == 0

    result = talk(service, created.run_id, "nessa", "gimme all your money")

    assert standing(result.snapshot, "nessa") == -12
    others = [npc.relationship for npc in result.snapshot.npcs if npc.id != "nessa"]
    assert others == [0] * len(others)


def test_public_extortion_ripples_faintly_to_every_witness() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = new_run(service)

    result = talk(service, created.run_id, "nessa", "gimme all your money", public=True)

    assert standing(result.snapshot, "nessa") == -12
    others = [npc.relationship for npc in result.snapshot.npcs if npc.id != "nessa"]
    assert others == [-3] * len(others)


def test_repeated_public_hostility_compounds_until_the_town_turns() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = new_run(service)
    run_id = created.run_id

    for _ in range(4):
        result = talk(service, run_id, "nessa", "gimme all your money", public=True)

    # The direct target degrades four times faster than the bystanders.
    assert standing(result.snapshot, "nessa") == -48
    others = [npc.relationship for npc in result.snapshot.npcs if npc.id != "nessa"]
    assert others == [-12] * len(others)


def test_courtesy_raises_standing_instead_of_lowering_it() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = new_run(service)

    result = talk(service, created.run_id, "nessa", "thank you, please tell me about the town")

    assert standing(result.snapshot, "nessa") > 0


def test_ordinary_questions_leave_standing_untouched() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = new_run(service)

    result = talk(service, created.run_id, "nessa", "What should a newcomer know?")

    assert standing(result.snapshot, "nessa") == 0


def test_hostile_chat_is_cued_to_the_player() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = new_run(service)

    result = talk(service, created.run_id, "nessa", "gimme all your money", public=True)

    assert result.snapshot.dialogue is not None
    cue = result.snapshot.dialogue.treatment_cue
    assert cue is not None
    assert "Hostile" in cue
    assert "whole town heard it" in cue


def test_witnesses_stay_still_for_a_private_exchange() -> None:
    assert chat_standing_deltas("hostile", public_statement=False) == (-12, 0)
    assert chat_standing_deltas("hostile", public_statement=True) == (-12, -3)
    assert chat_standing_deltas("neutral", public_statement=True) == (0, 0)
    assert chat_standing_deltas("generous", public_statement=False) == (6, 0)
