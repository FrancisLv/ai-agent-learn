"""Seam 1：通过 MCP 客户端（Streamable HTTP）对资源、工具、prompt 做黑盒断言。"""

from __future__ import annotations

import asyncio

from customer_service.app import create_app

from helpers import session_ctx, tool_json


def run(coro):
    return asyncio.run(coro)


def test_lists_tools_resources_prompts(tmp_path):
    app = create_app(tmp_path / "orders.json")

    async def main():
        async with session_ctx(app) as session:
            tools = await session.list_tools()
            assert sorted(t.name for t in tools.tools) == ["query_order", "refund_order"]

            resources = await session.list_resources()
            assert {str(r.uri) for r in resources.resources} == {
                "docs://faq",
                "docs://return-policy",
                "docs://contact",
            }

            prompts = await session.list_prompts()
            assert sorted(p.name for p in prompts.prompts) == ["order-tracking", "refund-flow"]

    run(main())


def test_read_resources_and_prompts(tmp_path):
    app = create_app(tmp_path / "orders.json")

    async def main():
        async with session_ctx(app) as session:
            faq = await session.read_resource("docs://faq")
            assert "7 天" in "".join(c.text for c in faq.contents)

            policy = await session.read_resource("docs://return-policy")
            assert "15 天" in "".join(c.text for c in policy.contents)

            contact = await session.read_resource("docs://contact")
            assert "400-800-1234" in "".join(c.text for c in contact.contents)

            prompt = await session.get_prompt("refund-flow", {})
            text = "".join(
                m.content.text for m in prompt.messages if getattr(m.content, "text", None)
            )
            assert "refund_order" in text

    run(main())


def test_query_order_seed_and_missing(tmp_path):
    app = create_app(tmp_path / "orders.json")

    async def main():
        async with session_ctx(app) as session:
            result = await session.call_tool("query_order", {"order_id": "20260101003"})
            data = tool_json(result)
            assert data["found"] is True
            assert data["status"] == "已发货"
            assert data["amount"] == 159.0
            assert data["courier"] == "顺丰速运"
            assert data["tracking_no"] == "SF202601010003"

            missing = await session.call_tool("query_order", {"order_id": "NOPE"})
            mdata = tool_json(missing)
            assert mdata["found"] is False
            assert "订单不存在" in mdata["error"]

    run(main())


def test_refund_success_and_persist(tmp_path):
    app = create_app(tmp_path / "orders.json")

    async def main():
        async with session_ctx(app) as session:
            result = await session.call_tool(
                "refund_order", {"order_id": "20260101002", "reason": "不想要了"}
            )
            data = tool_json(result)
            assert data["refunded"] is True
            assert data["status"] == "已退款"
            assert data["amount"] == 299.0
            assert data["reason"] == "不想要了"

            check = await session.call_tool("query_order", {"order_id": "20260101002"})
            assert tool_json(check)["status"] == "已退款"

    run(main())


def test_refund_rejections(tmp_path):
    app = create_app(tmp_path / "orders.json")

    async def main():
        async with session_ctx(app) as session:
            for order_id, expected_status in [("20260101001", "待支付"), ("20260101005", "已退款")]:
                result = await session.call_tool("refund_order", {"order_id": order_id})
                data = tool_json(result)
                assert data["refunded"] is False
                assert data["status"] == expected_status
                assert "不支持退款" in data["error"]

                check = await session.call_tool("query_order", {"order_id": order_id})
                assert tool_json(check)["status"] == expected_status

    run(main())

