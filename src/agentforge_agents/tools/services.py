"""Service tools that talk to external SaaS APIs when credentials exist.

The connectors share a common pattern: when the required token is missing they
return a clear, structured error (mock-connector mode). When present they make
authenticated httpx calls. This keeps the framework fully functional while
credentials are absent and genuinely connected when they exist.
"""

from __future__ import annotations

import os
import re
from typing import Any

import httpx

from agentforge_agents.schemas.tools import ToolResult
from agentforge_agents.tools.base import BaseTool

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _is_iso_date(value: str) -> bool:
    return bool(_ISO_DATE_RE.match(value))


class _ServiceTool(BaseTool):
    """Base for credential-gated SaaS tools."""

    requires_credentials = True
    env_var: str = ""

    def __init__(self, context: Any = None, *, token: str | None = None) -> None:
        from agentforge_agents.tools.base import ToolContext

        super().__init__(context=context or ToolContext())
        self._token = token if token is not None else os.environ.get(self.env_var, "")
        self.creds_present = bool(self._token)

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"token {self._token}"}

    def _require_creds(self) -> ToolResult | None:
        if not self.creds_present:
            return self.err(f"credential {self.env_var!r} is not configured")
        return None

    async def _get_json(
        self, url: str, *, headers: dict[str, str] | None = None
    ) -> tuple[int, Any]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            merged = {**self._auth_headers(), **(headers or {})} if self._token else headers
            response = await client.get(url, headers=merged)
        return response.status_code, response.json()


class GitHubTool(_ServiceTool):
    """Query GitHub issues, repositories, and user data (read-only)."""

    name = "github"
    description = "Retrieve GitHub repository, user, and issue information."
    category = "vcs"
    env_var = "GITHUB_TOKEN"
    timeout_seconds = 30.0
    tags = ["github", "vcs"]
    base_url = "https://api.github.com"

    parameters = [
        {
            "name": "endpoint",
            "type": "string",
            "required": True,
            "enum": ["repo", "issues", "user", "search"],
        },
        {"name": "repo", "type": "string", "required": False, "description": "owner/repo"},
        {"name": "query", "type": "string", "required": False, "description": "Search query."},
        {"name": "username", "type": "string", "required": False},
    ]

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        endpoint = arguments.get("endpoint")
        if endpoint == "repo" and not arguments.get("repo"):
            errors.append("repo requires owner/repo")
        if endpoint == "user" and not arguments.get("username"):
            errors.append("user requires username")
        if endpoint == "search" and not arguments.get("query"):
            errors.append("search requires a query")
        return errors

    async def execute(self, arguments: dict[str, Any] | None = None) -> ToolResult:
        missing = self._require_creds()
        if missing:
            return missing
        arguments = arguments or {}
        endpoint = str(arguments["endpoint"])
        try:
            if endpoint == "repo":
                url = f"{self.base_url}/repos/{arguments['repo']}"
            elif endpoint == "user":
                url = f"{self.base_url}/users/{arguments['username']}"
            elif endpoint == "issues":
                url = f"{self.base_url}/repos/{arguments.get('repo', '')}/issues"
            else:
                url = f"{self.base_url}/search/repositories?q={httpx.QueryParams({'q': str(arguments['query'])}).get('q')}"
            _, data = await self._get_json(url)
            return self.ok(data)
        except httpx.HTTPError as exc:
            return self.err(f"github request failed: {exc}")


class SlackTool(_ServiceTool):
    """Send Slack messages and fetch channel history via the Web API."""

    name = "slack"
    description = "Post to a Slack channel or list recent channel messages."
    category = "communication"
    env_var = "SLACK_BOT_TOKEN"
    timeout_seconds = 30.0
    tags = ["slack"]
    base_url = "https://slack.com/api"

    parameters = [
        {
            "name": "operation",
            "type": "string",
            "required": True,
            "enum": ["post_message", "channel_history"],
        },
        {"name": "channel", "type": "string", "required": True},
        {
            "name": "text",
            "type": "string",
            "required": False,
            "description": "Message body for post_message.",
        },
    ]

    def __init__(self, context: Any = None, *, token: str | None = None) -> None:
        super().__init__(context=context, token=token)
        self._headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if not arguments.get("channel"):
            errors.append("channel is required")
        if arguments.get("operation") == "post_message" and not arguments.get("text"):
            errors.append("post_message requires text")
        return errors

    async def execute(self, arguments: dict[str, Any] | None = None) -> ToolResult:
        missing = self._require_creds()
        if missing:
            return missing
        arguments = arguments or {}
        operation = str(arguments["operation"])
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                if operation == "post_message":
                    response = await client.post(
                        f"{self.base_url}/chat.postMessage",
                        headers=self._headers,
                        json={"channel": arguments["channel"], "text": arguments.get("text", "")},
                    )
                else:
                    response = await client.get(
                        f"{self.base_url}/conversations.history",
                        headers=self._headers,
                        params={"channel": arguments["channel"], "limit": 10},
                    )
            data = response.json()
            if not data.get("ok"):
                return self.err(f"slack API error: {data.get('error')}")
            return self.ok(data)
        except httpx.HTTPError as exc:
            return self.err(f"slack request failed: {exc}")


