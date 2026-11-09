# 智能客服

基于 MCP 的电商智能客服系统：FastMCP 暴露资源、工具与 prompt，FastAPI 同进程托管
Streamable HTTP 的 MCP 端点与前端静态页，后端 `/chat` 作为 MCP 客户端接入 DeepSeek
`deepseek-v4-pro` 做自动问答。

## 快速开始

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # 填入 DEEPSEEK_API_KEY 后可启用自动问答
.venv/bin/uvicorn --app-dir src customer_service.app:app --reload --port 8000
```

打开 <http://127.0.0.1:8000>。MCP 端点为 <http://127.0.0.1:8000/mcp>。

## 测试

```bash
.venv/bin/python -m pytest
```

## 目录

- `src/customer_service/`：后端（MCP server、FastAPI 应用、订单存储、自动问答编排）
- `static/`：前端静态页
- `data/orders.json`：预置覆盖五种状态的种子订单

