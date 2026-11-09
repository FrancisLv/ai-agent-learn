"""测试共用工具：ASGI 版 MCP 客户端会话与假实现。"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager

import httpx

from customer_service.mcp_client import McpFacade, open_mcp_session


@asynccontextmanager
async def session_ctx(app):
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8000"
    )
    async with app.router.lifespan_context(app):
        async with open_mcp_session(
            "http://127.0.0.1:8000/mcp", http_client=client
        ) as session:
            yield session
    await client.aclose()


def tool_json(result) -> dict:
    text = "\n".join(
        content.text for content in result.content if getattr(content, "text", None) is not None
    )
    return json.loads(text)


class FakeFacade:
    def __init__(
        self,
        tools=None,
        resources=None,
        resource_contents=None,
        call_results=None,
    ):
        self.tools = tools or []
        self.resources = resources or []
        self.resource_contents = resource_contents or {}
        self.call_results = call_results or {}
        self.calls: list[tuple] = []

    async def list_tools(self):
        return self.tools

    async def list_resources(self):
        return self.resources

    async def read_resource(self, uri):
        return self.resource_contents.get(uri, "")

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return self.call_results.get(name, {})


class FakeLLM:
    def __init__(self, script):
        self.script = list(script)
        self.messages_seen: list[dict] = []

    async def complete(self, messages, tools=None):
        self.messages_seen.append({"messages": list(messages), "tools": tools})
        return self.script.pop(0)

