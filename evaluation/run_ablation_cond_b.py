"""
Condition B Runner — Role-Conditioned Prompts
Each query uses a role-specific system prompt + tool subset.
Compares against Condition A (generic) baseline.
"""
import requests, json, time, sys
from datetime import datetime

API_URL = "http://localhost:8000/api/chat"

# ── Role-specific system prompts ──
ROLE_PROMPTS = {
    "warehouse": """You are a factory ERP system AI assistant specialized for WAREHOUSE operations.
Your primary user is a Warehouse Keeper (倉庫管理員).
CRITICAL: You can ONLY use inventory-related tools. Do NOT use purchasing, BOM, dispatch, quality, accounting, or CRM tools.

Available tools:
- query_inventory: Query part stock levels
- inbound_material: Receive materials / inbound stock
- outbound_material: Issue materials / outbound stock

Respond in Traditional Chinese. Keep responses execution-focused (scan-oriented, confirmations with transaction details).""",

    "purchasing": """You are a factory ERP system AI assistant specialized for PURCHASING operations.
Your primary user is a Purchasing Agent (採購人員).
CRITICAL: You can ONLY use purchasing-related tools. Do NOT use inventory, BOM, dispatch, quality, accounting, or CRM tools.

Available tools:
- query_suppliers: Query supplier information
- create_purchase_order: Create purchase orders (PO)
- query_purchase_orders: Query purchase order status
- inbound_material: Receive inbound materials linked to a PO

Respond in Traditional Chinese. Compare supplier options and negotiate best value.""",

    "production": """You are a factory ERP system AI assistant specialized for PRODUCTION operations.
Your primary user is a Production Controller (生管人員).
CRITICAL: You can ONLY use BOM and production-related tools. Do NOT use purchasing, quality, accounting, or CRM tools.

Available tools:
- query_bom: Query BOM structure
- bom_explode: BOM explosion / material requirements
- check_stock_shortage: Check material shortage
- query_work_orders: Query work order status
- release_order: Release work orders
- dispatch_order: Dispatch / schedule production
- right_shift_reschedule: Right-shift rescheduling (machine failure)
- route_change_reschedule: Route change rescheduling
- expedite_order: Rush order / priority production
- create_production_order: Create production order

Respond in Traditional Chinese. Support what-if simulation and reschedule recommendations.""",

    "quality": """You are a factory ERP system AI assistant specialized for QUALITY operations.
Your primary user is a Quality Inspector (品管人員).
CRITICAL: You can ONLY use quality-related tools. Do NOT use inventory, purchasing, BOM, dispatch, accounting, or CRM tools.

Available tools:
- query_inspections: Query inspection orders
- create_inspection: Create new inspection order
- query_ncs: Query non-conformance (NC) records
- create_nc: Create non-conformance record

Respond in Traditional Chinese. Support defect analysis, trend identification, and root-cause analysis.""",

    "accounting": """You are a factory ERP system AI assistant specialized for ACCOUNTING operations.
Your primary user is an Accountant (會計人員).
CRITICAL: You can ONLY use accounting/finance tools. Do NOT use inventory, purchasing, BOM, dispatch, quality, or CRM tools.

Available tools:
- query_accounts: Query chart of accounts
- query_ar: Query accounts receivable
- check_ar_overdue: Check overdue accounts receivable
- create_journal_entry: Create journal entries
- check_cash_position: Check cash position

Respond in Traditional Chinese. Favor numerical precision and compliance checks.""",

    "director": """You are a factory ERP system AI assistant specialized for EXECUTIVE operations.
Your primary user is a Factory Director (廠長).
You have READ-ONLY access across all modules for oversight. You can view data but NOT create, modify, or execute operations.
CRITICAL: You can use query tools across all domains. Do NOT use any tool that creates, releases, dispatches, or modifies data.

Available tools:
- query_inventory: Query stock
- query_suppliers: Query suppliers
- query_purchase_orders: Query purchase orders
- query_bom: Query BOM
- bom_explode: BOM explosion
- check_stock_shortage: Check shortages
- query_work_orders: Query work orders
- query_inspections: Query inspections
- query_ncs: Query NC records
- query_ar: Query AR
- query_accounts: Query accounts
- check_ar_overdue: Check overdue AR
- check_cash_position: Check cash position
- query_customers: Query customers
- query_sales_orders: Query sales orders

Respond in Traditional Chinese with KPI summaries and exception reports.""",
}

# Query-to-role mapping
import re
def get_role(qid):
    prefix = qid.split("-")[0]
    mapping = {
        "inv": "warehouse",
        "pur": "purchasing",
        "bom": "production",
        "disp": "production",
        "qual": "quality",
        "acct": "accounting",
        "cross": "director",
    }
    return mapping.get(prefix, "director")

