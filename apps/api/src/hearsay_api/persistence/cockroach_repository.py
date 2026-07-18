from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, TypeVar, cast
from uuid import UUID, uuid4

from sqlalchemy import delete, insert, select, text, update
from sqlalchemy.engine import CursorResult, Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy_cockroachdb import run_transaction  # type: ignore[import-untyped]

from hearsay_api.conflicts import (
    ClaimResolution,
    CurrentBelief,
    IncomingClaim,
    resolve_conflict,
)
from hearsay_api.memory import MemoryEffects
from hearsay_api.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from hearsay_api.persistence.models import (
    ActionModel,
    ActiveMemoryModel,
    BeliefInputModel,
    BeliefModel,
    BeliefVersionModel,
    EventModel,
    EvidenceLinkModel,
    EvidenceModel,
    GameRunModel,
    GossipTickModel,
    HistorianAuditModel,
    PlayerModel,
    PropositionModel,
    RelationshipModel,
    RetrievalTraceModel,
    TransmissionModel,
)
from hearsay_api.repository import ConcurrentRunUpdateError, RunNotFoundError
from hearsay_api.schemas import (
    ActionRequest,
    ActionResponse,
    BeliefInputState,
    HistorianAuditState,
    MemoryLineageResponse,
    MemoryRecallResponse,
    MemoryVersionState,
    RecalledMemory,
    RunSnapshot,
    TransmissionState,
)

T = TypeVar("T")


