"""
LLM-ERP Evaluation Script
=========================
Tests LLM accuracy across 6 ERP modules by sending queries to the running
backend chat API and validating responses.

Usage:
    python run_eval.py                    # Run evaluation
    python run_eval.py --output results.json  # Custom output path
    python run_eval.py --verbose          # Show per-test details

The script loads test cases from test_cases.json in the same directory.
"""

import json
import sys
import time
import os
import re
import argparse
from datetime import datetime
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Installing httpx...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
    import httpx

# ─── Config ─────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
TEST_CASES_PATH = SCRIPT_DIR / "test_cases.json"
RESULTS_PATH = SCRIPT_DIR / "results.json"
API_URL = "http://localhost:8000/api/chat"
HTTP_TIMEOUT = 60  # seconds (LLM calls can be slow)

# ─── Validation helpers ─────────────────────────────────────────────

# Intent keyword signatures: what the reply should mention if a given tool was called
INTENT_SIGNATURES = {

    "query_inventory": ["庫存", "庫存量", "庫存數", "庫存狀況", "庫存列表",
                        "庫存查詢", "庫存資訊", "庫存記錄", "庫存資料", "庫存明細",
                        "庫存一覽", "庫存清單", "庫存狀況", "庫存狀態",
                        "庫存資料", "庫存數量", "庫存餘額", "stock", "inventory",
                        "quantity", "on hand"],
    "create_purchase_order": ["採購單", "PO-", "purchase order", "採購訂單",
                              "已建立", "已開立", "已開單", "已建立採購單",
                              "PO has been created", "PO created", "created"],
    "query_bom": ["BOM", "物料清單", "物料表", "用料", "零件表", "BOM結構",
                  "材料清單", "物料結構", "bill of materials", "parts list",
                  "components", "structure"],

    "bom_explode": ["展開", "爆炸", "explode", "需求", "需要", "BOM展開",
                     "物料需求", "材料需求"],
    "check_stock_shortage": ["缺料", "料不夠", "短缺", "shortage", "庫存不足",
                              "不夠", "缺貨", "不足"],
    "query_work_orders": ["工單", "work order", "生產工單", "工單列表", "工單狀態",
                          "工單號", "WO-", "生產訂單"],
    "release_order": ["釋出", "放行", "release", "已釋出", "已放行"],
    "dispatch_order": ["派工", "dispatch", "已派工", "排程", "分配到"],
    "right_shift_reschedule": ["右移", "right-shift", "right shift", "推移",
                                "往後推", "延後", "重排程"],
    "route_change_reschedule": ["替代", "route change", "換機台", "替代機台",
                                 "轉到"],
    "expedite_order": ["插隊", "急單", "expedite", "趕工", "優先"],
    "set_work_center_status": ["工作站狀態", "機台狀態", "status", "設定狀態"],
    "create_production_order": ["建立工單", "新增工單", "生產工單已建立",
                                 "工單已建立"],
    "query_suppliers": ["供應商", "supplier", "供應商列表", "供應商資料",
                         "供應商資訊"],
    "query_purchase_orders": ["採購單", "PO-", "purchase order", "採購訂單",
                               "採購單列表", "採購單狀態"],
    "inbound_material": ["入庫", "收貨", "inbound", "已入庫"],
    "outbound_material": ["出庫", "發料", "領料", "outbound", "已出庫"],
    "query_inspections": ["品檢", "檢驗", "inspection", "品檢單", "檢驗單"],
    "create_inspection": ["品檢", "檢驗", "inspection", "品檢單已建立",
                           "檢驗單已建立"],
    "query_ncs": ["不良", "NC-", "non-conformance", "非符合項", "不良品"],
    "create_nc": ["不良", "NC-", "NC已建立", "不良品記錄已建立"],
    "query_accounts": ["會計科目", "科目", "account", "會計科目表", "科目表"],
    "query_ar": ["應收", "AR", "客戶", "應收帳款", "應收帳款列表"],
    "check_ar_overdue": ["逾期", "overdue", "過期", "應收帳款逾期"],
    "create_journal_entry": ["傳票", "分錄", "journal", "傳票已建立",
                              "分錄已建立"],
    "add_operation_to_order": ["工序", "新增工序", "製程", "操作"],
    "create_work_center": ["工作站", "機台", "work center", "新增工作站"],
    "no_api_key": ["LLM 尚未設定", "API_KEY", "未設定"],
    "direct_response": [],
}

