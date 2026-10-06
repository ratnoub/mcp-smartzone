"""
SmartZone system tools (read-only).

Covers system information, summary statistics, inventory and
cluster state.
"""
import logging

from mcp.server.fastmcp import FastMCP

from mcp_smartzone.api.client import get_client
from mcp_smartzone.tools._util import to_json

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP) -> None:
    """Register all SmartZone system tools."""

    @mcp.tool()
    async def smartzone_get_system_info() -> str:
        """Get SmartZone controller system information (version, model, uptime).

        Returns:
            JSON with controller details (softwareVersion, hostName,
            clusterUpTime, apCount, ...).
        """
        result = await get_client().get("controller")
        return to_json(result)

    @mcp.tool()
    async def smartzone_get_system_summary() -> str:
        """Get system summary with AP count, client count and zone statistics.

        Tries /system/systemSummary first, falls back to /system/inventory
        on older SmartZone versions.

        Returns:
            JSON with aggregate system statistics.
        """
        result = await get_client().get("system/systemSummary")
        if isinstance(result, str) and "404" in result:
            result = await get_client().get("system/inventory")
        return to_json(result)

    @mcp.tool()
    async def smartzone_get_system_inventory() -> str:
        """Get system inventory with per-zone AP and client statistics.

        Returns:
            JSON with the device inventory and per-zone statistics.
        """
        result = await get_client().get("system/inventory")
        return to_json(result)

    @mcp.tool()
    async def smartzone_get_cluster_state() -> str:
        """Get cluster state including node status and roles.

        Returns:
            JSON with cluster node status and roles.
        """
        result = await get_client().get("cluster/state")
        return to_json(result)

    @mcp.tool()
    async def smartzone_get_controller_list() -> str:
        """List all controllers in the cluster.

        Returns:
            JSON list of controllers with their status.
        """
        result = await get_client().get("controller")
        return to_json(result)