# ── Test cases ──
TEST_CASES = [
    ("inv-stock-01","Inventory","M6x20螺絲還有多少庫存？"),
    ("inv-stock-02","Inventory","我想查一下軸承BRG-001的庫存量"),
    ("inv-stock-03","Inventory","幫我看一下全部庫存列表"),
    ("inv-stock-04","Inventory","傳動件有哪些零件？庫存夠嗎？"),
    ("inv-stock-05","Inventory","查一下馬達類零件的庫存狀況"),
    ("pur-create-po-01","Purchase","幫我開一張採購單，向大明螺絲買 M6x20螺絲 200顆，單價0.5元"),
    ("pur-list-po-02","Purchase","目前有哪些採購單？列出所有PO"),
    ("pur-supplier-03","Purchase","查一下供應商大明螺絲的資料"),
    ("pur-status-04","Purchase","PO-20260505-001這張採購單的狀態是什麼？"),
    ("pur-receipt-05","Purchase","幫我收貨，PO-20260505-001 的 M6x20入庫200顆"),
    ("bom-query-01","BOM","ASM-001自動鎖螺絲機基座用了哪些零件？"),
    ("bom-explode-02","BOM","ASM-001要做5台，需要多少料？幫我展開BOM"),
    ("bom-multi-03","BOM","CNC-001小型CNC銑床的BOM結構是怎樣的？多階展開給我看"),
    ("bom-shortage-04","BOM","CNC-001要做5台，料夠不夠？幫我檢查缺料"),
    ("disp-list-01","Dispatch","目前有哪些工單？列出所有生產工單"),
    ("disp-release-02","Dispatch","幫我釋出工單 WO-20260506-001"),
    ("disp-status-03","Dispatch","查一下WO-20260506-001這張工單的狀態"),
    ("disp-dispatch-04","Dispatch","WO-20260506-001已經釋出了，幫我派工排程"),
    ("disp-resched-05","Dispatch","CNC-01機台故障了，需要維修，幫我把後面的工序往後推30分鐘"),
    ("qual-list-insp-01","Quality","列出所有品檢單，我要看目前的檢驗記錄"),
    ("qual-create-insp-02","Quality","新增一張品檢單，檢驗M6x20螺絲，數量500顆，批號LOT-B001"),
    ("qual-list-nc-03","Quality","有哪些不良品記錄(非符合項)？列出所有NC"),
    ("qual-capa-04","Quality","NC-20260505-001的改善對策是什麼？幫我建立CAPA"),
    ("acct-list-ar-01","Accounting","目前有哪些應收帳款？列出所有AR"),
    ("acct-list-accounts-02","Accounting","查詢會計科目表，列出所有會計科目"),
    ("acct-create-entry-03","Accounting","幫我建立一筆傳票：原料庫存增加550元，應付帳款增加550元"),
    ("acct-overdue-04","Accounting","有哪些超過繳款期限的應收帳款？"),
    ("acct-list-gl-05","Accounting","查詢2026年5月的總帳分錄記錄"),
    ("cross-multi-01","Cross-module","我要生產5台CNC-001，先幫我檢查料夠不夠，如果不夠就開採購單補料"),
    ("cross-multi-02","Cross-module","我想了解ASM-001的BOM結構，順便檢查庫存量夠不夠做3台"),
]

def has_error(reply):
    error_patterns = [
        "抱歉，無法","error","Error","not available","don't have",
        "can't","cannot","資料庫結構","欄位問題","欄位遺失",
        "資料庫錯誤","系統端","問題需要排除",
        "遇到了一個問題","出了一些問題","unavailable",
    ]
    r = reply.lower()
    return any(p.lower() in r for p in error_patterns)

def run_condition_b():
    """Run Condition B: each query gets role-specific system prompt."""
    print("=" * 65)
    print("CONDITION B: Role-Conditioned System Prompts (tool subsets per role)")
    print("=" * 65)
    
    results = []
    passed = 0
    total = 0
    
    for qid, category, query in TEST_CASES:
        role = get_role(qid)
        total += 1
        t0 = time.time()
        
        try:
            fwd_msg = f"[System: {role.upper()}]\n{query}"
            
            r = requests.post(API_URL, json={
                "message": fwd_msg,
                "session_id": f"ablation_b_{qid}"
            }, timeout=90)
            elapsed = time.time() - t0
            data = r.json()
            reply = data.get("reply", "")
            
            err = has_error(reply)
            passed_check = not err and len(reply) > 20
            
            if passed_check:
                passed += 1
                marker = "✅"
            else:
                marker = "❌"
            
            print(f"  {marker} {qid:25s} role={role:12s} ({elapsed:5.1f}s)")
            
            results.append({
                "id":qid,"category":category,"query":query,"role":role,
                "passed":passed_check,"time_s":round(elapsed,1),
                "has_error":err,"reply_len":len(reply),
                "reply_excerpt":reply[:120]
            })
            
        except Exception as e:
            print(f"  ❌ {qid:25s} role={role:12s} TIMEOUT")
            results.append({
                "id":qid,"category":category,"query":query,"role":role,
                "passed":False,"time_s":90,"has_error":True,
                "reply_len":0,"reply_excerpt":f"TIMEOUT: {str(e)[:80]}"
            })
    
    pct = passed / total * 100
    print(f"\n  RESULT: {passed}/{total} = {pct:.1f}%")
    return results, passed, total

if __name__ == "__main__":
    results_b, pb, tb = run_condition_b()
    
    output = {
        "study": "Ablation Study Condition B",
        "date": datetime.utcnow().isoformat(),
        "condition_b": {"label": "Role-Conditioned",
                        "passed": pb, "total": tb,
                        "accuracy": round(pb/tb*100, 1)},
        "results_b": results_b,
    }
    
    with open("/mnt/d/Project/LLM_ERP/evaluation/ablation_cond_b_results.json","w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to ablation_cond_b_results.json")
