from __future__ import annotations

from sqlalchemy import text

from database_setup import configured_environment, install_windows_root_certificate
from hearsay_api.persistence.database import create_database_engine, resolve_database_url


def main() -> int:
    environment = configured_environment()
    install_windows_root_certificate(environment)
    database_url = resolve_database_url(environment, database_name="hearsay")
    engine = create_database_engine(database_url, pool_size=1)
    try:
        with engine.connect() as connection:
            database_name = connection.scalar(text("SELECT current_database()"))
            dimensions = connection.scalar(text("SELECT vector_dims(CAST('[1, 0]' AS VECTOR(2)))"))
            migration_revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
            vector_enabled = connection.scalar(
                text("SHOW CLUSTER SETTING feature.vector_index.enabled")
            )
            indexes = connection.execute(text("SHOW INDEXES FROM active_memories")).mappings()
            vector_index_present = any(
                row["index_name"] == "active_memories_retrieval_vector_idx" for row in indexes
            )
    finally:
        engine.dispose()

    if dimensions != 2:
        raise RuntimeError("CockroachDB VECTOR support did not return two dimensions.")
    if not vector_enabled:
        raise RuntimeError("CockroachDB vector indexes are not enabled.")
    if not vector_index_present:
        raise RuntimeError("The Hearsay scoped vector index is missing.")
    if migration_revision != "20260719_0006":
        raise RuntimeError("The Hearsay application database is not at migration head.")
    print(
        f"CockroachDB database '{database_name}' is healthy at {migration_revision}; "
        "VECTOR support and the scoped recall index are enabled."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