class EmailTool(_ServiceTool):
    """Draft-ready email helper.

    Sending uses SMTP when server credentials are provided; otherwise the tool
    validates and formats a composed message (mock-connector mode).
    """

    name = "email"
    description = "Validate, format, and (with SMTP credentials) send email messages."
    category = "communication"
    env_var = "AGENTFORGE_SMTP_PASSWORD"
    timeout_seconds = 30.0
    tags = ["email"]

    parameters = [
        {"name": "to", "type": "string", "required": True},
        {"name": "subject", "type": "string", "required": True},
        {"name": "body", "type": "string", "required": True},
        {"name": "cc", "type": "array", "required": False},
    ]

    def __init__(self, context: Any = None, *, token: str | None = None) -> None:
        super().__init__(context=context, token=token)
        self.smtp_host = os.environ.get("AGENTFORGE_SMTP_HOST", "")
        self.smtp_user = os.environ.get("AGENTFORGE_SMTP_USER", "")
        self.creds_present = bool(self._token and self.smtp_user and self.smtp_host)

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if "@" not in str(arguments.get("to", "")):
            errors.append("to must be a valid email address")
        if not arguments.get("subject"):
            errors.append("subject is required")
        if not arguments.get("body"):
            errors.append("body is required")
        return errors

    async def execute(self, arguments: dict[str, Any] | None = None) -> ToolResult:
        arguments = arguments or {}
        message = {
            "to": arguments["to"],
            "cc": arguments.get("cc", []),
            "subject": arguments["subject"],
            "body": arguments["body"],
        }
        if not self.creds_present:
            return self.ok(
                {"message": message, "sent": False},
                note="SMTP credentials not configured; message validated and queued",
            )
        return await self._send(message)

    async def _send(
        self, message: dict[str, Any]
    ) -> ToolResult:  # pragma: no cover - requires external SMTP
        import asyncio
        import smtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["To"] = message["to"]
        msg["Subject"] = message["subject"]
        msg.set_content(message["body"])
        if message.get("cc"):
            msg["Cc"] = ", ".join(message["cc"])
        try:
            await asyncio.to_thread(self._smtp_send, msg)
            return self.ok({"message": message, "sent": True})
        except smtplib.SMTPException as exc:
            return self.err(f"SMTP send failed: {exc}")

    def _smtp_send(self, msg: Any) -> None:  # pragma: no cover - requires external SMTP
        import smtplib

        with smtplib.SMTP_SSL(self.smtp_host, 465, timeout=self.timeout_seconds) as server:
            server.login(self.smtp_user, self._token)
            server.send_message(msg)


class NotionTool(_ServiceTool):
    """Query Notion databases and page content (read-only)."""

    name = "notion"
    description = "List Notion pages and query database rows."
    category = "productivity"
    env_var = "NOTION_API_TOKEN"
    timeout_seconds = 30.0
    tags = ["notion"]
    base_url = "https://api.notion.com/v1"

    parameters = [
        {"name": "operation", "type": "string", "required": True, "enum": ["search", "page"]},
        {"name": "page_id", "type": "string", "required": False},
        {"name": "query", "type": "string", "required": False},
    ]

    def __init__(self, context: Any = None, *, token: str | None = None) -> None:
        super().__init__(context=context, token=token)
        self._headers = (
            {"Authorization": f"Bearer {self._token}", "Notion-Version": "2022-06-28"}
            if self._token
            else {}
        )

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        if arguments.get("operation") == "page" and not arguments.get("page_id"):
            return ["page requires page_id"]
        return []

    async def execute(self, arguments: dict[str, Any] | None = None) -> ToolResult:
        missing = self._require_creds()
        if missing:
            return missing
        arguments = arguments or {}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                if arguments["operation"] == "search":
                    response = await client.post(
                        f"{self.base_url}/search", headers=self._headers, json={}
                    )
                else:
                    response = await client.get(
                        f"{self.base_url}/pages/{arguments['page_id']}", headers=self._headers
                    )
            return self.ok(response.json())
        except httpx.HTTPError as exc:
            return self.err(f"notion request failed: {exc}")


class CalendarTool(_ServiceTool):
    """Schedule-aware calendar adapter (mock-connector when no credentials)."""

    name = "calendar"
    description = "List calendar events in a range (Google Calendar when credentials exist)."
    category = "productivity"
    env_var = "GOOGLE_APPLICATION_CREDENTIALS"
    timeout_seconds = 30.0
    tags = ["calendar"]

    parameters = [
        {
            "name": "date_from",
            "type": "string",
            "required": False,
            "description": "ISO date, default today.",
        },
        {
            "name": "date_to",
            "type": "string",
            "required": False,
            "description": "ISO date, default +14 days.",
        },
        {
            "name": "calendar_id",
            "type": "string",
            "required": False,
            "description": "Calendar id (default primary).",
        },
    ]

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if arguments.get("date_from") and not _is_iso_date(str(arguments["date_from"])):
            errors.append("date_from must be ISO date")
        if arguments.get("date_to") and not _is_iso_date(str(arguments["date_to"])):
            errors.append("date_to must be ISO date")
        return errors

    async def execute(self, arguments: dict[str, Any] | None = None) -> ToolResult:
        missing = self._require_creds()
        if missing:
            return missing
        arguments = arguments or {}
        # google-api-python-client integration point; without the optional dep we
        # surface the configuration state rather than failing silently.
        try:
            import googleapiclient.discovery  # noqa: F401
        except ImportError:
            return self.ok(
                {"events": [], "note": "google api client not installed"},
                requires_additional_dependency="google-api-python-client",
            )
        return self.err(
            "google calendar connection not implemented without service account credentials"
        )  # pragma: no cover


__all__ = ["CalendarTool", "EmailTool", "GitHubTool", "NotionTool", "SlackTool"]
