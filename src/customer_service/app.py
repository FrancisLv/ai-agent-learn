"""FastAPI 应用：同进程托管 MCP Streamable HTTP 端点与前端静态页。"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import resources
from .chat import auto_answer, build_llm_from_env
from .mcp_client import McpFacade, open_mcp_session
from .orders import OrderStore, default_orders_path
from .server import TOOL_SPECS, build_mcp_server

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"
DEFAULT_MCP_URL = "http://127.0.0.1:8000/mcp"


class ChatMessage(BaseModel):
    role: str
    content: str = ""


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(default_factory=list)


class OrderActionRequest(BaseModel):
    order_id: str
    reason: str = ""


async def get_mcp_facade(request: Request) -> AsyncIterator[McpFacade]:
    factory = request.app.state.mcp_facade_factory
    if factory is None:
        async with open_mcp_session(request.app.state.mcp_url) as session:
            yield McpFacade(session)
    else:
        async with factory() as facade:
            yield facade


def get_llm(request: Request):
    return request.app.state.llm


def create_app(orders_file: str | Path | None = None) -> FastAPI:
    store = OrderStore(orders_file or default_orders_path())
    mcp = build_mcp_server(store)
    mcp_http = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        async with mcp.session_manager.run():
            yield

    app = FastAPI(title="智能客服", lifespan=lifespan)
    app.state.llm = build_llm_from_env()
    app.state.mcp_url = os.environ.get("MCP_SERVER_URL", DEFAULT_MCP_URL)
    app.state.mcp_facade_factory = None

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/capabilities")
    def capabilities():
        return {
            "resources": [
                {
                    "slug": spec["slug"],
                    "uri": spec["uri"],
                    "name": spec["name"],
                    "description": spec["description"],
                }
                for spec in resources.RESOURCE_SPECS
            ],
            "tools": TOOL_SPECS,
            "prompts": [
                {"name": spec["name"], "description": spec["description"]}
                for spec in resources.PROMPT_SPECS
            ],
        }

    @app.get("/api/resources/{slug}")
    def resource_content(slug: str):
        for spec in resources.RESOURCE_SPECS:
            if spec["slug"] == slug:
                return {"slug": slug, "name": spec["name"], "content": spec["content"]}
        return JSONResponse(status_code=404, content={"error": "资源不存在"})

    @app.post("/api/query")
    async def query_order(req: OrderActionRequest, facade: McpFacade = Depends(get_mcp_facade)):
        return await facade.call_tool("query_order", {"order_id": req.order_id})

    @app.post("/api/refund")
    async def refund(req: OrderActionRequest, facade: McpFacade = Depends(get_mcp_facade)):
        return await facade.call_tool(
            "refund_order", {"order_id": req.order_id, "reason": req.reason}
        )

    @app.post("/chat")
    async def chat(req: ChatRequest, facade: McpFacade = Depends(get_mcp_facade)):
        llm = app.state.llm
        if llm is None:
            return {
                "answer": (
                    "自动问答未配置：缺少环境变量 DEEPSEEK_API_KEY。"
                    "请配置后重启服务；MCP 查询与退款能力仍可正常使用，也可转人工客服。"
                )
            }
        messages = [{"role": item.role, "content": item.content} for item in req.messages]
        answer = await auto_answer(llm, facade, messages)
        return {"answer": answer}

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.mount("/", mcp_http)
    return app


app = create_app()

