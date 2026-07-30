from __future__ import annotations

import argparse
import os

import pytest

from database_setup import prepare_database


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare hearsay_test and run scoped CockroachDB tests.",
    )
    parser.add_argument(
        "tests",
        nargs="*",
        help="Optional pytest node IDs; defaults to every cockroach-marked test.",
    )
    args = parser.parse_args()

    database_url = prepare_database("hearsay_test")
    os.environ["DATABASE_URL"] = database_url
    os.environ["HEARSAY_TEST_DATABASE_URL"] = database_url
    return pytest.main(args.tests or ["-m", "cockroach"])


if __name__ == "__main__":
    raise SystemExit(main())
