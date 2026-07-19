from __future__ import annotations

import asyncio
import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url

from hearsay_api.conflicts import ClaimResolution, IncomingClaim
from hearsay_api.historian import HistorianService
from hearsay_api.memory import DeterministicEmbeddingProvider
from hearsay_api.persistence.cockroach_repository import CockroachRunRepository
from hearsay_api.persistence.database import normalize_cockroach_url
from hearsay_api.persistence.models import (
    ActionModel,
    ActiveMemoryModel,
    BeliefInputModel,
    BeliefModel,
    BeliefVersionModel,
    ElectionModel,
    EventModel,
    EvidenceLinkModel,
    EvidenceModel,
    GameRunModel,
    HistorianAuditModel,
    RelationshipModel,
    RetrievalTraceModel,
    TransmissionModel,
    VoteInputModel,
    VoteModel,
)
from hearsay_api.schemas import ActionRequest, CreateRunRequest, HistorianTraceRequest
from hearsay_api.service import GameService

TEST_DATABASE_URL = os.getenv("HEARSAY_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.cockroach,
    pytest.mark.skipif(
        not TEST_DATABASE_URL,
        reason="HEARSAY_TEST_DATABASE_URL is not configured.",
    ),
]


@pytest.fixture
def repository() -> Iterator[CockroachRunRepository]:
    assert TEST_DATABASE_URL is not None
    database_name = make_url(normalize_cockroach_url(TEST_DATABASE_URL)).database
    if database_name is None or not database_name.endswith("_test"):
        pytest.fail("Cockroach integration tests require a database ending in '_test'.")
    repo = CockroachRunRepository(TEST_DATABASE_URL)
    repo.clear_all()
    try:
        yield repo
    finally:
        repo.clear_all()
        repo.dispose()


def test_run_and_idempotent_action_survive_repository_recreation(
    repository: CockroachRunRepository,
) -> None:
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=42))
    action = ActionRequest(
        idempotency_key=uuid4(),
        verb="promise_help",
        target_id="marta",
    )

    first = service.take_action(created.run_id, action)
    second = service.take_action(created.run_id, action)

    assert first == second
    assert first.snapshot.revision == 1

    replacement = CockroachRunRepository(TEST_DATABASE_URL or "")
    try:
        restored = replacement.get(created.run_id)
        assert restored == first.snapshot
    finally:
        replacement.dispose()

    with repository.session_factory() as session:
        action_count = session.scalar(select(func.count()).select_from(ActionModel))
        event_count = session.scalar(select(func.count()).select_from(EventModel))
    assert action_count == 1
    assert event_count == 2


def test_concurrent_actions_commit_complete_monotonic_history(
    repository: CockroachRunRepository,
) -> None:
    service = GameService(repository=repository, max_concurrency_retries=8)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=7))
    requests = [
        ActionRequest(
            idempotency_key=uuid4(),
            verb="talk",
            target_id=target,
        )
        for target in ("marta", "bram")
    ]

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda request: service.take_action(created.run_id, request),
                requests,
            )
        )

    restored = repository.get(created.run_id)
    assert {result.snapshot.revision for result in results} == {1, 2}
    assert restored.revision == 2
    assert restored.action_count == 2
    assert restored.world_tick == 1

    with repository.session_factory() as session:
        revisions = list(
            session.scalars(select(ActionModel.after_revision).order_by(ActionModel.after_revision))
        )
        persisted_revision = session.scalar(
            select(GameRunModel.revision).where(GameRunModel.id == created.run_id)
        )
        event_count = session.scalar(select(func.count()).select_from(EventModel))
    assert revisions == [1, 2]
    assert persisted_revision == 2
    assert event_count == 4


def test_signature_rumor_is_transactional_recallable_and_provenanced(
    repository: CockroachRunRepository,
) -> None:
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=19))

    for verb, target in (("promise_help", "marta"), ("confront", "bram")):
        service.take_action(
            created.run_id,
            ActionRequest(
                idempotency_key=uuid4(),
                verb=verb,
                target_id=target,
            ),
        )

    lineage = repository.list_memory_lineage(
        created.run_id,
        "bram-price-confrontation",
    )
    assert len(lineage.versions) == 6
    assert len(lineage.transmissions) == 5
    ambient_versions = [
        version for version in lineage.versions if version.holder_id not in {"bram", "pip"}
    ]
    ambient_transmissions = [item for item in lineage.transmissions if item.speaker_id == "pip"]
    assert len(ambient_versions) == 4
    assert {version.normalized_position["echo_hop"] for version in ambient_versions} == {2}
    assert len(ambient_transmissions) == 4
    assert {item.model_id for item in ambient_transmissions} == {"hearsay-ambient-echo-v1"}
    transmission = next(item for item in lineage.transmissions if item.speaker_id == "bram")
    assert transmission.speaker_id == "bram"
    assert transmission.listener_id == "pip"
    assert transmission.original_text != transmission.retold_text
    assert transmission.provider_id == "deterministic"
    assert transmission.model_id == "hearsay-rules-v1"
    assert transmission.fallback_used is False
    assert transmission.fallback_reason is None
    assert transmission.inference_attempts == 1
    assert transmission.inference_latency_ms is not None

    embedding = (
        DeterministicEmbeddingProvider().embed("What happened to Bram in market row?").vector
    )
    recall = repository.recall_memories(
        created.run_id,
        "pip",
        "What happened to Bram in market row?",
        embedding,
        4,
    )
    assert recall.memories
    assert recall.memories[0].proposition_key == "bram-price-confrontation"

    service.take_action(
        created.run_id,
        ActionRequest(
            idempotency_key=uuid4(),
            verb="confront",
            target_id="bram",
        ),
    )
    revised_lineage = repository.list_memory_lineage(
        created.run_id,
        "bram-price-confrontation",
    )
    for holder_id in ("bram", "pip"):
        holder_versions = [
            version for version in revised_lineage.versions if version.holder_id == holder_id
        ]
        assert [version.version for version in holder_versions] == [1, 2]
        assert [version.active for version in holder_versions] == [False, True]

    with repository.session_factory() as session:
        belief_count = session.scalar(select(func.count()).select_from(BeliefModel))
        version_count = session.scalar(select(func.count()).select_from(BeliefVersionModel))
        transmission_count = session.scalar(select(func.count()).select_from(TransmissionModel))
        relationship_count = session.scalar(select(func.count()).select_from(RelationshipModel))
        trace_count = session.scalar(select(func.count()).select_from(RetrievalTraceModel))
        ambient_gossip_count = session.scalar(
            select(func.count()).select_from(EventModel).where(EventModel.kind == "ambient_gossip")
        )
        pip_dimensions = session.scalar(
            select(func.vector_dims(ActiveMemoryModel.embedding))
            .where(ActiveMemoryModel.holder_id == "pip")
            .limit(1)
        )
        active_memory_count = session.scalar(select(func.count()).select_from(ActiveMemoryModel))
        vector_indexes = list(session.execute(text("SHOW INDEXES FROM active_memories")).mappings())
        explain_rows = session.execute(
            text(
                "EXPLAIN SELECT belief_id, belief_version "
                "FROM active_memories@{FORCE_INDEX=active_memories_retrieval_vector_idx} "
                "WHERE game_run_id = :run_id "
                "AND holder_id = :holder_id "
                "AND status = 'active' "
                "ORDER BY embedding <=> CAST(:embedding AS VECTOR(384)) "
                "LIMIT 8"
            ),
            {
                "run_id": created.run_id,
                "holder_id": "pip",
                "embedding": str(list(embedding)),
            },
        ).all()

    assert belief_count == 7
    assert version_count == 9
    assert transmission_count == 6
    assert relationship_count == 3
    assert trace_count == 1
    assert ambient_gossip_count == 1
    assert active_memory_count == 7
    assert pip_dimensions == 384
    assert any(
        index["index_name"] == "active_memories_retrieval_vector_idx" for index in vector_indexes
    )
    assert "active_memories_retrieval_vector_idx" in "\n".join(str(row[0]) for row in explain_rows)


