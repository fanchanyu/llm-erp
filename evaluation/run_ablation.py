"""
Ablation Study Runner — Role Conditioning vs Generic Baseline
"""
import requests, json, time, sys, math
from datetime import datetime

API_URL = "http://localhost:8000/api/chat"
RESULTS_DIR = "/mnt/d/Project/LLM_ERP/evaluation"

# ── 30 Test Cases from original evaluation ──
TEST_CASES = [
    # Inventory (Warehouse Keeper)
    ("inv-stock-01","Inventory","M6x20螺絲還有多少庫存？","query_inventory"),
    ("inv-stock-02","Inventory","我想查一下軸承BRG-001的庫存量","query_inventory"),
    ("inv-stock-03","Inventory","幫我看一下全部庫存列表","query_inventory"),
    ("inv-stock-04","Inventory","傳動件有哪些零件？庫存夠嗎？","query_inventory"),
    ("inv-stock-05","Inventory","查一下馬達類零件的庫存狀況","query_inventory"),
    # Purchase (Purchasing Agent)
    ("pur-create-po-01","Purchase","幫我開一張採購單，向大明螺絲買 M6x20螺絲 200顆，單價0.5元","create_purchase_order"),
    ("pur-list-po-02","Purchase","目前有哪些採購單？列出所有PO","query_purchase_orders"),
    ("pur-supplier-03","Purchase","查一下供應商大明螺絲的資料","query_suppliers"),
    ("pur-status-04","Purchase","PO-20260505-001這張採購單的狀態是什麼？","query_purchase_orders"),
    ("pur-receipt-05","Purchase","幫我收貨，PO-20260505-001 的 M6x20入庫200顆","inbound_material"),
    # BOM (Production Controller)
    ("bom-query-01","BOM","ASM-001自動鎖螺絲機基座用了哪些零件？","query_bom"),
    ("bom-explode-02","BOM","ASM-001要做5台，需要多少料？幫我展開BOM","bom_explode"),
    ("bom-multi-03","BOM","CNC-001小型CNC銑床的BOM結構是怎樣的？多階展開給我看","query_bom"),
    ("bom-shortage-04","BOM","CNC-001要做5台，料夠不夠？幫我檢查缺料","check_stock_shortage"),
    # Dispatch (Production Controller)
    ("disp-list-01","Dispatch","目前有哪些工單？列出所有生產工單","query_work_orders"),
    ("disp-release-02","Dispatch","幫我釋出工單 WO-20260506-001","release_order"),
    ("disp-status-03","Dispatch","查一下WO-20260506-001這張工單的狀態","query_work_orders"),
    ("disp-dispatch-04","Dispatch","WO-20260506-001已經釋出了，幫我派工排程","dispatch_order"),
    ("disp-resched-05","Dispatch","CNC-01機台故障了，需要維修，幫我把後面的工序往後推30分鐘","right_shift_reschedule"),
    # Quality (Quality Inspector)
    ("qual-list-insp-01","Quality","列出所有品檢單，我要看目前的檢驗記錄","query_inspections"),
    ("qual-create-insp-02","Quality","新增一張品檢單，檢驗M6x20螺絲，數量500顆，批號LOT-B001","create_inspection"),
    ("qual-list-nc-03","Quality","有哪些不良品記錄(非符合項)？列出所有NC","query_ncs"),
    ("qual-capa-04","Quality","NC-20260505-001的改善對策是什麼？幫我建立CAPA","direct_response"),
    # Accounting (Accountant)
    ("acct-list-ar-01","Accounting","目前有哪些應收帳款？列出所有AR","query_ar"),
    ("acct-list-accounts-02","Accounting","查詢會計科目表，列出所有會計科目","query_accounts"),
    ("acct-create-entry-03","Accounting","幫我建立一筆傳票：原料庫存增加550元，應付帳款增加550元","create_journal_entry"),
    ("acct-overdue-04","Accounting","有哪些超過繳款期限的應收帳款？","check_ar_overdue"),
    ("acct-list-gl-05","Accounting","查詢2026年5月的總帳分錄記錄","direct_response"),
    # Cross-module (Factory Director)
    ("cross-multi-01","Cross-module","我要生產5台CNC-001，先幫我檢查料夠不夠，如果不夠就開採購單補料","check_stock_shortage"),
    ("cross-multi-02","Cross-module","我想了解ASM-001的BOM結構，順便檢查庫存量夠不夠做3台","query_bom"),
]

# ── Role-to-query mapping ──
ROLE_MAP = {
    "Warehouse Keeper":    ["inv-stock-01","inv-stock-02","inv-stock-03","inv-stock-04","inv-stock-05"],
    "Purchasing Agent":    ["pur-create-po-01","pur-list-po-02","pur-supplier-03","pur-status-04","pur-receipt-05"],
    "Production Controller": ["bom-query-01","bom-explode-02","bom-multi-03","bom-shortage-04",
                              "disp-list-01","disp-release-02","disp-status-03","disp-dispatch-04","disp-resched-05"],
    "Quality Inspector":   ["qual-list-insp-01","qual-create-insp-02","qual-list-nc-03","qual-capa-04"],
    "Accountant":          ["acct-list-ar-01","acct-list-accounts-02","acct-create-entry-03","acct-overdue-04","acct-list-gl-05"],
    "Factory Director":    ["cross-multi-01","cross-multi-02"],
}