class CockroachRunRepository:
    def __init__(
        self,
        database_url: str,
        pool_size: int = 5,
        max_transaction_retries: int = 4,
        engine: Engine | None = None,
    ) -> None:
        self.engine = engine or create_database_engine(database_url, pool_size)
        self.session_factory: sessionmaker[Session] = create_session_factory(self.engine)
        self.max_transaction_retries = max_transaction_retries

    @property
    def backend_name(self) -> str:
        return "cockroachdb"

    def _run_transaction(self, callback: Callable[[Session], T]) -> T:
        result: T = run_transaction(
            self.session_factory,
            callback,
            max_retries=self.max_transaction_retries,
            max_backoff=1,
        )
        return result

    def create(self, snapshot: RunSnapshot) -> RunSnapshot:
        player_id = uuid4()
        snapshot_json = snapshot.model_dump(mode="json")
        arrival = snapshot.recent_events[0]

        def create_run(session: Session) -> RunSnapshot:
            session.execute(
                insert(PlayerModel).values(
                    id=player_id,
                    display_name=snapshot.player.display_name,
                    credibility=0.5,
                )
            )
            session.execute(
                insert(GameRunModel).values(
                    id=snapshot.run_id,
                    player_id=player_id,
                    seed=snapshot.seed,
                    revision=snapshot.revision,
                    status=snapshot.status,
                    day=snapshot.day,
                    phase=snapshot.phase,
                    action_count=snapshot.action_count,
                    world_tick=snapshot.world_tick,
                    current_location_id=snapshot.player.location_id,
                    weather=snapshot.weather,
                    snapshot=snapshot_json,
                )
            )
            session.execute(
                insert(EventModel).values(
                    id=arrival.id,
                    game_run_id=snapshot.run_id,
                    kind=arrival.kind,
                    text=arrival.text,
                    visibility="public" if arrival.visible else "private",
                    day=snapshot.day,
                    phase=snapshot.phase,
                    world_tick=snapshot.world_tick,
                    payload={},
                )
            )
            return snapshot.model_copy(deep=True)

        return self._run_transaction(create_run)

    def get(self, run_id: UUID) -> RunSnapshot:
        with self.session_factory() as session:
            snapshot = session.scalar(
                select(GameRunModel.snapshot).where(GameRunModel.id == run_id)
            )
        if snapshot is None:
            raise RunNotFoundError(run_id)
        return RunSnapshot.model_validate(snapshot)

    def get_action_result(self, run_id: UUID, key: UUID) -> ActionResponse | None:
        with self.session_factory() as session:
            response = session.scalar(
                select(ActionModel.response).where(
                    ActionModel.game_run_id == run_id,
                    ActionModel.idempotency_key == key,
                )
            )
            if response is not None:
                return ActionResponse.model_validate(response)
            exists = session.scalar(select(GameRunModel.id).where(GameRunModel.id == run_id))
        if exists is None:
            raise RunNotFoundError(run_id)
        return None

    def get_observed_belief_version(
        self,
        run_id: UUID,
        proposition_key: str,
        holder_id: str,
    ) -> int | None:
        with self.session_factory() as session:
            version = session.scalar(
                select(BeliefModel.current_version)
                .join(
                    PropositionModel,
                    PropositionModel.id == BeliefModel.proposition_id,
                )
                .where(
                    BeliefModel.game_run_id == run_id,
                    PropositionModel.proposition_key == proposition_key,
                    BeliefModel.holder_kind == "npc",
                    BeliefModel.holder_id == holder_id,
                )
            )
            if version is not None:
                return version
            exists = session.scalar(select(GameRunModel.id).where(GameRunModel.id == run_id))
        if exists is None:
            raise RunNotFoundError(run_id)
        return None

    def record_evidence(
        self,
        run_id: UUID,
        *,
        proposition_key: str,
        subject_kind: str,
        subject_id: str | None,
        predicate: str,
        evidence_key: str,
        title: str,
        description: str,
        effect: str,
        weight: float,
        payload: dict[str, object] | None = None,
        discovered_by_player: bool = False,
    ) -> UUID:
        if effect not in {"supports", "contradicts"}:
            raise ValueError("Evidence effect must be supports or contradicts.")
        if not 0 <= weight <= 1:
            raise ValueError("Evidence weight must be between zero and one.")

        def write_evidence(session: Session) -> UUID:
            if session.scalar(select(GameRunModel.id).where(GameRunModel.id == run_id)) is None:
                raise RunNotFoundError(run_id)
            proposition_id = session.scalar(
                select(PropositionModel.id).where(
                    PropositionModel.game_run_id == run_id,
                    PropositionModel.proposition_key == proposition_key,
                )
            )
            if proposition_id is None:
                proposition_id = uuid4()
                session.execute(
                    insert(PropositionModel).values(
                        id=proposition_id,
                        game_run_id=run_id,
                        proposition_key=proposition_key,
                        subject_kind=subject_kind,
                        subject_id=subject_id,
                        predicate=predicate,
                    )
                )

            existing = session.scalar(
                select(EvidenceModel.id).where(
                    EvidenceModel.game_run_id == run_id,
                    EvidenceModel.evidence_key == evidence_key,
                )
            )
            if existing is None:
                evidence_id = uuid4()
                session.execute(
                    insert(EvidenceModel).values(
                        id=evidence_id,
                        game_run_id=run_id,
                        evidence_key=evidence_key,
                        title=title,
                        description=description,
                        payload=payload or {},
                        discovered_by_player=discovered_by_player,
                    )
                )
            else:
                evidence_id = existing

            linked = session.scalar(
                select(EvidenceLinkModel.evidence_id).where(
                    EvidenceLinkModel.evidence_id == evidence_id,
                    EvidenceLinkModel.proposition_id == proposition_id,
                )
            )
            if linked is None:
                session.execute(
                    insert(EvidenceLinkModel).values(
                        evidence_id=evidence_id,
                        proposition_id=proposition_id,
                        effect=effect,
                        weight=weight,
                    )
                )
            return evidence_id

        return self._run_transaction(write_evidence)

    def apply_claim(
        self,
        run_id: UUID,
        claim: IncomingClaim,
        *,
        observed_version: int | None = None,
        first_read_hook: Callable[[], None] | None = None,
    ) -> ClaimResolution:
        if len(claim.embedding) != 384:
            raise ValueError("Belief embeddings must contain exactly 384 values.")

        input_id = uuid4()
        callback_attempts = 0

        def write_claim(session: Session) -> ClaimResolution:
            nonlocal callback_attempts
            callback_attempts += 1

            if session.scalar(select(GameRunModel.id).where(GameRunModel.id == run_id)) is None:
                raise RunNotFoundError(run_id)

            proposition_id = session.scalar(
                select(PropositionModel.id).where(
                    PropositionModel.game_run_id == run_id,
                    PropositionModel.proposition_key == claim.proposition_key,
                )
            )
            if proposition_id is None:
                proposition_id = uuid4()
                session.execute(
                    insert(PropositionModel).values(
                        id=proposition_id,
                        game_run_id=run_id,
                        proposition_key=claim.proposition_key,
                        subject_kind=claim.subject_kind,
                        subject_id=claim.subject_id,
                        predicate=claim.predicate,
                    )
                )

            current_row = session.execute(
                select(
                    BeliefModel.id,
                    BeliefModel.current_version,
                    BeliefModel.contested,
                    BeliefVersionModel.narrative_text,
                    BeliefVersionModel.normalized_position,
                    BeliefVersionModel.confidence,
                    BeliefVersionModel.salience,
                    BeliefVersionModel.embedding,
                    BeliefVersionModel.embedding_model_id,
                )
                .join(
                    BeliefVersionModel,
                    (BeliefVersionModel.belief_id == BeliefModel.id)
                    & (BeliefVersionModel.version == BeliefModel.current_version),
                )
                .where(
                    BeliefModel.game_run_id == run_id,
                    BeliefModel.proposition_id == proposition_id,
                    BeliefModel.holder_kind == "npc",
                    BeliefModel.holder_id == claim.holder_id,
                )
            ).one_or_none()

            if callback_attempts == 1 and first_read_hook is not None:
                first_read_hook()

            current = (
                CurrentBelief(
                    belief_id=current_row.id,
                    version=current_row.current_version,
                    narrative_text=current_row.narrative_text,
                    normalized_position=current_row.normalized_position,
                    confidence=current_row.confidence,
                    salience=current_row.salience,
                    contested=current_row.contested,
                )
                if current_row is not None
                else None
            )
            decision = resolve_conflict(current, claim)
            evaluated_version = current.version if current is not None else None
            recalculated = observed_version is not None and evaluated_version != observed_version

            if current is None:
                belief_id = uuid4()
                version = 1
                session.execute(
                    insert(BeliefModel).values(
                        id=belief_id,
                        game_run_id=run_id,
                        proposition_id=proposition_id,
                        holder_kind="npc",
                        holder_id=claim.holder_id,
                        current_version=version,
                        status="active",
                        contested=decision.contested,
                    )
                )
            else:
                belief_id = current.belief_id
                version = current.version

            if decision.create_version:
                if current is not None:
                    version = current.version + 1
                    session.execute(
                        update(BeliefModel)
                        .where(BeliefModel.id == belief_id)
                        .values(
                            current_version=version,
                            status="active",
                            contested=decision.contested,
                            updated_at=text("now()"),
                        )
                    )

                preserve_current = decision.outcome == "contested" and current_row is not None
                if preserve_current:
                    assert current_row is not None
                    embedding = list(current_row.embedding or claim.embedding)
                    embedding_model_id = current_row.embedding_model_id
                    salience = current_row.salience
                    source_kind = "conflict_resolution"
                else:
                    embedding = list(claim.embedding)
                    embedding_model_id = claim.embedding_model_id
                    salience = claim.salience
                    source_kind = claim.source_kind
                session.execute(
                    insert(BeliefVersionModel).values(
                        belief_id=belief_id,
                        version=version,
                        game_run_id=run_id,
                        holder_id=claim.holder_id,
                        status="stored",
                        narrative_text=decision.narrative_text,
                        normalized_position=decision.normalized_position,
                        confidence=decision.confidence,
                        salience=salience,
                        embedding=embedding,
                        embedding_model_id=embedding_model_id,
                        source_kind=source_kind,
                        source_id=claim.source_id,
                    )
                )
                active_values = {
                    "belief_version": version,
                    "status": "active",
                    "narrative_text": decision.narrative_text,
                    "embedding": embedding,
                    "embedding_model_id": embedding_model_id,
                    "confidence": decision.confidence,
                    "salience": salience,
                    "updated_at": datetime.now(UTC),
                }
                active_exists = session.scalar(
                    select(ActiveMemoryModel.belief_id).where(
                        ActiveMemoryModel.belief_id == belief_id
                    )
                )
                if active_exists is None:
                    session.execute(
                        insert(ActiveMemoryModel).values(
                            game_run_id=run_id,
                            holder_id=claim.holder_id,
                            belief_id=belief_id,
                            **active_values,
                        )
                    )
                else:
                    session.execute(
                        update(ActiveMemoryModel)
                        .where(ActiveMemoryModel.belief_id == belief_id)
                        .values(**active_values)
                    )
            elif current is not None and decision.contested != current.contested:
                session.execute(
                    update(BeliefModel)
                    .where(BeliefModel.id == belief_id)
                    .values(
                        contested=decision.contested,
                        updated_at=text("now()"),
                    )
                )

            session.execute(
                insert(BeliefInputModel).values(
                    id=input_id,
                    game_run_id=run_id,
                    proposition_id=proposition_id,
                    holder_kind="npc",
                    holder_id=claim.holder_id,
                    source_kind=claim.source_kind,
                    source_id=claim.source_id,
                    narrative_text=claim.narrative_text,
                    normalized_position=claim.normalized_position,
                    source_trust=claim.source_trust,
                    evidence_weight=claim.evidence_weight,
                    corroboration=claim.corroboration,
                    recency=claim.recency,
                    bias_alignment=claim.bias_alignment,
                    incoming_strength=decision.incoming_strength,
                    classification=decision.classification,
                    outcome=decision.outcome,
                    rationale=decision.rationale,
                    observed_version=observed_version,
                    evaluated_against_version=evaluated_version,
                    resulting_belief_id=belief_id,
                    resulting_version=version,
                    transaction_attempts=callback_attempts,
                    recalculated_after_conflict=recalculated,
                )
            )
            return ClaimResolution(
                input_id=input_id,
                belief_id=belief_id,
                belief_version=version,
                classification=decision.classification,
                outcome=decision.outcome,
                contested=decision.contested,
                observed_version=observed_version,
                evaluated_against_version=evaluated_version,
                transaction_attempts=callback_attempts,
                recalculated_after_conflict=recalculated,
            )

        return self._run_transaction(write_claim)

    def update(
        self,
        run_id: UUID,
        snapshot: RunSnapshot,
        request: ActionRequest,
        idempotency_key: UUID,
        result: ActionResponse,
        memory_effects: MemoryEffects,
    ) -> ActionResponse:
        expected_revision = snapshot.revision - 1
        snapshot_json = snapshot.model_dump(mode="json")
        response_json = result.model_dump(mode="json")

        def update_run(session: Session) -> ActionResponse:
            cached = session.scalar(
                select(ActionModel.response).where(
                    ActionModel.game_run_id == run_id,
                    ActionModel.idempotency_key == idempotency_key,
                )
            )
            if cached is not None:
                return ActionResponse.model_validate(cached)

            current = session.execute(
                select(
                    GameRunModel.revision,
                    GameRunModel.action_count,
                    GameRunModel.snapshot,
                ).where(
                    GameRunModel.id == run_id
                )
            ).one_or_none()
            if current is None:
                raise RunNotFoundError(run_id)
            if current.revision != expected_revision:
                raise ConcurrentRunUpdateError(
                    f"Run {run_id} changed at revision {current.revision}."
                )

            updated = cast(
                CursorResult[Any],
                session.execute(
                    update(GameRunModel)
                    .where(
                        GameRunModel.id == run_id,
                        GameRunModel.revision == expected_revision,
                    )
                    .values(
                        revision=snapshot.revision,
                        status=snapshot.status,
                        day=snapshot.day,
                        phase=snapshot.phase,
                        action_count=snapshot.action_count,
                        world_tick=snapshot.world_tick,
                        current_location_id=snapshot.player.location_id,
                        weather=snapshot.weather,
                        snapshot=snapshot_json,
                        finished_at=(text("now()") if snapshot.status == "completed" else None),
                        updated_at=text("now()"),
                    )
                ),
            )
            if updated.rowcount != 1:
                raise ConcurrentRunUpdateError(f"Run {run_id} changed concurrently.")

            session.execute(
                insert(ActionModel).values(
                    id=result.action_id,
                    game_run_id=run_id,
                    idempotency_key=idempotency_key,
                    verb=request.verb.value,
                    target_id=request.target_id,
                    content=request.content,
                    consumed_time=result.consumed_time,
                    before_revision=expected_revision,
                    after_revision=snapshot.revision,
                    before_action_count=current.action_count,
                    after_action_count=snapshot.action_count,
                    response=response_json,
                )
            )
            previous_event_ids = {
                str(item["id"])
                for item in current.snapshot.get("recent_events", [])
            }
            new_events = [
                event
                for event in reversed(snapshot.recent_events)
                if str(event.id) not in previous_event_ids
            ]
            for event in new_events:
                session.execute(
                    insert(EventModel).values(
                        id=event.id,
                        game_run_id=run_id,
                        kind=event.kind,
                        text=event.text,
                        visibility="public" if event.visible else "private",
                        day=snapshot.day,
                        phase=snapshot.phase,
                        world_tick=snapshot.world_tick,
                        payload={},
                    )
                )
            self._apply_memory_effects(session, run_id, memory_effects)
            return ActionResponse.model_validate(response_json)

        return self._run_transaction(update_run)

    @staticmethod
    def _apply_memory_effects(
        session: Session,
        run_id: UUID,
        effects: MemoryEffects,
    ) -> None:
        if not effects.beliefs and not effects.relationships:
            return

        tick_id: UUID | None = None
        transmission_count = sum(belief.parent_holder_id is not None for belief in effects.beliefs)
        if effects.gossip_tick_number is not None:
            tick_id = session.scalar(
                select(GossipTickModel.id).where(
                    GossipTickModel.game_run_id == run_id,
                    GossipTickModel.tick_number == effects.gossip_tick_number,
                )
            )
            if tick_id is None:
                tick_id = uuid4()
                session.execute(
                    insert(GossipTickModel).values(
                        id=tick_id,
                        game_run_id=run_id,
                        tick_number=effects.gossip_tick_number,
                        finished_at=text("now()"),
                        hops_attempted=transmission_count,
                        hops_committed=transmission_count,
                        serialization_retries=0,
                    )
                )

        written: dict[tuple[str, str], tuple[UUID, int, UUID, str]] = {}
        for planned in effects.beliefs:
            proposition_id = session.scalar(
                select(PropositionModel.id).where(
                    PropositionModel.game_run_id == run_id,
                    PropositionModel.proposition_key == planned.proposition_key,
                )
            )
            if proposition_id is None:
                proposition_id = uuid4()
                session.execute(
                    insert(PropositionModel).values(
                        id=proposition_id,
                        game_run_id=run_id,
                        proposition_key=planned.proposition_key,
                        subject_kind=planned.subject_kind,
                        subject_id=planned.subject_id,
                        predicate=planned.predicate,
                    )
                )

            current = session.execute(
                select(BeliefModel.id, BeliefModel.current_version).where(
                    BeliefModel.game_run_id == run_id,
                    BeliefModel.proposition_id == proposition_id,
                    BeliefModel.holder_kind == "npc",
                    BeliefModel.holder_id == planned.holder_id,
                )
            ).one_or_none()
            if current is None:
                belief_id = uuid4()
                version = 1
                session.execute(
                    insert(BeliefModel).values(
                        id=belief_id,
                        game_run_id=run_id,
                        proposition_id=proposition_id,
                        holder_kind="npc",
                        holder_id=planned.holder_id,
                        current_version=version,
                        status="active",
                        contested=False,
                    )
                )
            else:
                belief_id = current.id
                version = current.current_version + 1
                session.execute(
                    update(BeliefModel)
                    .where(BeliefModel.id == belief_id)
                    .values(
                        current_version=version,
                        status="active",
                        contested=False,
                        updated_at=text("now()"),
                    )
                )

            session.execute(
                insert(BeliefVersionModel).values(
                    belief_id=belief_id,
                    version=version,
                    game_run_id=run_id,
                    holder_id=planned.holder_id,
                    status="stored",
                    narrative_text=planned.narrative_text,
                    normalized_position=planned.normalized_position,
                    confidence=planned.confidence,
                    salience=planned.salience,
                    embedding=list(planned.embedding),
                    embedding_model_id=planned.embedding_model_id,
                    source_kind=planned.source_kind,
                    source_id=planned.source_id,
                )
            )
            active_memory = session.scalar(
                select(ActiveMemoryModel.belief_id).where(ActiveMemoryModel.belief_id == belief_id)
            )
            active_values = {
                "belief_version": version,
                "status": "active",
                "narrative_text": planned.narrative_text,
                "embedding": list(planned.embedding),
                "embedding_model_id": planned.embedding_model_id,
                "confidence": planned.confidence,
                "salience": planned.salience,
                "updated_at": datetime.now(UTC),
            }
            if active_memory is None:
                session.execute(
                    insert(ActiveMemoryModel).values(
                        game_run_id=run_id,
                        holder_id=planned.holder_id,
                        belief_id=belief_id,
                        **active_values,
                    )
                )
            else:
                session.execute(
                    update(ActiveMemoryModel)
                    .where(ActiveMemoryModel.belief_id == belief_id)
                    .values(**active_values)
                )
            written[(planned.proposition_key, planned.holder_id)] = (
                belief_id,
                version,
                proposition_id,
                planned.narrative_text,
            )

            if planned.parent_holder_id is not None:
                parent = written.get((planned.proposition_key, planned.parent_holder_id))
                if parent is None:
                    parent_row = session.execute(
                        select(
                            BeliefModel.id,
                            BeliefModel.current_version,
                            BeliefVersionModel.narrative_text,
                        )
                        .join(
                            BeliefVersionModel,
                            (BeliefVersionModel.belief_id == BeliefModel.id)
                            & (BeliefVersionModel.version == BeliefModel.current_version),
                        )
                        .where(
                            BeliefModel.game_run_id == run_id,
                            BeliefModel.proposition_id == proposition_id,
                            BeliefModel.holder_id == planned.parent_holder_id,
                        )
                    ).one()
                    parent = (
                        parent_row.id,
                        parent_row.current_version,
                        proposition_id,
                        parent_row.narrative_text,
                    )
                session.execute(
                    insert(TransmissionModel).values(
                        id=uuid4(),
                        game_run_id=run_id,
                        proposition_id=proposition_id,
                        from_belief_id=parent[0],
                        from_version=parent[1],
                        to_belief_id=belief_id,
                        to_version=version,
                        speaker_id=planned.parent_holder_id,
                        listener_id=planned.holder_id,
                        original_text=parent[3],
                        retold_text=planned.narrative_text,
                        mutation_note=planned.mutation_note,
                        trust_at_time=planned.trust_at_time,
                        provider_id=planned.retelling_provider_id or "deterministic",
                        model_id=(planned.retelling_model_id or "hearsay-deterministic-rules-v1"),
                        fallback_used=planned.fallback_used,
                        fallback_reason=planned.fallback_reason,
                        inference_attempts=planned.inference_attempts,
                        inference_latency_ms=planned.inference_latency_ms,
                        tick_id=tick_id,
                    )
                )

        for relationship_plan in effects.relationships:
            relationship = session.get(
                RelationshipModel,
                (
                    run_id,
                    relationship_plan.a_kind,
                    relationship_plan.a_id,
                    relationship_plan.b_kind,
                    relationship_plan.b_id,
                ),
            )
            if relationship is None:
                trust = min(
                    max(0.5 + relationship_plan.trust_delta, 0.0),
                    1.0,
                )
                if relationship_plan.trust_floor is not None:
                    trust = max(trust, relationship_plan.trust_floor)
                if relationship_plan.trust_ceiling is not None:
                    trust = min(trust, relationship_plan.trust_ceiling)
                session.execute(
                    insert(RelationshipModel).values(
                        game_run_id=run_id,
                        a_kind=relationship_plan.a_kind,
                        a_id=relationship_plan.a_id,
                        b_kind=relationship_plan.b_kind,
                        b_id=relationship_plan.b_id,
                        trust=trust,
                        affinity=min(
                            max(relationship_plan.affinity_delta, -1.0),
                            1.0,
                        ),
                        fear=min(max(relationship_plan.fear_delta, 0.0), 1.0),
                        debt=min(max(relationship_plan.debt_delta, -1.0), 1.0),
                        last_interaction=datetime.now(UTC),
                    )
                )
            else:
                relationship.trust = min(
                    max(
                        relationship.trust + relationship_plan.trust_delta,
                        0.0,
                    ),
                    1.0,
                )
                if relationship_plan.trust_floor is not None:
                    relationship.trust = max(
                        relationship.trust,
                        relationship_plan.trust_floor,
                    )
                if relationship_plan.trust_ceiling is not None:
                    relationship.trust = min(
                        relationship.trust,
                        relationship_plan.trust_ceiling,
                    )
                relationship.affinity = min(
                    max(
                        relationship.affinity + relationship_plan.affinity_delta,
                        -1.0,
                    ),
                    1.0,
                )
                relationship.fear = min(
                    max(
                        relationship.fear + relationship_plan.fear_delta,
                        0.0,
                    ),
                    1.0,
                )
                relationship.debt = min(
                    max(
                        relationship.debt + relationship_plan.debt_delta,
                        -1.0,
                    ),
                    1.0,
                )
                relationship.last_interaction = datetime.now(UTC)

    def check_health(self) -> bool:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def list_memory_lineage(
        self,
        run_id: UUID,
        proposition_key: str | None = None,
    ) -> MemoryLineageResponse:
        with self.session_factory() as session:
            if session.scalar(select(GameRunModel.id).where(GameRunModel.id == run_id)) is None:
                raise RunNotFoundError(run_id)

            version_query = (
                select(
                    BeliefVersionModel,
                    PropositionModel.proposition_key,
                    BeliefModel.current_version,
                    BeliefModel.contested,
                )
                .join(BeliefModel, BeliefModel.id == BeliefVersionModel.belief_id)
                .join(
                    PropositionModel,
                    PropositionModel.id == BeliefModel.proposition_id,
                )
                .where(BeliefVersionModel.game_run_id == run_id)
                .order_by(
                    PropositionModel.proposition_key,
                    BeliefVersionModel.holder_id,
                    BeliefVersionModel.version,
                )
            )
            transmission_query = (
                select(TransmissionModel, PropositionModel.proposition_key)
                .join(
                    PropositionModel,
                    PropositionModel.id == TransmissionModel.proposition_id,
                )
                .where(TransmissionModel.game_run_id == run_id)
                .order_by(TransmissionModel.created_at)
            )
            input_query = (
                select(BeliefInputModel, PropositionModel.proposition_key)
                .join(
                    PropositionModel,
                    PropositionModel.id == BeliefInputModel.proposition_id,
                )
                .where(BeliefInputModel.game_run_id == run_id)
                .order_by(BeliefInputModel.created_at, BeliefInputModel.id)
            )
            if proposition_key is not None:
                version_query = version_query.where(
                    PropositionModel.proposition_key == proposition_key
                )
                transmission_query = transmission_query.where(
                    PropositionModel.proposition_key == proposition_key
                )
                input_query = input_query.where(PropositionModel.proposition_key == proposition_key)
            version_rows = session.execute(version_query).all()
            transmission_rows = session.execute(transmission_query).all()
            input_rows = session.execute(input_query).all()

        versions = [
            MemoryVersionState(
                belief_id=version.belief_id,
                version=version.version,
                proposition_key=key,
                holder_id=version.holder_id,
                narrative_text=version.narrative_text,
                normalized_position=version.normalized_position,
                confidence=version.confidence,
                salience=version.salience,
                source_kind=version.source_kind,
                source_id=version.source_id,
                embedding_model_id=version.embedding_model_id,
                active=version.version == current_version,
                contested=contested and version.version == current_version,
                created_at=version.created_at,
            )
            for version, key, current_version, contested in version_rows
        ]
        transmissions = [
            TransmissionState(
                id=transmission.id,
                proposition_key=key,
                speaker_id=transmission.speaker_id,
                listener_id=transmission.listener_id,
                from_belief_id=transmission.from_belief_id,
                from_version=transmission.from_version,
                to_belief_id=transmission.to_belief_id,
                to_version=transmission.to_version,
                original_text=transmission.original_text,
                retold_text=transmission.retold_text,
                mutation_note=transmission.mutation_note,
                trust_at_time=transmission.trust_at_time,
                provider_id=transmission.provider_id,
                model_id=transmission.model_id,
                fallback_used=transmission.fallback_used,
                fallback_reason=transmission.fallback_reason,
                inference_attempts=transmission.inference_attempts,
                inference_latency_ms=transmission.inference_latency_ms,
                created_at=transmission.created_at,
            )
            for transmission, key in transmission_rows
        ]
        inputs = [
            BeliefInputState(
                id=item.id,
                proposition_key=key,
                holder_id=item.holder_id,
                source_kind=item.source_kind,
                source_id=item.source_id,
                narrative_text=item.narrative_text,
                normalized_position=item.normalized_position,
                source_trust=item.source_trust,
                evidence_weight=item.evidence_weight,
                corroboration=item.corroboration,
                recency=item.recency,
                bias_alignment=item.bias_alignment,
                incoming_strength=item.incoming_strength,
                classification=item.classification,
                outcome=item.outcome,
                rationale=item.rationale,
                observed_version=item.observed_version,
                evaluated_against_version=item.evaluated_against_version,
                resulting_belief_id=item.resulting_belief_id,
                resulting_version=item.resulting_version,
                transaction_attempts=item.transaction_attempts,
                recalculated_after_conflict=item.recalculated_after_conflict,
                created_at=item.created_at,
            )
            for item, key in input_rows
        ]
        return MemoryLineageResponse(
            run_id=run_id,
            proposition_key=proposition_key,
            versions=versions,
            transmissions=transmissions,
            inputs=inputs,
        )

    def recall_memories(
        self,
        run_id: UUID,
        holder_id: str,
        query_text: str,
        query_embedding: tuple[float, ...],
        limit: int,
    ) -> MemoryRecallResponse:
        trace_id = uuid4()
        distance = ActiveMemoryModel.embedding.cosine_distance(list(query_embedding))

        def retrieve(session: Session) -> MemoryRecallResponse:
            if session.scalar(select(GameRunModel.id).where(GameRunModel.id == run_id)) is None:
                raise RunNotFoundError(run_id)

            candidates = session.execute(
                select(
                    ActiveMemoryModel.belief_id,
                    ActiveMemoryModel.belief_version,
                    PropositionModel.proposition_key,
                    ActiveMemoryModel.narrative_text,
                    ActiveMemoryModel.confidence,
                    ActiveMemoryModel.salience,
                    BeliefVersionModel.source_id,
                    BeliefVersionModel.normalized_position,
                    BeliefModel.contested,
                    distance.label("distance"),
                )
                .join(
                    BeliefVersionModel,
                    (BeliefVersionModel.belief_id == ActiveMemoryModel.belief_id)
                    & (BeliefVersionModel.version == ActiveMemoryModel.belief_version),
                )
                .join(BeliefModel, BeliefModel.id == ActiveMemoryModel.belief_id)
                .join(
                    PropositionModel,
                    PropositionModel.id == BeliefModel.proposition_id,
                )
                .where(
                    ActiveMemoryModel.game_run_id == run_id,
                    ActiveMemoryModel.holder_id == holder_id,
                    ActiveMemoryModel.status == "active",
                    BeliefModel.current_version == ActiveMemoryModel.belief_version,
                )
                .order_by(distance)
                .limit(30)
            ).all()
            trust_by_source: dict[str, float] = {
                source_id: trust
                for source_id, trust in session.execute(
                    select(RelationshipModel.b_id, RelationshipModel.trust).where(
                        RelationshipModel.game_run_id == run_id,
                        RelationshipModel.a_id == holder_id,
                    )
                ).tuples()
            }

            recalled = []
            candidate_trace: list[dict[str, Any]] = []
            for candidate in candidates:
                semantic_similarity = max(0.0, 1.0 - float(candidate.distance))
                source_trust = trust_by_source.get(candidate.source_id, 0.5)
                final_score = (
                    semantic_similarity * candidate.confidence * candidate.salience * source_trust
                )
                recalled.append(
                    RecalledMemory(
                        belief_id=candidate.belief_id,
                        version=candidate.belief_version,
                        proposition_key=candidate.proposition_key,
                        narrative_text=candidate.narrative_text,
                        normalized_position=candidate.normalized_position,
                        semantic_similarity=semantic_similarity,
                        final_score=final_score,
                        confidence=candidate.confidence,
                        salience=candidate.salience,
                        source_id=candidate.source_id,
                        contested=candidate.contested,
                    )
                )
                candidate_trace.append(
                    {
                        "belief_id": str(candidate.belief_id),
                        "version": candidate.belief_version,
                        "distance": float(candidate.distance),
                        "source_trust": source_trust,
                        "final_score": final_score,
                        "contested": candidate.contested,
                    }
                )
            recalled.sort(key=lambda memory: memory.final_score, reverse=True)
            selected = recalled[:limit]
            session.execute(
                insert(RetrievalTraceModel).values(
                    id=trace_id,
                    game_run_id=run_id,
                    holder_id=holder_id,
                    query_text=query_text,
                    query_embedding=list(query_embedding),
                    candidate_versions=candidate_trace,
                    selected_versions=[
                        {
                            "belief_id": str(memory.belief_id),
                            "version": memory.version,
                            "final_score": memory.final_score,
                        }
                        for memory in selected
                    ],
                )
            )
            return MemoryRecallResponse(
                trace_id=trace_id,
                run_id=run_id,
                holder_id=holder_id,
                query=query_text,
                memories=selected,
            )

        return self._run_transaction(retrieve)

    def record_historian_audit(
        self,
        run_id: UUID,
        audit: HistorianAuditState,
    ) -> None:
        def write_audit(session: Session) -> None:
            if session.scalar(select(GameRunModel.id).where(GameRunModel.id == run_id)) is None:
                raise RunNotFoundError(run_id)
            session.execute(
                insert(HistorianAuditModel).values(
                    id=audit.id,
                    game_run_id=run_id,
                    operation=audit.operation,
                    proposition_key=audit.proposition_key,
                    provider_id=audit.provider_id,
                    attempted_provider_id=audit.attempted_provider_id,
                    tool_name=audit.tool_name,
                    auth_mode=audit.auth_mode,
                    cluster_fingerprint=audit.cluster_fingerprint,
                    managed_mcp=audit.managed_mcp,
                    sponsor_proof=audit.sponsor_proof,
                    success=audit.success,
                    fallback_used=audit.fallback_used,
                    fallback_reason=audit.fallback_reason,
                    query_id=audit.query_id,
                    result_counts=audit.result_counts,
                    latency_ms=audit.latency_ms,
                    created_at=audit.created_at,
                )
            )

        self._run_transaction(write_audit)

    def clear_all(self) -> None:
        """Delete test data. This is intentionally not exposed by the API."""

        def clear(session: Session) -> None:
            session.execute(delete(HistorianAuditModel))
            session.execute(delete(RetrievalTraceModel))
            session.execute(delete(BeliefInputModel))
            session.execute(delete(EvidenceLinkModel))
            session.execute(delete(EvidenceModel))
            session.execute(delete(TransmissionModel))
            session.execute(delete(GossipTickModel))
            session.execute(delete(RelationshipModel))
            session.execute(delete(ActiveMemoryModel))
            session.execute(delete(BeliefVersionModel))
            session.execute(delete(BeliefModel))
            session.execute(delete(PropositionModel))
            session.execute(delete(EventModel))
            session.execute(delete(ActionModel))
            session.execute(delete(GameRunModel))
            session.execute(delete(PlayerModel))

        self._run_transaction(clear)

    def dispose(self) -> None:
        self.engine.dispose()
