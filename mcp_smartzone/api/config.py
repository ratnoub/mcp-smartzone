"""Configuration loading for the SmartZone (vSZ) controller.

The controller connection is read from ``config.yaml``. The file is
discovered in this order:

1. ``--config <path>`` CLI flag (forwarded via ``SMARTZONE_CONFIG``)
2. ``SMARTZONE_CONFIG`` environment variable
3. User config directory (``~/.config/mcp-smartzone/`` on Linux/macOS,
   ``%APPDATA%\\mcp-smartzone\\`` on Windows)
4. ``./config.yaml`` in the current working directory
5. ``config.yaml`` next to the source tree (development only)

Example ``config.yaml``::

   smartzone:
     controller:
       host: "https://172.18.3.34:8443"
       base_path: "/wsg/api/public/v11_0/"
       username: "mcp"
       password: "..."

Every value can be overridden with an environment variable:

- ``SMARTZONE_CONFIG``     — explicit path to the YAML config file
- ``SMARTZONE_HOST``       — controller base URL (e.g. https://172.18.3.34:8443)
- ``SMARTZONE_BASE_PATH``  — API base path (e.g. /wsg/api/public/v11_0/)
- ``SMARTZONE_USERNAME``   — API username
- ``SMARTZONE_PASSWORD``   — API password
- ``SMARTZONE_VERIFY_SSL`` — verify TLS certificates (default: false)
- ``SMARTZONE_TIMEOUT``    — HTTP timeout in seconds (default: 30)
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

SERVER_NAME = "mcp-smartzone"
DEFAULT_TIMEOUT = 30.0
DEFAULT_BASE_PATH = "/wsg/api/public/v11_0/"

# Source tree root — the directory that contains the mcp_smartzone package
# (only meaningful when running from a checkout, not from an install).
APP_ROOT = Path(__file__).resolve().parent.parent.parent


def user_config_dir() -> Path:
    """Per-user configuration directory for mcp-smartzone."""
    if os.name == "nt":
        base = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / SERVER_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / SERVER_NAME
    base = os.getenv("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / SERVER_NAME


def user_data_dir() -> Path:
    """Per-user data directory for runtime files (PID, logs)."""
    if os.name == "nt":
        base = os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / SERVER_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / SERVER_NAME
    base = os.getenv("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / SERVER_NAME


@dataclass(frozen=True)
class SmartzoneConfig:
    """Connection settings for one SmartZone controller."""

    host: str
    base_path: str
    username: str
    password: str
    verify_ssl: bool = False
    timeout: float = DEFAULT_TIMEOUT

    @property
    def base_url(self) -> str:
        """Full API base URL with a trailing slash (for relative joins)."""
        host = self.host
        if not host.startswith(("http://", "https://")):
            host = f"https://{host}"
        return f"{host.rstrip('/')}/{self.base_path.strip('/')}/"


def _find_config_file() -> Path | None:
    """Locate config.yaml (env override first, then user dir, cwd, source root)."""
    env_path = os.getenv("SMARTZONE_CONFIG", "").strip()
    if env_path:
        p = Path(env_path).expanduser()
        return p if p.is_file() else None
    candidates = (
        user_config_dir() / "config.yaml",
        Path.cwd() / "config.yaml",
        APP_ROOT / "config.yaml",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def load_config() -> SmartzoneConfig:
    """Load controller settings from config.yaml + environment overrides.

    Raises:
        RuntimeError: If host, username or password cannot be resolved.
    """
    data: dict = {}
    cfg_file = _find_config_file()
    if cfg_file is not None:
        with open(cfg_file, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
            data = (raw.get("smartzone", {}) or {}).get("controller", {}) or {}

    host = os.getenv("SMARTZONE_HOST", "").strip() or str(data.get("host", "")).strip()
    base_path = (
        os.getenv("SMARTZONE_BASE_PATH", "").strip()
        or str(data.get("base_path", "")).strip()
        or DEFAULT_BASE_PATH
    )
    username = os.getenv("SMARTZONE_USERNAME", "").strip() or str(data.get("username", "")).strip()
    password = os.getenv("SMARTZONE_PASSWORD", "").strip() or str(data.get("password", "")).strip()
    verify_ssl = os.getenv("SMARTZONE_VERIFY_SSL", "false").strip().lower() in ("true", "1", "yes")
    try:
        timeout = float(os.getenv("SMARTZONE_TIMEOUT", "").strip() or DEFAULT_TIMEOUT)
    except ValueError:
        timeout = DEFAULT_TIMEOUT

    if not host or not username or not password:
        raise RuntimeError(
            "SmartZone controller is not configured. Provide host/username/password "
            "in config.yaml (smartzone.controller) or via SMARTZONE_* environment "
            "variables (SMARTZONE_HOST, SMARTZONE_USERNAME, SMARTZONE_PASSWORD)."
        )
    return SmartzoneConfig(
        host=host,
        base_path=base_path,
        username=username,
        password=password,
        verify_ssl=verify_ssl,
        timeout=timeout,
    )