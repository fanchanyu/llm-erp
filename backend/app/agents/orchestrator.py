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
    },
    {
        "type": "function",
        "function": {
            "name": "query_suppliers",
            "description": "查詢供應商列表。可輸入名稱關鍵字過濾供應商名稱、聯絡人、評分等資訊。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "供應商名稱關鍵字 (留空查全部)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_purchase_orders",
            "description": "查詢採購單列表。可過濾狀態(draft/approved/shipped/received)或依採購單號搜尋。",
            "parameters": {
                "type": "object",
                "properties": {
                    "po_no": {"type": "string", "description": "採購單號關鍵字 (留空查全部)"},
                    "status": {"type": "string", "description": "狀態過濾: draft/approved/shipped/received"}
                }
            }
        }
    },
    # ── Inventory Inbound / Outbound ──
    {
        "type": "function",
        "function": {
            "name": "inbound_material",
            "description": "入庫作業。將指定料號的物料入庫，可指定儲位。使用者說「收貨/入庫」時調用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_no": {"type": "string", "description": "料號"},
                    "quantity": {"type": "number", "description": "入庫數量"},
                    "location": {"type": "string", "description": "儲位/倉庫位置 (留空用預設)"}
                },
                "required": ["part_no", "quantity"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "outbound_material",
            "description": "出庫作業。將指定料號的物料從庫存發出（例如發料至工單）。使用者說「發料/出庫/領料」時調用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_no": {"type": "string", "description": "料號"},
                    "quantity": {"type": "number", "description": "出庫數量"},
                    "work_order": {"type": "string", "description": "關聯工單號 (選填)"}
                },
                "required": ["part_no", "quantity"]
            }
        }
    },
    # ── Quality / Inspection ──
    {
        "type": "function",
        "function": {
            "name": "query_inspections",
            "description": "查詢品檢單列表。可過濾狀態：pending(待檢)/approved(合格)/rejected(不合格)/conditional(條件允收)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "狀態過濾: pending/approved/rejected/conditional (留空查全部)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_inspection",
            "description": "新增品檢單。需指定採購單號或料號。使用者說「開品檢/新增品檢單/檢驗」時調用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "po_ref": {"type": "string", "description": "採購單號 (選填)"},
                    "part_no": {"type": "string", "description": "料號 (選填)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_ncs",
            "description": "查詢不良品記錄(NC/非符合項)列表。可過濾狀態：open/investigating/resolved/closed。",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "狀態過濾: open/investigating/resolved/closed (留空查全部)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_nc",
            "description": "建立不良品記錄(Non-Conformance/非符合項)。需指定料號、缺陷代碼、描述、嚴重程度(major/minor/critical)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_no": {"type": "string", "description": "料號"},
                    "defect_code": {"type": "string", "description": "缺陷代碼"},
                    "description": {"type": "string", "description": "缺陷描述"},
                    "severity": {"type": "string", "description": "嚴重程度: major(主要)/minor(次要)/critical(致命), 預設major"}
                },
                "required": ["part_no", "defect_code", "description"]
            }
        }
    },
    # ── Accounting ──
    {
        "type": "function",
        "function": {
            "name": "query_accounts",
            "description": "查詢會計科目表。可依科目類型過濾：asset(資產)/liability(負債)/equity(權益)/revenue(收入)/expense(費用)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "description": "科目類型過濾: asset/liability/equity/revenue/expense (留空查全部)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_ar",
            "description": "查詢應收帳款(AR)列表。可過濾狀態：open(未收)/overdue(逾期)/paid(已收)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "狀態過濾: open/overdue/paid (留空查全部)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_ar_overdue",
            "description": "查詢逾期應收帳款。可設定逾期天數門檻。使用者說「逾期帳款/過期AR/催收」時調用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "逾期天數門檻 (預設30天)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_journal_entry",
            "description": "建立會計傳票/分錄。需提供摘要說明和明細行(每個明細包含account_no會計科目編號、debit借方金額、credit貸方金額)。借方總額必須等於貸方總額。",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "傳票摘要說明"},
                    "lines": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "account_no": {"type": "string", "description": "會計科目編號"},
                                "debit": {"type": "number", "description": "借方金額"},
                                "credit": {"type": "number", "description": "貸方金額"},
                                "description": {"type": "string", "description": "行項目說明(選填)"}
                            },
                            "required": ["account_no"]
                        }
                    }
                },
                "required": ["description", "lines"]
            }
        }
    },
    # ── Dispatch / Production ──
    {
        "type": "function",
        "function": {
            "name": "create_work_center",
            "description": "新增工作站/機台。需指定名稱、每日可用工時、可替代群組(用於Route Changing)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "工作站名稱 (e.g. CNC-01, 裝配線A)"},
                    "description": {"type": "string", "description": "描述"},
                    "capacity_hours": {"type": "number", "description": "每日可用工時 (預設8)"},
                    "alternate_group": {"type": "string", "description": "可替代機台群組，同組可在故障時互換"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_production_order",
            "description": "建立生產工單。需指定產品料號、數量、交期(YYYY-MM-DD)、優先級(1-5)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_no": {"type": "string", "description": "產品料號 (e.g. CNC-001)"},
                    "quantity": {"type": "number", "description": "生產數量"},
                    "due_date": {"type": "string", "description": "交期 (YYYY-MM-DD格式)"},
                    "priority": {"type": "integer", "description": "優先級 1=最急~5=最低, 預設3"}
                },
                "required": ["product_no", "quantity", "due_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "release_order",
            "description": "釋出工單，變更狀態為 released（可派工）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_no": {"type": "string", "description": "工單號 (e.g. WO-20260506-001)"}
                },
                "required": ["order_no"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_operation_to_order",
            "description": "為工單新增工序。需指定工單號、工作站名稱、工序序號、設定時間和循環時間。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_no": {"type": "string", "description": "工單號"},
                    "work_center_name": {"type": "string", "description": "工作站名稱"},
                    "sequence_no": {"type": "integer", "description": "工序序號 (1,2,3...)"},
                    "name": {"type": "string", "description": "工序名稱 (e.g. 銑削, 鑽孔, 組裝)"},
                    "setup_time_min": {"type": "number", "description": "設定時間(分鐘)"},
                    "cycle_time_min": {"type": "number", "description": "每件循環時間(分鐘)"}
                },
                "required": ["order_no", "work_center_name", "sequence_no"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "dispatch_order",
            "description": "派工 — 將已釋出的工單分配到工作站。系統會依優先級和交期自動排程。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_no": {"type": "string", "description": "工單號"}
                },
                "required": ["order_no"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_work_orders",
            "description": "查詢工單列表。可過濾狀態：draft/released/dispatched/in_progress/completed。",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "狀態過濾 (留空查全部)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "right_shift_reschedule",
            "description": "Right-Shift 重排程：機台故障或延誤時，將該機台上所有未完工序向後推移。",
            "parameters": {
                "type": "object",
                "properties": {
                    "work_center_name": {"type": "string", "description": "受影響的工作站名稱"},
                    "delay_minutes": {"type": "number", "description": "延遲分鐘數 (預設30)"},
                    "reason": {"type": "string", "description": "原因說明"}
                },
                "required": ["work_center_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "route_change_reschedule",
            "description": "Route Changing：機台故障時，將工序轉到同一群組的替代機台。",
            "parameters": {
                "type": "object",
                "properties": {
                    "work_center_name": {"type": "string", "description": "故障的工作站名稱"},
                    "reason": {"type": "string", "description": "原因說明"}
                },
                "required": ["work_center_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "expedite_order",
            "description": "急單插隊：將指定工單設為最高優先級，下次派工時優先排程。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_no": {"type": "string", "description": "要插隊的工單號"},
                    "reason": {"type": "string", "description": "原因說明"}
                },
                "required": ["order_no"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_work_center_status",
            "description": "設定工作站狀態：idle(閒置)/running(運行中)/down(故障)/maintenance(保養)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "work_center_name": {"type": "string", "description": "工作站名稱"},
                    "status": {"type": "string", "description": "狀態: idle/running/down/maintenance"}
                },
                "required": ["work_center_name", "status"]
            }
        }
    }
]

SYSTEM_PROMPT = """你是一個工廠 ERP 系統的智能助手，幫助使用者管理整個生產流程。

⚠️ 禁止規則（嚴格遵守）：
- 若使用者提到 採購單/PO/供應商/買/訂貨 → 用採購工具(query_suppliers, query_purchase_orders, create_purchase_order)
- 若使用者提到 品檢/檢驗/NC/不良品/品質異常 → 用品管工具(query_inspections, create_inspection, query_ncs, create_nc)
- 若使用者提到 應收帳款/AR/傳票/分錄/記帳/科目/逾期 → 用會計工具(query_ar, query_accounts, check_ar_overdue, create_journal_entry)
- 若使用者提到 入庫/收貨/發料/出庫/領料 → 用庫存異動工具(inbound_material, outbound_material)
- 若使用者提到 工單/派工/機台故障/急單/插隊 → 用生產工具(release_order, dispatch_order, right_shift_reschedule, route_change_reschedule, expedite_order)
- 若使用者提到 BOM/展開/缺料/料夠不夠 → 用BOM工具(query_bom, bom_explode, check_stock_shortage)
- ❌ 查採購單絕對不能用 query_inventory
- ❌ 查供應商絕對不能用 query_inventory
- ❌ 查品檢單絕對不能用 query_inventory
- ❌ 查AR/會計資料絕對不能用 query_inventory
- ❌ 入庫/出庫是 inbound_material/outbound_material，不能用 query_inventory

你可以執行的操作：

【庫存管理】
1. 查詢庫存 — 使用者問「還有多少庫存？」時調用 query_inventory
2. 入庫作業 — 使用者說「入庫/收貨」時調用 inbound_material
3. 出庫作業 — 使用者說「發料/出庫/領料」時調用 outbound_material

【採購管理】
4. 查詢供應商 — 使用者問「供應商有哪些/查大明螺絲」時調用 query_suppliers
5. 建立採購單 — 使用者說「幫我買/訂/採購」時調用 create_purchase_order
6. 查詢採購單 — 使用者問「採購單有哪些/PO狀態」時調用 query_purchase_orders

【BOM 與物料】
7. 查詢 BOM 結構 — 使用者問「XX 產品用哪些料/結構是怎樣的」時調用 query_bom
8. BOM 展開 — 使用者問「XX 產品需要多少料/展開BOM/物料需求」時調用 bom_explode
9. 缺料檢查 — 使用者問「料夠不夠？/缺不缺料？」時調用 check_stock_shortage

【工單與生產】
10. 建立工單 — 使用者說「開工單/下生產工單」時調用 create_production_order
11. 新增機台 — 使用者說「新增工作站/機台」時調用 create_work_center
12. 新增工序 — 使用者說「設定工序/製程」時調用 add_operation_to_order
13. 釋出工單 — 使用者說「釋出/放行工單」時調用 release_order
14. 派工 — 使用者說「派工/安排生產」時調用 dispatch_order
15. 查詢工單 — 使用者問「工單狀態/工單列表」時調用 query_work_orders

【現場應變】
16. 機台故障右移(Right-Shift) — 機台故障需要將工序往後推時調用 right_shift_reschedule
17. 替代路徑(Route Change) — 機台故障需換到同組替代機台時調用 route_change_reschedule
18. 急單插隊(Expedite) — 使用者說「急單/插單/趕工/優先生產」時調用 expedite_order
19. 機台狀態 — 使用者說「機台 idle/down/保養」時調用 set_work_center_status

【品管檢驗】
20. 查詢品檢單 — 使用者問「品檢記錄/檢驗單列表」時調用 query_inspections
21. 新增品檢單 — 使用者說「開品檢/檢驗物料」時調用 create_inspection
22. 查詢不良品(NC) — 使用者問「不良品/非符合項/NC記錄」時調用 query_ncs
23. 建立不良品記錄 — 使用者說「報不良/開NC/品質異常」時調用 create_nc

【會計財務】
24. 查詢科目表 — 使用者問「會計科目/科目有哪些」時調用 query_accounts
25. 查詢應收帳款 — 使用者問「AR/應收帳款/客戶欠款」時調用 query_ar
26. 查詢逾期帳款 — 使用者問「逾期帳款/過期沒收的錢」時調用 check_ar_overdue
27. 建立傳票 — 使用者說「開傳票/做分錄/記帳」時調用 create_journal_entry

【典型流程】
使用者說：「開工單做 5 台 CNC-001，交期 5/15」
→ create_production_order(product_no="CNC-001", quantity=5, due_date="2026-05-15")
→ add_operation_to_order → release_order → dispatch_order

使用者說：「CNC-01 故障了，把後面都往後推 2 小時」
→ right_shift_reschedule(work_center_name="CNC-01", delay_minutes=120)

使用者說：「CNC-01 故障了，換到替代機台」
→ route_change_reschedule(work_center_name="CNC-01")

回覆原則：
- 用繁體中文回覆
- 數字加上千分號（如 1,250 顆）
- 查詢結果用條列式或表格呈現
- 建立採購單後提供 PO 編號
- 派工後提供排程時間表
- 如果資訊不足，先問清楚再操作
- 使用者在說機台、設備、工作站時指的是 WorkCenter"""

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
    max_rounds = settings.max_tool_rounds  # configurable: 5 for cloud, up to 10 for local

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
