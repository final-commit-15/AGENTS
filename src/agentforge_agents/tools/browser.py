"""Browser tool - Playwright-driven browser automation with graceful fallback."""

from __future__ import annotations

from typing import Any

from agentforge_agents.schemas.tools import ToolParameter, ToolResult
from agentforge_agents.tools.base import BaseTool

_OPERATIONS = {"navigate", "screenshot", "html", "text", "download"}


class BrowserTool(BaseTool):
    """Navigate, fill, screenshot, and extract from web pages.

    Uses Playwright when it is installed. Without it the tool degrades to a
    static fetch-and-parse mode for ``navigate``/``text``/``html`` (no JS
    execution), returning a documented note.
    """

    name = "browser"
    description = "Navigate web pages, extract text/HTML, take screenshots, and download files."
    category = "web"
    timeout_seconds = 60.0
    tags = ["browser"]

    parameters = [
        ToolParameter(name="operation", type="string", required=True, enum=sorted(_OPERATIONS)),
        ToolParameter(name="url", type="string", required=False),
        ToolParameter(
            name="selector",
            type="string",
            required=False,
            description="CSS selector for extraction.",
        ),
        ToolParameter(name="viewport", type="string", required=False, default="1280x800"),
    ]

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if arguments.get("operation") not in _OPERATIONS:
            errors.append("invalid operation")
        if arguments.get("operation") in {
            "navigate",
            "screenshot",
            "download",
        } and not arguments.get("url"):
            errors.append(f"{arguments.get('operation')} requires url")
        return errors

    async def execute(self, arguments: dict[str, Any] | None = None) -> ToolResult:
        arguments = arguments or {}
        operation = str(arguments["operation"])
        if _playwright_available():
            return await self._playwright_execute(operation, arguments)
        if operation in {"navigate", "text", "html"}:
            return await self._static_execute(operation, arguments)
        return self.err(f"operation {operation!r} requires the playwright package")

    async def _static_execute(self, operation: str, arguments: dict[str, Any]) -> ToolResult:
        import httpx

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds, follow_redirects=True
            ) as client:
                response = await client.get(
                    str(arguments["url"]), headers={"User-Agent": "agentforge-browser/1.0"}
                )
            if response.status_code != 200:
                return self.err(f"static fetch returned HTTP {response.status_code}")
        except httpx.HTTPError as exc:
            return self.err(f"static fetch failed: {exc}")
        if operation == "navigate":
            return self._text_of(response.text, arguments.get("selector"))
        if operation == "html":
            return self.ok(
                {"html": response.text[: 256 * 1024]},
                mode="static-fallback",
            )
        return self._text_of(response.text, arguments.get("selector"))

    def _text_of(self, html: str, selector: str | None) -> ToolResult:
        try:
            from bs4 import BeautifulSoup
        except ImportError:  # pragma: no cover
            return self.ok({"text": "".join(html.split())[:10000]}, mode="static-fallback")
        soup = BeautifulSoup(html, "html.parser")
        node = soup.select_one(selector) if selector else soup.body or soup
        text = node.get_text(" ", strip=True)[:50000] if node else ""
        return self.ok(
            {"text": text, "title": soup.title.get_text(strip=True) if soup.title else ""},
            mode="static-fallback",
        )

    async def _playwright_execute(self, operation: str, arguments: dict[str, Any]) -> ToolResult:
        from playwright.async_api import Browser, async_playwright

        viewport = _parse_viewport(str(arguments.get("viewport") or "1280x800"))
        browser: Browser | None = None
        try:
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page(viewport=viewport)
            if arguments.get("url"):
                await page.goto(
                    str(arguments["url"]),
                    wait_until="domcontentloaded",
                    timeout=int(self.timeout_seconds * 1000),
                )
            if operation == "navigate":
                selector = arguments.get("selector")
                if selector:
                    text = await page.inner_text(selector)
                    return self.ok({"text": text[:50000]})
                return self.ok({"title": await page.title(), "url": page.url})
            if operation == "html":
                return self.ok({"html": (await page.content())[: 512 * 1024]})
            if operation == "text":
                return self.ok({"text": (await page.inner_text("body"))[:50000]})
            if operation == "screenshot":
                png = await page.screenshot(full_page=True, type="png")
                from base64 import b64encode

                return self.ok({"screenshot_b64": b64encode(png).decode(), "bytes": len(png)})
            if operation == "download":
                async with page.expect_download() as download_info:
                    await page.goto(str(arguments["url"]))
                download = await download_info.value
                path = await download.path()
                suggested = download.suggested_filename
                return self.ok({"downloaded": str(path), "filename": suggested})
        except Exception as exc:  # noqa: BLE001
            return self.err(f"playwright {operation} failed: {exc}")
        finally:
            if browser is not None:
                await browser.close()
        return self.err("unreachable")  # pragma: no cover


def _playwright_available() -> bool:
    try:
        import playwright  # noqa: F401

        return True
    except ImportError:
        return False


def _parse_viewport(value: str) -> dict[str, int]:
    width, _, height = value.partition("x")
    try:
        return {"width": int(width), "height": int(height)}
    except ValueError:
        return {"width": 1280, "height": 800}


__all__ = ["BrowserTool"]
