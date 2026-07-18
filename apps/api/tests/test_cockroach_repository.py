from __future__ import annotations

import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import make_url

from hearsay_api.persistence.cockroach_repository import CockroachRunRepository
from hearsay_api.persistence.database import normalize_cockroach_url
from hearsay_api.persistence.models import ActionModel, EventModel, GameRunModel
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
