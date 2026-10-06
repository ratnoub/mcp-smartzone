"""
SmartZone system tools (read-only).

Covers system information, summary statistics, inventory and
cluster state.
"""
import asyncio
import logging
from typing import Any

from fastmcp import FastMCP

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
            """Get a system summary with controller info and AP/client counts.

            Aggregates the controller identity (name, model, version, uptime)
            with live counts of APs (total / online / offline), clients, zones
            and WLANs, computed from the query API.

            Returns:
                JSON with controller details and aggregate counts.
            """
            c = get_client()
            controller, ap_q, client_q, zone_q, wlan_q = await asyncio.gather(
                c.get("controller"),
                c.post("query/ap", data={"page": 1, "limit": 1}),
                c.post("query/client", data={"page": 1, "limit": 1}),
                c.post("query/zone", data={"page": 1, "limit": 1000}),
                c.post("query/wlan", data={"page": 1, "limit": 1}),
            )

            def _total(r: Any) -> int:
                return r.get("totalCount", 0) if isinstance(r, dict) else 0

            zones = zone_q.get("list", []) if isinstance(zone_q, dict) else []
            online_aps = sum(z.get("apCountOnline", 0) or 0 for z in zones)
            offline_aps = sum(z.get("apCountOffline", 0) or 0 for z in zones)

            # /controller returns a paginated list in vSZ; take the first entry.
            ctrl: dict[str, Any] = {}
            if isinstance(controller, dict):
                lst = controller.get("list")
                if isinstance(lst, list) and lst:
                    ctrl = lst[0]
                else:
                    ctrl = controller
            summary = {
                "controller": {
                    "name": ctrl.get("name") or ctrl.get("hostName"),
                    "model": ctrl.get("model"),
                    "version": ctrl.get("version"),
                    "uptime_seconds": ctrl.get("uptimeInSec"),
                    "management_ip": ctrl.get("managementIp"),
                },
                "counts": {
                    "total_aps": _total(ap_q),
                    "online_aps": online_aps,
                    "offline_aps": offline_aps,
                    "total_clients": _total(client_q),
                    "total_zones": _total(zone_q),
                    "total_wlans": _total(wlan_q),
                },
            }
            return to_json(summary)

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