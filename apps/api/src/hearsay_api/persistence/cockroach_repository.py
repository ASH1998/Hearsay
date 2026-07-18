from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast
from uuid import UUID, uuid4

from sqlalchemy import delete, insert, select, text, update
from sqlalchemy.engine import CursorResult, Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy_cockroachdb import run_transaction  # type: ignore[import-untyped]

from hearsay_api.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from hearsay_api.persistence.models import (
    ActionModel,
    EventModel,
    GameRunModel,
    PlayerModel,
)
from hearsay_api.repository import ConcurrentRunUpdateError, RunNotFoundError
from hearsay_api.schemas import ActionRequest, ActionResponse, RunSnapshot

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
            return ActionResponse.model_validate(response_json)

        return self._run_transaction(update_run)

    def check_health(self) -> bool:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def clear_all(self) -> None:
        """Delete test data. This is intentionally not exposed by the API."""

        def clear(session: Session) -> None:
            session.execute(delete(EventModel))
            session.execute(delete(ActionModel))
            session.execute(delete(GameRunModel))
            session.execute(delete(PlayerModel))

        self._run_transaction(clear)

    def dispose(self) -> None:
        self.engine.dispose()
