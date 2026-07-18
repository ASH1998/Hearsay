from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from threading import RLock
from typing import Protocol
from uuid import UUID

from hearsay_api.schemas import ActionRequest, ActionResponse, RunSnapshot


@dataclass
class StoredRun:
    snapshot: RunSnapshot
    action_results: dict[UUID, ActionResponse] = field(default_factory=dict)


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
    ) -> ActionResponse: ...

    def check_health(self) -> bool: ...


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
            return deepcopy(result)

    def check_health(self) -> bool:
        return True