def test_autonomous_later_hops_persist_and_enter_the_vote_audit(
    repository: CockroachRunRepository,
) -> None:
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=19))
    for verb, target in (
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
        result = service.take_action(
            created.run_id,
            ActionRequest(
                idempotency_key=uuid4(),
                verb=verb,
                target_id=target,
            ),
        )

    election = result.snapshot.election
    assert election is not None
    assert election.player_votes == 12
    assert election.ending.key == "narrow_win"

    lineage = repository.list_memory_lineage(
        created.run_id,
        "bram-price-confrontation",
    )
    autonomous_edges = [
        edge for edge in lineage.transmissions if edge.model_id == "hearsay-autonomous-echo-v1"
    ]
    assert {
        ("fen", "orin"),
        ("fen", "rhea"),
    } <= {(edge.speaker_id, edge.listener_id) for edge in autonomous_edges}
    assert all(edge.original_text != edge.retold_text for edge in autonomous_edges)
    autonomous_versions = [
        version
        for version in lineage.versions
        if version.normalized_position.get("autonomous_retelling") is True
    ]
    assert autonomous_versions
    assert {int(version.normalized_position["echo_hop"]) for version in autonomous_versions} == {3}

    with repository.session_factory() as session:
        autonomous_rows = list(
            session.scalars(
                select(TransmissionModel).where(
                    TransmissionModel.game_run_id == created.run_id,
                    TransmissionModel.model_id == "hearsay-autonomous-echo-v1",
                )
            )
        )
        rumor_event_count = session.scalar(
            select(func.count())
            .select_from(EventModel)
            .where(
                EventModel.game_run_id == created.run_id,
                EventModel.kind == "rumor_continues",
            )
        )
        orin_vote_input = session.scalar(
            select(VoteInputModel)
            .join(VoteModel, VoteModel.id == VoteInputModel.vote_id)
            .where(
                VoteInputModel.game_run_id == created.run_id,
                VoteModel.voter_id == "orin",
                VoteInputModel.input_key == "bram-price-confrontation",
            )
        )

    assert len(autonomous_rows) == 5
    assert all(row.tick_id is not None for row in autonomous_rows)
    assert rumor_event_count == 3
    assert orin_vote_input is not None
    assert orin_vote_input.contribution == pytest.approx(-0.0125)
    assert orin_vote_input.belief_id is not None
    assert orin_vote_input.belief_version == 1
    assert "Rumor hop 3" in orin_vote_input.explanation

    replacement = CockroachRunRepository(TEST_DATABASE_URL or "")
    try:
        restored = replacement.get(created.run_id)
    finally:
        replacement.dispose()
    assert restored.election == election
    assert any(
        echo.hop == 3 and echo.speaker_id != "pip"
        for npc in restored.npcs
        for echo in npc.recent_echoes
    )


def test_concurrent_conflicting_claims_preserve_both_inputs_and_one_active_state(
    repository: CockroachRunRepository,
) -> None:
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=23))
    embeddings = DeterministicEmbeddingProvider()
    repository.record_evidence(
        created.run_id,
        proposition_key="relic-culprit",
        subject_kind="mystery",
        subject_id="relic-theft",
        predicate="relic_stolen_by",
        evidence_key="signed-harbor-ledger",
        title="Signed harbor ledger",
        description="A signed ledger places Bram's payment beside the crate.",
        effect="supports",
        weight=0.8,
        discovered_by_player=True,
    )

    def claim(source_id: str, suspect: str) -> IncomingClaim:
        narrative = f"{source_id.title()} says {suspect.title()} arranged the relic theft."
        return IncomingClaim(
            proposition_key="relic-culprit",
            subject_kind="mystery",
            subject_id="relic-theft",
            predicate="relic_stolen_by",
            holder_id="elias",
            narrative_text=narrative,
            normalized_position={"suspect": suspect},
            source_kind="npc",
            source_id=source_id,
            source_trust=0.8,
            evidence_weight=0.3,
            corroboration=0.3,
            recency=1.0,
            bias_alignment=0.0,
            salience=1.0,
            embedding=embeddings.embed(narrative).vector,
            embedding_model_id=embeddings.model_id,
        )

    for source_id in ("orin", "pip", "rhea", "nessa"):
        repository.apply_claim(
            created.run_id,
            claim(source_id, "talia"),
        )

    observed_version = repository.get_observed_belief_version(
        created.run_id,
        "relic-culprit",
        "elias",
    )
    assert observed_version == 4
    start_together = Barrier(2)
    competing = (
        claim("marta", "bram"),
        claim("bram", "nessa"),
    )

    def submit(item: IncomingClaim) -> ClaimResolution:
        return repository.apply_claim(
            created.run_id,
            item,
            observed_version=observed_version,
            first_read_hook=start_together.wait,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        resolutions = list(executor.map(submit, competing))

    assert {result.outcome for result in resolutions} == {"contested"}
    assert {result.belief_version for result in resolutions} == {5, 6}
    assert any(result.transaction_attempts > 1 for result in resolutions)
    assert any(result.recalculated_after_conflict for result in resolutions)

    lineage = repository.list_memory_lineage(
        created.run_id,
        "relic-culprit",
    )
    elias_versions = [version for version in lineage.versions if version.holder_id == "elias"]
    assert [version.version for version in elias_versions] == [1, 2, 3, 4, 5, 6]
    assert [version.active for version in elias_versions].count(True) == 1
    assert elias_versions[-1].active is True
    assert elias_versions[-1].contested is True

    concurrent_inputs = [item for item in lineage.inputs if item.source_id in {"marta", "bram"}]
    assert {item.source_id for item in concurrent_inputs} == {"marta", "bram"}
    assert {item.observed_version for item in concurrent_inputs} == {4}
    assert {item.evaluated_against_version for item in concurrent_inputs} == {
        4,
        5,
    }
    assert {item.resulting_version for item in concurrent_inputs} == {5, 6}

    dialogue = service.take_action(
        created.run_id,
        ActionRequest(
            idempotency_key=uuid4(),
            verb="talk",
            target_id="elias",
            content="Who arranged the relic theft?",
        ),
    )
    assert dialogue.snapshot.dialogue is not None
    assert "[contested]" in dialogue.snapshot.dialogue.text
    assert dialogue.snapshot.dialogue.recalled_memories[0].contested is True
    assert dialogue.snapshot.dialogue.provider_id == "deterministic"
    elias = next(npc for npc in dialogue.snapshot.npcs if npc.id == "elias")
    assert elias.relationship == -5
    assert dialogue.snapshot.dialogue.treatment_cue is not None
    assert dialogue.snapshot.dialogue.treatment_cue.startswith("Guarded:")
    restored_dialogue = repository.get(created.run_id).dialogue
    assert restored_dialogue is not None
    assert restored_dialogue.recalled_memories[0].belief_id == (
        dialogue.snapshot.dialogue.recalled_memories[0].belief_id
    )
    repeated_dialogue = service.take_action(
        created.run_id,
        ActionRequest(
            idempotency_key=uuid4(),
            verb="talk",
            target_id="elias",
            content="What would prove which account is true?",
        ),
    )
    repeated_elias = next(npc for npc in repeated_dialogue.snapshot.npcs if npc.id == "elias")
    assert repeated_elias.relationship == -5

    with repository.session_factory() as session:
        belief = session.execute(select(BeliefModel.current_version, BeliefModel.contested)).one()
        active_version = session.scalar(
            select(ActiveMemoryModel.belief_version).where(ActiveMemoryModel.holder_id == "elias")
        )
        input_count = session.scalar(select(func.count()).select_from(BeliefInputModel))
        evidence_count = session.scalar(select(func.count()).select_from(EvidenceModel))
        evidence_link_count = session.scalar(select(func.count()).select_from(EvidenceLinkModel))
        elias_player_trust = session.scalar(
            select(RelationshipModel.trust).where(
                RelationshipModel.a_id == "elias",
                RelationshipModel.b_id == "player",
            )
        )

    assert belief.current_version == 6
    assert belief.contested is True
    assert active_version == 6
    assert input_count == 6
    assert evidence_count == 1
    assert evidence_link_count == 1
    assert elias_player_trust == 0.45


def test_historian_fallback_audit_is_durable_and_cannot_claim_mcp_proof(
    repository: CockroachRunRepository,
) -> None:
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=31))
    service.take_action(
        created.run_id,
        ActionRequest(
            idempotency_key=uuid4(),
            verb="confront",
            target_id="bram",
        ),
    )
    historian = HistorianService(
        repository=repository,
        provider_mode="auto",
        database_name="hearsay_test",
    )

    response = asyncio.run(
        historian.trace_rumor(
            created.run_id,
            HistorianTraceRequest(
                proposition_key="bram-price-confrontation",
            ),
        )
    )

    with repository.session_factory() as session:
        persisted = session.get(HistorianAuditModel, response.audit.id)
        assert persisted is not None
        assert persisted.game_run_id == created.run_id
        assert persisted.managed_mcp is False
        assert persisted.sponsor_proof is False
        assert persisted.fallback_reason == "managed_mcp_not_configured"


