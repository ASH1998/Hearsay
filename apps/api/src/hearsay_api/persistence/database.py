from __future__ import annotations

import re
from collections.abc import Mapping
from urllib.parse import quote, urlencode, urlunsplit

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker

CONNECTION_URL_PATTERN = re.compile(r"(?:postgres(?:ql)?|cockroachdb)(?:\+psycopg)?://[^\s\"']+")


def normalize_cockroach_url(database_url: str) -> str:
    replacements = (
        ("postgresql+psycopg://", "cockroachdb+psycopg://"),
        ("postgresql://", "cockroachdb+psycopg://"),
        ("cockroachdb://", "cockroachdb+psycopg://"),
    )
    for prefix, replacement in replacements:
        if database_url.startswith(prefix):
            return replacement + database_url[len(prefix) :]
    if database_url.startswith("cockroachdb+psycopg://"):
        return database_url
    raise ValueError("DATABASE_URL must use a PostgreSQL or CockroachDB scheme.")


def derive_database_url(
    connection_command: str,
    *,
    username: str | None = None,
    password: str | None = None,
    database_name: str | None = None,
) -> str:
    match = CONNECTION_URL_PATTERN.search(connection_command)
    if match is None:
        raise ValueError("command_to_connect must contain a PostgreSQL or CockroachDB URL.")

    url: URL = make_url(match.group(0))
    if username is not None:
        url = url.set(username=username)
    if password is not None:
        url = url.set(password=password)
    if database_name is not None:
        url = url.set(database=database_name)
    host = url.host or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    if url.port is not None:
        host = f"{host}:{url.port}"
    user_info = ""
    if url.username is not None:
        user_info = quote(url.username, safe="")
        if url.password is not None:
            user_info += f":{quote(url.password, safe='')}"
        user_info += "@"
    path = f"/{quote(url.database or '', safe='')}"
    query = urlencode(url.query, doseq=True)
    return urlunsplit((url.drivername, f"{user_info}{host}", path, query, ""))


def resolve_database_url(
    environment: Mapping[str, str],
    *,
    database_name: str | None = None,
) -> str:
    configured = environment.get("DATABASE_URL")
    if configured:
        if database_name is None:
            return configured
        return (
            make_url(configured).set(database=database_name).render_as_string(hide_password=False)
        )

    command = environment.get("command_to_connect") or environment.get("COMMAND_TO_CONNECT")
    if not command:
        raise ValueError("Set DATABASE_URL or provide command_to_connect in the environment.")
    return derive_database_url(
        command,
        username=environment.get("username") or environment.get("COCKROACH_USERNAME"),
        password=environment.get("password") or environment.get("COCKROACH_PASSWORD"),
        database_name=database_name,
    )


def create_database_engine(database_url: str, pool_size: int = 5) -> Engine:
    return create_engine(
        normalize_cockroach_url(database_url),
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max(2, pool_size),
        connect_args={"connect_timeout": 5},
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
