from __future__ import annotations

import argparse
import asyncio
from uuid import uuid4

from database_setup import configured_environment
from hearsay_api.config import Settings
from hearsay_api.historian import (
    MANAGED_MCP_TOOL,
    CockroachCloudMcpTransport,
    create_historian_service,
)
from hearsay_api.persistence.cockroach_repository import CockroachRunRepository
from hearsay_api.persistence.database import resolve_database_url
from hearsay_api.schemas import (
    ActionRequest,
    CreateRunRequest,
    HistorianTraceRequest,
)
from hearsay_api.service import GameService


async def check(*, execute: bool, trace_fixture: bool) -> int:
    settings = Settings()
    cluster_id = settings.historian_mcp_cluster_id
    api_key = (
        settings.historian_mcp_api_key.get_secret_value()
        if settings.historian_mcp_api_key is not None
        else None
    )
    if not cluster_id or not api_key:
        if settings.historian_provider == "managed_mcp":
            print(
                "Managed MCP Historian is forced but its independent cluster ID "
                "or API key is missing."
            )
            return 1
        print(
            "Managed MCP Historian is not configured; runtime lineage will be "
            "labeled as non-sponsor-proof fallback."
        )
        return 1 if execute else 0

    if not execute:
        print(
            "Managed MCP configuration is present. No external request was made. "
            "Pass --execute to run the bounded authentication check."
        )
        return 0

    transport = CockroachCloudMcpTransport(
        url=settings.historian_mcp_url,
        cluster_id=cluster_id,
        api_key=api_key,
        timeout_seconds=settings.historian_timeout_seconds,
    )
    if trace_fixture:
        return await trace_test_fixture(settings, transport)

    tools = await transport.list_tools()
    names = {tool.name for tool in tools}
    if MANAGED_MCP_TOOL not in names:
        print("Managed MCP authenticated, but select_query was not advertised.")
        return 1
    print(
        "Managed MCP Historian authenticated independently and advertised the "
        "allowlisted select_query tool."
    )
    return 0


async def trace_test_fixture(
    settings: Settings,
    transport: CockroachCloudMcpTransport,
) -> int:
    database_name = "hearsay_test"
    database_url = resolve_database_url(
        configured_environment(),
        database_name=database_name,
    )
    repository = CockroachRunRepository(database_url)
    try:
        game = GameService(repository=repository)
        created = game.create_run(
            CreateRunRequest(
                display_name="MCP proof",
                seed=1729,
                release_profile="hackathon_small",
            )
        )
        for verb, target_id in (
            ("promise_help", "marta"),
            ("negotiate_bram", "bram"),
        ):
            game.take_action(
                created.run_id,
                ActionRequest(
                    idempotency_key=uuid4(),
                    verb=verb,
                    target_id=target_id,
                ),
            )

        proof_settings = settings.model_copy(
            update={
                "historian_provider": "managed_mcp",
                "historian_database": database_name,
            }
        )
        historian = create_historian_service(
            proof_settings,
            repository,
            transport=transport,
        )
        result = await historian.trace_rumor(
            created.run_id,
            HistorianTraceRequest(
                proposition_key="bram-price-confrontation",
            ),
        )
    finally:
        repository.dispose()

    audit = result.audit
    if not audit.sponsor_proof:
        print("Managed MCP lineage trace completed without sponsor-proof status.")
        return 1
    print(
        "Managed MCP lineage proof passed "
        f"(run={created.run_id}, audit={audit.id}, "
        f"cluster={audit.cluster_fingerprint}, counts={audit.result_counts}, "
        f"latency_ms={audit.latency_ms:.1f})."
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run an explicit, short-lived Managed MCP authentication or lineage proof. "
            "The lineage fixture uses deterministic inference and never calls an LLM."
        )
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Allow the external Managed MCP request.",
    )
    parser.add_argument(
        "--trace-fixture",
        action="store_true",
        help=(
            "Create a small deterministic hearsay_test fixture and prove its lineage "
            "through Managed MCP select_query."
        ),
    )
    args = parser.parse_args()
    if args.trace_fixture and not args.execute:
        parser.error("--trace-fixture requires --execute")
    return args


if __name__ == "__main__":
    arguments = parse_args()
    raise SystemExit(
        asyncio.run(
            check(
                execute=arguments.execute,
                trace_fixture=arguments.trace_fixture,
            )
        )
    )