def test_broken_promise_persists_both_visible_events_and_memory_consequence(
    repository: CockroachRunRepository,
) -> None:
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=37))
    actions = (
        ("promise_help", "marta"),
        ("talk", "bram"),
        ("talk", "pip"),
        ("talk", "rhea"),
    )
    for verb, target in actions:
        result = service.take_action(
            created.run_id,
            ActionRequest(
                idempotency_key=uuid4(),
                verb=verb,
                target_id=target,
            ),
        )

    assert result.snapshot.promises[0].status == "broken"
    assert result.snapshot.player.traits == ["Dishonest", "Troublemaker"]
    assert result.snapshot.recent_events[0].kind == "promise_broken"
    assert result.snapshot.recent_events[1].kind == "ambient_gossip"
    assert result.snapshot.recent_events[2].kind == "conversation"

    lineage = repository.list_memory_lineage(
        created.run_id,
        "player-promise-marta-shipment",
    )
    assert len(lineage.versions) == 5
    assert len(lineage.transmissions) == 3
    assert (
        next(
            version
            for version in lineage.versions
            if version.holder_id == "marta" and version.active
        ).normalized_position["promise_status"]
        == "broken"
    )

    with repository.session_factory() as session:
        event_kinds = list(
            session.scalars(
                select(EventModel.kind)
                .where(EventModel.game_run_id == created.run_id)
                .order_by(EventModel.created_at)
            )
        )
        marta_trust = session.scalar(
            select(RelationshipModel.trust).where(
                RelationshipModel.game_run_id == created.run_id,
                RelationshipModel.a_id == "marta",
                RelationshipModel.b_id == "player",
            )
        )

    assert event_kinds.count("conversation") == 3
    assert event_kinds.count("promise_broken") == 1
    assert event_kinds.count("schedule_shift") == 2
    assert event_kinds.count("storm_begins") == 1
    assert event_kinds.count("ambient_gossip") == 1
    assert len(event_kinds) == 10
    assert marta_trust is not None
    assert marta_trust <= 0.25


