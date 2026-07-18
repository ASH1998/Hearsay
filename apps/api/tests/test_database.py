from __future__ import annotations

import pytest

from hearsay_api.persistence.database import (
    derive_database_url,
    normalize_cockroach_url,
    resolve_database_url,
)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "postgresql://root@localhost:26257/hearsay?sslmode=disable",
            "cockroachdb+psycopg://root@localhost:26257/hearsay?sslmode=disable",
        ),
        (
            "postgresql+psycopg://root@localhost:26257/hearsay",
            "cockroachdb+psycopg://root@localhost:26257/hearsay",
        ),
        (
            "cockroachdb://root@localhost:26257/hearsay",
            "cockroachdb+psycopg://root@localhost:26257/hearsay",
        ),
        (
            "cockroachdb+psycopg://root@localhost:26257/hearsay",
            "cockroachdb+psycopg://root@localhost:26257/hearsay",
        ),
    ],
)
def test_normalize_cockroach_url(source: str, expected: str) -> None:
    assert normalize_cockroach_url(source) == expected


def test_normalize_cockroach_url_rejects_unrelated_schemes() -> None:
    with pytest.raises(ValueError, match="PostgreSQL or CockroachDB"):
        normalize_cockroach_url("sqlite:///hearsay.db")


def test_derive_database_url_combines_existing_env_fields() -> None:
    derived = derive_database_url(
        "cockroach sql --url 'postgresql://old:placeholder@example.test:26257/defaultdb"
        "?sslmode=verify-full'",
        username="ash",
        password="new password",
        database_name="hearsay",
    )

    assert derived == (
        "postgresql://ash:new%20password@example.test:26257/hearsay?sslmode=verify-full"
    )


def test_resolve_database_url_prefers_explicit_url() -> None:
    resolved = resolve_database_url(
        {
            "DATABASE_URL": (
                "cockroachdb+psycopg://root@example.test:26257/defaultdb?sslmode=verify-full"
            ),
            "command_to_connect": "ignored",
        },
        database_name="hearsay_test",
    )

    assert resolved == (
        "cockroachdb+psycopg://root@example.test:26257/hearsay_test?sslmode=verify-full"
    )
