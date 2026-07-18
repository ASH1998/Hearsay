from __future__ import annotations

import os

import pytest

from database_setup import prepare_database


def main() -> int:
    database_url = prepare_database("hearsay_test")
    os.environ["DATABASE_URL"] = database_url
    os.environ["HEARSAY_TEST_DATABASE_URL"] = database_url
    return pytest.main(["-m", "cockroach"])


if __name__ == "__main__":
    raise SystemExit(main())
