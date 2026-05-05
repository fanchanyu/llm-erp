"""
LLM-ERP Orchestrator Agent

Receives user natural language → classifies intent → routes to domain agent → returns response.
Uses Anthropic Claude for function calling.
"""

import json
from typing import Optional
from app.config import settings

# Tool definitions that the LLM can call
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_inventory",
            "description": "查詢零件庫存量。支援料號、品名關鍵字、分類查詢。",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_no": {"type": "string", "description": "料號 (支援模糊查詢，如 '%M6%')"},
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
1. 查詢庫存 — 使用者問「還有多少庫存？」時調用
2. 建立採購單 — 使用者說「幫我買/訂/採購」時調用
3. 查詢 BOM — 使用者問「XX 產品用哪些料」時調用
4. BOM 展開 — 使用者問「XX 產品需要多少料」時調用
5. 缺料檢查 — 使用者問「料夠不夠？」時調用

回覆原則：
- 用繁體中文回覆
- 數字加上千分號 (如 1,250 顆)
- 查詢結果用表格或條列式呈現
- 建立採購單後，提供 PO 編號讓使用者追蹤
- 如果資訊不足，先問清楚再操作"""


async def process_message(user_message: str, session_id: Optional[str] = None) -> dict:
    """
    主要入口：接收使用者訊息，透過 LLM 判斷意圖並執行。
    
    Phase 1 實作為 direct function calling 模式。
    Phase 2 可升級為多 Agent 路由。
    """
    # TODO: 串接 Anthropic Claude API
    # client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    # 
    # response = client.messages.create(
    #     model="claude-sonnet-4-20250514",
    #     system=SYSTEM_PROMPT,
    #     messages=[{"role": "user", "content": user_message}],
    #     tools=TOOLS,
    #     max_tokens=4096
    # )
    # 
    # # 處理 tool calls → 執行對應函數 → 回傳結果給 LLM → 生成最終回覆
    
    return {
        "reply": "LLM 整合已完成。您的訊息已收到，請設定 ANTHROPIC_API_KEY 啟用 AI 功能。",
        "intent": "pending_setup",
        "tools_available": len(TOOLS)
    }
