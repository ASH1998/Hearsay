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


def test_market_day_draw_clusters_ambients_blocks_bram_and_restores() -> None:
    repository = InMemoryRunRepository()
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=1729))

    started = act(service, created.run_id, "sleep")
    market_day = next(event for event in started.snapshot.town_events if event.key == "market_day")

    assert market_day.status == "active"
    assert market_day.draw_seed == 2788
    assert market_day.draw_roll == 0
    assert market_day.started_day == 2
    assert market_day.started_phase == "morning"
    assert set(market_day.affected_resident_ids) == set(service.content.ambients_by_id)
    assert market_day.busy_resident_ids == ["bram"]
    assert "market_audio" in market_day.effects
    assert {
        npc.location_id for npc in started.snapshot.npcs if npc.id in service.content.ambients_by_id
    } == {"market"}
    assert any(
        event.kind == "market_day_begins"
        and event.payload["draw_seed"] == 2788
        and event.payload["affected_resident_ids"] == market_day.affected_resident_ids
        for event in started.snapshot.recent_events
    )
    assert "Half the coast" in (
        next(npc for npc in started.snapshot.npcs if npc.id == "bram").speech or ""
    )

    restored = service.get_snapshot(created.run_id)
    assert restored.town_events == started.snapshot.town_events
    assert restored.npcs == started.snapshot.npcs

    with pytest.raises(InvalidActionError, match="Walk to Market row"):
        act(service, created.run_id, "talk", "bram")

    act(service, created.run_id, "move", "square")
    act(service, created.run_id, "move", "market")
    reached = act(service, created.run_id, "talk", "bram")
    assert reached.snapshot.dialogue is not None
    assert "Half the coast" in reached.snapshot.dialogue.text

    cleared = act(service, created.run_id, "talk", "bram")
    market_day = next(event for event in cleared.snapshot.town_events if event.key == "market_day")
    argument = next(
        event for event in cleared.snapshot.town_events if event.key == "public_argument"
    )
    assert market_day.status == "resolved"
    assert market_day.resolved_day == 2
    assert market_day.resolved_phase == "afternoon"
    assert argument.status == "active"
    assert {npc.location_id for npc in cleared.snapshot.npcs} == {"square"}
    assert cleared.snapshot.recent_events[1].kind == "public_argument_begins"
    assert cleared.snapshot.recent_events[2].kind == "market_day_clears"


def test_market_day_skip_is_deterministic_and_private() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=1728))

    result = act(service, created.run_id, "sleep")
    market_day = next(event for event in result.snapshot.town_events if event.key == "market_day")
    skip = next(
        event for event in result.snapshot.recent_events if event.kind == "market_day_skipped"
    )

    assert market_day.status == "skipped"
    assert market_day.draw_seed == 2787
    assert market_day.draw_roll == 1
    assert skip.visible is False
    assert skip.payload["draw_roll"] == 1
    assert {
        npc.location_id for npc in result.snapshot.npcs if npc.id in service.content.ambients_by_id
    } != {"market"}
