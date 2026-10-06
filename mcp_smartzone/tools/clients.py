"""
SmartZone wireless client tools (read-only).

Covers client listing, details and query operations.
"""
import json
import logging
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from mcp_smartzone.api.client import get_client
from mcp_smartzone.tools._util import to_json

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP) -> None:
    """Register all SmartZone wireless-client tools."""

    @mcp.tool()
    async def smartzone_list_clients(page: int = 1, limit: int = 50) -> str:
        """List currently connected wireless clients.

        Uses the query API to retrieve the client table.

        Args:
            page: Page number (1-indexed).
            limit: Results per page (max 1000).

        Returns:
            JSON with the client list and pagination info
            (clientMac, hostname, userName, ipAddress, ssid, apName, ...).
        """
        body: dict[str, Any] = {"page": page, "limit": limit}
        result = await get_client().post("query/client", data=body)
        return to_json(result)

    @mcp.tool()
    async def smartzone_get_client(client_mac: str) -> str:
        """Get details of a specific wireless client by MAC address.

        Args:
            client_mac: Client MAC address (e.g. "AB:CD:EF:12:34:56").

        Returns:
            JSON with the matching client(s).
        """
        body: dict[str, Any] = {
            "fullTextSearch": {"type": "AND", "value": client_mac},
            "page": 1,
            "limit": 10,
        }
        result = await get_client().post("query/client", data=body)
        return to_json(result)

    @mcp.tool()
    async def smartzone_query_clients(
        filters: Optional[str] = None,
        full_text_search: Optional[str] = None,
        sort_column: Optional[str] = None,
        sort_dir: str = "ASC",
        page: int = 1,
        limit: int = 50,
    ) -> str:
        """Query wireless clients with advanced filters.

        Args:
            filters: JSON string of filter criteria.
            full_text_search: Free-text search across client fields
                (hostname, MAC, username, IP, AP name).
            sort_column: Field to sort by (e.g. "txRxBytes", "clientMac",
                "insertionTime").
            sort_dir: Sort direction, "ASC" or "DESC".
            page: Page number (1-indexed).
            limit: Results per page (max 1000).

        Returns:
            JSON with the matching clients and pagination info.
        """
        body: dict[str, Any] = {"page": page, "limit": limit}
        if filters:
            try:
                body["filters"] = json.loads(filters)
            except json.JSONDecodeError:
                return "ERROR: 'filters' must be valid JSON"
        if full_text_search:
            body["fullTextSearch"] = {"type": "AND", "value": full_text_search}
        if sort_column:
            body["sortInfo"] = {"sortColumn": sort_column, "dir": sort_dir.upper()}
        result = await get_client().post("query/client", data=body)
        return to_json(result)