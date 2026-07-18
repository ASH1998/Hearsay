from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, TypeVar, cast
from uuid import UUID, uuid4

from sqlalchemy import delete, insert, select, text, update
from sqlalchemy.engine import CursorResult, Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy_cockroachdb import run_transaction  # type: ignore[import-untyped]

from hearsay_api.memory import MemoryEffects
from hearsay_api.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from hearsay_api.persistence.models import (
    ActionModel,
    ActiveMemoryModel,
    BeliefModel,
    BeliefVersionModel,
    EventModel,
    GameRunModel,
    GossipTickModel,
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
        event = snapshot.recent_events[0]

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
                select(GameRunModel.revision, GameRunModel.action_count).where(
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
                        model_id="hearsay-deterministic-rules-v1",
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
                session.execute(
                    insert(RelationshipModel).values(
                        game_run_id=run_id,
                        a_kind=relationship_plan.a_kind,
                        a_id=relationship_plan.a_id,
                        b_kind=relationship_plan.b_kind,
                        b_id=relationship_plan.b_id,
                        trust=min(
                            max(0.5 + relationship_plan.trust_delta, 0.0),
                            1.0,
                        ),
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
                )
                .join(BeliefModel, BeliefModel.id == BeliefVersionModel.belief_id)
                .join(
                    PropositionModel,
                    PropositionModel.id == BeliefModel.proposition_id,
                )
                .where(BeliefVersionModel.game_run_id == run_id)
                .order_by(BeliefVersionModel.created_at, BeliefVersionModel.version)
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
            if proposition_key is not None:
                version_query = version_query.where(
                    PropositionModel.proposition_key == proposition_key
                )
                transmission_query = transmission_query.where(
                    PropositionModel.proposition_key == proposition_key
                )
            version_rows = session.execute(version_query).all()
            transmission_rows = session.execute(transmission_query).all()

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
                created_at=version.created_at,
            )
            for version, key, current_version in version_rows
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
                model_id=transmission.model_id,
                created_at=transmission.created_at,
            )
            for transmission, key in transmission_rows
        ]
        return MemoryLineageResponse(
            run_id=run_id,
            proposition_key=proposition_key,
            versions=versions,
            transmissions=transmissions,
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
                        semantic_similarity=semantic_similarity,
                        final_score=final_score,
                        confidence=candidate.confidence,
                        salience=candidate.salience,
                        source_id=candidate.source_id,
                    )
                )
                candidate_trace.append(
                    {
                        "belief_id": str(candidate.belief_id),
                        "version": candidate.belief_version,
                        "distance": float(candidate.distance),
                        "source_trust": source_trust,
                        "final_score": final_score,
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

    def clear_all(self) -> None:
        """Delete test data. This is intentionally not exposed by the API."""

        def clear(session: Session) -> None:
            session.execute(delete(RetrievalTraceModel))
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
