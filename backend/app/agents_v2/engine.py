"""
Phase C — Multi-Agent Router Engine

Flow:
1. User message → Intent Router → picks Domain Agent
2. Agent LLM call with scoped tools → tool calls
3. Execute tools via existing TOOL_FUNCTIONS
4. Return NL response
"""
from __future__ import annotations
import json, logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.llm_client import chat_completion
from app.tools.functions import TOOL_FUNCTIONS
from app.agents_v2.domain_agents import (
    DomainAgent, AGENT_REGISTRY, AGENT_INTENT_MAP
)

logger = logging.getLogger(__name__)

# ─── System Prompt ─────────────────────────────────────────────────

BASE_SYSTEM_PROMPT = """你是一個智能工廠 ERP 助手，協助使用者透過自然語言管理工廠營運。
你是繁體中文的台灣工廠助手，請全程使用繁體中文（台灣用語）回應。

基本規則：
1. 使用者問什麼就用相對應的工具回答（查詢、建立、修改）
2. 如果是查詢操作，直接回答查詢結果
3. 如果是新增/修改操作，先取得必要資訊再執行
4. 若使用者要求不明確，詢問清楚再操作
5. 所有回覆要友善、專業、簡潔

當前使用者資訊：{user_context}"""


# ─── Intent Router ─────────────────────────────────────────────────

def classify_intent(message: str) -> str:
    """Classify user message to a domain agent name using keyword matching."""
    msg_lower = message.lower()
    for keyword, agent_name in AGENT_INTENT_MAP.items():
        if keyword.lower() in msg_lower:
            return agent_name
    return "production"  # default to production if unknown


def get_agent_for_user(
    agent_name: str,
    db: AsyncSession,
    user_id: str,
    employee_id: str,
    roles: list[str],
    permissions: list[str],
) -> Optional[DomainAgent]:
    """Instantiate the right agent for this user."""
    agent_cls = AGENT_REGISTRY.get(agent_name)
    if not agent_cls:
        return None
    return agent_cls(db, user_id, employee_id, roles, permissions)


def build_system_prompt(agent: DomainAgent, user_info: dict) -> str:
    """Build the system prompt with agent-specific instructions and user context."""
    perms = user_info.get('permissions', [])
    roles = user_info.get('roles', [])
    perm_modules = ', '.join(p.get('module', '') if isinstance(p, dict) else str(p) for p in perms)
    role_names = ', '.join(
        r.get('role_name', r.get('role_code', '')) if isinstance(r, dict) else str(r)
        for r in roles
    )
    context = (
        f"姓名: {user_info.get('name', '')}, "
        f"角色: {role_names}, "
        f"部門: {user_info.get('department', '')}, "
        f"可操作模組: {perm_modules}"
    )
    prompt = BASE_SYSTEM_PROMPT.format(user_context=context)
    
    # Add agent-specific instructions
    agent_prompts = {
        "inventory": "\n\n你負責庫存管理。可以查詢庫存、入庫、出庫、零件主檔。",
        "purchase": "\n\n你負責採購管理。可以查詢供應商、採購單、建立採購單。補貨檢查會自動偵測低庫存物料。",
        "production": "\n\n你負責生產管理。可以查詢工單、建立工單、派工、排程。也可以查看現場控制面板和甘特圖。",
        "quality": "\n\n你負責品管。可以查詢品檢單、不良品記錄(NC)。",
        "accounting": "\n\n你負責會計。可以查詢會計科目、應收帳款、逾期帳款。",
        "crm": "\n\n你負責客戶關係管理。可以查詢客戶、銷售訂單、潛在客戶、商機。",
        "organization": "\n\n你負責組織人事。可以查詢組織架構、員工、權限、簽核流程、待簽核事項。",
        "warehouse": "\n\n你負責倉儲管理。可以查詢倉庫區域、調撥記錄、揀貨任務、盤點記錄。",
        "security": "\n\n你負責安全管理。可以查詢系統使用者、可疑活動、安全策略。需要管理員權限。",
        "compliance": "\n\n你負責合規管理。可以執行異常偵測、查詢合規規則、查詢操作稽核日誌。",
    }
    prompt += agent_prompts.get(agent.name, "")
    return prompt


# ─── Tool Executor ─────────────────────────────────────────────────

async def execute_tool(tool_name: str, args: dict) -> dict:
    """Execute a tool function and return result."""
    func = TOOL_FUNCTIONS.get(tool_name)
    if not func:
        return {"error": f"Unknown tool: {tool_name}"}
    try:
        if asyncio.iscoroutinefunction(func):
            result = await func(**args)
        else:
            result = func(**args)
        return {"result": result}
    except Exception as e:
        logger.exception(f"Tool {tool_name} failed")
        return {"error": str(e)}


# ─── Main Engine ───────────────────────────────────────────────────

async def process_message(
    message: str,
    user_info: dict,
    conversation_history: list[dict],
) -> str:
    """Process a user message through the multi-agent pipeline."""
    # 1. Classify intent → pick agent
    agent_name = classify_intent(message)
    agent = get_agent_for_user(
        agent_name,
        db=None,  # Will be created in the LLM call context
        user_id=user_info.get("user_id", ""),
        employee_id=user_info.get("employee_id", ""),
        roles=user_info.get("roles", []),
        permissions=user_info.get("permissions", []),
    )
    
    # 2. Get scoped tools
    tools = agent.get_tools() if agent else []
    
    # 3. Build system prompt
    system_prompt = build_system_prompt(agent or DomainAgent(), user_info)
    
    # 4. Make LLM call with tools
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history[-10:])  # Keep last 10 messages
    messages.append({"role": "user", "content": message})
    
    # 5. Call LLM with tool support
    max_rounds = 5
    final_response = ""
    
    for _ in range(max_rounds):
        response = await chat_completion(messages, tools if tools else None)

        content = response.get("content", "")
        tool_calls = response.get("tool_calls", [])

        if content:
            final_response = content

        if not tool_calls:
            break  # No more tool calls, we're done

        # Execute tool calls
        messages.append({
            "role": "assistant",
            "content": content or "",
            "tool_calls": [
                {
                    "id": tc.get("id", f"call_{i}"),
                    "type": "function",
                    "function": {"name": tc["function"]["name"], "arguments": tc["function"]["arguments"]}
                }
                for i, tc in enumerate(tool_calls)
            ],
        })
        for tc in tool_calls:
            tool_name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                args = {}

            result = await execute_tool(tool_name, args)

            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", f"call_{tool_calls.index(tc)}"),
                "content": json.dumps(result, ensure_ascii=False),
            })
    
    # 6. If we exhausted tool rounds but got a final response, use it
    if not final_response and messages:
        # Get the last assistant message
        for msg in reversed(messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                final_response = msg["content"]
                break
    
    return final_response or "系統無法處理您的請求，請稍後再試。"


# Need asyncio for iscoroutinefunction check
import asyncio
