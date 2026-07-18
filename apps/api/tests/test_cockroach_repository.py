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
    assert result.snapshot.recent_events[1].kind == "conversation"

    lineage = repository.list_memory_lineage(
        created.run_id,
        "player-promise-marta-shipment",
    )
    assert len(lineage.versions) == 3
    assert len(lineage.transmissions) == 1
    assert next(
        version
        for version in lineage.versions
        if version.holder_id == "marta" and version.active
    ).normalized_position["promise_status"] == "broken"

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
    assert len(event_kinds) == 8
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
    assert next(
        npc.location_id
        for npc in result.snapshot.npcs
        if npc.id == "pip"
    ) == "market"

    replacement = CockroachRunRepository(TEST_DATABASE_URL or "")
    try:
        restored = replacement.get(created.run_id)
    finally:
        replacement.dispose()

    assert {
        npc.id: npc.location_id
        for npc in restored.npcs
    } == {
        npc.id: npc.location_id
        for npc in result.snapshot.npcs
    }

    with repository.session_factory() as session:
        schedule_events = list(
            session.scalars(
                select(EventModel)
                .where(
                    EventModel.game_run_id == created.run_id,
                    EventModel.kind == "schedule_shift",
                )
            )
        )

    assert len(schedule_events) == 1
    assert schedule_events[0].day == 1
    assert schedule_events[0].phase == "afternoon"
    assert schedule_events[0].visibility == "public"


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
