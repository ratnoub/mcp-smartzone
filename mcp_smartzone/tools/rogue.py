"""
SmartZone rogue AP tools (read-only).

Covers listing detected rogue APs.
"""
import json
import logging
from typing import Any, Optional

from fastmcp import FastMCP

from mcp_smartzone.api.client import get_client
from mcp_smartzone.tools._util import to_json

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP) -> None:
    """Register all SmartZone rogue-AP tools."""

    @mcp.tool()
    async def smartzone_list_rogue_aps(
        filters: Optional[str] = None,
    ) -> str:
        """List detected rogue access points.

        Args:
            filters: JSON string of filter criteria.

        Returns:
            JSON list of detected rogue APs.
        """
        body: dict[str, Any] = {}
        if filters:
            try:
                body["filters"] = json.loads(filters)
            except json.JSONDecodeError:
                return "ERROR: 'filters' must be valid JSON"
        result = await get_client().post("query/roguesInfoList", data=body)
        return to_json(result)