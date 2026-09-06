"""Search tool - web search via the DuckDuckGo HTML endpoint (no API key needed)."""

from __future__ import annotations

import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

from agentforge_agents.schemas.tools import ToolParameter, ToolResult
from agentforge_agents.tools.base import BaseTool


class SearchTool(BaseTool):
    """Web search returning ranked result titles, snippets, and URLs.

    Uses the public DuckDuckGo endpoint; no credentials required. Results are
    capped and the request is bounded by a timeout.
    """

    name = "search"
    description = "Search the web and return ranked result titles, URLs, and snippets."
    category = "web"
    timeout_seconds = 20.0
    tags = ["search", "web"]
    endpoint = "https://html.duckduckgo.com/html/"

    parameters = [
        ToolParameter(name="query", type="string", required=True),
        ToolParameter(name="max_results", type="integer", required=False, default=5),
    ]

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        if not arguments.get("query") or not str(arguments["query"]).strip():
            return ["query is required"]
        return []

    async def execute(self, arguments: dict[str, Any] | None = None) -> ToolResult:
        arguments = arguments or {}
        max_results = int(arguments.get("max_results") or 5)
        async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
            response = await client.post(
                self.endpoint,
                data={"q": str(arguments["query"])},
                headers={"User-Agent": "agentforge-agents/1.0"},
            )
            if response.status_code != 200:
                return self.err(f"search backend returned HTTP {response.status_code}")
            soup = BeautifulSoup(response.text, "html.parser")
        results: list[dict[str, str]] = []
        for link in soup.select("a.result__a")[:max_results]:
            url = link.get("href", "")
            match = re.search(r"uddg=([^&]+)", url)
            if match:
                from urllib.parse import unquote

                url = unquote(match.group(1))
            snippet = link.find_parent("div", class_="result")
            snippet_text = snippet.get_text(" ", strip=True) if snippet else ""
            results.append(
                {"title": link.get_text(" ", strip=True), "url": url, "snippet": snippet_text[:500]}
            )
        return self.ok({"query": arguments["query"], "results": results, "count": len(results)})


__all__ = ["SearchTool"]
