"""
Expanded test set — adds CRM (Sales Manager) + edge cases
"""
import json, requests, time

API_URL = "http://localhost:8000/api/chat"

# ── New CRM test cases for Sales Manager role ──
CRM_CASES = [
    # Customer queries
    ("crm-cust-01","CRM","查詢客戶大明機械的資料", "query_customers"),
    ("crm-cust-02","CRM","列出所有客戶", "query_customers"),
    ("crm-cust-03","CRM","查詢客戶台灣工具機的聯絡人是誰", "query_customers"),
    # Sales Orders
    ("crm-so-01","CRM","查詢銷售訂單SO-20260501的狀態", "query_sales_orders"),
    ("crm-so-02","CRM","列出所有銷售訂單", "query_sales_orders"),
    # CRM Events
    ("crm-event-01","CRM","記錄一筆客戶互動：大明機械來電詢問交期", "create_customer_event"),
    # Contracts (if available - use decision_logs as proxy for CRM features)
    ("crm-decision-01","CRM","查詢過去的決策記錄", "query_decisions"),
    # Cross-module with CRM
    ("crm-cross-01","CRM","客戶大明機械想要追加一台CNC-001，查一下庫存夠不夠", "query_sales_orders"),
]

# ── Additional edge cases ──
EDGE_CASES = [
    # Edge: out-of-stock check
    ("edge-stock-01","Edge","零件CTL-001庫存剩下5顆，安全庫存2顆，夠不夠生產？", "query_inventory"),
    # Edge: supplier price query
    ("edge-price-01","Edge","大明螺絲的M6x20螺絲一顆多少錢？", "query_suppliers"),
    # Edge: work center status
    ("edge-wc-01","Edge","CNC-01機台現在的狀態是什麼？", "query_work_orders"),
    # Edge: cash position
    ("edge-cash-01","Edge","目前的現金水位是多少？", "check_cash_position"),
    # Edge: account balance
    ("edge-bal-01","Edge","原料庫存科目目前的餘額是多少？", "query_accounts"),
    # Edge: AR aging
    ("edge-ar-aging-01","Edge","應收帳款的分齡分析", "query_ar"),
    # Edge: lead management
    ("edge-lead-01","Edge","目前有哪些潛在客戶？", "query_customers"),
]

# Combine all
ALL_EXTRA = CRM_CASES + EDGE_CASES

def has_error(reply):
    error_patterns = [
        "抱歉，無法","error","Error","not available","don't have",
        "can't","cannot","資料庫結構","欄位問題","欄位遺失",
        "資料庫錯誤","系統端","問題需要排除","unavailable",
    ]
    r = reply.lower()
    return any(p.lower() in r for p in error_patterns)

print("=" * 55)
print("EXPANDED TEST SET — CRM + Edge Cases")
print(f"Total new cases: {len(ALL_EXTRA)}")
print("=" * 55)

results = []
passed = 0

for qid, category, query, expected in ALL_EXTRA:
    t0 = time.time()
    try:
        r = requests.post(API_URL, json={
            "message": query,
            "session_id": f"expand_{qid}"
        }, timeout=60)
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
        
        print(f"  {marker} {qid:25s} ({elapsed:5.1f}s) err={err}")
        print(f"        {reply[:100]}")
        
        results.append({
            "id":qid,"category":category,"query":query,
            "expected_intent":expected,"passed":passed_check,
            "time_s":round(elapsed,1),"reply_excerpt":reply[:120]
        })
        
    except Exception as e:
        print(f"  ❌ {qid:25s} TIMEOUT")
        results.append({
            "id":qid,"category":category,"query":query,
            "expected_intent":expected,"passed":False,
            "time_s":60,"reply_excerpt":f"TIMEOUT: {str(e)[:80]}"
        })

print(f"\n  Result: {passed}/{len(ALL_EXTRA)} = {passed/len(ALL_EXTRA)*100:.1f}%")

# Save
output = {
    "study": "Expanded Test Set",
    "date": __import__('datetime').datetime.utcnow().isoformat(),
    "total": len(ALL_EXTRA), "passed": passed,
    "accuracy": round(passed/len(ALL_EXTRA)*100, 1),
    "cases": results,
}
with open("/mnt/d/Project/LLM_ERP/evaluation/expanded_test_results.json","w") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"Saved to expanded_test_results.json")
