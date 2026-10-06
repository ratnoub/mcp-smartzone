"""
SmartZone tools package — aggregates all read-only tool modules.

Each sub-module exposes a ``register_tools(mcp)`` function that is
called by ``register_all_tools()`` to register every SmartZone tool
on the FastMCP server instance.
"""
from mcp.server.fastmcp import FastMCP

from mcp_smartzone.tools import (
    aaa,
    alarms,
    aps,
    block_clients,
    clients,
    dhcp,
    domains,
    monitoring,
    rogue,
    system,
    wlans,
    zones,
)

_MODULES = [
    system,
    zones,
    aps,
    wlans,
    clients,
    alarms,
    domains,
    aaa,
    dhcp,
    monitoring,
    block_clients,
    rogue,
]


def register_all_tools(mcp: FastMCP) -> None:
    """Register every SmartZone (read-only) tool on *mcp*."""
    for module in _MODULES:
        module.register_tools(mcp)