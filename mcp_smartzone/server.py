"""
mcp-smartzone — read-only FastMCP server for the Ruckus SmartZone (vSZ)
wireless controller.

The controller connection is read from ``config.yaml`` (see
``mcp_smartzone.api.config`` for environment overrides).

Default transport is **streamable HTTP** on ``0.0.0.0:5754``, so MCP
clients can connect to ``http://<IP>:5754/mcp``.

Usage
-----
Foreground (streamable HTTP, default)::

    mcp-smartzone

Background daemon (detached, PID + log files in the user data dir)::

    mcp-smartzone --daemon
    mcp-smartzone --stop

Other options::

    mcp-smartzone --transport sse --host 0.0.0.0 --port 5754
    mcp-smartzone --transport stdio
    mcp-smartzone --config /path/to/config.yaml

Security (HTTP transports only)
-------------------------------
* If ``MCP_API_KEY`` is set, every request must carry
  ``Authorization: ******
* If ``MCP_ALLOWED_IPS`` is set (comma-separated CIDR list), requests
  from addresses outside the allowlist are rejected with HTTP 403.
"""
import argparse
import ipaddress
import logging
import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# load_dotenv FIRST — sub-modules must see .env values at import time.
load_dotenv()

from fastmcp import FastMCP  # noqa: E402

import mcp_smartzone as _pkg  # noqa: E402
from mcp_smartzone.api.config import (  # noqa: E402
    APP_ROOT,
    SERVER_NAME,
    load_config,
    user_data_dir,
)
from mcp_smartzone.tools import register_all_tools  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 5754
DEFAULT_TRANSPORT = "streamable-http"

# Per-user data dir — holds the daemon PID file and log file
DATA_DIR = user_data_dir()
PID_FILE = DATA_DIR / f"{SERVER_NAME}.pid"
LOG_FILE = DATA_DIR / f"{SERVER_NAME}.log"

# The daemon child runs ``python -m mcp_smartzone``; when running from a
# source checkout the package is only importable from the source root,
# while an installed (pip/pipx) package works from any directory.
_PKG_DIR = str(Path(_pkg.__file__).resolve()).replace(os.sep, "/")
DAEMON_CWD = str(DATA_DIR) if "/site-packages/" in _PKG_DIR else str(APP_ROOT)

# ---------------------------------------------------------------------------
# Logging — stderr ONLY, never stdout (stdout is reserved for STDIO transport)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog=SERVER_NAME,
        description="Read-only MCP server for the Ruckus SmartZone (vSZ) controller.",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="run the server in the background (detached process; "
             f"PID in {PID_FILE.name}, logs in {LOG_FILE.name})",
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="stop the background daemon started with --daemon",
    )
    parser.add_argument(
        "--transport",
        choices=["streamable-http", "sse", "stdio"],
        default=os.getenv("MCP_TRANSPORT", DEFAULT_TRANSPORT),
        help="MCP transport (default: %(default)s)",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_HOST", DEFAULT_HOST),
        help="bind address for HTTP transports (default: %(default)s)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_PORT", str(DEFAULT_PORT))),
        help="bind port for HTTP transports (default: %(default)s)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="path to config.yaml (default: auto-discovered)",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Daemon management
# ---------------------------------------------------------------------------

def _pid_alive(pid: int) -> bool:
    """Return True if a process with *pid* is currently running."""
    if os.name == "nt":
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True,
        ).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _read_pid() -> int | None:
    """Read the daemon PID from the PID file (None if absent/stale)."""
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return None
    return pid if _pid_alive(pid) else None


def start_daemon(args: argparse.Namespace) -> int:
    """Spawn the server as a detached background process."""
    existing = _read_pid()
    if existing is not None:
        print(f"mcp-smartzone is already running (PID {existing}).")
        print(f"Stop it first with: mcp-smartzone --stop")
        return 1

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "mcp_smartzone",
        "--transport", args.transport,
        "--host", args.host,
        "--port", str(args.port),
    ]
    if args.config:
        cmd += ["--config", args.config]

    log_fh = open(LOG_FILE, "a", encoding="utf-8")
    kwargs: dict[str, Any] = dict(
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        cwd=DAEMON_CWD,
        close_fds=True,
    )
    if os.name == "nt":
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        )
    else:
        kwargs["start_new_session"] = True

    proc = subprocess.Popen(cmd, **kwargs)
    log_fh.close()
    PID_FILE.write_text(str(proc.pid))

    # Wait briefly for the server to come up (or die).
    for _ in range(20):
        if proc.poll() is not None:
            break
        time.sleep(0.25)

    if proc.poll() is not None:
        PID_FILE.unlink(missing_ok=True)
        print(f"Daemon failed to start (exit code {proc.returncode}).")
        print(f"Check the log: {LOG_FILE}")
        return 1

    print(f"mcp-smartzone daemon started (PID {proc.pid}).")
    if args.transport != "stdio":
        print(f"  MCP endpoint: http://<IP>:{args.port}/mcp")
    print(f"  Log file:     {LOG_FILE}")
    print(f"  Stop with:    mcp-smartzone --stop")
    return 0


def stop_daemon() -> int:
    """Stop the background daemon (if running)."""
    pid = _read_pid()
    if pid is None:
        print("No running mcp-smartzone daemon found.")
        PID_FILE.unlink(missing_ok=True)
        return 0

    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
        )
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    for _ in range(20):
        if not _pid_alive(pid):
            break
        time.sleep(0.25)

    PID_FILE.unlink(missing_ok=True)
    if _pid_alive(pid):
        print(f"Warning: process {pid} is still alive after stop request.")
        return 1
    print(f"mcp-smartzone daemon stopped (PID {pid}).")
    return 0


