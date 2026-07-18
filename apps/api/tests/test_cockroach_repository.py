from __future__ import annotations

import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url

from hearsay_api.memory import DeterministicEmbeddingProvider
from hearsay_api.persistence.cockroach_repository import CockroachRunRepository
from hearsay_api.persistence.database import normalize_cockroach_url
from hearsay_api.persistence.models import (
    ActionModel,
    ActiveMemoryModel,
    BeliefModel,
    BeliefVersionModel,
    EventModel,
    GameRunModel,
    RelationshipModel,
    RetrievalTraceModel,
    TransmissionModel,
)
from hearsay_api.schemas import ActionRequest, CreateRunRequest
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
    assert event_count == 3


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
    assert len(lineage.versions) == 2
    assert len(lineage.transmissions) == 1
    transmission = lineage.transmissions[0]
    assert transmission.speaker_id == "bram"
    assert transmission.listener_id == "pip"
    assert transmission.original_text != transmission.retold_text
    assert transmission.provider_id == "deterministic"
    assert transmission.model_id == "hearsay-rules-v1"
    assert transmission.fallback_used is False
    assert transmission.fallback_reason is None
    assert transmission.inference_attempts == 1
    assert transmission.inference_latency_ms is not None

    embedding = DeterministicEmbeddingProvider().embed("What happened to Bram in market row?")
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

    assert belief_count == 3
    assert version_count == 5
    assert transmission_count == 2
    assert relationship_count == 3
    assert trace_count == 1
    assert active_memory_count == 3
    assert pip_dimensions == 384
    assert any(
        index["index_name"] == "active_memories_retrieval_vector_idx" for index in vector_indexes
    )
    assert "active_memories_retrieval_vector_idx" in "\n".join(str(row[0]) for row in explain_rows)
