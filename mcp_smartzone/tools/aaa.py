"""
SmartZone authentication / AAA tools (read-only).

Covers authentication server listing and details.
"""
import logging

from mcp.server.fastmcp import FastMCP

from mcp_smartzone.api.client import get_client
from mcp_smartzone.tools._util import to_json

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP) -> None:
    """Register all SmartZone AAA / authentication tools."""

    @mcp.tool()
    async def smartzone_list_auth_servers() -> str:
        """List all authentication (AAA) servers.

        Returns:
            JSON list of RADIUS/TACACS+ authentication servers.
        """
        result = await get_client().get("services/auth/radius")
        return to_json(result)

    @mcp.tool()
    async def smartzone_get_auth_server(server_id: str) -> str:
        """Get details of a specific authentication server.

        Args:
            server_id: Auth server UUID.

        Returns:
            JSON with the authentication server configuration.
        """
        result = await get_client().get(f"services/auth/radius/{server_id}")
        return to_json(result)