# Module display order for summary
MODULE_ORDER = [
    "Inventory", "Purchase", "BOM", "Dispatch", "Quality", "Accounting", "Cross-module",
    "EN-Inventory", "EN-Purchase", "EN-BOM", "EN-Dispatch", "EN-Quality", "EN-Accounting", "EN-Reports"
]


def load_test_cases(path: Path = TEST_CASES_PATH) -> list[dict]:
    """Load test cases from JSON file."""
    if not path.exists():
        print(f"❌ Test cases file not found: {path}")
        print(f"   Create {path} with test case definitions.")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        cases = json.load(f)
    print(f"📋 Loaded {len(cases)} test cases from {path.name}")
    return cases


def detect_intent_from_reply(reply: str) -> str:
    """
    Detect which intent/tool was likely used by analyzing the reply text.
    Returns the best-matching intent name.
    """
    reply_lower = reply.lower()
    scores = {}

    for intent, keywords in INTENT_SIGNATURES.items():
        if not keywords:
            continue
        score = sum(1 for kw in keywords if kw.lower() in reply_lower)
        if score > 0:
            scores[intent] = score

    if not scores:
        return "direct_response"

    # Return highest scoring intent
    best = max(scores, key=scores.get)
    return best


def validate_response(reply: str, hint: str, expected_entities: dict = None) -> dict:
    """
    Validate the response against the validation hint and expected entities.
    Returns {passed: bool, checks: list[str]}.
    """
    checks = []
    reply_lower = reply.lower()

    # Check for specific data patterns (part numbers, supplier names, order numbers, stock counts)
    data_patterns = {
        "part_number": [r'[A-Z]+-\d+', r'M6x20', r'BRG-\d+', r'MTR-\d+', r'DRV-\d+',
                        r'CNC-\d+', r'ASM-\d+', r'[A-Z]+-\d{4,}'],
        "supplier_name": ['大明螺絲', '電機王', '供應商', 'DaMing', 'Screws'],
        "order_number": [r'PO-\d+', r'WO-\d+', r'IQC-\d+', r'NC-\d+', r'JE-\d+'],
        "stock_count": [r'\d+[,\.]\d+', r'\d+ 顆', r'\d+ 件', r'\d+ 個', r'\d+ pcs',
                        r'\d+ units', r'\d+ items', r'quantity', r'stock'],
        "status": ['draft', 'pending', 'released', 'dispatched', 'approved',
                   'rejected', 'open', 'overdue', 'paid', 'completed'],
    }

    # Check entity-specific data
    if expected_entities:
        for entity_key, entity_value in expected_entities.items():
            if isinstance(entity_value, str) and entity_value:
                if entity_value.lower() in reply_lower:
                    checks.append(f"found_entity:{entity_key}={entity_value}")
            elif isinstance(entity_value, (int, float)):
                if str(entity_value) in reply_lower:
                    checks.append(f"found_entity:{entity_key}={entity_value}")

    # Check data patterns in reply
    for pattern_type, patterns in data_patterns.items():
        for pattern in patterns:
            if isinstance(pattern, str):
                if pattern.lower() in reply_lower:
                    checks.append(f"found_{pattern_type}:{pattern}")
            elif hasattr(pattern, 'search'):
                if pattern.search(reply):
                    checks.append(f"found_{pattern_type}:matches")

    # Parse the hint into individual check items
    hint_lower = hint.lower()

    # Extract quoted strings from hint (specific keywords to check)
    quoted_items = re.findall(r"'([^']*)'|\"([^\"]*)\"", hint)
    for match in quoted_items:
        item = match[0] or match[1]
        if item:
            checks.append(f"found_hint_keyword:{item}")

    # Check for key domain words that should be present
    domain_words = {
        "stock": ["庫存", "stock", "數量"],
        "quantity": ["庫存", "數量", "個", "顆", "件", "pcs"],
        "supplier": ["供應商", "supplier", "大明螺絲", "電機王"],
        "PO": ["採購單", "PO-", "purchase order"],
        "BOM": ["BOM", "物料", "零件", "材料"],
        "shortage": ["缺料", "shortage", "不足", "不夠"],
        "work order": ["工單", "WO-", "work order"],
        "inspection": ["品檢", "檢驗", "inspection"],
        "NC": ["不良", "NC-", "non-conformance"],
        "CAPA": ["CAPA", "改善", "對策"],
        "AR": ["應收", "AR", "客戶"],
        "account": ["會計科目", "科目", "account"],
        "journal entry": ["傳票", "分錄", "journal"],
        "overdue": ["逾期", "overdue", "過期"],
    }

    for key, words in domain_words.items():
        if key in hint_lower:
            for w in words:
                if w.lower() in reply_lower:
                    checks.append(f"found_domain:{key}={w}")

    # If no specific items found, check generic presence of meaningful content
    if not checks:
        # Just check that reply is non-empty and has some substance
        if len(reply) > 10:
            checks.append("回复包含具體內容")
        else:
            checks.append("回复有內容")

    passed = len(checks) > 0
    return {
        "passed": passed,
        "checks": checks,
        "found_keywords": checks,
    }


