from __future__ import annotations

from uuid import UUID, uuid4

from hearsay_api.repository import InMemoryRunRepository
from hearsay_api.schemas import ActionRequest, ActionResponse, CreateRunRequest
from hearsay_api.service import GameService


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


def test_storm_has_render_state_schedule_override_awareness_and_refresh() -> None:
    repository = InMemoryRunRepository()
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=90))

    for target in ("marta", "bram", "pip", "rhea"):
        storm = act(service, created.run_id, "talk", target)

    assert storm.snapshot.day == 1
    assert storm.snapshot.phase == "evening"
    assert storm.snapshot.weather == "rain"
    assert len(storm.snapshot.town_events) == 1
    event = storm.snapshot.town_events[0]
    assert event.key == "storm"
    assert event.status == "active"
    assert event.started_day == 1
    assert event.started_phase == "evening"
    assert {npc.location_id for npc in storm.snapshot.npcs} == {"inn"}
    assert storm.snapshot.recent_events[1].kind == "storm_begins"
    assert storm.snapshot.recent_events[2].kind == "schedule_shift"
    nessa = next(npc for npc in storm.snapshot.npcs if npc.id == "nessa")
    assert "living crews" in (nessa.speech or "")

    restored = service.get_snapshot(created.run_id)
    assert restored.weather == "rain"
    assert restored.town_events == storm.snapshot.town_events
    assert restored.npcs == storm.snapshot.npcs

    aware = act(service, created.run_id, "talk", "nessa")
    assert aware.snapshot.dialogue is not None
    assert "living crews" in aware.snapshot.dialogue.text

    cleared = act(service, created.run_id, "sleep")
    assert cleared.snapshot.day == 2
    assert cleared.snapshot.phase == "morning"
    assert cleared.snapshot.weather == "clear"
    assert cleared.snapshot.town_events[0].status == "resolved"
    assert cleared.snapshot.town_events[0].resolved_day == 2
    assert cleared.snapshot.town_events[0].resolved_phase == "morning"
    assert cleared.snapshot.recent_events[1].kind == "storm_clears"
    assert {npc.location_id for npc in cleared.snapshot.npcs} != {"inn"}
    assert "harbor is open again" in (
        next(npc for npc in cleared.snapshot.npcs if npc.id == "nessa").speech or ""
    )


def test_sleeping_through_storm_still_records_both_lifecycle_events() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=92))

    result = act(service, created.run_id, "sleep")

    assert result.snapshot.day == 2
    assert result.snapshot.weather == "clear"
    assert result.snapshot.town_events[0].status == "resolved"
    assert [event.kind for event in result.snapshot.recent_events[:3]] == [
        "sleep",
        "storm_begins",
        "storm_clears",
    ]
