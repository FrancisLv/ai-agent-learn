"""MCP 资源文档与 prompt 模板的单一事实来源。"""

from __future__ import annotations

FAQ_CONTENT = """常见问题标准答案

1. 如何查询订单？
   在前端「订单查询」输入订单号，即可查看订单状态、金额与物流信息。

2. 如何申请退款？
   对「已支付、已发货、已签收」的订单可申请退款。提交后需在确认弹窗中确认，退款成功后订单状态变为「已退款」；「待支付」「已退款」订单不支持退款。

3. 如何退换货？
   签收后 7 天内、商品完好且吊牌/包装齐全、非定制且非易耗商品，支持无理由退货退款；质量问题可 15 天内换货。

4. 退款多久到账？
   退款审核通过后 1–3 个工作日原路退回。"""

RETURN_POLICY_CONTENT = """退换货政策

一、时效
- 无理由退货：签收后 7 天内。
- 质量问题换货：签收后 15 天内。

二、条件
- 商品完好，吊牌/包装齐全；
- 非定制商品、非易耗商品。

三、流程
申请 → 审核 → 寄回 → 商家收货验货 → 退款/换货。

四、退款规则
- 全额退款到原支付账户；
- 退货成功后才触发退款。"""

CONTACT_CONTENT = """客服联系方式

- 客服热线：400-800-1234
- 在线时段：每日 9:00–21:00
- 邮箱：support@example.com"""

RESOURCE_SPECS: list[dict] = [
    {
        "slug": "faq",
        "uri": "docs://faq",
        "name": "常见问题标准答案",
        "description": "常见问题（FAQ）的标准答案",
        "content": FAQ_CONTENT,
    },
    {
        "slug": "return-policy",
        "uri": "docs://return-policy",
        "name": "退换货政策",
        "description": "退换货时效、条件与流程政策",
        "content": RETURN_POLICY_CONTENT,
    },
    {
        "slug": "contact",
        "uri": "docs://contact",
        "name": "客服联系方式",
        "description": "客服热线、在线时段与邮箱",
        "content": CONTACT_CONTENT,
    },
]

REFUND_FLOW_TEMPLATE = """退款处理全流程

作为智能客服，请按以下步骤协助用户退款：
1. 使用 query_order 工具确认订单状态与金额；
2. 判断是否满足退款条件（已支付/已发货/已签收可退，待支付/已退款不可退）；
3. 生成「待确认」的订单摘要与退款说明，不直接执行退款；
4. 提醒用户在前端确认后由系统调用 refund_order 工具执行退款。"""

ORDER_TRACKING_TEMPLATE = """订单查询与物流追踪

作为智能客服，请按以下步骤协助用户查询订单：
1. 使用 query_order 工具按订单号查询；
2. 返回订单状态、金额、快递公司、运单号、物流状态描述；
3. 若订单不存在，明确告知用户订单号有误。"""

PROMPT_SPECS: list[dict] = [
    {
        "name": "refund-flow",
        "description": "退款处理全流程",
        "template": REFUND_FLOW_TEMPLATE,
    },
    {
        "name": "order-tracking",
        "description": "订单查询与物流追踪",
        "template": ORDER_TRACKING_TEMPLATE,
    },
]

