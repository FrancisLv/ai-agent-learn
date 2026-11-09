"""后端作为 MCP 客户端与自身 server 交互的封装。"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from pydantic import AnyUrl


@dataclass
class ToolInfo:
    name: str
    description: str
    input_schema: dict


@dataclass
class ResourceInfo:
    uri: str
    name: str
    description: str


class McpFacade:
    """面向业务代码的 MCP 客户端统一接口，便于测试时注入假实现。"""

    def __init__(self, session: ClientSession):
        self._session = session

    async def list_tools(self) -> list[ToolInfo]:
        result = await self._session.list_tools()
        return [
            ToolInfo(
                name=tool.name,
                description=tool.description or "",
                input_schema=tool.inputSchema or {},
            )
            for tool in result.tools
        ]

    async def list_resources(self) -> list[ResourceInfo]:
        result = await self._session.list_resources()
        return [
            ResourceInfo(uri=str(res.uri), name=res.name or "", description=res.description or "")
            for res in result.resources
        ]

    async def read_resource(self, uri: str) -> str:
        result = await self._session.read_resource(AnyUrl(uri))
        parts: list[str] = []
        for content in result.contents:
            text = getattr(content, "text", None)
            if text is not None:
                parts.append(text)
        return "\n".join(parts)

    async def call_tool(self, name: str, arguments: dict) -> dict:
        result = await self._session.call_tool(name, arguments)
        text = "\n".join(
            content.text for content in result.content if getattr(content, "text", None) is not None
        )
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return {"result": text}


@asynccontextmanager
async def open_mcp_session(
    url: str, http_client: Any = None
) -> AsyncIterator[ClientSession]:
    """建立并初始化一个 Streamable HTTP MCP 客户端会话。"""
    kwargs: dict[str, Any] = {}
    if http_client is not None:
        kwargs["http_client"] = http_client
    async with streamable_http_client(url, **kwargs) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session