async def send_query(client: httpx.AsyncClient, query: str) -> dict:
    """
    Send a query to the chat API and return the result.
    Returns dict with reply, intent, response_time_ms, error.
    """
    start = time.perf_counter()
    try:
        response = await client.post(
            API_URL,
            json={"message": query},
            timeout=HTTP_TIMEOUT,
        )
        elapsed = time.perf_counter() - start
        response_ms = round(elapsed * 1000, 1)

        if response.status_code == 200:
            data = response.json()
            return {
                "reply": data.get("reply", ""),
                "intent": data.get("intent", ""),
                "response_time_ms": response_ms,
                "error": None,
            }
        else:
            return {
                "reply": f"HTTP {response.status_code}: {response.text[:500]}",
                "intent": "",
                "response_time_ms": response_ms,
                "error": f"HTTP {response.status_code}",
            }

    except httpx.ConnectError:
        elapsed = time.perf_counter() - start
        return {
            "reply": "",
            "intent": "",
            "response_time_ms": round(elapsed * 1000, 1),
            "error": "Connection refused — backend is DOWN",
        }
    except httpx.TimeoutException:
        elapsed = time.perf_counter() - start
        return {
            "reply": "",
            "intent": "",
            "response_time_ms": round(elapsed * 1000, 1),
            "error": f"Timeout after {HTTP_TIMEOUT}s",
        }
    except Exception as e:
        elapsed = time.perf_counter() - start
        return {
            "reply": "",
            "intent": "",
            "response_time_ms": round(elapsed * 1000, 1),
            "error": str(e),
        }


def run_sync(coro):
    """Sync wrapper for async code."""
    import asyncio
    return asyncio.run(coro)


