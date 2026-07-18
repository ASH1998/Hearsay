from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from threading import RLock
from typing import Protocol
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from hearsay_api.memory import MemoryEffects
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


@dataclass
class StoredRun:
    snapshot: RunSnapshot
    action_results: dict[UUID, ActionResponse] = field(default_factory=dict)
    memory_effects: list[MemoryEffects] = field(default_factory=list)


class RunNotFoundError(KeyError):
    pass


class ConcurrentRunUpdateError(RuntimeError):
    pass


class RunRepository(Protocol):
    @property
    def backend_name(self) -> str: ...

    def create(self, snapshot: RunSnapshot) -> RunSnapshot: ...

    def get(self, run_id: UUID) -> RunSnapshot: ...

    def get_action_result(self, run_id: UUID, key: UUID) -> ActionResponse | None: ...

    def update(
        self,
        run_id: UUID,
        snapshot: RunSnapshot,
        request: ActionRequest,
        idempotency_key: UUID,
        result: ActionResponse,
        memory_effects: MemoryEffects,
    ) -> ActionResponse: ...

    def check_health(self) -> bool: ...

    def list_memory_lineage(
        self,
        run_id: UUID,
        proposition_key: str | None = None,
    ) -> MemoryLineageResponse: ...

    def recall_memories(
        self,
        run_id: UUID,
        holder_id: str,
        query_text: str,
        query_embedding: tuple[float, ...],
        limit: int,
    ) -> MemoryRecallResponse: ...


