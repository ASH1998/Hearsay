from __future__ import annotations

from uuid import UUID, uuid4

from hearsay_api.repository import InMemoryRunRepository
from hearsay_api.schemas import ActionRequest, CreateRunRequest
from hearsay_api.service import GameService


def act(service: GameService, run_id: UUID, verb: str, target_id: str) -> None:
    service.take_action(
        run_id,
        ActionRequest(
            idempotency_key=uuid4(),
            verb=verb,
            target_id=target_id,
        ),
    )


def locations_by_resident(service: GameService, run_id: UUID) -> dict[str, str]:
    return {
        npc.id: npc.location_id
        for npc in service.get_snapshot(run_id).npcs
    }


def test_three_day_schedules_move_all_residents_and_survive_refresh() -> None:
    repository = InMemoryRunRepository()
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=73))

    morning = locations_by_resident(service, created.run_id)
    assert len(morning) == 20
    assert morning["pip"] == "square"
    assert morning["elias"] == "constable"

    act(service, created.run_id, "talk", "marta")
    act(service, created.run_id, "talk", "pip")
    afternoon_snapshot = service.get_snapshot(created.run_id)
    afternoon = {npc.id: npc.location_id for npc in afternoon_snapshot.npcs}

    assert afternoon["pip"] == "market"
    assert afternoon["elias"] == "market"
    assert afternoon != morning
    assert afternoon_snapshot.recent_events[1].kind == "schedule_shift"
    assert "Afternoon routines move" in afternoon_snapshot.recent_events[1].text
    assert locations_by_resident(service, created.run_id) == afternoon

    act(service, created.run_id, "talk", "bram")
    act(service, created.run_id, "talk", "rhea")
    evening_snapshot = service.get_snapshot(created.run_id)
    evening = {npc.id: npc.location_id for npc in evening_snapshot.npcs}
    assert evening["pip"] == "inn"
    assert evening["rhea"] == "inn"
    assert evening["nessa"] == "inn"
    assert evening_snapshot.recent_events[1].kind == "schedule_shift"

    act(service, created.run_id, "sleep", "marta")
    day_two_snapshot = service.get_snapshot(created.run_id)
    assert day_two_snapshot.day == 2
    assert day_two_snapshot.phase == "morning"
    assert next(
        npc.location_id
        for npc in day_two_snapshot.npcs
        if npc.id == "pip"
    ) == "square"
    assert day_two_snapshot.recent_events[1].kind == "schedule_shift"
    assert locations_by_resident(service, created.run_id) == {
        npc.id: npc.location_id
        for npc in day_two_snapshot.npcs
    }