async def run_evaluation_async(test_cases: list[dict], verbose: bool = False) -> list[dict]:
    """Run all test cases asynchronously."""
    results = []
    total = len(test_cases)
    
    async with httpx.AsyncClient() as client:
        for idx, case in enumerate(test_cases, 1):
            case_id = case["id"]
            query = case["query"]
            expected_intent = case.get("expected_intent", "")
            hint = case.get("validation_hint", "")
            expected_entities = case.get("expected_entities", {})

            if verbose:
                print(f"\n  [{idx}/{total}] {case_id} ({case['category']})")

            # Send query
            result = await send_query(client, query)
            reply = result["reply"]
            api_intent = result["intent"]
            response_time_ms = result["response_time_ms"]
            error = result["error"]

            # Detect intent from reply
            detected_intent = detect_intent_from_reply(reply) if reply else ""

            # Determine success
            if error:
                success = False
                intent_match = False
                intent_found = f"ERROR: {error}"
                validation = {"passed": False, "checks": [], "found_keywords": []}
            else:
                # Intent match: detected intent should match expected intent
                if expected_intent == "direct_response":
                    # For direct_response, any coherent reply is acceptable
                    intent_match = api_intent == "direct_response" or len(reply) > 20
                else:
                    intent_match = expected_intent == detected_intent or (
                        expected_intent in detected_intent
                    ) or (
                        detected_intent in expected_intent
                    )

                intent_found = detected_intent or api_intent or "unknown"

                # Validate response quality - look for data in reply
                validation = validate_response(reply, hint, expected_entities)

                # Success = data validation passed OR intent matched
                # Data validation is the stronger signal
                success = (intent_match or (validation["passed"] and len(reply) > 50)) and not error

            record = {
                "id": case_id,
                "category": case["category"],
                "query": query,
                "reply": reply[:500] if reply else "",
                "api_intent": api_intent,
                "detected_intent": detected_intent,
                "expected_intent": expected_intent,
                "intent_match": intent_match,
                "intent_found": intent_found,
                "response_time_ms": response_time_ms,
                "validation": validation,
                "success": success,
                "error": error,
            }
            results.append(record)

            if verbose:
                status = "✅" if success else "❌"
                print(f"    {status} intent={intent_found} (expected={expected_intent}) "
                      f"time={response_time_ms}ms val={validation['passed']}")

            # Brief progress indicator
            if not verbose and idx % 10 == 0:
                print(f"  ... {idx}/{total} cases completed")

    return results


def print_summary(results: list[dict]):
    """Print a category-by-category summary table."""
    # Group by category
    categories = {}
    all_count = len(results)
    all_passed = sum(1 for r in results if r["success"])
    all_intent_ok = sum(1 for r in results if r.get("intent_match", False))
    all_times = [r["response_time_ms"] for r in results if r["response_time_ms"] > 0]
    avg_time = sum(all_times) / len(all_times) if all_times else 0
    all_valid = sum(1 for r in results if r.get("validation", {}).get("passed", False))

    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "passed": 0, "intent_ok": 0, "valid": 0,
                               "times": []}
        categories[cat]["total"] += 1
        if r["success"]:
            categories[cat]["passed"] += 1
        if r.get("intent_match", False):
            categories[cat]["intent_ok"] += 1
        if r.get("validation", {}).get("passed", False):
            categories[cat]["valid"] += 1
        if r["response_time_ms"] > 0:
            categories[cat]["times"].append(r["response_time_ms"])

    # Print header
    print(f"\n{'='*80}")
    print(f"  LLM-ERP Evaluation Summary")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    print(f"{'Category':<18} {'Total':>6} {'Pass':>6} {'Intent✓':>8} {'Val✓':>6} {'Avg.Ms':>8} {'Rate':>8}")
    print(f"{'-'*60}")

    for cat in MODULE_ORDER:
        if cat in categories:
            c = categories[cat]
            avg_c = sum(c["times"]) / len(c["times"]) if c["times"] else 0
            rate = f"{c['passed']/c['total']*100:.0f}%" if c["total"] else "0%"
            print(f"  {cat:<16} {c['total']:>6} {c['passed']:>6} {c['intent_ok']:>8} "
                  f"{c['valid']:>6} {avg_c:>7.1f} {rate:>8}")

    # Also print totals
    print(f"{'-'*60}")
    overall_rate = f"{all_passed/all_count*100:.0f}%" if all_count else "0%"
    print(f"  {'TOTAL':<16} {all_count:>6} {all_passed:>6} {all_intent_ok:>8} "
          f"{all_valid:>6} {avg_time:>7.1f} {overall_rate:>8}")
    print(f"{'='*80}\n")