# ---------------------------------------------------------------------------
# Pure-ASGI security middleware (streaming-safe: no response buffering)
# ---------------------------------------------------------------------------

class _SecurityMiddleware:
    """ASGI middleware enforcing API-key and IP-allowlist checks.

    Implemented as a pure ASGI callable so that streaming responses
    (SSE, chunked HTTP) pass through without any buffering.
    """

    def __init__(
        self,
        app: Any,
        api_key: str,
        allowed_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network],
    ) -> None:
        self.app = app
        self.api_key = api_key
        self.allowed_networks = allowed_networks

    async def __call__(
        self,
        scope: dict,
        receive: Callable,
        send: Callable,
    ) -> None:
        """Handle an ASGI request."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # --- IP allowlist check ---
        if self.allowed_networks:
            client = scope.get("client")
            client_host: str | None = client[0] if client else None

            if not client_host:
                await self._respond(scope, send, 403, "Forbidden: no client IP")
                return
            try:
                client_ip = ipaddress.ip_address(client_host)
                if not any(client_ip in net for net in self.allowed_networks):
                    logger.warning(
                        "Rejected request from %s: not in MCP_ALLOWED_IPS",
                        client_host,
                    )
                    await self._respond(scope, send, 403, "Forbidden: IP not allowed")
                    return
            except ValueError:
                await self._respond(scope, send, 403, "Forbidden: invalid client IP")
                return

        # --- API-key check ---
        if self.api_key:
            headers: dict[bytes, bytes] = dict(scope.get("headers", []))
            auth_bytes = headers.get(b"authorization", b"")
            auth_header = auth_bytes.decode("latin-1", errors="replace")

            if not auth_header.startswith("Bearer "):
                await self._respond(scope, send, 401, "Unauthorized: missing ******")
                return

            token = auth_header[len("Bearer "):].strip()
            if token != self.api_key:
                await self._respond(scope, send, 401, "Unauthorized: invalid API key")
                return

        await self.app(scope, receive, send)

    @staticmethod
    async def _respond(
        scope: dict,
        send: Callable,
        status: int,
        body: str,
    ) -> None:
        """Send a minimal HTTP error response."""
        encoded = body.encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"text/plain; charset=utf-8"),
                    (b"content-length", str(len(encoded)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": encoded, "more_body": False})


def _build_allowed_networks() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """Parse ``MCP_ALLOWED_IPS`` into a list of network objects."""
    raw = os.getenv("MCP_ALLOWED_IPS", "").strip()
    if not raw:
        return []

    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for cidr in raw.split(","):
        cidr = cidr.strip()
        if not cidr:
            continue
        try:
            networks.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError:
            logger.warning("Invalid CIDR in MCP_ALLOWED_IPS: %r — entry ignored", cidr)
    return networks


def _apply_security(app: Any) -> Any:
    """Wrap *app* with security middleware when auth is configured.

    If neither ``MCP_API_KEY`` nor ``MCP_ALLOWED_IPS`` are set the
    original app is returned unchanged (zero overhead).
    """
    api_key = os.getenv("MCP_API_KEY", "").strip()
    allowed_networks = _build_allowed_networks()

    if not api_key and not allowed_networks:
        logger.debug(
            "No MCP_API_KEY / MCP_ALLOWED_IPS configured — security middleware skipped"
        )
        return app

    logger.info(
        "Security middleware enabled: api_key=%s, allowed_networks=%d entries",
        "yes" if api_key else "no",
        len(allowed_networks),
    )
    return _SecurityMiddleware(app, api_key, allowed_networks)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Start the mcp-smartzone server.

    * ``--stop``   → stop the background daemon
    * ``--daemon`` → spawn the server detached and return
    * otherwise    → run in the foreground with the selected transport
    """
    args = parse_args()

    if args.stop:
        sys.exit(stop_daemon())
    if args.daemon:
        sys.exit(start_daemon(args))

    if args.config:
        os.environ["SMARTZONE_CONFIG"] = args.config

    # Fail fast on missing/invalid controller configuration.
    try:
        cfg = load_config()
    except RuntimeError as exc:
        logger.error("%s", exc)
        sys.exit(1)

    mcp = FastMCP(SERVER_NAME)
    register_all_tools(mcp)

    transport = args.transport.strip().lower()
    logger.info(
        "Starting %s (transport=%s, controller=%s)",
        SERVER_NAME, transport, cfg.host,
    )

    if transport == "stdio":
        mcp.run(transport="stdio")
        return

    if transport not in ("sse", "streamable-http"):
        logger.error(
            "Unknown transport %r — expected stdio, sse or streamable-http",
            transport,
        )
        sys.exit(1)

    # HTTP transports: build Starlette app, apply security, serve via uvicorn.
    import uvicorn

    mcp_app = mcp.http_app(transport=transport)
    secured_app = _apply_security(mcp_app)

    endpoint = "/mcp" if transport == "streamable-http" else "/sse"
    logger.info(
        "Uvicorn listening on %s:%d (transport=%s) — MCP endpoint: %s",
        args.host, args.port, transport, endpoint,
    )
    uvicorn.run(
        secured_app,
        host=args.host,
        port=args.port,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )


if __name__ == "__main__":
    main()