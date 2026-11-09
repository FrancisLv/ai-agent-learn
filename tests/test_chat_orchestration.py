"""Seam 2：注入假 LLM，断言 /chat 编排的查询与退款行为。"""

from __future__ import annotations

import asyncio

from customer_service.chat import auto_answer
from customer_service.mcp_client import ResourceInfo, ToolInfo

from helpers import FakeFacade, FakeLLM


def query_tools():
    return [
        ToolInfo(
            name="query_order",
            description="查询订单",
            input_schema={
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        ),
        ToolInfo(name="refund_order", description="退款", input_schema={}),
    ]


def sample_resources():
    return [
        ResourceInfo(uri="docs://faq", name="FAQ", description=""),
        ResourceInfo(uri="docs://contact", name="联系方式", description=""),
    ]


def test_order_query_triggers_query_order():
    llm = FakeLLM(
        [
            {
                "content": "",
                "tool_calls": [
                    {"id": "1", "name": "query_order", "arguments": {"order_id": "20260101003"}}
                ],
            },
            {"content": "订单 20260101003 已发货，顺丰速运运输中。", "tool_calls": []},
        ]
    )
    facade = FakeFacade(
        tools=query_tools(),
        resources=sample_resources(),
        resource_contents={"docs://faq": "7 天无理由退货", "docs://contact": "400-800-1234"},
        call_results={
            "query_order": {
                "order_id": "20260101003",
                "status": "已发货",
                "amount": 159.0,
                "courier": "顺丰速运",
            }
        },
    )

    answer = asyncio.run(
        auto_answer(llm, facade, [{"role": "user", "content": "查订单 20260101003"}])
    )

    assert facade.calls == [("query_order", {"order_id": "20260101003"})]
    assert "已发货" in answer

    first = llm.messages_seen[0]
    assert [t["function"]["name"] for t in first["tools"]] == ["query_order"]
    system = first["messages"][0]["content"]
    assert "7 天无理由退货" in system
    assert "400-800-1234" in system


def test_refund_intent_does_not_execute_refund():
    llm = FakeLLM(
        [
            {
                "content": "已为您生成待确认的订单摘要与退款说明，请在前端确认后执行退款。",
                "tool_calls": [],
            }
        ]
    )
    facade = FakeFacade(
        tools=query_tools(),
        resources=sample_resources(),
        resource_contents={"docs://faq": "FAQ", "docs://contact": "联系方式"},
    )

    answer = asyncio.run(
        auto_answer(llm, facade, [{"role": "user", "content": "我要退款"}])
    )

    assert facade.calls == []
    assert "待确认" in answer
    assert "退款" in answer
    assert [t["function"]["name"] for t in llm.messages_seen[0]["tools"]] == ["query_order"]

