from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from urllib.request import urlopen

import psycopg
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values

from hearsay_api.persistence.database import resolve_database_url

REPO_ROOT = Path(__file__).resolve().parents[1]


def configured_environment() -> dict[str, str]:
    values = {
        key: value for key, value in dotenv_values(REPO_ROOT / ".env").items() if value is not None
    }
    values.update(os.environ)
    return values


def install_windows_root_certificate(environment: dict[str, str]) -> None:
    if sys.platform != "win32":
        return
    app_data = environment.get("APPDATA")
    command_value = environment.get("command_to_create_cert") or environment.get(
        "COMMAND_TO_CREATE_CERT"
    )
    if not app_data or not command_value:
        return
    certificate_path = Path(app_data) / "postgresql" / "root.crt"
    if certificate_path.is_file():
        return
    source_match = re.search(r"https://[^\s\"']+", command_value)
    if source_match is None:
        raise RuntimeError("command_to_create_cert does not contain an HTTPS URL.")
    source = source_match.group(0)
    certificate_path.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(source, timeout=30) as response:  # noqa: S310
        certificate_path.write_bytes(response.read())
    print(f"Installed the CockroachDB CA at {certificate_path}.")


def ensure_database(admin_url: str, database_name: str) -> None:
    with psycopg.connect(admin_url, autocommit=True, connect_timeout=10) as connection:
        cursor = connection.execute(
            "SELECT 1 FROM [SHOW DATABASES] WHERE database_name = %s",
            (database_name,),
        )
        if cursor.fetchone() is None:
            connection.execute(
                psycopg.sql.SQL("CREATE DATABASE {}").format(psycopg.sql.Identifier(database_name))
            )


def migrate(database_url: str) -> None:
    os.environ["DATABASE_URL"] = database_url
    alembic = Config(REPO_ROOT / "alembic.ini")
    command.upgrade(alembic, "head")


def prepare_database(database_name: str) -> str:
    environment = configured_environment()
    install_windows_root_certificate(environment)
    admin_url = resolve_database_url(environment, database_name="defaultdb")
    database_url = resolve_database_url(environment, database_name=database_name)
    ensure_database(admin_url, database_name)
    migrate(database_url)
    return database_url


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a configured CockroachDB.")
    parser.add_argument(
        "--database",
        choices=("hearsay", "hearsay_test"),
        default="hearsay",
    )
    args = parser.parse_args()

    prepare_database(args.database)
    print(f"CockroachDB database '{args.database}' is ready at migration head.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
