"""
SmartZone monitoring and query tools (read-only).

Covers the generic query API, AP statistics and WLAN statistics.
"""
import json
import logging
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from mcp_smartzone.api.client import get_client
from mcp_smartzone.tools._util import to_json

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP) -> None:
    """Register all SmartZone monitoring / query tools."""

    @mcp.tool()
    async def smartzone_query(
        query_type: str,
        filters: Optional[str] = None,
        full_text_search: Optional[str] = None,
        page: int = 1,
        limit: int = 100,
    ) -> str:
        """Run a generic SmartZone query with optional filters.

        Supported query types: ap, client, wlan, dpsk, roguesInfoList, etc.

        Args:
            query_type: Query type (ap, client, wlan, dpsk, roguesInfoList).
            filters: JSON string of filter criteria.
            full_text_search: Free-text search.
            page: Page number (1-indexed).
            limit: Results per page (max 1000).

        Returns:
            JSON with the query results and pagination info.
        """
        body: dict[str, Any] = {"page": page, "limit": limit}
        if filters:
            try:
                body["filters"] = json.loads(filters)
            except json.JSONDecodeError:
                return "ERROR: 'filters' must be valid JSON"
        if full_text_search:
            body["fullTextSearch"] = {"type": "AND", "value": full_text_search}
        result = await get_client().post(f"query/{query_type}", data=body)
        return to_json(result)

    @mcp.tool()
    async def smartzone_get_ap_statistics(ap_mac: str) -> str:
        """Get traffic statistics for a specific AP.

        Args:
            ap_mac: AP MAC address.

        Returns:
            JSON with the AP operational/traffic summary.
        """
        result = await get_client().get(f"aps/{ap_mac}/operational/summary")
        return to_json(result)

    @mcp.tool()
    async def smartzone_get_wlan_statistics(
        wlan_name: Optional[str] = None,
    ) -> str:
        """Get statistics for WLANs via the query API.

        Returns WLAN statistics including client count, traffic and status.
        Optionally filter by WLAN name.

        Args:
            wlan_name: WLAN name to filter (optional, returns all if omitted).

        Returns:
            JSON with WLAN statistics.
        """
        body: dict[str, Any] = {}
        if wlan_name:
            body["fullTextSearch"] = {"type": "AND", "value": wlan_name}
        result = await get_client().post("query/wlan", data=body)
        return to_json(result)