"""
SmartZone block client tools (read-only).

Covers listing blocked (blacklisted) clients.
"""
import logging

from mcp.server.fastmcp import FastMCP

from mcp_smartzone.api.client import get_client
from mcp_smartzone.tools._util import to_json

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP) -> None:
    """Register all SmartZone block-client tools."""

    @mcp.tool()
    async def smartzone_list_blocked_clients() -> str:
        """List all blocked (blacklisted) clients.

        Returns:
            JSON list of blocked client entries (mac, description, ...).
        """
        result = await get_client().post("blockClient/query", data={})
        return to_json(result)