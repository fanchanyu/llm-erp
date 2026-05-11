"""
Phase C — Domain Agent Definitions (10 agents, scoped tools)
"""
from __future__ import annotations
import json
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents_v2 import DomainAgent


# ═══════════════════════════════════════════════════════════════════
# 1. INVENTORY AGENT
# ═══════════════════════════════════════════════════════════════════

INVENTORY_TOOLS = [
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
            "name": "inbound_material",
            "description": "入庫作業。將指定料號的物料入庫，可指定儲位。",
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
            "description": "出庫作業。將指定料號的物料從庫存發出（例如發料至工單）。",
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
    {
        "type": "function",
        "function": {
            "name": "query_parts",
            "description": "查詢零件主檔列表。可過濾分類或搜尋料號/品名關鍵字。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "料號或品名關鍵字"},
                    "category": {"type": "string", "description": "分類過濾"}
                }
            }
        }
    },
]

class InventoryAgent(DomainAgent):
    name = "inventory"
    description = "庫存管理 — 查詢庫存、入庫、出庫、零件主檔"
    tools = INVENTORY_TOOLS
    required_permissions = ["inventory:read"]


# ═══════════════════════════════════════════════════════════════════
# 2. PURCHASE AGENT
# ═══════════════════════════════════════════════════════════════════

PURCHASE_TOOLS = [
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
                    "po_no": {"type": "string", "description": "採購單號關鍵字"},
                    "status": {"type": "string", "description": "狀態: draft/approved/shipped/received"}
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
            "name": "check_reorder",
            "description": "檢查所有需要補貨的物料（低於安全庫存量）。",
            "parameters": {"type": "object", "properties": {}}
        }
    },
]

class PurchaseAgent(DomainAgent):
    name = "purchase"
    description = "採購管理 — 查詢供應商、採購單、建立採購單、自動補貨檢查"
    tools = PURCHASE_TOOLS
    required_permissions = ["purchase:read"]


# ═══════════════════════════════════════════════════════════════════
# 3. PRODUCTION AGENT
# ═══════════════════════════════════════════════════════════════════

PRODUCTION_TOOLS = [
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
            "name": "query_gantt",
            "description": "查詢生產排程甘特圖。查看所有工作站上的工單排程。",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_shop_floor",
            "description": "查看現場控制面板 — 機台狀態、WIP、人員負荷即時資訊。",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_mps",
            "description": "查詢主生產排程(MPS)彙總。依產品料號顯示各期規劃產量。",
            "parameters": {"type": "object", "properties": {}}
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
]

class ProductionAgent(DomainAgent):
    name = "production"
    description = "生產管理 — 工單管理、派工、排程、現場控制面板、急單處理"
    tools = PRODUCTION_TOOLS
    required_permissions = ["dispatch:read"]


# ═══════════════════════════════════════════════════════════════════
# 4. QUALITY AGENT
# ═══════════════════════════════════════════════════════════════════

QUALITY_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_inspections",
            "description": "查詢品檢單列表。可過濾狀態：pending(待檢)/approved(合格)/rejected(不合格)/conditional(條件允收)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "狀態: pending/approved/rejected/conditional"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_ncs",
            "description": "查詢不良品記錄(NC/非符合項)列表。狀態：open/investigating/resolved/closed。",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "狀態: open/investigating/resolved/closed"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_nc",
            "description": "建立不良品記錄。需指定料號、缺陷代碼、描述、嚴重程度。",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_no": {"type": "string", "description": "料號"},
                    "defect_code": {"type": "string", "description": "缺陷代碼"},
                    "description": {"type": "string", "description": "缺陷描述"},
                    "severity": {"type": "string", "description": "嚴重程度: major/minor/critical"}
                },
                "required": ["part_no", "defect_code", "description"]
            }
        }
    },
]

class QualityAgent(DomainAgent):
    name = "quality"
    description = "品管管理 — 品檢單查詢、不良品記錄(NC)、CAPA"
    tools = QUALITY_TOOLS
    required_permissions = ["quality:read"]


# ═══════════════════════════════════════════════════════════════════
# 5. ACCOUNTING AGENT
# ═══════════════════════════════════════════════════════════════════

