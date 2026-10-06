"""
SmartZone zone tools (read-only).

Covers zone listing, zone details and AP groups per zone.
"""
import logging

from mcp.server.fastmcp import FastMCP

from mcp_smartzone.api.client import get_client
from mcp_smartzone.tools._util import to_json

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP) -> None:
    """Register all SmartZone zone tools."""

    @mcp.tool()
    async def smartzone_list_zones() -> str:
        """List all zones configured on the SmartZone controller.

        Returns:
            JSON list of zones (id, name, description, ...).
        """
        result = await get_client().get("rkszones", params={"listSize": 1000})
        return to_json(result)

    @mcp.tool()
    async def smartzone_get_zone(zone_id: str) -> str:
        """Get detailed information about a specific zone.

        Args:
            zone_id: Zone UUID.

        Returns:
            JSON with the zone configuration.
        """
        result = await get_client().get(f"rkszones/{zone_id}")
        return to_json(result)

    @mcp.tool()
    async def smartzone_list_zone_ap_groups(zone_id: str) -> str:
        """List AP groups configured in a specific zone.

        Args:
            zone_id: Zone UUID.

        Returns:
            JSON list of AP groups in the zone.
        """
        result = await get_client().get(f"rkszones/{zone_id}/apgroups")
        return to_json(result)