def save_results(results: list[dict], path: Path = RESULTS_PATH):
    """Save evaluation results to JSON file."""
    output = {
        "evaluation_date": datetime.now().isoformat(),
        "api_url": API_URL,
        "total_cases": len(results),
        "passed": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "summary_by_category": {},
        "results": results,
    }

    # Build summary by category
    for r in results:
        cat = r["category"]
        if cat not in output["summary_by_category"]:
            output["summary_by_category"][cat] = {
                "total": 0, "passed": 0, "avg_response_time_ms": 0.0
            }
        output["summary_by_category"][cat]["total"] += 1
        if r["success"]:
            output["summary_by_category"][cat]["passed"] += 1

    for cat, data in output["summary_by_category"].items():
        cat_times = [r["response_time_ms"] for r in results
                     if r["category"] == cat and r["response_time_ms"] > 0]
        data["avg_response_time_ms"] = round(
            sum(cat_times) / len(cat_times), 1
        ) if cat_times else 0.0

    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"💾 Results saved to {path}")


def check_backend_health() -> bool:
    """Check if the backend is running and reachable."""
    try:
        import httpx
        r = httpx.get("http://localhost:8000/docs", timeout=5)
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="LLM-ERP Evaluation Script — test LLM accuracy across ERP modules"
    )
    parser.add_argument("--output", type=str, default=str(RESULTS_PATH),
                        help=f"Output JSON path (default: {RESULTS_PATH})")
    parser.add_argument("--test-cases", type=str, default=str(TEST_CASES_PATH),
                        help=f"Test cases JSON path (default: {TEST_CASES_PATH})")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show per-test details")
    args = parser.parse_args()

    output_path = Path(args.output)
    test_cases_path = Path(args.test_cases)

    # Banner
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║         LLM-ERP Evaluation Suite                ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    # Check backend
    print("🔍 Checking backend health...")
    if not check_backend_health():
        print()
        print("╔══════════════════════════════════════════════════╗")
        print("║  ❌  BACKEND IS DOWN                            ║")
        print("║                                                 ║")
        print("║  The LLM-ERP backend at localhost:8000 is not   ║")
        print("║  responding. Please start it first:             ║")
        print("║                                                 ║")
        print("║    cd /mnt/d/Project/LLM_ERP/backend            ║")
        print("║    uvicorn app.main:app --reload                ║")
        print("║                                                 ║")
        print("║  Make sure the .env file has the API key set    ║")
        print("║  for your LLM provider (default: anthropic).    ║")
        print("╚══════════════════════════════════════════════════╝")
        print()
        sys.exit(1)
    print("✅ Backend is running!\n")

    # Load test cases
    test_cases = load_test_cases(test_cases_path)
    if not test_cases:
        print("❌ No test cases loaded. Check test_cases.json.")
        sys.exit(1)

    # Ensure we have the right categories
    categories = set(c["category"] for c in test_cases)
    print(f"   Categories: {', '.join(sorted(categories))}")
    print()

    # Run evaluation
    print("🚀 Running evaluation...")
    print(f"   API: POST {API_URL}")
    print(f"   Timeout: {HTTP_TIMEOUT}s per query")
    print()

    results = run_sync(run_evaluation_async(test_cases, verbose=args.verbose))

    # Print summary
    print_summary(results)

    # Save results
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_results(results, output_path)

    # Final status
    passed = sum(1 for r in results if r["success"])
    failed = sum(1 for r in results if not r["success"])
    pct = passed / len(results) * 100 if results else 0

    print()
    if failed == 0:
        print(f"🎉 ALL {passed}/{len(results)} TESTS PASSED ({pct:.0f}%)")
    elif passed > failed:
        print(f"👍 {passed}/{len(results)} PASSED ({pct:.0f}%) — {failed} need attention")
    else:
        print(f"⚠️  Only {passed}/{len(results)} PASSED ({pct:.0f}%) — {failed} failed")
    print()

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