def test_schedule_shift_persists_event_and_resident_locations(
    repository: CockroachRunRepository,
) -> None:
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=71))

    for target in ("marta", "pip"):
        result = service.take_action(
            created.run_id,
            ActionRequest(
                idempotency_key=uuid4(),
                verb="talk",
                target_id=target,
            ),
        )

    assert result.snapshot.phase == "afternoon"
    assert result.snapshot.recent_events[1].kind == "schedule_shift"
    assert next(npc.location_id for npc in result.snapshot.npcs if npc.id == "pip") == "market"

    replacement = CockroachRunRepository(TEST_DATABASE_URL or "")
    try:
        restored = replacement.get(created.run_id)
    finally:
        replacement.dispose()

    assert {npc.id: npc.location_id for npc in restored.npcs} == {
        npc.id: npc.location_id for npc in result.snapshot.npcs
    }

    with repository.session_factory() as session:
        schedule_events = list(
            session.scalars(
                select(EventModel).where(
                    EventModel.game_run_id == created.run_id,
                    EventModel.kind == "schedule_shift",
                )
            )
        )

    assert len(schedule_events) == 1
    assert schedule_events[0].day == 1
    assert schedule_events[0].phase == "afternoon"
    assert schedule_events[0].visibility == "public"


def test_storm_state_event_and_evacuated_routes_survive_repository_recreation(
    repository: CockroachRunRepository,
) -> None:
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=93))
    for target in ("marta", "bram", "pip", "rhea"):
        result = service.take_action(
            created.run_id,
            ActionRequest(
                idempotency_key=uuid4(),
                verb="talk",
                target_id=target,
            ),
        )

    assert result.snapshot.weather == "rain"
    assert result.snapshot.town_events[0].status == "active"
    assert {npc.location_id for npc in result.snapshot.npcs} == {"inn"}

    with repository.session_factory() as session:
        storm_events = list(
            session.scalars(
                select(EventModel).where(
                    EventModel.game_run_id == created.run_id,
                    EventModel.kind == "storm_begins",
                )
            )
        )
    assert len(storm_events) == 1
    assert storm_events[0].day == 1
    assert storm_events[0].phase == "evening"
    assert storm_events[0].visibility == "public"

    replacement = CockroachRunRepository(TEST_DATABASE_URL or "")
    try:
        restored = replacement.get(created.run_id)
    finally:
        replacement.dispose()
    assert restored.weather == "rain"
    assert restored.town_events == result.snapshot.town_events
    assert restored.npcs == result.snapshot.npcs


def test_market_day_draw_payload_crowd_and_busy_state_survive_repository_recreation(
    repository: CockroachRunRepository,
) -> None:
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=1729))
    result = service.take_action(
        created.run_id,
        ActionRequest(
            idempotency_key=uuid4(),
            verb="sleep",
        ),
    )

    market_day = next(event for event in result.snapshot.town_events if event.key == "market_day")
    assert market_day.status == "active"
    assert market_day.draw_seed == 2788
    assert market_day.draw_roll == 0
    assert set(market_day.affected_resident_ids) == set(service.content.ambients_by_id)
    assert market_day.busy_resident_ids == ["bram"]
    assert {
        npc.location_id for npc in result.snapshot.npcs if npc.id in service.content.ambients_by_id
    } == {"market"}

    with repository.session_factory() as session:
        market_events = list(
            session.scalars(
                select(EventModel).where(
                    EventModel.game_run_id == created.run_id,
                    EventModel.kind == "market_day_begins",
                )
            )
        )
    assert len(market_events) == 1
    assert market_events[0].day == 2
    assert market_events[0].phase == "morning"
    assert market_events[0].visibility == "public"
    assert market_events[0].payload == {
        "draw_seed": 2788,
        "draw_roll": 0,
        "effects": [
            "three_market_stalls",
            "double_market_crowd",
            "ambient_market_cluster",
            "bram_busy",
            "market_audio",
        ],
        "affected_resident_ids": list(market_day.affected_resident_ids),
        "busy_resident_ids": ["bram"],
    }

    replacement = CockroachRunRepository(TEST_DATABASE_URL or "")
    try:
        restored = replacement.get(created.run_id)
    finally:
        replacement.dispose()
    assert restored.town_events == result.snapshot.town_events
    assert restored.npcs == result.snapshot.npcs


def test_public_argument_persists_faction_damage_choice_and_vote_inputs(
    repository: CockroachRunRepository,
) -> None:
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=103))
    actions = (
        ("sleep", None),
        ("declare_candidacy", "rhea"),
        ("talk", "pip"),
        ("calm_argument", None),
        ("sleep", None),
        ("sleep", None),
    )
    for verb, target in actions:
        result = service.take_action(
            created.run_id,
            ActionRequest(
                idempotency_key=uuid4(),
                verb=verb,
                target_id=target,
            ),
        )

    assert result.snapshot.election is not None
    assert result.snapshot.player.argument_choice == "calm_argument"
    assert "Influential" in result.snapshot.player.traits

    with repository.session_factory() as session:
        faction_trust = {
            (a_id, b_id): trust
            for a_id, b_id, trust in session.execute(
                select(
                    RelationshipModel.a_id,
                    RelationshipModel.b_id,
                    RelationshipModel.trust,
                ).where(
                    RelationshipModel.game_run_id == created.run_id,
                    RelationshipModel.a_id.in_(("bram", "nessa")),
                    RelationshipModel.b_id.in_(("bram", "nessa")),
                )
            ).tuples()
        }
        argument_inputs = list(
            session.scalars(
                select(VoteInputModel).where(
                    VoteInputModel.game_run_id == created.run_id,
                    VoteInputModel.input_key == "public-argument-player-intervention",
                )
            )
        )
        event_kinds = set(
            session.scalars(
                select(EventModel.kind).where(
                    EventModel.game_run_id == created.run_id,
                    EventModel.kind.in_(
                        (
                            "public_argument_begins",
                            "argument_calmed",
                            "public_argument_clears",
                        )
                    ),
                )
            )
        )

    assert faction_trust == {
        ("bram", "nessa"): pytest.approx(0.15),
        ("nessa", "bram"): pytest.approx(0.15),
    }
    assert len(argument_inputs) == 3
    assert {item.input_value for item in argument_inputs} == {"calm_argument"}
    assert all(item.belief_id is not None for item in argument_inputs)
    assert event_kinds == {
        "public_argument_begins",
        "argument_calmed",
        "public_argument_clears",
    }

    replacement = CockroachRunRepository(TEST_DATABASE_URL or "")
    try:
        restored = replacement.get(created.run_id)
    finally:
        replacement.dispose()
    assert restored.election == result.snapshot.election


