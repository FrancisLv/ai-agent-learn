"""订单数据存储：单 JSON 文件，预置覆盖五种状态的种子订单。"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

STATUS_PENDING = "待支付"
STATUS_PAID = "已支付"
STATUS_SHIPPED = "已发货"
STATUS_DELIVERED = "已签收"
STATUS_REFUNDED = "已退款"

REFUNDABLE_STATUSES = (STATUS_PAID, STATUS_SHIPPED, STATUS_DELIVERED)

SEED_ORDERS: list[dict] = [
    {
        "order_id": "20260101001",
        "status": STATUS_PENDING,
        "amount": 199.0,
        "courier": "",
        "tracking_no": "",
        "logistics_status": "未发货",
    },
    {
        "order_id": "20260101002",
        "status": STATUS_PAID,
        "amount": 299.0,
        "courier": "",
        "tracking_no": "",
        "logistics_status": "待发货",
    },
    {
        "order_id": "20260101003",
        "status": STATUS_SHIPPED,
        "amount": 159.0,
        "courier": "顺丰速运",
        "tracking_no": "SF202601010003",
        "logistics_status": "运输中，预计明天送达",
    },
    {
        "order_id": "20260101004",
        "status": STATUS_DELIVERED,
        "amount": 399.0,
        "courier": "中通快递",
        "tracking_no": "ZT202601010004",
        "logistics_status": "已签收",
    },
    {
        "order_id": "20260101005",
        "status": STATUS_REFUNDED,
        "amount": 99.0,
        "courier": "",
        "tracking_no": "",
        "logistics_status": "已退款",
    },
]


def default_orders_path() -> Path:
    """默认订单文件路径：仓库根目录下的 data/orders.json，可用 ORDERS_FILE 覆盖。"""
    configured = os.environ.get("ORDERS_FILE", "").strip()
    if configured:
        return Path(configured)
    root = Path(__file__).resolve().parents[2]
    return root / "data" / "orders.json"


class OrderStore:
    """线程安全的订单存储，读写单个 JSON 文件。"""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._ensure_seed()

    def _ensure_seed(self) -> None:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._write(SEED_ORDERS)

    def _load(self) -> list[dict]:
        with self.path.open("r", encoding="utf-8") as handle:
            return list(json.load(handle))

    def _write(self, orders: list[dict]) -> None:
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(orders, handle, ensure_ascii=False, indent=2)

    def query(self, order_id: str) -> dict | None:
        with self._lock:
            for order in self._load():
                if order["order_id"] == order_id:
                    return dict(order)
        return None

    def refund(self, order_id: str, reason: str = "") -> dict:
        with self._lock:
            orders = self._load()
            for order in orders:
                if order["order_id"] != order_id:
                    continue
                if order["status"] not in REFUNDABLE_STATUSES:
                    return {
                        "order_id": order_id,
                        "refunded": False,
                        "status": order["status"],
                        "error": f"订单当前状态为「{order['status']}」，不支持退款",
                    }
                order["status"] = STATUS_REFUNDED
                self._write(orders)
                return {
                    "order_id": order_id,
                    "refunded": True,
                    "status": STATUS_REFUNDED,
                    "amount": order["amount"],
                    "reason": reason,
                }
        return {"order_id": order_id, "refunded": False, "error": f"订单不存在：{order_id}"}

