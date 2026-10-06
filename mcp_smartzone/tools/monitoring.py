"""
SmartZone monitoring and query tools (read-only).

Covers the generic query API, AP statistics and WLAN statistics.
"""
import asyncio
import json
import logging
from typing import Any, Optional

from fastmcp import FastMCP

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

                Use this to search any SmartZone resource by free text (MAC, IP,
                hostname, SSID, username, ...) or by structured filters.

                Args:
                    query_type: Resource type to query. Common values:
                        ``ap``, ``client``, ``wlan``, ``zone``, ``dpsk``, ``user``.
                    filters: Optional JSON string of filter criteria, e.g.
                        ``[{"type": "ZONE", "value": "Perpustakaan"}]``.
                        Valid filter types depend on the resource (for ``ap``:
                        CONTROLBLADE, DOMAIN, ZONE, APGROUP, AP, INDOORMAP,
                        SYNCEDSTATUS, REGISTRATIONSTATE).
                    full_text_search: Optional free-text search term. Matches
                        against names, MAC addresses, IPs, hostnames, SSIDs, etc.
                    page: Page number (1-indexed).
                    limit: Results per page (max 1000).

                Returns:
                    JSON with the query results, ``totalCount`` and pagination info.
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
            """Get full statistics for a specific AP.

            Combines the AP operational summary (connection state, client count,
            uptime, radio channels, location) with rich traffic statistics
            (per-band throughput, airtime, noise, latency, retries, MCS rates).

            Args:
                ap_mac: AP MAC address (e.g. 00:11:22:33:44:55).

            Returns:
                JSON with ``operational`` and ``traffic`` sections.
            """
            c = get_client()
            op, q = await asyncio.gather(
                c.get(f"aps/{ap_mac}/operational/summary"),
                c.post(
                    "query/ap",
                    data={
                        "page": 1,
                        "limit": 1,
                        "filters": [{"type": "AP", "value": ap_mac}],
                    },
                ),
            )

            traffic = None
            if isinstance(q, dict) and q.get("list"):
                a = q["list"][0]
                traffic = {
                    k: a.get(k)
                    for k in (
                        "apMac", "deviceName", "status",
                        "numClients", "numClients24G", "numClients5G", "numClients6G",
                        "tx", "rx", "txRx",
                        "tx24G", "rx24G", "tx50G", "rx50G", "tx6G", "rx6G",
                        "airtime24G", "airtime5G", "airtime6G",
                        "noise24G", "noise5G", "noise6G",
                        "latency24G", "latency50G", "latency6G",
                        "retry24G", "retry5G", "retry6G",
                        "medianTxRadioMCSRate24G", "medianTxRadioMCSRate50G",
                        "medianTxRadioMCSRate6G",
                        "uptime", "zoneName", "firmwareVersion", "model", "ip",
                    )
                }

            return to_json({"operational": op, "traffic": traffic})

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