ACCOUNTING_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_accounts",
            "description": "查詢會計科目表。可依科目類型過濾：asset/liability/equity/revenue/expense。",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "description": "科目類型: asset/liability/equity/revenue/expense"}
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
                    "status": {"type": "string", "description": "狀態: open/overdue/paid"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_ar_overdue",
            "description": "查詢逾期應收帳款。可設定逾期天數門檻。",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "逾期天數門檻 (預設30天)"}
                }
            }
        }
    },
]

class AccountingAgent(DomainAgent):
    name = "accounting"
    description = "會計管理 — 科目查詢、應收帳款(AR)、逾期催收"
    tools = ACCOUNTING_TOOLS
    required_permissions = ["accounting:read"]


# ═══════════════════════════════════════════════════════════════════
# 6. CRM AGENT
# ═══════════════════════════════════════════════════════════════════

CRM_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_customers",
            "description": "查詢客戶列表。輸入名稱關鍵字查詢，留空查全部。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "客戶名稱關鍵字"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_sales_orders",
            "description": "查詢銷售訂單列表。狀態：draft/confirmed/production/shipped/delivered。",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "狀態: draft/confirmed/production/shipped/delivered"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_leads",
            "description": "查詢潛在客戶(Leads)列表。可過濾狀態。",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "狀態: new/contacted/qualified/lost"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_opportunities",
            "description": "查詢商機(Opportunities)列表。可過濾階段(stage)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stage": {"type": "string", "description": "階段: prospecting/negotiation/closed_won/closed_lost"}
                }
            }
        }
    },
]

class CRMAgent(DomainAgent):
    name = "crm"
    description = "客戶關係管理 — 客戶、銷售訂單、潛在客戶、商機"
    tools = CRM_TOOLS
    required_permissions = ["customer:read"]


# ═══════════════════════════════════════════════════════════════════
# 7. ORGANIZATION AGENT
# ═══════════════════════════════════════════════════════════════════

ORG_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_organization_chart",
            "description": "查詢組織架構樹。可查看總公司、各部門與員工的樹狀結構。",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_employees",
            "description": "查詢員工列表。可依部門、職稱或姓名查詢。",
            "parameters": {
                "type": "object",
                "properties": {
                    "department": {"type": "string", "description": "部門名稱關鍵字"},
                    "title": {"type": "string", "description": "職稱過濾"},
                    "name": {"type": "string", "description": "姓名關鍵字"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_my_permissions",
            "description": "查詢當前登入用戶的角色、權限及可操作的模組。",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_approval_flows",
            "description": "查詢簽核流程定義。可用 module 過濾：purchase/inventory/leave。",
            "parameters": {
                "type": "object",
                "properties": {
                    "module": {"type": "string", "description": "模組: purchase/inventory/leave (留空查全部)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_pending_approvals",
            "description": "查詢待簽核的請求列表。使用者可查看有哪些請求正在等他們批准。",
            "parameters": {"type": "object", "properties": {}}
        }
    },
]

class OrganizationAgent(DomainAgent):
    name = "organization"
    description = "組織人事管理 — 組織架構、員工查詢、權限、簽核流程、待簽核事項"
    tools = ORG_TOOLS
    required_permissions = ["organization:read"]


# ═══════════════════════════════════════════════════════════════════
# 8. WAREHOUSE AGENT
# ═══════════════════════════════════════════════════════════════════

WAREHOUSE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_zones",
            "description": "查詢倉儲區域/庫別列表。可依類型過濾：raw(原料)/wip(在製品)/finished(成品)/qa(待檢)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "zone_type": {"type": "string", "description": "庫別類型: raw/wip/finished/qa"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_transfers",
            "description": "查詢庫存調撥記錄。可依狀態或料號過濾。",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "狀態: pending/completed/cancelled"},
                    "part_no": {"type": "string", "description": "料號"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_pick_tasks",
            "description": "查詢揀貨任務列表。可過濾狀態。",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "狀態: pending/in_progress/completed"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_cycle_counts",
            "description": "查詢盤點記錄。可依料號或狀態過濾。",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
]

class WarehouseAgent(DomainAgent):
    name = "warehouse"
    description = "倉儲管理 — 倉庫區域、調撥、揀貨、盤點"
    tools = WAREHOUSE_TOOLS
    required_permissions = ["inventory:read"]


# ═══════════════════════════════════════════════════════════════════
# 9. SECURITY AGENT
# ═══════════════════════════════════════════════════════════════════

SECURITY_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_system_users",
            "description": "查詢所有系統使用者帳號（管理員用）。可搜尋使用者名稱。",
            "parameters": {
                "type": "object",
                "properties": {
                    "search": {"type": "string", "description": "使用者名稱關鍵字"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_suspicious_activity",
            "description": "偵測可疑登入活動（異常時段登入、暴力攻擊嘗試）。",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_security_settings",
            "description": "查詢當前安全策略設定（密碼政策、session timeout、鎖定門檻等）。",
            "parameters": {"type": "object", "properties": {}}
        }
    },
]

class SecurityAgent(DomainAgent):
    name = "security"
    description = "安全管理 — 系統使用者管理、可疑活動偵測、安全策略查詢"
    tools = SECURITY_TOOLS
    required_permissions = ["organization:read"]


# ═══════════════════════════════════════════════════════════════════
# 10. COMPLIANCE AGENT
# ═══════════════════════════════════════════════════════════════════

COMPLIANCE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_compliance_anomalies",
            "description": "執行合規異常偵測，回傳所有發現的異常（庫存不足、延遲出貨、品質異常等）。",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_compliance_rules",
            "description": "查詢所有監控中的合規規則，含適用法規標準（ISO 9001、GMP、FDA等）對照。",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_audit_log",
            "description": "查詢系統操作稽核日誌。可依操作者、日期範圍、模組過濾。",
            "parameters": {
                "type": "object",
                "properties": {
                    "user": {"type": "string", "description": "操作者名稱"},
                    "days": {"type": "integer", "description": "查詢最近N天 (預設7)"},
                    "module": {"type": "string", "description": "模組: inventory/purchase/dispatch/quality/accounting"}
                }
            }
        }
    },
]

