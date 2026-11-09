"""FastMCP server：注册 3 份资源、2 个 prompt、2 个工具。"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from . import resources
from .orders import OrderStore

TOOL_SPECS: list[dict] = [
    {"name": "query_order", "description": "按订单号查询订单状态、金额与物流信息"},
    {"name": "refund_order", "description": "对符合条件的订单执行全额退款并返回结果"},
]


def build_mcp_server(store: OrderStore) -> FastMCP:
    """用给定的订单存储构建一个新的 FastMCP server。"""

    mcp = FastMCP(
        "customer-service",
        instructions="智能客服 MCP Server：提供订单查询与退款工具、三份资源文档与两个 prompt。",
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=["localhost", "127.0.0.1", "localhost:*", "127.0.0.1:*"],
        ),
    )

    def _register_resource(uri: str, name: str, description: str, content: str) -> None:
        @mcp.resource(uri, name=name, description=description, mime_type="text/plain")
        def _read() -> str:
            return content

    def _register_prompt(name: str, description: str, template: str) -> None:
        @mcp.prompt(name=name, description=description)
        def _get() -> str:
            return template

    for spec in resources.RESOURCE_SPECS:
        _register_resource(spec["uri"], spec["name"], spec["description"], spec["content"])

    for spec in resources.PROMPT_SPECS:
        _register_prompt(spec["name"], spec["description"], spec["template"])

    @mcp.tool(name="query_order", description="按订单号查询订单状态、金额与物流信息")
    def query_order(order_id: str) -> dict:
        order = store.query(order_id)
        if order is None:
            return {"order_id": order_id, "found": False, "error": f"订单不存在：{order_id}"}
        order["found"] = True
        return order

    @mcp.tool(name="refund_order", description="对符合条件的订单执行全额退款并返回结果")
    def refund_order(order_id: str, reason: str = "") -> dict:
        return store.refund(order_id, reason)

    return mcp

