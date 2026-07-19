from __future__ import annotations

from uuid import UUID, uuid4

from hearsay_api.repository import InMemoryRunRepository
from hearsay_api.schemas import (
    ActionRequest,
    ActionResponse,
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
) -> ActionResponse:
    return service.take_action(
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
        transmission for transmission in lineage.transmissions if transmission.speaker_id == "pip"
    ]
    assert 2 <= len(ambient_transmissions) <= 4
    listeners = {transmission.listener_id for transmission in ambient_transmissions}
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


def test_later_tick_continues_a_rumor_from_an_ambient_holder() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=19))
    act(service, created.run_id, "promise_help", "marta")
    act(service, created.run_id, "negotiate_bram", "bram")
    act(service, created.run_id, "settle_shipment", "bram")
    continued = act(service, created.run_id, "talk", "elias")

    assert continued.snapshot.recent_events[1].kind == "rumor_continues"
    assert "Fen Lark" in continued.snapshot.recent_events[1].text
    lineage = service.get_memory_lineage(
        created.run_id,
        "bram-price-confrontation",
    )
    autonomous = [
        edge for edge in lineage.transmissions if edge.model_id == "hearsay-autonomous-echo-v1"
    ]
    assert {(edge.speaker_id, edge.listener_id) for edge in autonomous} == {
        ("fen", "orin"),
        ("fen", "rhea"),
    }
    assert all(edge.original_text != edge.retold_text for edge in autonomous)
    assert all(edge.from_version == 1 and edge.to_version == 1 for edge in autonomous)
    for listener_id in ("orin", "rhea"):
        listener = next(npc for npc in continued.snapshot.npcs if npc.id == listener_id)
        speaker = next(npc for npc in continued.snapshot.npcs if npc.id == "fen")
        assert listener.location_id == speaker.location_id
        assert listener.recent_echoes[-1].speaker_id == "fen"
        assert listener.recent_echoes[-1].speaker_name == "Fen Lark"
        assert listener.recent_echoes[-1].hop == 3
        assert listener.speech == listener.recent_echoes[-1].text

    active_autonomous = [
        version
        for version in lineage.versions
        if version.active and version.normalized_position.get("autonomous_retelling") is True
    ]
    assert {version.holder_id for version in active_autonomous} == {
        "orin",
        "rhea",
    }
    assert {version.normalized_position["echo_hop"] for version in active_autonomous} == {3}
    assert service.get_snapshot(created.run_id).npcs == continued.snapshot.npcs


def test_autonomous_rumors_stop_at_hop_four_without_duplicate_holders() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=20))
    sequence = [
        ("promise_help", "marta"),
        ("negotiate_bram", "bram"),
        *[
            ("talk", resident_id)
            for resident_id in (
                "marta",
                "elias",
                "nessa",
                "orin",
                "talia",
                "rhea",
                "pip",
                "bram",
                "marta",
                "elias",
                "nessa",
                "orin",
                "talia",
                "rhea",
            )
        ],
    ]
    for verb, target_id in sequence:
        act(service, created.run_id, verb, target_id)

    lineage = service.get_memory_lineage(created.run_id)
    autonomous_edges = [
        edge for edge in lineage.transmissions if edge.model_id == "hearsay-autonomous-echo-v1"
    ]
    assert autonomous_edges
    holder_keys = [(edge.proposition_key, edge.listener_id) for edge in autonomous_edges]
    assert len(holder_keys) == len(set(holder_keys))
    autonomous_versions = [
        version
        for version in lineage.versions
        if version.normalized_position.get("autonomous_retelling") is True
    ]
    assert max(int(version.normalized_position["echo_hop"]) for version in autonomous_versions) == 4
    assert all(int(version.normalized_position["echo_hop"]) <= 4 for version in autonomous_versions)


def test_quiet_family_memories_do_not_enter_autonomous_gossip() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=27))
    act(service, created.run_id, "accept_talia_favor", "talia")
    act(service, created.run_id, "help_oswin_quietly", "talia")
    act(service, created.run_id, "talk", "marta")
    result = act(service, created.run_id, "talk", "elias")

    lineage = service.get_memory_lineage(
        created.run_id,
        "talia-oswin-sick-house",
    )
    assert not any(edge.model_id == "hearsay-autonomous-echo-v1" for edge in lineage.transmissions)
    assert not any(event.kind == "rumor_continues" for event in result.snapshot.recent_events)


def test_later_hop_is_distance_attenuated_in_the_election_audit() -> None:
    service = GameService(repository=InMemoryRunRepository())
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=19))
    for verb, target_id in (
        ("promise_help", "marta"),
        ("negotiate_bram", "bram"),
        ("settle_shipment", "bram"),
        ("talk", "elias"),
        ("talk", "nessa"),
        ("talk", "orin"),
        ("declare_candidacy", "rhea"),
        ("sleep", None),
        ("sleep", None),
    ):
        result = act(service, created.run_id, verb, target_id)

    assert result.snapshot.election is not None
    assert result.snapshot.election.player_votes == 12
    orin_vote = next(vote for vote in result.snapshot.election.votes if vote.voter_id == "orin")
    rumor_input = next(item for item in orin_vote.inputs if item.key == "bram-price-confrontation")
    assert rumor_input.contribution == -0.0125
    assert rumor_input.belief_id is not None
    assert rumor_input.belief_version == 1
    assert "Rumor hop 3" in rumor_input.explanation


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
