"""
LLM-ERP Orchestrator Agent

Complete flow:
1. Receive user message
2. Call LLM with tools
3. Handle tool calls → execute real functions against DB
4. Return final natural language response
"""

import json
import uuid
from datetime import datetime
from typing import Optional
from app.config import settings
from app.agents.llm_client import chat_completion
from app.tools.functions import TOOL_FUNCTIONS

# Tool definitions for LLM function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_inventory",
            "description": "查詢零件庫存量。支援料號、品名關鍵字、分類查詢。",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_no": {"type": "string", "description": "料號 (支援模糊查詢)"},
                    "name": {"type": "string", "description": "品名關鍵字"},
                    "category": {"type": "string", "description": "分類過濾"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_purchase_order",
            "description": "建立採購單。需要供應商名稱、品項列表(料號/數量/單價)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "supplier_name": {"type": "string", "description": "供應商名稱"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "part_no": {"type": "string", "description": "料號"},
                                "quantity": {"type": "number", "description": "採購數量"},
                                "unit_price": {"type": "number", "description": "單價"}
                            },
                            "required": ["part_no", "quantity"]
                        }
                    },
                    "notes": {"type": "string", "description": "備註"}
                },
                "required": ["supplier_name", "items"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_bom",
            "description": "查詢產品 BOM 結構。輸入產品料號或名稱，回傳完整的物料清單。",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_no": {"type": "string", "description": "產品料號"},
                    "product_name": {"type": "string", "description": "產品名稱關鍵字"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "bom_explode",
            "description": "BOM 多階展開。輸入成品料號和需求數量，展開所有層級的子件需求。",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_no": {"type": "string", "description": "成品料號"},
                    "quantity": {"type": "number", "description": "需求數量"}
                },
                "required": ["product_no", "quantity"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_stock_shortage",
            "description": "檢查缺料情況。輸入成品料號和需求數量，展開 BOM 後比對庫存，列出缺料項目。",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_no": {"type": "string", "description": "成品料號"},
                    "quantity": {"type": "number", "description": "需求數量"}
                },
                "required": ["product_no", "quantity"]
            }
        }
    }
]

SYSTEM_PROMPT = """你是一個 ERP 系統的智能助手，幫助使用者管理庫存、採購和 BOM。

你可以執行的操作：
1. 查詢庫存 — 使用者問「還有多少庫存？」時調用 query_inventory
2. 建立採購單 — 使用者說「幫我買/訂/採購」時調用 create_purchase_order
3. 查詢 BOM — 使用者問「XX 產品用哪些料」時調用 query_bom
4. BOM 展開 — 使用者問「XX 產品需要多少料」時調用 bom_explode
5. 缺料檢查 — 使用者問「料夠不夠？」時調用 check_stock_shortage

回覆原則：
- 用繁體中文回覆
- 數字加上千分號（如 1,250 顆）
- 查詢結果用條列式或表格呈現
- 建立採購單後提供 PO 編號
- 如果資訊不足，先問清楚再操作"""

# Anthropic tool format converter
ANTHROPIC_TOOLS = [
    {
        "name": t["function"]["name"],
        "description": t["function"]["description"],
        "input_schema": {
            "type": "object",
            "properties": t["function"]["parameters"]["properties"],
            "required": t["function"]["parameters"].get("required", []),
        }
    }
    for t in TOOLS
]


def _format_tool_for_provider(tools: list[dict], provider: str) -> list[dict]:
    """Convert tools to the format expected by the provider."""
    if provider == "anthropic":
        return [
            {
                "name": t["function"]["name"],
                "description": t["function"]["description"],
                "input_schema": {
                    "type": "object",
                    "properties": t["function"]["parameters"]["properties"],
                    "required": t["function"]["parameters"].get("required", []),
                }
            }
            for t in tools
        ]
    return tools  # OpenAI format works for openai/deepseek/openrouter/ollama


async def process_message(user_message: str, session_id: Optional[str] = None) -> dict:
    """
    Main entry point.
    1. Send user message + tools to LLM
    2. Handle tool calls
    3. Return final response
    """
    if not settings.active_api_key and settings.llm_provider != "ollama":
        return {
            "reply": (
                f"⚠️ LLM 尚未設定。請在 `backend/.env` 中設定 "
                f"`{settings.llm_provider.upper()}_API_KEY`。\n\n"
                f"目前支援的 Provider：anthropic, openai, deepseek, openrouter, ollama\n"
                f"當前設定：{settings.llm_provider}"
            ),
            "intent": "no_api_key",
            "tools_available": len(TOOLS),
        }

    if not session_id:
        session_id = str(uuid.uuid4())

    messages = [{"role": "user", "content": user_message}]
    tool_uses = []
    max_rounds = 5  # prevent infinite loops

    for _ in range(max_rounds):
        # 1. Call LLM
        fmt_tools = _format_tool_for_provider(TOOLS, settings.llm_provider)
        response = await chat_completion(
            messages=messages,
            tools=fmt_tools,
            system_prompt=SYSTEM_PROMPT,
        )

        content = response.get("content", "")
        tool_calls = response.get("tool_calls", [])

        # 2. If no tool calls, we're done
        if not tool_calls:
            return {
                "reply": content or "處理完成。",
                "intent": "direct_response",
                "session_id": session_id,
            }

        # 3. Add assistant response to messages
        assistant_msg = {"role": "assistant", "content": content or ""}
        if settings.llm_provider == "anthropic":
            assistant_msg["content"] = content or ""
            # Add tool use blocks to content
            tool_blocks = []
            if content:
                tool_blocks.append({"type": "text", "text": content})
            for tc in tool_calls:
                tool_blocks.append({
                    "type": "tool_use",
                    "id": tc.get("id", ""),
                    "name": tc.get("name", ""),
                    "input": tc.get("input", {}),
                })
            if tool_blocks:
                assistant_msg["content"] = tool_blocks
        else:
            # OpenAI format
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.get("id", f"call_{i}"),
                    "type": "function",
                    "function": {
                        "name": tc.get("name") or tc.get("function", {}).get("name", ""),
                        "arguments": json.dumps(
                            tc.get("input") or tc.get("function", {}).get("arguments", {}),
                            ensure_ascii=False,
                        ),
                    },
                }
                for i, tc in enumerate(tool_calls)
            ]

        messages.append(assistant_msg)

        # 4. Execute each tool call
        for tc in tool_calls:
            name = tc.get("name") or tc.get("function", {}).get("name", "")
            raw_args = tc.get("input") or tc.get("function", {}).get("arguments", {})
            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    args = {}
            else:
                args = raw_args or {}

            func = TOOL_FUNCTIONS.get(name)
            if not func:
                result_text = f"Unknown tool: {name}"
            else:
                try:
                    result = await func(**args)
                    result_text = json.dumps(result, ensure_ascii=False, default=str)
                except Exception as e:
                    result_text = f"Error executing {name}: {str(e)}"

            # 5. Add tool result to messages
            if settings.llm_provider == "anthropic":
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tc.get("id", ""),
                            "content": result_text,
                        }
                    ]
                })
            else:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", f"call_{len(tool_uses)}"),
                    "content": result_text,
                })

            tool_uses.append({"tool": name, "args": args, "result": result_text})

    # Max rounds reached
    return {
        "reply": "已處理您的請求（達到最大對話輪數）。請查看上方結果。",
        "intent": "max_rounds",
        "session_id": session_id,
        "tool_calls_executed": len(tool_uses),
    }