def test_nessa_favor_persists_correction_endorsement_and_faction_votes(
    repository: CockroachRunRepository,
) -> None:
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=113))
    actions = (
        ("sleep", None),
        ("accept_nessa_favor", "nessa"),
        ("deliver_harbor_log", "elias"),
        ("correct_storm_rumor", "pip"),
        ("ask_nessa_endorsement", "nessa"),
        ("declare_candidacy", "rhea"),
        ("sleep", None),
        ("sleep", None),
    )
    for verb, target in actions:
        result = service.take_action(
            created.run_id,
            ActionRequest(
                idempotency_key=uuid4(),
                verb=verb,
                target_id=target,
            ),
        )

    assert result.snapshot.election is not None
    assert result.snapshot.player.endorsements == ["nessa"]
    assert result.snapshot.favors[0].corrected_publicly is True
    lineage = repository.list_memory_lineage(
        created.run_id,
        "nessa-storm-harbor-log",
    )
    assert {version.holder_id for version in lineage.versions} == {
        "nessa",
        "elias",
        "pip",
        "jonas",
        "mae",
    }
    assert {(edge.speaker_id, edge.listener_id) for edge in lineage.transmissions} == {
        ("elias", "pip"),
        ("nessa", "jonas"),
        ("nessa", "mae"),
    }

    with repository.session_factory() as session:
        favor_inputs = list(
            session.scalars(
                select(VoteInputModel).where(
                    VoteInputModel.game_run_id == created.run_id,
                    VoteInputModel.input_key == "nessa-storm-harbor-log",
                )
            )
        )
        nessa_trust = session.scalar(
            select(RelationshipModel.trust).where(
                RelationshipModel.game_run_id == created.run_id,
                RelationshipModel.a_id == "nessa",
                RelationshipModel.b_id == "player",
            )
        )

    assert len(favor_inputs) == 5
    assert all(item.belief_id is not None for item in favor_inputs)
    assert nessa_trust is not None
    assert nessa_trust >= 0.8

    replacement = CockroachRunRepository(TEST_DATABASE_URL or "")
    try:
        restored = replacement.get(created.run_id)
    finally:
        replacement.dispose()
    assert restored.favors == result.snapshot.favors
    assert restored.player.endorsements == ["nessa"]
    assert restored.election == result.snapshot.election


def test_orin_concealment_persists_blessing_lineage_and_elder_votes(
    repository: CockroachRunRepository,
) -> None:
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=134))
    for verb, target in (
        ("accept_orin_confession", "orin"),
        ("conceal_orin_confession", "orin"),
        ("sleep", None),
        ("declare_candidacy", "rhea"),
        ("sleep", None),
        ("sleep", None),
    ):
        result = service.take_action(
            created.run_id,
            ActionRequest(
                idempotency_key=uuid4(),
                verb=verb,
                target_id=target,
            ),
        )

    election = result.snapshot.election
    assert election is not None
    assert election.player_votes == 13
    assert election.ending.key == "narrow_win"
    assert result.snapshot.favors[0].resolution == "concealed"
    assert result.snapshot.player.endorsements == ["orin"]

    lineage = repository.list_memory_lineage(
        created.run_id,
        "orin-rhea-election-confession",
    )
    assert {version.holder_id for version in lineage.versions} == {
        "orin",
        "player",
        "edda",
        "will",
    }
    assert {(edge.speaker_id, edge.listener_id) for edge in lineage.transmissions} == {
        ("orin", "player"),
        ("player", "orin"),
        ("orin", "edda"),
        ("orin", "will"),
    }

    with repository.session_factory() as session:
        confession_inputs = list(
            session.scalars(
                select(VoteInputModel).where(
                    VoteInputModel.game_run_id == created.run_id,
                    VoteInputModel.input_key == "orin-rhea-election-confession",
                )
            )
        )
        trust_by_resident = {
            resident_id: session.scalar(
                select(RelationshipModel.trust).where(
                    RelationshipModel.game_run_id == created.run_id,
                    RelationshipModel.a_id == resident_id,
                    RelationshipModel.b_id == "player",
                )
            )
            for resident_id in ("orin", "edda", "will")
        }
        event_kinds = set(
            session.scalars(
                select(EventModel.kind).where(
                    EventModel.game_run_id == created.run_id,
                    EventModel.kind.in_(
                        (
                            "orin_confession_entrusted",
                            "orin_confession_concealed",
                        )
                    ),
                )
            )
        )

    assert len(confession_inputs) == 3
    assert {item.input_value for item in confession_inputs} == {"concealed"}
    assert all(item.belief_id is not None for item in confession_inputs)
    assert trust_by_resident == {
        "orin": pytest.approx(0.9),
        "edda": pytest.approx(0.65),
        "will": pytest.approx(0.7),
    }
    assert event_kinds == {
        "orin_confession_entrusted",
        "orin_confession_concealed",
    }

    replacement = CockroachRunRepository(TEST_DATABASE_URL or "")
    try:
        restored = replacement.get(created.run_id)
    finally:
        replacement.dispose()
    assert restored.favors == result.snapshot.favors
    assert restored.player.endorsements == ["orin"]
    assert restored.election == election