class ComplianceAgent(DomainAgent):
    name = "compliance"
    description = "合規管理 — 異常偵測、合規規則、稽核日誌查詢"
    tools = COMPLIANCE_TOOLS
    required_permissions = ["report:read"]


# ═══════════════════════════════════════════════════════════════════
# AGENT REGISTRY — all agents in one map
# ═══════════════════════════════════════════════════════════════════

AGENT_REGISTRY: dict[str, type[DomainAgent]] = {
    "inventory":    InventoryAgent,
    "purchase":     PurchaseAgent,
    "production":   ProductionAgent,
    "quality":      QualityAgent,
    "accounting":   AccountingAgent,
    "crm":          CRMAgent,
    "organization": OrganizationAgent,
    "warehouse":    WarehouseAgent,
    "security":     SecurityAgent,
    "compliance":   ComplianceAgent,
}

AGENT_INTENT_MAP: dict[str, str] = {
    # Inventory intents
    "庫存": "inventory", "庫存量": "inventory", "零件": "inventory",
    "入庫": "inventory", "出庫": "inventory", "發料": "inventory",
    "領料": "inventory", "收貨": "inventory", "stock": "inventory",
    # Purchase intents
    "採購": "purchase", "供應商": "purchase", "補貨": "purchase",
    "採購單": "purchase", "廠商": "purchase", "purchase": "purchase",
    # Production intents
    "工單": "production", "生產": "production", "派工": "production",
    "排程": "production", "甘特": "production", "急單": "production",
    "機台": "production", "工作站": "production", "現場": "production",
    "進度": "production", "production": "production",
    # Quality intents
    "品檢": "quality", "品管": "quality", "不良": "quality",
    "NC": "quality", "CAPA": "quality", "quality": "quality",
    # Accounting intents
    "會計": "accounting", "AR": "accounting", "應收": "accounting",
    "科目": "accounting", "帳款": "accounting", "accounting": "accounting",
    # CRM intents
    "客戶": "crm", "銷售": "crm", "訂單": "crm", "商機": "crm",
    "業務": "crm", "SO": "crm", "crm": "crm",
    # Organization intents
    "組織": "organization", "員工": "organization", "部門": "organization",
    "權限": "organization", "簽核": "organization", "核准": "organization",
    "人事": "organization",
    # Warehouse intents
    "倉庫": "warehouse", "倉儲": "warehouse", "儲位": "warehouse",
    "調撥": "warehouse", "揀貨": "warehouse", "盤點": "warehouse",
    "warehouse": "warehouse",
    # Security intents
    "安全": "security", "使用者": "security", "密碼": "security",
    "帳號": "security", "可疑": "security", "security": "security",
    # Compliance intents
    "合規": "compliance", "稽核": "compliance", "audit": "compliance",
    "法規": "compliance", "異常": "compliance", "報表": "compliance",
}
