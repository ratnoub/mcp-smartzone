"""Async HTTP client for the Ruckus SmartZone (vSZ) public API.

Authentication uses the *serviceTicket* pattern: a ticket is obtained
once via ``POST /serviceTicket`` and then sent as the ``serviceTicket``
**query parameter** on every data request (NOT as an ``Authorization``
header — that yields 401/403).

Tickets expire after ~270 s, so the client caches the ticket and
refreshes it automatically before expiry, and again on 401/403.

Usage::

    from mcp_smartzone.api.client import get_client

    client = get_client()
    result = await client.get("controller")
    result = await client.post("query/client", data={...})
"""
from __future__ import annotations

import logging
import time
import warnings
from typing import Any, Optional

import httpx

from mcp_smartzone.api.config import SmartzoneConfig, load_config

logger = logging.getLogger(__name__)

# Suppress SSL-related warnings for self-signed certs (verify=False)
warnings.filterwarnings("ignore", message=".*Unverified HTTPS.*")

# Server-side ticket lifetime is ~270 s; refresh a bit earlier.
TICKET_TTL_S = 240.0


class SmartzoneAuthError(RuntimeError):
    """Raised when the controller rejects the credentials."""


class SmartzoneClient:
    """Async, ticket-caching client for one SmartZone controller.

    All paths are *relative* to the configured API base path, e.g.
    ``"controller"``, ``"query/client"``, ``"rkszones/{id}"``.
    """

    def __init__(self, config: SmartzoneConfig) -> None:
        self._config = config
        self._http: Optional[httpx.AsyncClient] = None
        self._ticket: Optional[str] = None
        self._ticket_obtained_at: float = 0.0

    # -- lifecycle ------------------------------------------------------
    def _client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                base_url=self._config.base_url,
                verify=self._config.verify_ssl,
                timeout=self._config.timeout,
                headers={"Content-Type": "application/json;charset=UTF-8"},
            )
        return self._http

    async def close(self) -> None:
        """Close the underlying HTTP client (best effort)."""
        if self._http is not None and not self._http.is_closed:
            await self._http.aclose()
        self._http = None
        self._ticket = None

    # -- authentication ---------------------------------------------------
    async def _login(self) -> None:
        """Obtain a fresh service ticket from the controller."""
        cfg = self._config
        resp = await self._client().post(
            "serviceTicket",
            json={"username": cfg.username, "password": cfg.password},
        )
        if resp.status_code >= 400:
            raise SmartzoneAuthError(
                f"login failed: HTTP {resp.status_code} — {resp.text[:200]}"
            )
        data = resp.json()
        ticket = data.get("serviceTicket") if isinstance(data, dict) else None
        if not ticket:
            raise SmartzoneAuthError(
                f"login failed: no serviceTicket in response: {str(data)[:200]}"
            )
        self._ticket = ticket
        self._ticket_obtained_at = time.monotonic()
        logger.debug("service ticket obtained from %s", cfg.host)

    async def _ensure_ticket(self) -> str:
        """Return a valid ticket, refreshing it when close to expiry."""
        if self._ticket and (time.monotonic() - self._ticket_obtained_at) < TICKET_TTL_S:
            return self._ticket
        await self._login()
        assert self._ticket is not None
        return self._ticket

    # -- requests ---------------------------------------------------------
    async def request(
        self,
        method: str,
        path: str,
        data: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any] | list | str:
        """Execute an authenticated API request.

        Args:
            method: HTTP method (GET, POST, ...).
            path: Endpoint path relative to the API base path.
            data: JSON body for POST/PUT/PATCH requests.
            params: Extra query parameters (serviceTicket is added
                automatically).

        Returns:
            Parsed JSON response (dict or list), or an ``"ERROR: ..."``
            string on failure.
        """
        try:
            ticket = await self._ensure_ticket()
            query: dict[str, Any] = {"serviceTicket": ticket}
            if params:
                query.update(params)

            for attempt in (1, 2):
                resp = await self._client().request(
                    method, path, json=data, params=query
                )
                if resp.status_code in (401, 403) and attempt == 1:
                    # Ticket may have expired server-side — refresh once.
                    logger.info(
                        "ticket rejected (HTTP %s) on %s %s — refreshing",
                        resp.status_code, method, path,
                    )
                    self._ticket = None
                    ticket = await self._ensure_ticket()
                    query["serviceTicket"] = ticket
                    continue
                if resp.status_code >= 400:
                    logger.error(
                        "API %s %s -> %s: %s",
                        method, path, resp.status_code, resp.text[:300],
                    )
                    return f"ERROR: API {resp.status_code} — {resp.text[:500]}"
                if resp.status_code == 204 or not resp.content:
                    return {"success": True, "status_code": resp.status_code}
                return resp.json()
        except SmartzoneAuthError as exc:
            logger.error("Authentication failed: %s", exc)
            return f"ERROR: Authentication failed — {exc}"
        except Exception as exc:  # noqa: BLE001 — surface as tool error string
            logger.error("Request error on %s %s: %s", method, path, exc)
            return f"ERROR: {exc}"

    # -- convenience wrappers ----------------------------------------------
    async def get(
        self, path: str, params: Optional[dict[str, Any]] = None
    ) -> dict[str, Any] | list | str:
        """GET request to the SmartZone API."""
        return await self.request("GET", path, params=params)

    async def post(
        self,
        path: str,
        data: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any] | list | str:
        """POST request to the SmartZone API."""
        return await self.request("POST", path, data=data, params=params)


# ---------------------------------------------------------------------------
# Shared singleton — one client (and one cached ticket) for the whole server
# ---------------------------------------------------------------------------
_client: Optional[SmartzoneClient] = None


def get_client() -> SmartzoneClient:
    """Return the process-wide :class:`SmartzoneClient` (lazy init)."""
    global _client
    if _client is None:
        _client = SmartzoneClient(load_config())
    return _client