def test_talia_quiet_help_persists_family_lineage_and_votes(
    repository: CockroachRunRepository,
) -> None:
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=143))
    for verb, target in (
        ("accept_talia_favor", "talia"),
        ("help_oswin_quietly", "talia"),
        ("sleep", None),
        ("declare_candidacy", "rhea"),
        ("sleep", None),
        ("sleep", None),
    ):
        result = service.take_action(
            created.run_id,
            ActionRequest(
                idempotency_key=uuid4(),
                verb=verb,
                target_id=target,
            ),
        )

    election = result.snapshot.election
    assert election is not None
    assert election.player_votes == 12
    assert election.ending.key == "narrow_win"
    assert result.snapshot.favors[0].resolution == "helped_quietly"
    assert result.snapshot.player.endorsements == ["talia"]

    lineage = repository.list_memory_lineage(
        created.run_id,
        "talia-oswin-sick-house",
    )
    assert {version.holder_id for version in lineage.versions} == {
        "talia",
        "player",
        "oswin",
        "lina",
        "marta",
    }
    assert {(edge.speaker_id, edge.listener_id) for edge in lineage.transmissions} == {
        ("talia", "player"),
        ("player", "talia"),
        ("talia", "oswin"),
        ("talia", "lina"),
        ("talia", "marta"),
    }

    with repository.session_factory() as session:
        sick_house_inputs = list(
            session.scalars(
                select(VoteInputModel).where(
                    VoteInputModel.game_run_id == created.run_id,
                    VoteInputModel.input_key == "talia-oswin-sick-house",
                )
            )
        )
        trust_by_resident = {
            resident_id: session.scalar(
                select(RelationshipModel.trust).where(
                    RelationshipModel.game_run_id == created.run_id,
                    RelationshipModel.a_id == resident_id,
                    RelationshipModel.b_id == "player",
                )
            )
            for resident_id in ("talia", "oswin", "lina", "marta")
        }
        event_kinds = set(
            session.scalars(
                select(EventModel.kind).where(
                    EventModel.game_run_id == created.run_id,
                    EventModel.kind.in_(
                        (
                            "talia_sick_house_entrusted",
                            "talia_sick_house_helped",
                        )
                    ),
                )
            )
        )

    assert len(sick_house_inputs) == 4
    assert {item.input_value for item in sick_house_inputs} == {"helped_quietly"}
    assert all(item.belief_id is not None for item in sick_house_inputs)
    assert trust_by_resident == {
        "talia": pytest.approx(0.9),
        "oswin": pytest.approx(0.75),
        "lina": pytest.approx(0.7),
        "marta": pytest.approx(0.6),
    }
    assert event_kinds == {
        "talia_sick_house_entrusted",
        "talia_sick_house_helped",
    }

    replacement = CockroachRunRepository(TEST_DATABASE_URL or "")
    try:
        restored = replacement.get(created.run_id)
    finally:
        replacement.dispose()
    assert restored.favors == result.snapshot.favors
    assert restored.player.endorsements == ["talia"]
    assert restored.election == election


def test_elias_investigation_persists_multihop_legitimacy_and_votes(
    repository: CockroachRunRepository,
) -> None:
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=153))
    for verb, target in (
        ("accept_elias_favor", "elias"),
        ("investigate_elias_arrest", "elias"),
        ("sleep", None),
        ("declare_candidacy", "rhea"),
        ("sleep", None),
        ("sleep", None),
    ):
        result = service.take_action(
            created.run_id,
            ActionRequest(
                idempotency_key=uuid4(),
                verb=verb,
                target_id=target,
            ),
        )

    election = result.snapshot.election
    assert election is not None
    assert election.player_votes == 16
    assert election.ending.key == "landslide"
    assert result.snapshot.favors[0].resolution == "investigated"
    assert result.snapshot.player.endorsements == ["elias"]

    lineage = repository.list_memory_lineage(
        created.run_id,
        "elias-tob-wrongful-arrest",
    )
    assert {
        "elias",
        "player",
        "tob",
        "marta",
        "edda",
        "pip",
    } <= {version.holder_id for version in lineage.versions}
    transmission_edges = {(edge.speaker_id, edge.listener_id) for edge in lineage.transmissions}
    assert {
        ("elias", "player"),
        ("player", "elias"),
        ("elias", "tob"),
        ("tob", "marta"),
        ("elias", "edda"),
        ("tob", "pip"),
    } <= transmission_edges
    assert any(edge.speaker_id == "pip" for edge in lineage.transmissions)

    with repository.session_factory() as session:
        arrest_inputs = list(
            session.scalars(
                select(VoteInputModel).where(
                    VoteInputModel.game_run_id == created.run_id,
                    VoteInputModel.input_key == "elias-tob-wrongful-arrest",
                )
            )
        )
        trust_by_resident = {
            resident_id: session.scalar(
                select(RelationshipModel.trust).where(
                    RelationshipModel.game_run_id == created.run_id,
                    RelationshipModel.a_id == resident_id,
                    RelationshipModel.b_id == "player",
                )
            )
            for resident_id in ("elias", "tob", "marta", "edda")
        }
        event_kinds = set(
            session.scalars(
                select(EventModel.kind).where(
                    EventModel.game_run_id == created.run_id,
                    EventModel.kind.in_(
                        (
                            "elias_wrongful_arrest_entrusted",
                            "elias_arrest_investigated",
                        )
                    ),
                )
            )
        )

    assert len(arrest_inputs) >= 5
    assert {item.input_value for item in arrest_inputs} == {"investigated"}
    assert all(item.belief_id is not None for item in arrest_inputs)
    assert trust_by_resident == {
        "elias": pytest.approx(0.8),
        "tob": pytest.approx(0.8),
        "marta": pytest.approx(0.65),
        "edda": pytest.approx(0.65),
    }
    assert event_kinds == {
        "elias_wrongful_arrest_entrusted",
        "elias_arrest_investigated",
    }

    replacement = CockroachRunRepository(TEST_DATABASE_URL or "")
    try:
        restored = replacement.get(created.run_id)
    finally:
        replacement.dispose()
    assert restored.favors == result.snapshot.favors
    assert restored.player.endorsements == ["elias"]
    assert restored.election == election


