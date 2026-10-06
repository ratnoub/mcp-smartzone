"""
SmartZone WLAN tools (read-only).

Covers WLAN listing and details within a zone.
"""
import logging

from mcp.server.fastmcp import FastMCP

from mcp_smartzone.api.client import get_client
from mcp_smartzone.tools._util import to_json

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP) -> None:
    """Register all SmartZone WLAN tools."""

    @mcp.tool()
    async def smartzone_list_wlans(zone_id: str) -> str:
        """List all WLANs in a zone.

        Args:
            zone_id: Zone UUID.

        Returns:
            JSON list of WLANs (ssid, vlan, security, ...).
        """
        result = await get_client().get(f"rkszones/{zone_id}/wlans")
        return to_json(result)

    @mcp.tool()
    async def smartzone_get_wlan(zone_id: str, wlan_id: str) -> str:
        """Get WLAN configuration details.

        Args:
            zone_id: Zone UUID.
            wlan_id: WLAN UUID.

        Returns:
            JSON with the WLAN configuration.
        """
        result = await get_client().get(f"rkszones/{zone_id}/wlans/{wlan_id}")
        return to_json(result)