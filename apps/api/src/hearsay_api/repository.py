from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from threading import RLock
from uuid import UUID

from hearsay_api.schemas import ActionResponse, RunSnapshot


@dataclass
class StoredRun:
    snapshot: RunSnapshot
    action_results: dict[UUID, ActionResponse] = field(default_factory=dict)


class RunNotFoundError(KeyError):
    pass


class InMemoryRunRepository:
    """Development repository used until the CockroachDB adapter is configured.

    It deliberately exposes transaction-shaped mutation through ``update`` and
    supports idempotency. Browser refreshes retain state for the life of the API
    process; the CockroachDB repository will replace this at the memory-spine
    milestone.
    """

    def __init__(self) -> None:
        self._runs: dict[UUID, StoredRun] = {}
        self._lock = RLock()

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
        idempotency_key: UUID,
        result: ActionResponse,
    ) -> ActionResponse:
        with self._lock:
            try:
                stored = self._runs[run_id]
            except KeyError as error:
                raise RunNotFoundError(run_id) from error
            stored.snapshot = deepcopy(snapshot)
            stored.action_results[idempotency_key] = deepcopy(result)
            return deepcopy(result)
