"""
SmartZone reporting tools (read-only).

Provides top-N rankings for APs, WLANs and clients, useful for
generating reports (e.g. "top 10 APs by clients", "top WLANs by
traffic", "top clients by data usage").
"""
import logging
from typing import Any, Callable

from fastmcp import FastMCP

from mcp_smartzone.api.client import get_client
from mcp_smartzone.tools._util import to_json

logger = logging.getLogger(__name__)

_PAGE_LIMIT = 1000


async def _fetch_all(
    c: Any,
    endpoint: str,
    max_scan: int,
) -> list[dict[str, Any]]:
    """Fetch up to *max_scan* items from a paginated query endpoint."""
    items: list[dict[str, Any]] = []
    page = 1
    while len(items) < max_scan:
        r = await c.post(endpoint, data={"page": page, "limit": _PAGE_LIMIT})
        if not isinstance(r, dict):
            break
        batch = r.get("list", [])
        if not batch:
            break
        items.extend(batch)
        if not r.get("hasMore"):
            break
        page += 1
    return items[:max_scan]


def register_tools(mcp: FastMCP) -> None:
    """Register all SmartZone reporting tools."""

    @mcp.tool()
    async def smartzone_top_aps(
        sort_by: str = "clients",
        limit: int = 10,
        max_scan: int = 2000,
    ) -> str:
        """Get the top N APs ranked by client count or traffic.

        Useful for reports such as "top 10 most-loaded APs".

        Args:
            sort_by: Rank by ``clients`` (connected clients) or
                ``traffic`` (total tx+rx bytes).
            limit: Number of APs to return (default 10).
            max_scan: Maximum APs to scan before ranking (default 2000,
                covers most deployments).

        Returns:
            JSON with the ranking key, number of APs scanned, and the
            top APs (name, MAC, zone, status, clients, traffic).
        """
        c = get_client()
        aps = await _fetch_all(c, "query/ap", max_scan)
        if sort_by == "traffic":
            key: Callable[[dict[str, Any]], float] = lambda a: a.get("txRx") or 0
        else:
            key = lambda a: a.get("numClients") or 0
        top = sorted(aps, key=key, reverse=True)[:limit]
        result = [
            {
                "name": a.get("deviceName"),
                "mac": a.get("apMac"),
                "zone": a.get("zoneName"),
                "status": a.get("status"),
                "clients": a.get("numClients"),
                "traffic_bytes": a.get("txRx"),
                "airtime_24g": a.get("airtime24G"),
                "noise_24g": a.get("noise24G"),
            }
            for a in top
        ]
        return to_json({"sort_by": sort_by, "scanned": len(aps), "top": result})

    @mcp.tool()
    async def smartzone_top_wlans(
        sort_by: str = "clients",
        limit: int = 10,
        max_scan: int = 500,
    ) -> str:
        """Get the top N WLANs ranked by client count or traffic.

        Useful for reports such as "top 10 most-used SSIDs".

        Args:
            sort_by: Rank by ``clients`` (connected clients) or
                ``traffic`` (total traffic bytes).
            limit: Number of WLANs to return (default 10).
            max_scan: Maximum WLANs to scan before ranking (default 500).

        Returns:
            JSON with the ranking key, number of WLANs scanned, and the
            top WLANs (name, SSID, zone, clients, traffic).
        """
        c = get_client()
        wlans = await _fetch_all(c, "query/wlan", max_scan)
        if sort_by == "traffic":
            key: Callable[[dict[str, Any]], float] = lambda w: w.get("traffic") or 0
        else:
            key = lambda w: w.get("clients") or 0
        top = sorted(wlans, key=key, reverse=True)[:limit]
        result = [
            {
                "name": w.get("name"),
                "ssid": w.get("ssid"),
                "zone": w.get("zoneName"),
                "domain": w.get("domainName"),
                "clients": w.get("clients"),
                "traffic_bytes": w.get("traffic"),
                "uplink_bytes": w.get("trafficUplink"),
                "downlink_bytes": w.get("trafficDownlink"),
            }
            for w in top
        ]
        return to_json({"sort_by": sort_by, "scanned": len(wlans), "top": result})

    @mcp.tool()
    async def smartzone_top_clients(
        sort_by: str = "traffic",
        limit: int = 10,
        max_scan: int = 2000,
    ) -> str:
        """Get the top N clients ranked by traffic or session duration.

        Useful for reports such as "top 10 heaviest data users".

        Note: clients are ranked over a sample of up to *max_scan* clients
        (the full client list can be very large). Increase *max_scan* for
        a more complete ranking.

        Args:
            sort_by: Rank by ``traffic`` (total tx+rx bytes) or
                ``session`` (longest-running sessions).
            limit: Number of clients to return (default 10).
            max_scan: Maximum clients to scan before ranking (default 2000).

        Returns:
            JSON with the ranking key, number of clients scanned, and the
            top clients (hostname, MAC, IP, SSID, AP, signal, traffic).
        """
        c = get_client()
        clients = await _fetch_all(c, "query/client", max_scan)
        if sort_by == "session":
            # Longest-running sessions = oldest sessionStartTime first.
            # Put missing timestamps last.
            def _session_key(cl: dict[str, Any]) -> tuple:
                ts = cl.get("sessionStartTime")
                # Treat both None and 0 as "no session start" -> rank last.
                return (1, 0) if not ts else (0, ts)

            top = sorted(clients, key=_session_key)[:limit]
        else:
            top = sorted(
                clients,
                key=lambda cl: cl.get("txRxBytes") or 0,
                reverse=True,
            )[:limit]
        result = [
            {
                "hostname": cl.get("hostname"),
                "mac": cl.get("clientMac"),
                "ip": cl.get("ipAddress"),
                "ssid": cl.get("ssid"),
                "ap": cl.get("apName"),
                "user": cl.get("userName"),
                "rssi": cl.get("rssi"),
                "snr": cl.get("snr"),
                "traffic_bytes": cl.get("txRxBytes"),
                "session_start": cl.get("sessionStartTime"),
            }
            for cl in top
        ]
        return to_json({"sort_by": sort_by, "scanned": len(clients), "top": result})