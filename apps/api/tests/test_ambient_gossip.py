from __future__ import annotations

from uuid import UUID, uuid4

from hearsay_api.repository import InMemoryRunRepository
from hearsay_api.schemas import (
    ActionRequest,
    CreateRunRequest,
    MemoryRecallRequest,
    MemoryRecallResponse,
)
from hearsay_api.service import GameService


def act(
    service: GameService,
    run_id: UUID,
    verb: str,
    target_id: str | None = None,
) -> None:
    service.take_action(
        run_id,
        ActionRequest(
            idempotency_key=uuid4(),
            verb=verb,
            target_id=target_id,
        ),
    )


def test_pip_echoes_to_two_to_four_colocated_ambients_with_lineage() -> None:
    repository = InMemoryRunRepository()
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=19))
    act(service, created.run_id, "promise_help", "marta")
    act(service, created.run_id, "negotiate_bram", "bram")

    snapshot = service.get_snapshot(created.run_id)
    assert snapshot.recent_events[1].kind == "ambient_gossip"
    lineage = service.get_memory_lineage(
        created.run_id,
        "bram-price-confrontation",
    )
    ambient_transmissions = [
        transmission
        for transmission in lineage.transmissions
        if transmission.speaker_id == "pip"
    ]
    assert 2 <= len(ambient_transmissions) <= 4
    listeners = {
        transmission.listener_id
        for transmission in ambient_transmissions
    }
    assert listeners <= set(service.content.ambients_by_id)
    assert all(
        next(npc for npc in snapshot.npcs if npc.id == listener).location_id
        == next(npc for npc in snapshot.npcs if npc.id == "pip").location_id
        for listener in listeners
    )
    for listener in listeners:
        npc = next(npc for npc in snapshot.npcs if npc.id == listener)
        assert len(npc.recent_echoes) == 1
        assert npc.recent_echoes[0].speaker_id == "pip"
        assert npc.speech == npc.recent_echoes[0].text
    assert service.get_snapshot(created.run_id).npcs == snapshot.npcs


def test_ambient_recall_is_capped_to_three_shallow_memories() -> None:
    class RecordingRepository(InMemoryRunRepository):
        recall_limit: int | None = None

        def recall_memories(
            self,
            run_id: UUID,
            holder_id: str,
            query_text: str,
            query_embedding: tuple[float, ...],
            limit: int,
        ) -> MemoryRecallResponse:
            self.recall_limit = limit
            return super().recall_memories(
                run_id,
                holder_id,
                query_text,
                query_embedding,
                limit,
            )

    repository = RecordingRepository()
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=20))

    service.recall_memories(
        created.run_id,
        MemoryRecallRequest(
            holder_id="jonas",
            query="What has Pip said?",
            limit=8,
        ),
    )

    assert repository.recall_limit == 3
