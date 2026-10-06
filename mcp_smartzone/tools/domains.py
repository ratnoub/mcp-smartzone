"""
SmartZone domain tools (read-only).

Covers domain listing and details.
"""
import logging

from fastmcp import FastMCP

from mcp_smartzone.api.client import get_client
from mcp_smartzone.tools._util import to_json

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP) -> None:
    """Register all SmartZone domain tools."""

    @mcp.tool()
    async def smartzone_list_domains() -> str:
        """List all administration domains.

        Returns:
            JSON list of domains (id, name, description, ...).
        """
        result = await get_client().get("domains")
        return to_json(result)

    @mcp.tool()
    async def smartzone_get_domain(domain_id: str) -> str:
        """Get details of a specific domain.

        Args:
            domain_id: Domain UUID.

        Returns:
            JSON with the domain configuration.
        """
        result = await get_client().get(f"domains/{domain_id}")
        return to_json(result)