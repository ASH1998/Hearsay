from __future__ import annotations

from typing import TYPE_CHECKING

from hearsay_api.repository import InMemoryRunRepository, RunRepository

if TYPE_CHECKING:
    from hearsay_api.config import Settings


def create_repository(settings: Settings) -> RunRepository:
    if settings.persistence_backend == "memory":
        return InMemoryRunRepository()
    if settings.database_url is None:
        raise RuntimeError("HEARSAY_PERSISTENCE_BACKEND=cockroachdb requires DATABASE_URL.")

    from hearsay_api.persistence.cockroach_repository import CockroachRunRepository

    return CockroachRunRepository(
        database_url=settings.database_url.get_secret_value(),
        pool_size=settings.database_pool_size,
        max_transaction_retries=settings.transaction_max_retries,
    )


__all__ = ["create_repository"]
