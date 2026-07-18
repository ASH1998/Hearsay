from __future__ import annotations

import asyncio

from hearsay_api.config import Settings
from hearsay_api.historian import (
    MANAGED_MCP_TOOL,
    CockroachCloudMcpTransport,
)


async def check() -> int:
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
        return 0

    transport = CockroachCloudMcpTransport(
        url=settings.historian_mcp_url,
        cluster_id=cluster_id,
        api_key=api_key,
        timeout_seconds=settings.historian_timeout_seconds,
    )
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


if __name__ == "__main__":
    raise SystemExit(asyncio.run(check()))
