"""HTTP 端点测试：静态页、能力接口、查询/退款/聊天的请求路由。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

from customer_service.app import create_app
from customer_service.mcp_client import ResourceInfo, ToolInfo

from helpers import FakeFacade, FakeLLM


def make_factory(facade):
    @asynccontextmanager
    async def factory():
        yield facade

    return factory


def make_client(tmp_path, facade=None, llm=None):
    app = create_app(tmp_path / "orders.json")
    if facade is not None:
        app.state.mcp_facade_factory = make_factory(facade)
    if llm is not None:
        app.state.llm = llm
    return TestClient(app)


def test_index_and_capabilities(tmp_path):
    with make_client(tmp_path) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "<html" in response.text

        caps = client.get("/api/capabilities").json()
        assert len(caps["resources"]) == 3
        assert len(caps["tools"]) == 2
        assert len(caps["prompts"]) == 2

        faq = client.get("/api/resources/faq").json()
        assert "7 天" in faq["content"]


def test_query_endpoint(tmp_path):
    facade = FakeFacade(
        call_results={"query_order": {"order_id": "X", "found": True, "status": "已发货"}}
    )
    with make_client(tmp_path, facade=facade) as client:
        response = client.post("/api/query", json={"order_id": "X"})
        assert response.status_code == 200
        assert response.json()["status"] == "已发货"
        assert facade.calls == [("query_order", {"order_id": "X"})]


def test_refund_endpoint(tmp_path):
    facade = FakeFacade(
        call_results={"refund_order": {"order_id": "X", "refunded": True, "status": "已退款"}}
    )
    with make_client(tmp_path, facade=facade) as client:
        response = client.post("/api/refund", json={"order_id": "X", "reason": "不想要"})
        assert response.status_code == 200
        assert response.json()["refunded"] is True
        assert facade.calls == [("refund_order", {"order_id": "X", "reason": "不想要"})]


def test_chat_endpoint(tmp_path):
    facade = FakeFacade(
        tools=[
            ToolInfo(
                name="query_order",
                description="查询订单",
                input_schema={
                    "type": "object",
                    "properties": {"order_id": {"type": "string"}},
                },
            )
        ],
        resources=[ResourceInfo(uri="docs://faq", name="FAQ", description="")],
        resource_contents={"docs://faq": "7 天无理由退货"},
    )
    llm = FakeLLM([{"content": "您好，订单已发货。", "tool_calls": []}])
    with make_client(tmp_path, facade=facade, llm=llm) as client:
        response = client.post(
            "/chat", json={"messages": [{"role": "user", "content": "hi"}]}
        )
        assert response.status_code == 200
        assert response.json()["answer"] == "您好，订单已发货。"


def test_chat_without_api_key_returns_guidance(tmp_path):
    facade = FakeFacade()
    with make_client(tmp_path, facade=facade, llm=None) as client:
        response = client.post(
            "/chat", json={"messages": [{"role": "user", "content": "hi"}]}
        )
        assert response.status_code == 200
        assert "DEEPSEEK_API_KEY" in response.json()["answer"]

