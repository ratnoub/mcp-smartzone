"""
SmartZone access point tools (read-only).

Covers AP listing, details, operational info, radio info,
mesh/LLDP neighbours and query.
"""
import json
import logging
from typing import Any, Optional

from fastmcp import FastMCP

from mcp_smartzone.api.client import get_client
from mcp_smartzone.tools._util import to_json

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP) -> None:
    """Register all SmartZone access-point tools."""

    @mcp.tool()
    async def smartzone_list_aps() -> str:
        """List all access points managed by the SmartZone controller.

        Returns:
            JSON list of access points.
        """
        result = await get_client().get("aps")
        return to_json(result)

    @mcp.tool()
    async def smartzone_get_ap(ap_mac: str) -> str:
        """Get configuration details of a specific access point.

        Args:
            ap_mac: AP MAC address (e.g. "AB:CD:EF:12:34:56").

        Returns:
            JSON with the AP configuration.
        """
        result = await get_client().get(f"aps/{ap_mac}")
        return to_json(result)

    @mcp.tool()
    async def smartzone_get_ap_operational(ap_mac: str) -> str:
        """Get operational information of an AP (uptime, clients, status).

        Args:
            ap_mac: AP MAC address.

        Returns:
            JSON with the AP operational summary.
        """
        result = await get_client().get(f"aps/{ap_mac}/operational/summary")
        return to_json(result)

    @mcp.tool()
    async def smartzone_list_ap_mesh_neighbors(ap_mac: str) -> str:
        """Get mesh neighbor APs discovered by an AP (mesh topology).

        Args:
            ap_mac: AP MAC address.

        Returns:
            JSON list of mesh neighbours.
        """
        result = await get_client().get(f"aps/{ap_mac}/operational/neighbor")
        return to_json(result)

    @mcp.tool()
    async def smartzone_list_ap_lldp_neighbors(ap_mac: str) -> str:
        """Get LLDP neighbor devices discovered by an AP (switches, phones, etc.).

        Returns the list of LLDP neighbors with chassis ID, system name,
        port description, capabilities, management IP and power info.

        Args:
            ap_mac: AP MAC address (e.g. 00:33:58:07:70:E0).

        Returns:
            JSON list of LLDP neighbours.
        """
        result = await get_client().get(f"aps/{ap_mac}/apLldpNeighbors")
        return to_json(result)

    @mcp.tool()
    async def smartzone_get_ap_radio(ap_mac: str) -> str:
        """Get radio configuration of an AP (2.4G / 5G / 6G).

        Returns the radio-related fields from the AP configuration.

        Args:
            ap_mac: AP MAC address.

        Returns:
            JSON with the radio configuration section.
        """
        result = await get_client().get(f"aps/{ap_mac}")
        if isinstance(result, str):
            return result
        radio_info: dict = {}
        if isinstance(result, dict):
            for key in ("radioConfig", "wifi24Channel", "wifi50Channel", "wifi6gChannel"):
                if key in result:
                    radio_info[key] = result[key]
            if not radio_info:
                radio_info = result
        return json.dumps(radio_info, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def smartzone_query_aps(
        filters: Optional[str] = None,
        full_text_search: Optional[str] = None,
        page: int = 1,
        limit: int = 100,
    ) -> str:
        """Query access points with filters.

        Uses the SmartZone query API to search APs by criteria.

        Note: DOMAIN-type filters may return 403 depending on the API
        account privileges. Prefer full_text_search when possible.

        Args:
            filters: JSON string of filter criteria (e.g. '[{"type":"ZONE","value":"..."}]').
            full_text_search: Free-text search across AP fields (recommended).
            page: Page number (1-indexed).
            limit: Results per page (max 1000).

        Returns:
            JSON with the matching APs and pagination info.
        """
        body: dict[str, Any] = {"page": page, "limit": limit}
        if filters:
            try:
                body["filters"] = json.loads(filters)
            except json.JSONDecodeError:
                return "ERROR: 'filters' must be valid JSON"
        if full_text_search:
            body["fullTextSearch"] = {"type": "AND", "value": full_text_search}
        result = await get_client().post("query/ap", data=body)
        return to_json(result)