class InMemoryRunRepository:
    """Explicit credential-free development and unit-test repository.

    It deliberately exposes transaction-shaped mutation through ``update`` and
    supports idempotency. Browser refreshes retain state only for the life of
    the API process; configured runtime environments use CockroachDB instead.
    """

    def __init__(self) -> None:
        self._runs: dict[UUID, StoredRun] = {}
        self._lock = RLock()

    @property
    def backend_name(self) -> str:
        return "in-memory-development-fallback"

    def create(self, snapshot: RunSnapshot) -> RunSnapshot:
        with self._lock:
            self._runs[snapshot.run_id] = StoredRun(snapshot=deepcopy(snapshot))
            return deepcopy(snapshot)

    def get(self, run_id: UUID) -> RunSnapshot:
        with self._lock:
            try:
                return deepcopy(self._runs[run_id].snapshot)
            except KeyError as error:
                raise RunNotFoundError(run_id) from error

    def get_action_result(self, run_id: UUID, key: UUID) -> ActionResponse | None:
        with self._lock:
            try:
                result = self._runs[run_id].action_results.get(key)
            except KeyError as error:
                raise RunNotFoundError(run_id) from error
            return deepcopy(result)

    def update(
        self,
        run_id: UUID,
        snapshot: RunSnapshot,
        request: ActionRequest,
        idempotency_key: UUID,
        result: ActionResponse,
        memory_effects: MemoryEffects,
    ) -> ActionResponse:
        with self._lock:
            try:
                stored = self._runs[run_id]
            except KeyError as error:
                raise RunNotFoundError(run_id) from error
            cached = stored.action_results.get(idempotency_key)
            if cached is not None:
                return deepcopy(cached)
            expected_revision = snapshot.revision - 1
            if stored.snapshot.revision != expected_revision:
                raise ConcurrentRunUpdateError(
                    f"Run {run_id} changed at revision {stored.snapshot.revision}."
                )
            stored.snapshot = deepcopy(snapshot)
            stored.action_results[idempotency_key] = deepcopy(result)
            stored.memory_effects.append(deepcopy(memory_effects))
            return deepcopy(result)

    def check_health(self) -> bool:
        return True

    def get_memory_effects(self, run_id: UUID) -> list[MemoryEffects]:
        with self._lock:
            try:
                return deepcopy(self._runs[run_id].memory_effects)
            except KeyError as error:
                raise RunNotFoundError(run_id) from error

    def list_memory_lineage(
        self,
        run_id: UUID,
        proposition_key: str | None = None,
    ) -> MemoryLineageResponse:
        effects = self.get_memory_effects(run_id)
        versions: list[MemoryVersionState] = []
        transmissions: list[TransmissionState] = []
        current_versions: dict[tuple[str, str], int] = {}

        for effect_index, effect in enumerate(effects):
            for belief_index, planned in enumerate(effect.beliefs):
                if proposition_key is not None and planned.proposition_key != proposition_key:
                    continue
                key = (planned.proposition_key, planned.holder_id)
                version = current_versions.get(key, 0) + 1
                current_versions[key] = version
                belief_id = uuid5(
                    NAMESPACE_URL,
                    f"{run_id}:{planned.proposition_key}:{planned.holder_id}",
                )
                versions.append(
                    MemoryVersionState(
                        belief_id=belief_id,
                        version=version,
                        proposition_key=planned.proposition_key,
                        holder_id=planned.holder_id,
                        narrative_text=planned.narrative_text,
                        normalized_position=planned.normalized_position,
                        confidence=planned.confidence,
                        salience=planned.salience,
                        source_kind=planned.source_kind,
                        source_id=planned.source_id,
                        embedding_model_id=planned.embedding_model_id,
                        active=True,
                    )
                )
                if planned.parent_holder_id is not None:
                    parent_key = (planned.proposition_key, planned.parent_holder_id)
                    parent_belief_id = uuid5(
                        NAMESPACE_URL,
                        f"{run_id}:{planned.proposition_key}:{planned.parent_holder_id}",
                    )
                    parent_version = current_versions[parent_key]
                    original = next(
                        item.narrative_text
                        for item in reversed(versions)
                        if item.belief_id == parent_belief_id and item.version == parent_version
                    )
                    transmissions.append(
                        TransmissionState(
                            id=uuid5(
                                NAMESPACE_URL,
                                f"{run_id}:{effect_index}:{belief_index}:transmission",
                            ),
                            proposition_key=planned.proposition_key,
                            speaker_id=planned.parent_holder_id,
                            listener_id=planned.holder_id,
                            from_belief_id=parent_belief_id,
                            from_version=parent_version,
                            to_belief_id=belief_id,
                            to_version=version,
                            original_text=original,
                            retold_text=planned.narrative_text,
                            mutation_note=planned.mutation_note,
                            trust_at_time=planned.trust_at_time,
                            model_id="hearsay-deterministic-rules-v1",
                        )
                    )

        for memory_version in versions:
            memory_version.active = (
                memory_version.version
                == current_versions[(memory_version.proposition_key, memory_version.holder_id)]
            )
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
        lineage = self.list_memory_lineage(run_id)
        planned_by_key = {
            (planned.proposition_key, planned.holder_id): planned
            for effects in self.get_memory_effects(run_id)
            for planned in effects.beliefs
        }
        recalled: list[RecalledMemory] = []
        for version in lineage.versions:
            if version.holder_id != holder_id or not version.active:
                continue
            planned = planned_by_key[(version.proposition_key, version.holder_id)]
            similarity = max(
                0.0,
                sum(
                    left * right
                    for left, right in zip(
                        query_embedding,
                        planned.embedding,
                        strict=True,
                    )
                ),
            )
            recalled.append(
                RecalledMemory(
                    belief_id=version.belief_id,
                    version=version.version,
                    proposition_key=version.proposition_key,
                    narrative_text=version.narrative_text,
                    semantic_similarity=similarity,
                    final_score=similarity * version.confidence * version.salience * 0.5,
                    confidence=version.confidence,
                    salience=version.salience,
                    source_id=version.source_id,
                )
            )
        recalled.sort(key=lambda memory: memory.final_score, reverse=True)
        return MemoryRecallResponse(
            trace_id=uuid4(),
            run_id=run_id,
            holder_id=holder_id,
            query=query_text,
            memories=recalled[:limit],
        )
