"""
SmartZone DHCP and VLAN network tools (read-only).

Covers DHCP pool and VLAN pool listing and details within zones.
"""
import logging

from fastmcp import FastMCP

from mcp_smartzone.api.client import get_client
from mcp_smartzone.tools._util import to_json

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP) -> None:
    """Register all SmartZone DHCP / VLAN tools."""

    @mcp.tool()
    async def smartzone_list_dhcp_pools(zone_id: str) -> str:
        """List DHCP pools configured in a zone.

        Args:
            zone_id: Zone UUID.

        Returns:
            JSON list of DHCP pools in the zone.
        """
        result = await get_client().get(
            f"rkszones/{zone_id}/dhcpSite/dhcpProfile"
        )
        return to_json(result)

    @mcp.tool()
    async def smartzone_get_dhcp_pool(zone_id: str, pool_id: str) -> str:
        """Get details of a specific DHCP pool.

        Args:
            zone_id: Zone UUID.
            pool_id: DHCP pool UUID.

        Returns:
            JSON with the DHCP pool configuration.
        """
        result = await get_client().get(
            f"rkszones/{zone_id}/dhcpSite/dhcpProfile/{pool_id}"
        )
        return to_json(result)

    @mcp.tool()
    async def smartzone_list_vlan_pools() -> str:
        """List VLAN pooling profiles.

        Returns:
            JSON list of VLAN pooling profiles.
        """
        result = await get_client().post("vlanpoolings/query", data={})
        return to_json(result)

    @mcp.tool()
    async def smartzone_get_vlan_pool(pool_id: str) -> str:
        """Get details of a specific VLAN pool.

        Args:
            pool_id: VLAN pool UUID.

        Returns:
            JSON with the VLAN pool configuration.
        """
        result = await get_client().get(f"vlanpoolings/{pool_id}")
        return to_json(result)