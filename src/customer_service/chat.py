"""LLM 抽象与 /chat 自动问答编排。"""

from __future__ import annotations

import json
import os
from typing import Any, Protocol

from .mcp_client import McpFacade

ALLOWED_TOOL = "query_order"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_BASE_URL = "https://api.deepseek.com"

SYSTEM_PROMPT_TEMPLATE = """你是电商智能客服。请严格依据下面提供的资源文档回答用户问题。

【资源文档】
{resources}

【规则】
1. 当用户查询订单状态、金额或物流时，调用 query_order 工具获取真实订单信息后，再基于结果回答。
2. 当用户表达退款意图时，不要执行任何退款操作；只生成「待确认」的订单摘要与退款说明，并提醒用户在前端确认后才执行退款。
3. 回答尽量依据资源文档；当无法解答时，引导用户转人工客服，并给出客服联系方式。
4. 始终使用简体中文回答。"""


def build_system_prompt(resource_contents: dict[str, str]) -> str:
    sections = [f"### {uri}\n{content}" for uri, content in resource_contents.items()]
    return SYSTEM_PROMPT_TEMPLATE.format(resources="\n\n".join(sections) or "（无）")


def build_tools_schema(tools: list) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema,
            },
        }
        for tool in tools
        if tool.name == ALLOWED_TOOL
    ]


class LLMClient(Protocol):
    async def complete(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> dict:
        """返回 {"content": str, "tool_calls": [{"id", "name", "arguments"}]}"""
        ...


class DeepSeekLLM:
    def __init__(self, api_key: str, model: str, base_url: str):
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    async def complete(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> dict:
        kwargs: dict[str, Any] = {"model": self._model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
        response = await self._client.chat.completions.create(**kwargs)
        message = response.choices[0].message
        tool_calls: list[dict] = []
        for call in message.tool_calls or []:
            try:
                arguments = json.loads(call.function.arguments or "{}")
            except (json.JSONDecodeError, TypeError):
                arguments = {}
            tool_calls.append({"id": call.id, "name": call.function.name, "arguments": arguments})
        return {"content": message.content or "", "tool_calls": tool_calls}


def build_llm_from_env() -> DeepSeekLLM | None:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    model = os.environ.get("LLM_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    base_url = os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL
    if not api_key:
        return None
    return DeepSeekLLM(api_key=api_key, model=model, base_url=base_url)


async def auto_answer(
    llm: LLMClient,
    facade: McpFacade,
    messages: list[dict],
    max_steps: int = 6,
) -> str:
    tools = await facade.list_tools()
    tool_schema = build_tools_schema(tools)

    resource_infos = await facade.list_resources()
    contents: dict[str, str] = {}
    for info in resource_infos:
        contents[info.uri] = await facade.read_resource(info.uri)

    convo: list[dict] = [{"role": "system", "content": build_system_prompt(contents)}]
    for item in messages:
        convo.append({"role": item.get("role", "user"), "content": item.get("content", "")})

    for _ in range(max_steps):
        response = await llm.complete(convo, tools=tool_schema)
        assistant: dict[str, Any] = {"role": "assistant", "content": response.get("content", "")}
        tool_calls = response.get("tool_calls") or []
        if tool_calls:
            assistant["tool_calls"] = [
                {
                    "id": call["id"],
                    "type": "function",
                    "function": {
                        "name": call["name"],
                        "arguments": json.dumps(call.get("arguments", {}), ensure_ascii=False),
                    },
                }
                for call in tool_calls
            ]
        convo.append(assistant)

        if not tool_calls:
            return assistant["content"] or "抱歉，我暂时无法回答，请转人工客服。"

        for call in tool_calls:
            if call["name"] == ALLOWED_TOOL:
                result = await facade.call_tool(call["name"], call.get("arguments", {}))
            else:
                result = {"error": f"工具 {call['name']} 不可用"}
            convo.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    return "抱歉，暂时无法解答，请转人工客服。"

