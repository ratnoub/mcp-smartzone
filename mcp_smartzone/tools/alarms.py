"""
SmartZone alarm and event tools (read-only).

Covers alarm listing and details.
"""
import json
import logging

from fastmcp import FastMCP

from mcp_smartzone.api.client import get_client
from mcp_smartzone.tools._util import to_json

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP) -> None:
    """Register all SmartZone alarm tools."""

    @mcp.tool()
    async def smartzone_list_alarms() -> str:
        """List active alarms on the SmartZone controller.

        Returns:
            JSON with the active alarm list.
        """
        result = await get_client().post("alert/alarm/list", data={})
        return to_json(result)

    @mcp.tool()
    async def smartzone_get_alarm(alarm_id: str) -> str:
        """Get details of a specific alarm.

        Fetches the alarm list and filters for the matching alarm ID,
        as the SmartZone API does not expose a single-alarm GET endpoint.

        Args:
            alarm_id: Alarm UUID (e.g. 'Alarm_303_...').

        Returns:
            JSON with the matching alarm, or an error if not found.
        """
        result = await get_client().post("alert/alarm/list", data={})
        if isinstance(result, str):
            return result
        if isinstance(result, dict) and result.get("list"):
            for alarm in result["list"]:
                if alarm.get("id") == alarm_id or alarm.get("alarmUUID") == alarm_id:
                    return json.dumps(alarm, indent=2, ensure_ascii=False)
            return f"ERROR: Alarm '{alarm_id}' not found"
        return to_json(result)