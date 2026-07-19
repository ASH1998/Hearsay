from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import uuid4

import pytest

from hearsay_api.historian import (
    MANAGED_MCP_PROVIDER_ID,
    HistorianService,
    HistorianUnavailableError,
    McpTool,
    assert_read_only_sql,
    build_select_arguments,
)
from hearsay_api.repository import InMemoryRunRepository
from hearsay_api.schemas import (
    ActionRequest,
    ActionVerb,
    CreateRunRequest,
    CreateRunResponse,
    HistorianAuditState,
    HistorianTraceRequest,
)
from hearsay_api.service import GameService


class FakeMcpTransport:
    def __init__(
        self,
        payload: Mapping[str, Any],
        *,
        tools: tuple[McpTool, ...] | None = None,
    ) -> None:
        self.payload = payload
        self.tools = tools or (
            McpTool(
                name="select_query",
                input_schema={
                    "type": "object",
                    "properties": {
                        "database_name": {"type": "string"},
                        "query": {"type": "string"},
                    },
                    "required": ["database_name", "query"],
                },
            ),
            McpTool(
                name="insert_rows",
                input_schema={"type": "object", "properties": {}},
            ),
        )
        self.calls: list[tuple[str, Mapping[str, Any]]] = []

    async def list_tools(self) -> tuple[McpTool, ...]:
        return self.tools

    async def call_tool(
        self,
        name: str,
        arguments: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        self.calls.append((name, arguments))
        return {"structured_content": {"rows": [{"lineage": self.payload}]}}


def make_rumor_repository() -> tuple[
    InMemoryRunRepository,
    GameService,
    CreateRunResponse,
]:
    repository = InMemoryRunRepository()
    game = GameService(repository=repository)
    run = game.create_run(CreateRunRequest(display_name="Ada", seed=42))
    game.take_action(
        run.run_id,
        ActionRequest(
            idempotency_key=uuid4(),
            verb=ActionVerb.CONFRONT,
            target_id="bram",
        ),
    )
    return repository, game, run


@pytest.mark.asyncio
async def test_managed_mcp_trace_is_the_only_sponsor_proof_path() -> None:
    repository, game, run = make_rumor_repository()
    lineage = game.get_memory_lineage(run.run_id, "bram-price-confrontation")
    transport = FakeMcpTransport(
        {
            "versions": [item.model_dump(mode="json") for item in lineage.versions],
            "transmissions": [item.model_dump(mode="json") for item in lineage.transmissions],
            "inputs": [],
        }
    )
    historian = HistorianService(
        repository=repository,
        provider_mode="managed_mcp",
        database_name="hearsay",
        transport=transport,
        cluster_id="cluster-secret-identity",
    )

    response = await historian.trace_rumor(
        run.run_id,
        HistorianTraceRequest(proposition_key="bram-price-confrontation"),
    )

    assert response.audit.provider_id == MANAGED_MCP_PROVIDER_ID
    assert response.audit.managed_mcp is True
    assert response.audit.sponsor_proof is True
    assert response.audit.auth_mode == "service-account-api-key"
    assert response.audit.cluster_fingerprint is not None
    assert "cluster-secret-identity" not in response.model_dump_json()
    assert response.lineage.versions
    assert [name for name, _ in transport.calls] == ["select_query"]
    arguments = transport.calls[0][1]
    assert arguments["database_name"] == "hearsay"
    assert str(arguments["query"]).startswith("SELECT ")
    assert "INSERT " not in str(arguments["query"]).upper()
    assert repository.get_historian_audits(run.run_id) == [response.audit]


@pytest.mark.asyncio
async def test_auto_mode_fallback_is_conspicuous_and_not_sponsor_proof() -> None:
    repository, _game, run = make_rumor_repository()
    historian = HistorianService(
        repository=repository,
        provider_mode="auto",
        database_name="hearsay",
    )

    response = await historian.trace_rumor(
        run.run_id,
        HistorianTraceRequest(proposition_key="bram-price-confrontation"),
    )

    assert response.audit.managed_mcp is False
    assert response.audit.sponsor_proof is False
    assert response.audit.fallback_used is True
    assert response.audit.fallback_reason == "managed_mcp_not_configured"
    assert response.lineage.versions


@pytest.mark.asyncio
async def test_forced_managed_mode_fails_closed_and_audits_failure() -> None:
    repository, _game, run = make_rumor_repository()
    transport = FakeMcpTransport(
        {},
        tools=(McpTool(name="insert_rows", input_schema={}),),
    )
    historian = HistorianService(
        repository=repository,
        provider_mode="managed_mcp",
        database_name="hearsay",
        transport=transport,
        cluster_id="cluster-id",
    )

    with pytest.raises(HistorianUnavailableError):
        await historian.trace_rumor(
            run.run_id,
            HistorianTraceRequest(proposition_key="bram-price-confrontation"),
        )

    audit = repository.get_historian_audits(run.run_id)[0]
    assert audit.success is False
    assert audit.sponsor_proof is False
    assert audit.fallback_used is False
    assert audit.fallback_reason == "HistorianUnavailableError"


def test_select_argument_adapter_uses_advertised_schema() -> None:
    arguments = build_select_arguments(
        {
            "properties": {
                "db_name": {"description": "Database to inspect"},
                "statement": {"description": "SQL statement"},
            },
            "required": ["db_name", "statement"],
        },
        database_name="hearsay",
        sql="SELECT 1",
    )

    assert arguments == {"db_name": "hearsay", "statement": "SELECT 1"}


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO beliefs VALUES (1)",
        "WITH deleted AS (DELETE FROM beliefs RETURNING *) SELECT * FROM deleted",
        "SELECT 1; SELECT 2",
    ],
)
def test_read_only_guard_rejects_write_or_multiple_statements(sql: str) -> None:
    with pytest.raises(ValueError):
        assert_read_only_sql(sql)


def test_audit_schema_cannot_forge_sponsor_proof() -> None:
    with pytest.raises(ValueError):
        HistorianAuditState(
            id=uuid4(),
            run_id=uuid4(),
            proposition_key="bram-price-confrontation",
            provider_id="cockroachdb-direct-fallback",
            attempted_provider_id="cockroachdb-cloud-managed-mcp",
            auth_mode="application-database-credential",
            managed_mcp=False,
            sponsor_proof=True,
            success=True,
            fallback_used=True,
            fallback_reason="managed_mcp_not_configured",
            query_id="historian-trace-lineage-v1",
            result_counts={},
            latency_ms=1,
            created_at="2026-07-19T00:00:00Z",
        )