# ── Expected intents (ground truth) ──
ID_TO_INTENT = {tc[0]: tc[3] for tc in TEST_CASES}

def evaluate_response(qid, reply, api_intent):
    """Check if response contains the expected business data."""
    expected = ID_TO_INTENT.get(qid, "")
    reply_lower = reply.lower()
    
    # Domain-specific validation
    domain = qid.split("-")[0]
    
    if domain == "inv":
        # Must contain stock quantity number
        return any(kw in reply for kw in ["庫存", "數量", "顆", "pcs"]) and \
               any(c.isdigit() for c in reply[:100])
    
    elif domain == "pur":
        if "create" in qid or "receipt" in qid:
            return any(kw in reply for kw in ["PO-", "採購單", "收貨", "入庫"])
        return any(kw in reply for kw in ["大明螺絲", "供應商", "PO-", "採購單"])
    
    elif domain == "bom":
        if "shortage" in qid:
            return any(kw in reply for kw in ["缺料", "不足", "shortage", "夠"])
        return any(kw in reply for kw in ["ASM-001", "CNC-001", "BOM", "展開", "結構"])
    
    elif domain == "disp":
        if "release" in qid or "dispatch" in qid:
            return any(kw in reply for kw in ["WO-", "釋出", "派工", "排程"])
        if "resched" in qid:
            return any(kw in reply for kw in ["重排", "推移", "CNC-01"])
        return any(kw in reply for kw in ["WO-", "工單"])
    
    elif domain == "qual" or domain == "acct":
        if "create" in qid or "entry" in qid:
            return any(kw in reply for kw in ["建立", "新增", "創建", "created"])
        return len(reply) > 20  # General response is OK
    
    elif domain == "cross":
        return len(reply) > 30
    
    return True


def run_condition(label, session_prefix):
    """Run 30 queries and return results."""
    print(f"\n{'='*60}")
    print(f"CONDITION: {label}")
    print(f"{'='*60}")
    
    results = []
    passed = 0
    total = 0
    
    for qid, category, query, expected_intent in TEST_CASES:
        total += 1
        t0 = time.time()
        try:
            r = requests.post(API_URL, json={
                "message": query,
                "session_id": f"{session_prefix}_{qid}"
            }, timeout=60)
            elapsed = time.time() - t0
            data = r.json()
            reply = data.get("reply", "")
            api_intent = data.get("intent", "")
            
            # Determine pass/fail
            llm_failed = any(kw in reply for kw in [
                "抱歉", "無法", "error", "Error", "not available",
                "don't have", "can't", "cannot"
            ])
            passed_check = not llm_failed and len(reply) > 15
            
            status = "PASS" if passed_check else "FAIL"
            if passed_check:
                passed += 1
            
            results.append({
                "id": qid, "category": category, "query": query,
                "expected_intent": expected_intent, "api_intent": api_intent,
                "passed": passed_check, "time_s": round(elapsed, 1),
                "reply_excerpt": reply[:80]
            })
            
            if not passed_check:
                marker = "❌"
            else:
                marker = "✅"
            print(f"  {marker} {qid:25s} ({elapsed:5.1f}s) intent={api_intent or 'N/A':20s}")
            
        except Exception as e:
            print(f"  ❌ {qid:25s} ERROR: {str(e)[:60]}")
            results.append({
                "id": qid, "category": category, "query": query,
                "expected_intent": expected_intent, "api_intent": "ERROR",
                "passed": False, "time_s": 0, "reply_excerpt": str(e)[:80]
            })
    
    # Summary
    pct = passed / total * 100
    print(f"\n  {'─'*50}")
    print(f"  RESULT: {passed}/{total} = {pct:.1f}%")
    
    return results, passed, total


def main():
    print("ABLATION STUDY")
    print("Condition A: Generic SYSTEM_PROMPT (baseline)")
    print("Condition B: Role-Conditioned prompts (tool subsets)")
    
    # Run Condition A: Baseline (no modification needed - current system)
    results_a, pass_a, total_a = run_condition("A: Generic (Baseline)", "abl_a")
    
    print(f"\n\nBaseline complete: {pass_a}/{total_a}")
    print("Condition B requires modifying orchestrator SYSTEM_PROMPT.")
    print("Run the following before Condition B:")
    print("  1. Modify app/agents/orchestrator.py to use role-specific prompts")
    print("  2. Restart server")
    print("  3. Rerun with condition_label='B: Role-Conditioned'")
    
    # Save results
    output = {
        "study": "Ablation Study",
        "date": datetime.utcnow().isoformat(),
        "condition_a": {
            "label": "Generic (Baseline)",
            "passed": pass_a,
            "total": total_a,
            "accuracy": round(pass_a/total_a*100, 1)
        },
        "results_a": results_a,
    }
    
    with open(f"{RESULTS_DIR}/ablation_results.json", "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to ablation_results.json")

if __name__ == "__main__":
    main()
