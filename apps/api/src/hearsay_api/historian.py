from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Any, Protocol
from uuid import UUID, uuid4

import httpx
import structlog

from hearsay_api.config import Settings
from hearsay_api.repository import RunRepository
from hearsay_api.schemas import (
    HistorianAuditState,
    HistorianTraceRequest,
    HistorianTraceResponse,
    MemoryLineageResponse,
)

logger = structlog.get_logger(__name__)

MANAGED_MCP_PROVIDER_ID = "cockroachdb-cloud-managed-mcp"
MANAGED_MCP_TOOL = "select_query"
DIRECT_FALLBACK_PROVIDER_ID = "cockroachdb-direct-fallback"
TRACE_QUERY_ID = "historian-trace-lineage-v1"
READ_ONLY_TOOLS = frozenset(
    {
        "list_clusters",
        "get_cluster",
        "list_databases",
        "list_tables",
        "get_table_schema",
        "select_query",
        "explain_query",
        "show_running_queries",
    }
)
WRITE_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|UPSERT|CREATE|ALTER|DROP|TRUNCATE|GRANT|REVOKE|COPY|IMPORT)\b",
    re.IGNORECASE,
)


class HistorianUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class McpTool:
    name: str
    input_schema: Mapping[str, Any]


class ManagedMcpTransport(Protocol):
    async def list_tools(self) -> tuple[McpTool, ...]: ...

    async def call_tool(
        self,
        name: str,
        arguments: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...


class CockroachCloudMcpTransport:
    """Short-lived official MCP client with a separately supplied credential."""

    def __init__(
        self,
        *,
        url: str,
        cluster_id: str,
        api_key: str,
        timeout_seconds: float,
    ) -> None:
        self.url = url
        self.cluster_id = cluster_id
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={
                "mcp-cluster-id": self.cluster_id,
                "Authorization": f"Bearer {self.api_key}",
            },
            timeout=self.timeout_seconds,
            follow_redirects=True,
        )

    async def list_tools(self) -> tuple[McpTool, ...]:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        async with (
            self._client() as http_client,
            streamable_http_client(
                self.url,
                http_client=http_client,
            ) as (read_stream, write_stream, _),
            ClientSession(read_stream, write_stream) as session,
        ):
            await session.initialize()
            result = await session.list_tools()
            return tuple(
                McpTool(name=tool.name, input_schema=tool.inputSchema)
                for tool in result.tools
            )

    async def call_tool(
        self,
        name: str,
        arguments: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        if name not in READ_ONLY_TOOLS:
            raise ValueError(f"Historian MCP tool is not read-only: {name}")
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        async with (
            self._client() as http_client,
            streamable_http_client(
                self.url,
                http_client=http_client,
            ) as (read_stream, write_stream, _),
            ClientSession(read_stream, write_stream) as session,
        ):
            await session.initialize()
            result = await session.call_tool(name, arguments=dict(arguments))
            if result.isError:
                raise HistorianUnavailableError("Managed MCP tool returned an error.")
            return {
                "structured_content": result.structuredContent,
                "content": [
                    block.model_dump(mode="json")
                    for block in result.content
                ],
            }


class HistorianService:
    def __init__(
        self,
        *,
        repository: RunRepository,
        provider_mode: str,
        database_name: str,
        transport: ManagedMcpTransport | None = None,
        cluster_id: str | None = None,
    ) -> None:
        self.repository = repository
        self.provider_mode = provider_mode
        self.database_name = database_name
        self.transport = transport
        self.cluster_id = cluster_id

    async def trace_rumor(
        self,
        run_id: UUID,
        request: HistorianTraceRequest,
    ) -> HistorianTraceResponse:
        # Establish run existence before making any external request.
        self.repository.get(run_id)
        started = perf_counter()
        attempted_provider = (
            MANAGED_MCP_PROVIDER_ID
            if self.provider_mode != "fallback"
            else DIRECT_FALLBACK_PROVIDER_ID
        )
        tool_name: str | None = None
        fallback_reason: str | None = None

        try:
            if self.provider_mode == "managed_mcp" and self.transport is None:
                raise HistorianUnavailableError(
                    "Managed MCP mode requires independent MCP credentials."
                )
            if self.transport is not None and self.provider_mode != "fallback":
                tool_name = MANAGED_MCP_TOOL
                lineage = await self._trace_via_managed_mcp(
                    run_id,
                    request.proposition_key,
                )
                audit = self._audit(
                    run_id=run_id,
                    proposition_key=request.proposition_key,
                    provider_id=MANAGED_MCP_PROVIDER_ID,
                    attempted_provider_id=attempted_provider,
                    tool_name=tool_name,
                    auth_mode="service-account-api-key",
                    managed_mcp=True,
                    sponsor_proof=True,
                    success=True,
                    fallback_used=False,
                    fallback_reason=None,
                    lineage=lineage,
                    started=started,
                )
                self.repository.record_historian_audit(run_id, audit)
                return HistorianTraceResponse(audit=audit, lineage=lineage)
        except Exception as error:
            fallback_reason = type(error).__name__
            logger.warning(
                "historian_managed_mcp_failed",
                operation="trace_rumor",
                reason=fallback_reason,
            )
            if self.provider_mode == "managed_mcp":
                audit = self._audit(
                    run_id=run_id,
                    proposition_key=request.proposition_key,
                    provider_id=MANAGED_MCP_PROVIDER_ID,
                    attempted_provider_id=attempted_provider,
                    tool_name=tool_name,
                    auth_mode="service-account-api-key",
                    managed_mcp=True,
                    sponsor_proof=False,
                    success=False,
                    fallback_used=False,
                    fallback_reason=fallback_reason,
                    lineage=None,
                    started=started,
                )
                self.repository.record_historian_audit(run_id, audit)
                raise HistorianUnavailableError(
                    "The independently authenticated Managed MCP Historian is unavailable."
                ) from error

        if fallback_reason is None:
            fallback_reason = (
                "managed_mcp_not_configured"
                if self.provider_mode == "auto"
                else "fallback_forced"
            )
        lineage = self.repository.list_memory_lineage(
            run_id,
            request.proposition_key,
        )
        provider_id = (
            DIRECT_FALLBACK_PROVIDER_ID
            if self.repository.backend_name == "cockroachdb"
            else self.repository.backend_name
        )
        audit = self._audit(
            run_id=run_id,
            proposition_key=request.proposition_key,
            provider_id=provider_id,
            attempted_provider_id=attempted_provider,
            tool_name=tool_name,
            auth_mode="application-database-credential",
            managed_mcp=False,
            sponsor_proof=False,
            success=True,
            fallback_used=True,
            fallback_reason=fallback_reason,
            lineage=lineage,
            started=started,
        )
        self.repository.record_historian_audit(run_id, audit)
        return HistorianTraceResponse(audit=audit, lineage=lineage)

    async def _trace_via_managed_mcp(
        self,
        run_id: UUID,
        proposition_key: str,
    ) -> MemoryLineageResponse:
        assert self.transport is not None
        tools = await self.transport.list_tools()
        tool_by_name = {tool.name: tool for tool in tools}
        select_tool = tool_by_name.get(MANAGED_MCP_TOOL)
        if select_tool is None:
            raise HistorianUnavailableError("Managed MCP did not advertise select_query.")
        sql = build_trace_query(run_id, proposition_key)
        arguments = build_select_arguments(
            select_tool.input_schema,
            database_name=self.database_name,
            sql=sql,
        )
        result = await self.transport.call_tool(MANAGED_MCP_TOOL, arguments)
        payload = find_lineage_payload(result)
        return MemoryLineageResponse.model_validate(
            {
                "run_id": str(run_id),
                "proposition_key": proposition_key,
                **payload,
            }
        )

    def _audit(
        self,
        *,
        run_id: UUID,
        proposition_key: str,
        provider_id: str,
        attempted_provider_id: str,
        tool_name: str | None,
        auth_mode: str,
        managed_mcp: bool,
        sponsor_proof: bool,
        success: bool,
        fallback_used: bool,
        fallback_reason: str | None,
        lineage: MemoryLineageResponse | None,
        started: float,
    ) -> HistorianAuditState:
        counts = (
            {
                "versions": len(lineage.versions),
                "transmissions": len(lineage.transmissions),
                "inputs": len(lineage.inputs),
            }
            if lineage is not None
            else {}
        )
        cluster_fingerprint = (
            hashlib.sha256(self.cluster_id.encode("utf-8")).hexdigest()[:12]
            if self.cluster_id
            else None
        )
        return HistorianAuditState(
            id=uuid4(),
            run_id=run_id,
            proposition_key=proposition_key,
            provider_id=provider_id,
            attempted_provider_id=attempted_provider_id,
            tool_name=tool_name,
            auth_mode=auth_mode,
            cluster_fingerprint=cluster_fingerprint,
            managed_mcp=managed_mcp,
            sponsor_proof=sponsor_proof,
            success=success,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            query_id=TRACE_QUERY_ID,
            result_counts=counts,
            latency_ms=(perf_counter() - started) * 1000,
            created_at=datetime.now(UTC),
        )


def create_historian_service(
    settings: Settings,
    repository: RunRepository,
    *,
    transport: ManagedMcpTransport | None = None,
) -> HistorianService:
    cluster_id = settings.historian_mcp_cluster_id
    api_key = (
        settings.historian_mcp_api_key.get_secret_value()
        if settings.historian_mcp_api_key is not None
        else None
    )
    if transport is None and cluster_id and api_key:
        transport = CockroachCloudMcpTransport(
            url=settings.historian_mcp_url,
            cluster_id=cluster_id,
            api_key=api_key,
            timeout_seconds=settings.historian_timeout_seconds,
        )
    if settings.historian_provider == "managed_mcp" and transport is None:
        raise RuntimeError(
            "HEARSAY_HISTORIAN_PROVIDER=managed_mcp requires "
            "COCKROACH_MCP_CLUSTER_ID and COCKROACH_MCP_API_KEY."
        )
    return HistorianService(
        repository=repository,
        provider_mode=settings.historian_provider,
        database_name=settings.historian_database,
        transport=transport,
        cluster_id=cluster_id,
    )


def build_trace_query(run_id: UUID, proposition_key: str) -> str:
    safe_key = proposition_key.replace("'", "''")
    sql = f"""
SELECT jsonb_build_object(
  'versions', COALESCE((
    SELECT jsonb_agg(jsonb_build_object(
      'belief_id', bv.belief_id::STRING,
      'version', bv.version,
      'proposition_key', p.proposition_key,
      'holder_id', bv.holder_id,
      'narrative_text', bv.narrative_text,
      'normalized_position', bv.normalized_position,
      'confidence', bv.confidence,
      'salience', bv.salience,
      'source_kind', bv.source_kind,
      'source_id', bv.source_id,
      'embedding_model_id', bv.embedding_model_id,
      'active', bv.status = 'active',
      'contested', b.contested,
      'created_at', bv.created_at
    ) ORDER BY bv.created_at, bv.version)
    FROM belief_versions AS bv
    JOIN beliefs AS b ON b.id = bv.belief_id
    JOIN propositions AS p ON p.id = b.proposition_id
    WHERE bv.game_run_id = '{run_id}'::UUID
      AND p.proposition_key = '{safe_key}'
  ), '[]'::JSONB),
  'transmissions', COALESCE((
    SELECT jsonb_agg(jsonb_build_object(
      'id', t.id::STRING,
      'proposition_key', p.proposition_key,
      'speaker_id', t.speaker_id,
      'listener_id', t.listener_id,
      'from_belief_id', t.from_belief_id::STRING,
      'from_version', t.from_version,
      'to_belief_id', t.to_belief_id::STRING,
      'to_version', t.to_version,
      'original_text', t.original_text,
      'retold_text', t.retold_text,
      'mutation_note', t.mutation_note,
      'trust_at_time', t.trust_at_time,
      'provider_id', t.provider_id,
      'model_id', t.model_id,
      'fallback_used', t.fallback_used,
      'fallback_reason', t.fallback_reason,
      'inference_attempts', t.inference_attempts,
      'inference_latency_ms', t.inference_latency_ms,
      'created_at', t.created_at
    ) ORDER BY t.created_at)
    FROM transmissions AS t
    JOIN propositions AS p ON p.id = t.proposition_id
    WHERE t.game_run_id = '{run_id}'::UUID
      AND p.proposition_key = '{safe_key}'
  ), '[]'::JSONB),
  'inputs', COALESCE((
    SELECT jsonb_agg(jsonb_build_object(
      'id', i.id::STRING,
      'proposition_key', p.proposition_key,
      'holder_id', i.holder_id,
      'source_kind', i.source_kind,
      'source_id', i.source_id,
      'narrative_text', i.narrative_text,
      'normalized_position', i.normalized_position,
      'source_trust', i.source_trust,
      'evidence_weight', i.evidence_weight,
      'corroboration', i.corroboration,
      'recency', i.recency,
      'bias_alignment', i.bias_alignment,
      'incoming_strength', i.incoming_strength,
      'classification', i.classification,
      'outcome', i.outcome,
      'rationale', i.rationale,
      'observed_version', i.observed_version,
      'evaluated_against_version', i.evaluated_against_version,
      'resulting_belief_id', i.resulting_belief_id::STRING,
      'resulting_version', i.resulting_version,
      'transaction_attempts', i.transaction_attempts,
      'recalculated_after_conflict', i.recalculated_after_conflict,
      'created_at', i.created_at
    ) ORDER BY i.created_at)
    FROM belief_inputs AS i
    JOIN propositions AS p ON p.id = i.proposition_id
    WHERE i.game_run_id = '{run_id}'::UUID
      AND p.proposition_key = '{safe_key}'
  ), '[]'::JSONB)
) AS lineage
""".strip()
    assert_read_only_sql(sql)
    return sql


def assert_read_only_sql(sql: str) -> None:
    normalized = sql.lstrip()
    if not normalized.upper().startswith(("SELECT ", "WITH ")):
        raise ValueError("Historian queries must begin with SELECT or WITH.")
    if WRITE_SQL.search(sql):
        raise ValueError("Historian queries cannot contain write operations.")
    if ";" in sql:
        raise ValueError("Historian queries must contain exactly one statement.")


def build_select_arguments(
    schema: Mapping[str, Any],
    *,
    database_name: str,
    sql: str,
) -> dict[str, Any]:
    assert_read_only_sql(sql)
    properties = schema.get("properties")
    if not isinstance(properties, Mapping):
        raise HistorianUnavailableError("select_query has no usable input schema.")
    required = schema.get("required", [])
    if not isinstance(required, list):
        required = []

    query_key = _find_schema_key(
        properties,
        exact=("query", "sql", "statement"),
        description_terms=("query", "sql", "statement"),
    )
    database_key = _find_schema_key(
        properties,
        exact=("database", "database_name", "db_name"),
        description_terms=("database",),
    )
    if query_key is None or database_key is None:
        raise HistorianUnavailableError(
            "select_query input schema does not expose query and database fields."
        )
    arguments: dict[str, Any] = {
        query_key: sql,
        database_key: database_name,
    }
    unknown_required = set(required) - set(arguments)
    if unknown_required:
        raise HistorianUnavailableError(
            "select_query requires unsupported arguments: "
            + ", ".join(sorted(str(item) for item in unknown_required))
        )
    return arguments


def _find_schema_key(
    properties: Mapping[str, Any],
    *,
    exact: tuple[str, ...],
    description_terms: tuple[str, ...],
) -> str | None:
    for candidate in exact:
        if candidate in properties:
            return candidate
    for key, value in properties.items():
        if not isinstance(value, Mapping):
            continue
        description = str(value.get("description", "")).lower()
        if any(term in description for term in description_terms):
            return str(key)
    return None


def find_lineage_payload(result: Mapping[str, Any]) -> Mapping[str, Any]:
    found = _find_lineage(result)
    if found is None:
        raise HistorianUnavailableError(
            "Managed MCP response did not contain a structured lineage payload."
        )
    return found


def _find_lineage(value: Any) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        if {"versions", "transmissions", "inputs"}.issubset(value):
            return value
        for child in value.values():
            found = _find_lineage(child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_lineage(child)
            if found is not None:
                return found
    elif isinstance(value, str):
        stripped = value.strip()
        candidates = [stripped]
        first = stripped.find("{")
        last = stripped.rfind("}")
        if first >= 0 and last > first:
            candidates.append(stripped[first : last + 1])
        for candidate in candidates:
            try:
                decoded = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            found = _find_lineage(decoded)
            if found is not None:
                return found
    return None