def test_pip_source_verification_persists_mutation_graph_and_votes(
    repository: CockroachRunRepository,
) -> None:
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=163))
    for verb, target in (
        ("accept_pip_favor", "pip"),
        ("verify_pip_source", "pip"),
        ("sleep", None),
        ("declare_candidacy", "rhea"),
        ("sleep", None),
        ("sleep", None),
    ):
        result = service.take_action(
            created.run_id,
            ActionRequest(
                idempotency_key=uuid4(),
                verb=verb,
                target_id=target,
            ),
        )

    election = result.snapshot.election
    assert election is not None
    assert election.player_votes == 15
    assert election.ending.key == "landslide"
    assert result.snapshot.favors[0].resolution == "verified_source"
    assert result.snapshot.player.endorsements == ["pip"]

    lineage = repository.list_memory_lineage(
        created.run_id,
        "pip-rhea-ballot-source",
    )
    assert {"pip", "player", "kit", "edda", "tob"} <= {
        version.holder_id for version in lineage.versions
    }
    transmission_edges = {(edge.speaker_id, edge.listener_id) for edge in lineage.transmissions}
    assert {
        ("pip", "player"),
        ("player", "kit"),
        ("kit", "pip"),
        ("kit", "edda"),
        ("pip", "tob"),
    } <= transmission_edges
    assert (
        len(
            [
                edge
                for edge in lineage.transmissions
                if edge.speaker_id == "pip" and edge.listener_id not in {"player", "tob"}
            ]
        )
        == 4
    )

    with repository.session_factory() as session:
        source_inputs = list(
            session.scalars(
                select(VoteInputModel).where(
                    VoteInputModel.game_run_id == created.run_id,
                    VoteInputModel.input_key == "pip-rhea-ballot-source",
                )
            )
        )
        trust_by_resident = {
            resident_id: session.scalar(
                select(RelationshipModel.trust).where(
                    RelationshipModel.game_run_id == created.run_id,
                    RelationshipModel.a_id == resident_id,
                    RelationshipModel.b_id == "player",
                )
            )
            for resident_id in ("pip", "kit", "edda", "tob")
        }
        event_kinds = set(
            session.scalars(
                select(EventModel.kind).where(
                    EventModel.game_run_id == created.run_id,
                    EventModel.kind.in_(
                        (
                            "pip_source_entrusted",
                            "pip_source_verified",
                            "ambient_gossip",
                            "rumor_continues",
                        )
                    ),
                )
            )
        )

    assert len(source_inputs) == 10
    assert {item.input_value for item in source_inputs} == {"verified_source"}
    assert all(item.belief_id is not None for item in source_inputs)
    autonomous_inputs = [
        item
        for item in source_inputs
        if "Rumor hop 3" in item.explanation or "Rumor hop 4" in item.explanation
    ]
    assert len(autonomous_inputs) == 3
    assert all(abs(item.contribution) < 0.025 for item in autonomous_inputs)
    assert trust_by_resident == {
        "pip": pytest.approx(0.85),
        "kit": pytest.approx(0.7),
        "edda": pytest.approx(0.7),
        "tob": pytest.approx(0.6),
    }
    assert event_kinds == {
        "pip_source_entrusted",
        "pip_source_verified",
        "ambient_gossip",
        "rumor_continues",
    }

    replacement = CockroachRunRepository(TEST_DATABASE_URL or "")
    try:
        restored = replacement.get(created.run_id)
    finally:
        replacement.dispose()
    assert restored.favors == result.snapshot.favors
    assert restored.player.endorsements == ["pip"]
    assert restored.election == election


def test_rhea_ballot_challenge_persists_witness_graph_and_votes(
    repository: CockroachRunRepository,
) -> None:
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=173))
    for verb, target in (
        ("sleep", None),
        ("declare_candidacy", "rhea"),
        ("accept_rhea_compact", "rhea"),
        ("challenge_rhea_ballot", "rhea"),
        ("sleep", None),
        ("sleep", None),
    ):
        result = service.take_action(
            created.run_id,
            ActionRequest(
                idempotency_key=uuid4(),
                verb=verb,
                target_id=target,
            ),
        )

    election = result.snapshot.election
    assert election is not None
    assert election.player_votes == 12
    assert election.ending.key == "narrow_win"
    assert result.snapshot.favors[0].resolution == "challenged"
    assert result.snapshot.player.traits == ["Reliable", "Troublemaker"]

    lineage = repository.list_memory_lineage(
        created.run_id,
        "rhea-ballot-custody",
    )
    assert {
        "rhea",
        "player",
        "elias",
        "edda",
        "tob",
        "pip",
        "marta",
        "orin",
        "nessa",
        "lina",
        "kit",
    } <= {version.holder_id for version in lineage.versions}
    transmission_edges = {(edge.speaker_id, edge.listener_id) for edge in lineage.transmissions}
    assert {
        ("rhea", "player"),
        ("player", "rhea"),
        ("player", "elias"),
        ("elias", "edda"),
        ("edda", "tob"),
        ("tob", "pip"),
        ("tob", "marta"),
        ("edda", "orin"),
        ("elias", "nessa"),
        ("pip", "lina"),
        ("pip", "kit"),
    } <= transmission_edges

    with repository.session_factory() as session:
        compact_inputs = list(
            session.scalars(
                select(VoteInputModel).where(
                    VoteInputModel.game_run_id == created.run_id,
                    VoteInputModel.input_key == "rhea-ballot-custody",
                )
            )
        )
        trust_by_resident = {
            resident_id: session.scalar(
                select(RelationshipModel.trust).where(
                    RelationshipModel.game_run_id == created.run_id,
                    RelationshipModel.a_id == resident_id,
                    RelationshipModel.b_id == "player",
                )
            )
            for resident_id in (
                "rhea",
                "elias",
                "edda",
                "tob",
                "pip",
                "marta",
                "orin",
                "nessa",
                "lina",
                "kit",
            )
        }
        event_kinds = set(
            session.scalars(
                select(EventModel.kind).where(
                    EventModel.game_run_id == created.run_id,
                    EventModel.kind.in_(
                        (
                            "rhea_compact_offered",
                            "rhea_ballot_challenged",
                            "public_argument_begins",
                            "rumor_continues",
                        )
                    ),
                )
            )
        )

    assert len(compact_inputs) == 11
    assert {item.input_value for item in compact_inputs} == {"challenged"}
    assert all(item.belief_id is not None for item in compact_inputs)
    autonomous_inputs = [item for item in compact_inputs if "Rumor hop" in item.explanation]
    assert len(autonomous_inputs) == 1
    assert autonomous_inputs[0].contribution == pytest.approx(0.015)
    assert trust_by_resident == {
        "rhea": pytest.approx(0.15),
        "elias": pytest.approx(0.75),
        "edda": pytest.approx(0.75),
        "tob": pytest.approx(0.7),
        "pip": pytest.approx(0.65),
        "marta": pytest.approx(0.6),
        "orin": pytest.approx(0.6),
        "nessa": pytest.approx(0.6),
        "lina": pytest.approx(0.6),
        "kit": pytest.approx(0.6),
    }
    assert event_kinds == {
        "rhea_compact_offered",
        "rhea_ballot_challenged",
        "public_argument_begins",
        "rumor_continues",
    }

    replacement = CockroachRunRepository(TEST_DATABASE_URL or "")
    try:
        restored = replacement.get(created.run_id)
    finally:
        replacement.dispose()
    assert restored.favors == result.snapshot.favors
    assert restored.player.traits == ["Reliable", "Troublemaker"]
    assert restored.election == election


