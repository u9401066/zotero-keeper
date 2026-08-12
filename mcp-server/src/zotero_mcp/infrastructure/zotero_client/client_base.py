"""
Zotero Client - Base Classes and Configuration

Provides:
- ZoteroConfig: Connection configuration
- ZoteroConnectionError, ZoteroAPIError: Exception types
- ZoteroClientBase: HTTP request handling
"""

import asyncio
import json
import os
from collections.abc import AsyncIterable, Mapping
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from ipaddress import ip_address
from typing import Any

import httpx


class ZoteroConnectionError(Exception):
    """Raised when connection to Zotero fails"""

    pass


class ZoteroAPIError(Exception):
    """Raised when Zotero API returns an error"""

    def __init__(
        self,
        message: str,
        status_code: int = 0,
        response_text: str = "",
        response_headers: Mapping[str, str] | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
        header_items = response_headers.items() if isinstance(response_headers, Mapping) else ()
        self.response_headers = {str(key): str(value) for key, value in header_items}
        self.retry_after = self._response_header("Retry-After")
        self.server_id = self._response_header("Zotero-Server-ID")

    def _response_header(self, name: str) -> str | None:
        lower_name = name.lower()
        for key, value in self.response_headers.items():
            if key.lower() == lower_name:
                return value
        return None


@dataclass
class ZoteroConfig:
    """Zotero connection configuration"""

    host: str = field(default_factory=lambda: os.getenv("ZOTERO_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("ZOTERO_PORT", "23119")))
    timeout: float = field(default_factory=lambda: float(os.getenv("ZOTERO_TIMEOUT", "30")))

    @property
    def base_url(self) -> str:
        host = self.host.strip()
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        return f"http://{host}:{self.port}"

    @property
    def host_header(self) -> str:
        """Legacy Host override retained for compatibility tests."""
        return f"127.0.0.1:{self.port}"

    @property
    def is_loopback(self) -> bool:
        """Whether ``host`` is a literal loopback address or ``localhost``.

        Security-sensitive Local API writes intentionally do not resolve DNS
        names. Zotero's local HTTP service is only safe on the same machine.
        """
        host = self.host.strip().lower()
        if host == "localhost":
            return True
        try:
            return ip_address(host.strip("[]")).is_loopback
        except ValueError:
            return False

    @property
    def needs_host_header(self) -> bool:
        """Whether a legacy non-loopback configuration needs a Host override.

        Zotero's local HTTP service must not be exposed or forwarded to a
        network. Production configurations should use loopback.
        """
        return not self.is_loopback


@dataclass(frozen=True)
class LocalOperationBinding:
    """Task-local Zotero identity and credential snapshot for one mutation."""

    server_token: Token[str | None]
    key_token: Token[str | None]
    remembered_token: Token[bool]


class ZoteroClientBase:
    """
    Base HTTP Client for Zotero

    Handles HTTP communication with Zotero's built-in Local API.
    """

    def __init__(self, config: ZoteroConfig | None = None):
        self.config = config or ZoteroConfig()
        self._client: httpx.AsyncClient | None = None
        # Zotero 10+ Local API security state. These values are deliberately
        # process-memory only and are cleared when the client is closed.
        self._local_api_version: str | None = None
        self._local_schema_version: str | None = None
        self._local_server_id: str | None = None
        self._local_api_key: str | None = None
        self._local_api_key_server_id: str | None = None
        self._local_api_key_remembered = False
        self._local_write_lock = asyncio.Lock()
        self._local_operation_lock = asyncio.Lock()
        self._operation_server_id: ContextVar[str | None] = ContextVar(
            f"zotero_operation_server_id_{id(self)}",
            default=None,
        )
        self._operation_api_key: ContextVar[str | None] = ContextVar(
            f"zotero_operation_api_key_{id(self)}",
            default=None,
        )
        self._operation_key_remembered: ContextVar[bool] = ContextVar(
            f"zotero_operation_key_remembered_{id(self)}",
            default=False,
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            headers = {"Content-Type": "application/json"}

            # Retain the historical override for compatibility. This does not
            # make a network-exposed Zotero Local API a supported deployment.
            if self.config.needs_host_header:
                headers["Host"] = self.config.host_header

            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                headers=headers,
                # Zotero's Local/Connector APIs are a loopback trust boundary.
                # Never inherit HTTP(S)_PROXY, ALL_PROXY, or netrc settings
                # that could disclose unauthenticated reads or a Local API key.
                trust_env=False,
                limits=httpx.Limits(
                    max_connections=10,
                    max_keepalive_connections=5,
                    keepalive_expiry=30,
                ),
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._local_api_version = None
        self._local_schema_version = None
        self._local_server_id = None
        self._local_api_key = None
        self._local_api_key_server_id = None
        self._local_api_key_remembered = False

    async def _request(
        self,
        method: str,
        path: str,
        json_data: Any = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        """Make HTTP request to Zotero API"""
        response = await self._request_raw(
            method,
            path,
            json_data=json_data,
            params=params,
            headers=headers,
        )

        # Parse JSON response
        if response.text:
            try:
                return response.json()
            except json.JSONDecodeError:
                return response.text
        return None

    @staticmethod
    def _is_bound_local_api_path(path: str) -> bool:
        """Whether a Local API request must be bound to the discovered server.

        ``GET /api/`` is deliberately unbound so it can discover a newly
        started Zotero instance.  Phase-two upload URLs are authorized by their
        one-time upload key and must not receive Local API credentials or
        identity headers.
        """
        return path.startswith("/api/") and path != "/api/" and not path.startswith("/api/local/uploads/")

    def _observe_local_api_response(self, path: str, response: httpx.Response) -> None:
        """Capture Zotero 10's instance identity and invalidate stale state.

        Zotero object/library versions are meaningful only within one
        ``Zotero-Server-ID``.  Observing the header before raising an HTTP error
        ensures a 412 from either authorization, reads, or writes cannot leave
        the client permanently pinned to a stale database identity.
        """
        if not path.startswith("/api/") or path.startswith("/api/local/uploads/"):
            return

        server_id = self._header_value(response.headers, "Zotero-Server-ID")
        api_version = self._header_value(response.headers, "Zotero-API-Version")
        schema_version = self._header_value(response.headers, "Zotero-Schema-Version")

        operation_server_id = self._operation_server_id.get()
        if operation_server_id is not None and self._is_bound_local_api_path(path):
            # A confirmed mutation owns an immutable task-local identity.  Its
            # responses must never rebind shared client state when another MCP
            # call discovers or authorizes a different Zotero database.
            if (server_id is not None and server_id != operation_server_id) or (response.status_code < 400 and server_id is None):
                raise ZoteroAPIError(
                    "Zotero Server-ID changed during the confirmed operation",
                    status_code=412,
                    response_text=response.text,
                    response_headers=response.headers,
                )
            return

        if path == "/api/" and response.status_code < 400 and (api_version != "3" or not server_id):
            # The root probe is authoritative.  A Zotero downgrade/profile
            # switch to a pre-write Local API must never leave a Zotero 10 key
            # or Server-ID reusable in this client instance.
            self._local_api_key = None
            self._local_api_key_server_id = None
            self._local_api_key_remembered = False
            self._local_api_version = None
            self._local_schema_version = None
            self._local_server_id = None
            return

        if path != "/api/" and response.status_code < 400 and self._local_server_id is not None and not server_id:
            # Zotero 10+ promises a Server-ID on every Local API response.  A
            # successful response without one means a pre-10 process/profile
            # has taken over the port.  Preserve read compatibility, but never
            # label that response with or reuse the stale Zotero 10 identity.
            self._local_api_key = None
            self._local_api_key_server_id = None
            self._local_api_key_remembered = False
            self._local_api_version = None
            self._local_schema_version = None
            self._local_server_id = None
            return

        if server_id:
            if self._local_server_id is not None and self._local_server_id != server_id:
                self._local_api_key = None
                self._local_api_key_server_id = None
                self._local_api_key_remembered = False
                # A mismatching response proves that the previous discovery
                # state is stale.  The next independent operation must perform
                # a fresh GET /api/; never retry the current request.
                self._local_api_version = None
                self._local_schema_version = None
            self._local_server_id = server_id

        # Only successful responses establish API/schema compatibility.  A
        # 412 commonly carries just the new Server-ID and must force discovery.
        if response.status_code < 400:
            if api_version:
                self._local_api_version = api_version
            if schema_version:
                self._local_schema_version = schema_version

    async def _request_raw(
        self,
        method: str,
        path: str,
        json_data: Any = None,
        params: dict[str, Any] | None = None,
        content: bytes | AsyncIterable[bytes] | None = None,
        data: Mapping[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Make HTTP request and return the raw response for header-aware probes.

        When ``content`` is provided the request is sent as a raw/streaming body
        (used by attachment endpoints). ``data`` sends form fields, and
        ``headers`` may override per-request values such as ``Content-Type``.
        """
        client = await self._get_client()

        try:
            if content is not None and data is not None:
                raise ValueError("content and data are mutually exclusive")

            request_headers = dict(headers or {})
            bound_server_id = self._operation_server_id.get() or self._local_server_id
            if self._is_bound_local_api_path(path) and bound_server_id:
                if not any(key.lower() == "zotero-server-id" for key in request_headers):
                    request_headers["Zotero-Server-ID"] = bound_server_id

            if content is not None:
                response = await client.request(
                    method=method,
                    url=path,
                    content=content,
                    params=params,
                    headers=request_headers,
                )
            elif data is not None:
                response = await client.request(
                    method=method,
                    url=path,
                    data=data,
                    params=params,
                    headers=request_headers,
                )
            else:
                response = await client.request(
                    method=method,
                    url=path,
                    json=json_data,
                    params=params,
                    headers=request_headers,
                )

            self._observe_local_api_response(path, response)

            # Check for error responses
            if response.status_code >= 400:
                raise ZoteroAPIError(
                    f"Zotero API error: {response.status_code}",
                    status_code=response.status_code,
                    response_text=response.text,
                    response_headers=response.headers,
                )

            return response

        except httpx.ConnectError as e:
            # Close and reset client on connection failure to prevent stale connections
            await self.close()
            raise ZoteroConnectionError(
                f"無法連接到 Zotero ({self.config.base_url})。\n"
                f"請確認:\n"
                f"1. Zotero 正在運行\n"
                f"2. Zotero Local API 已啟用\n"
                f"3. Keeper 與 Zotero 在同一主機，且 port {self.config.port} 僅限 loopback\n"
                f"Details: {e}"
            ) from e
        except httpx.TimeoutException as e:
            await self.close()
            raise ZoteroConnectionError(f"連接 Zotero 超時 ({self.config.timeout}s)") from e

    async def ping(self) -> bool:
        """Check if Zotero is running"""
        try:
            result = await self._request("GET", "/connector/ping")
            return "Zotero is running" in str(result)
        except Exception:
            return False

    @staticmethod
    def _header_value(headers: Any, name: str) -> str | None:
        """Read a response header from httpx.Headers or a plain dict."""
        if not headers:
            return None
        value = headers.get(name)
        if value is not None:
            return str(value)
        lower_name = name.lower()
        for key, header_value in headers.items():
            if str(key).lower() == lower_name:
                return str(header_value)
        return None

    async def get_capabilities(self) -> dict[str, Any]:
        """
        Probe Zotero's local HTTP capabilities without mutating the library.

        Zotero exposes useful version metadata on the connector ping response,
        while Local API read access can be disabled independently. Keep those
        statuses separate so callers can diagnose Zotero 9 security/port changes.
        """
        capabilities: dict[str, Any] = {
            "connected": False,
            "endpoint": self.config.base_url,
            "zotero_version": None,
            "connector_api_version": None,
            "local_api_readable": False,
            "local_api_version": None,
            "local_api_schema_version": None,
            "local_api_server_id": None,
            "local_api_write_available": False,
            "local_api_write_authorized": self._local_api_key is not None,
            "local_api_write_authorization_remembered": self._local_api_key_remembered,
            "connector_save_available": None,
            "supports_zotero_major_versions": [7, 8, 9, 10],
        }

        try:
            ping_response = await self._request_raw("GET", "/connector/ping")
        except ZoteroAPIError as e:
            capabilities.update(
                {
                    "connector_status_code": e.status_code,
                    "message": e.response_text or str(e),
                }
            )
            return capabilities

        capabilities["zotero_version"] = self._header_value(ping_response.headers, "X-Zotero-Version")
        capabilities["connector_api_version"] = self._header_value(
            ping_response.headers,
            "X-Zotero-Connector-API-Version",
        )
        capabilities["connected"] = "Zotero is running" in ping_response.text

        if not capabilities["connected"]:
            capabilities["message"] = "Zotero responded but returned unexpected content"
            return capabilities

        capabilities["message"] = "Zotero is running"

        try:
            local_response = await self._request_raw("GET", "/api/")
            capabilities["local_api_readable"] = True
            capabilities["local_api_version"] = self._header_value(local_response.headers, "Zotero-API-Version")
            capabilities["local_api_schema_version"] = self._header_value(
                local_response.headers,
                "Zotero-Schema-Version",
            )
            capabilities["local_api_server_id"] = self._header_value(
                local_response.headers,
                "Zotero-Server-ID",
            )
            capabilities["local_api_write_available"] = (
                capabilities["local_api_version"] == "3" and capabilities["local_api_server_id"] is not None
            )
            # ``_request_raw`` observes the authoritative root response and
            # may have invalidated a key after a downgrade/profile switch.
            capabilities["local_api_write_authorized"] = self._local_api_key is not None
            capabilities["local_api_write_authorization_remembered"] = self._local_api_key_remembered
            if capabilities["local_api_write_available"]:
                server_id = capabilities["local_api_server_id"]
                if self._local_server_id is not None and self._local_server_id != server_id:
                    self._local_api_key = None
                    self._local_api_key_server_id = None
                    self._local_api_key_remembered = False
                self._local_api_version = capabilities["local_api_version"]
                self._local_schema_version = capabilities["local_api_schema_version"]
                self._local_server_id = server_id
        except ZoteroAPIError as e:
            capabilities["local_api_status_code"] = e.status_code
            capabilities["local_api_message"] = e.response_text or str(e)
        except Exception as e:
            capabilities["local_api_message"] = str(e)

        return capabilities
