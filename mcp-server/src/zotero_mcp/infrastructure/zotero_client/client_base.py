"""
Zotero Client - Base Classes and Configuration

Provides:
- ZoteroConfig: Connection configuration
- ZoteroConnectionError, ZoteroAPIError: Exception types
- ZoteroClientBase: HTTP request handling
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any

import httpx


class ZoteroConnectionError(Exception):
    """Raised when connection to Zotero fails"""

    pass


class ZoteroAPIError(Exception):
    """Raised when Zotero API returns an error"""

    def __init__(self, message: str, status_code: int = 0, response_text: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


@dataclass
class ZoteroConfig:
    """Zotero connection configuration"""

    host: str = field(default_factory=lambda: os.getenv("ZOTERO_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("ZOTERO_PORT", "23119")))
    timeout: float = field(default_factory=lambda: float(os.getenv("ZOTERO_TIMEOUT", "30")))

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def host_header(self) -> str:
        """Required header for port proxy"""
        return f"127.0.0.1:{self.port}"

    @property
    def needs_host_header(self) -> bool:
        """Check if we need Host header override (remote connection via port proxy)"""
        return self.host not in ("localhost", "127.0.0.1")


class ZoteroClientBase:
    """
    Base HTTP Client for Zotero

    Handles HTTP communication with Zotero's built-in Local API.
    """

    def __init__(self, config: ZoteroConfig | None = None):
        self.config = config or ZoteroConfig()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            headers = {"Content-Type": "application/json"}

            # Add Host header override for remote connections (port proxy)
            if self.config.needs_host_header:
                headers["Host"] = self.config.host_header

            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                headers=headers,
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

    async def _request(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make HTTP request to Zotero API"""
        response = await self._request_raw(method, path, json_data=json_data, params=params)

        # Parse JSON response
        if response.text:
            try:
                return response.json()
            except json.JSONDecodeError:
                return response.text
        return None

    async def _request_raw(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Make HTTP request and return the raw response for header-aware probes."""
        client = await self._get_client()

        try:
            response = await client.request(
                method=method,
                url=path,
                json=json_data,
                params=params,
            )

            # Check for error responses
            if response.status_code >= 400:
                raise ZoteroAPIError(
                    f"Zotero API error: {response.status_code}",
                    status_code=response.status_code,
                    response_text=response.text,
                )

            return response

        except httpx.ConnectError as e:
            # Close and reset client on connection failure to prevent stale connections
            await self.close()
            raise ZoteroConnectionError(
                f"無法連接到 Zotero ({self.config.base_url})。\n"
                f"請確認:\n"
                f"1. Zotero 正在運行\n"
                f"2. Windows 防火牆已開放 port {self.config.port}\n"
                f"3. Port proxy 已設定 (netsh interface portproxy)\n"
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

        Zotero 7/8/9 expose useful version metadata on the connector ping response,
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
            "connector_save_available": None,
            "supports_zotero_major_versions": [7, 8, 9],
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
            local_response = await self._request_raw("GET", "/api/users/0/items", params={"limit": 1})
            capabilities["local_api_readable"] = True
            capabilities["local_api_version"] = self._header_value(local_response.headers, "Zotero-API-Version")
        except ZoteroAPIError as e:
            capabilities["local_api_status_code"] = e.status_code
            capabilities["local_api_message"] = e.response_text or str(e)
        except Exception as e:
            capabilities["local_api_message"] = str(e)

        return capabilities
