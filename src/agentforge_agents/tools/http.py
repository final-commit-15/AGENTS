"""HTTP tool - configurable async requests with limits and timeout."""

from __future__ import annotations

from typing import Any

import httpx

from agentforge_agents.schemas.tools import ToolParameter, ToolResult
from agentforge_agents.tools.base import BaseTool

_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"}
_MAX_RESPONSE_BYTES = 512 * 1024


class HTTPTool(BaseTool):
    """Perform HTTP calls using httpx with an async client and strict caps."""

    name = "http"
    description = "Send an HTTP request with configurable method, headers, body, and timeout."
    category = "web"
    timeout_seconds = 30.0
    tags = ["http", "api"]

    parameters = [
        ToolParameter(name="method", type="string", required=True, enum=sorted(_METHODS)),
        ToolParameter(name="url", type="string", required=True),
        ToolParameter(name="headers", type="object", required=False),
        ToolParameter(name="body", type="object", required=False),
        ToolParameter(name="params", type="object", required=False),
        ToolParameter(name="timeout", type="number", required=False),
    ]

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if str(arguments.get("method", "")).upper() not in _METHODS:
            errors.append("invalid http method")
        url = str(arguments.get("url", ""))
        if not url.startswith(("http://", "https://")):
            errors.append("url must start with http:// or https://")
        return errors

    async def execute(self, arguments: dict[str, Any] | None = None) -> ToolResult:
        arguments = arguments or {}
        method = str(arguments["method"]).upper()
        url = str(arguments["url"])
        timeout = float(arguments.get("timeout") or self.timeout_seconds)
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.request(
                    method,
                    url,
                    headers=arguments.get("headers") or {},
                    params=arguments.get("params") or {},
                    json=arguments.get("body"),
                )
        except httpx.HTTPError as exc:
            return self.err(f"http request failed: {exc}")
        body = response.content[:_MAX_RESPONSE_BYTES]
        decoded: Any = None
        try:
            decoded = response.json()
        except ValueError:
            decoded = body.decode(errors="replace")[: 64 * 1024]
        return self.ok(
            {
                "status": response.status_code,
                "headers": dict(response.headers),
                "body": decoded,
                "url": str(response.url),
            }
        )


__all__ = ["HTTPTool"]