def test_square_speech_persists_audited_ten_ten_loss(
    repository: CockroachRunRepository,
) -> None:
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=123))
    for verb, target in (
        ("sleep", None),
        ("declare_candidacy", "rhea"),
        ("give_square_speech", "square"),
        ("sleep", None),
        ("sleep", None),
    ):
        result = service.take_action(
            created.run_id,
            ActionRequest(
                idempotency_key=uuid4(),
                verb=verb,
                target_id=target,
            ),
        )

    election = result.snapshot.election
    assert election is not None
    assert election.player_votes == election.rhea_votes == 10
    assert election.ending.key == "narrow_loss"

    with repository.session_factory() as session:
        speech_inputs = list(
            session.scalars(
                select(VoteInputModel).where(
                    VoteInputModel.game_run_id == created.run_id,
                    VoteInputModel.input_key == "player-square-speech",
                )
            )
        )
        speech_events = list(
            session.scalars(
                select(EventModel).where(
                    EventModel.game_run_id == created.run_id,
                    EventModel.kind == "square_speech",
                )
            )
        )
    assert speech_inputs
    assert all(item.belief_id is not None for item in speech_inputs)
    assert len(speech_events) == 1
    assert repository.get(created.run_id).election == election


def test_election_persists_twenty_votes_and_exact_decision_inputs(
    repository: CockroachRunRepository,
) -> None:
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=61))
    actions = (
        ("promise_help", "marta"),
        ("settle_shipment", "bram"),
        ("sleep", None),
        ("declare_candidacy", "rhea"),
        ("sleep", None),
        ("sleep", None),
    )
    for verb, target in actions:
        result = service.take_action(
            created.run_id,
            ActionRequest(
                idempotency_key=uuid4(),
                verb=verb,
                target_id=target,
            ),
        )

    election = result.snapshot.election
    assert election is not None
    assert election.player_votes == 11
    assert election.rhea_votes == 9
    assert election.winner == "player"
    assert election.ending.key == "narrow_win"

    with repository.session_factory() as session:
        persisted_election = session.get(ElectionModel, election.id)
        vote_count = session.scalar(
            select(func.count())
            .select_from(VoteModel)
            .where(VoteModel.game_run_id == created.run_id)
        )
        input_count = session.scalar(
            select(func.count())
            .select_from(VoteInputModel)
            .where(VoteInputModel.game_run_id == created.run_id)
        )
        pip_memory_input = session.execute(
            select(
                VoteInputModel.belief_id,
                VoteInputModel.belief_version,
                VoteInputModel.explanation,
            )
            .join(VoteModel, VoteModel.id == VoteInputModel.vote_id)
            .where(
                VoteModel.voter_id == "pip",
                VoteInputModel.input_kind == "belief",
                VoteInputModel.input_key == "player-promise-marta-shipment",
            )
        ).one()

    assert persisted_election is not None
    assert persisted_election.ending_key == "narrow_win"
    assert vote_count == 20
    assert input_count is not None
    assert input_count >= 40
    assert pip_memory_input.belief_id is not None
    assert pip_memory_input.belief_version == 1
    assert "promise was kept" in pip_memory_input.explanation

    restored = repository.get(created.run_id)
    assert restored.election == election


def test_threat_path_persists_run_out_ending_and_rumor_decision_input(
    repository: CockroachRunRepository,
) -> None:
    service = GameService(repository=repository)
    created = service.create_run(CreateRunRequest(display_name="Ada", seed=83))
    actions = (
        ("threaten_bram", "bram"),
        ("sleep", None),
        ("declare_candidacy", "rhea"),
        ("sleep", None),
        ("sleep", None),
    )
    for verb, target in actions:
        result = service.take_action(
            created.run_id,
            ActionRequest(
                idempotency_key=uuid4(),
                verb=verb,
                target_id=target,
            ),
        )

    assert result.snapshot.election is not None
    assert result.snapshot.election.ending.key == "run_out_of_town"
    assert result.snapshot.player.traits == ["Dangerous", "Troublemaker"]

    with repository.session_factory() as session:
        stored_inputs = list(
            session.scalars(
                select(VoteInputModel).where(
                    VoteInputModel.game_run_id == created.run_id,
                    VoteInputModel.input_key == "bram-price-confrontation",
                )
            )
        )
        rumor_events = list(
            session.scalars(
                select(EventModel).where(
                    EventModel.game_run_id == created.run_id,
                    EventModel.kind == "bram_threatened",
                )
            )
        )

    assert len(stored_inputs) == 2
    assert {item.input_value for item in stored_inputs} == {"threaten_bram"}
    assert all(item.belief_id is not None for item in stored_inputs)
    assert len(rumor_events) == 1

    replacement = CockroachRunRepository(TEST_DATABASE_URL or "")
    try:
        restored = replacement.get(created.run_id)
    finally:
        replacement.dispose()
    assert restored.election == result.snapshot.election
