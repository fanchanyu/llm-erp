"""
Ablation Study Script — Role Conditioning vs Generic Baseline
Compares:
  Condition A (Baseline): Generic SYSTEM_PROMPT (existing 93.3%)
  Condition B (Role-Conditioned): Prompt restricted to role's tool subset

Each query is assigned to the role that would perform the task:
  U_w Warehouse Keeper:  inv-stock-01~05 (5)
  U_b Purchasing Agent:  pur-* (5)
  U_p Production Controller:  bom-* + disp-* (9)
  U_q Quality Inspector:  qual-* (4)
  U_a Accountant:  acct-* (5)
  U_d Factory Director:  cross-* (2)
  U_s Sales Manager:  0 (not tested)
"""

# Role-to-query mapping
ROLE_QUERIES = {
    "Warehouse Keeper": ["inv-stock-01","inv-stock-02","inv-stock-03","inv-stock-04","inv-stock-05"],
    "Purchasing Agent": ["pur-create-po-01","pur-list-po-02","pur-supplier-03","pur-status-04","pur-receipt-05"],
    "Production Controller": ["bom-query-01","bom-explode-02","bom-multi-03","bom-shortage-04",
                              "disp-list-01","disp-release-02","disp-status-03","disp-dispatch-04","disp-resched-05"],
    "Quality Inspector": ["qual-list-insp-01","qual-create-insp-02","qual-list-nc-03","qual-capa-04"],
    "Accountant": ["acct-list-ar-01","acct-list-accounts-02","acct-create-entry-03","acct-overdue-04","acct-list-gl-05"],
    "Factory Director": ["cross-multi-01","cross-multi-02"],
}

# Role-specific tool subsets
ROLE_TOOLS_W = ["query_inventory", "inbound_material", "outbound_material"]
ROLE_TOOLS_B = ["query_suppliers", "create_purchase_order", "query_purchase_orders", "inbound_material"]
ROLE_TOOLS_P = ["query_bom", "bom_explode", "check_stock_shortage", "query_work_orders",
                "release_order", "dispatch_order", "right_shift_reschedule", "route_change_reschedule",
                "expedite_order", "create_work_center", "add_operation_to_order", "set_work_center_status",
                "create_production_order"]
ROLE_TOOLS_Q = ["query_inspections", "create_inspection", "query_ncs", "create_nc"]
ROLE_TOOLS_A = ["query_accounts", "query_ar", "check_ar_overdue", "create_journal_entry"]
ROLE_TOOLS_D = ["query_inventory", "query_purchase_orders", "query_work_orders",
                "query_inspections", "query_ncs", "query_ar", "query_accounts",
                "query_suppliers", "query_bom", "check_stock_shortage",
                "right_shift_reschedule", "route_change_reschedule", "expedite_order",
                "check_cash_position", "query_customers", "query_sales_orders"]

import json

print("=== ABLATION STUDY DESIGN ===")
print("\nCondition A (Baseline): Generic SYSTEM_PROMPT (all 30+ tools)")
print(f"  Existing result: 28/30 = 93.3%")
print()
print("Condition B: Role-Conditioned Prompt (tool subset per role)")
for role, queries in ROLE_QUERIES.items():
    if role == "Warehouse Keeper":
        tools = ROLE_TOOLS_W
    elif role == "Purchasing Agent":
        tools = ROLE_TOOLS_B
    elif role == "Production Controller":
        tools = ROLE_TOOLS_P
    elif role == "Quality Inspector":
        tools = ROLE_TOOLS_Q
    elif role == "Accountant":
        tools = ROLE_TOOLS_A
    elif role == "Factory Director":
        tools = ROLE_TOOLS_D
    print(f"  {role}: {len(queries)} queries, {len(tools)} tools")
    for q in queries:
        print(f"    - {q}")
print()
print(f"Total queries: {sum(len(q) for q in ROLE_QUERIES.values())}")
print()
print("=== HYPOTHESES ===")
print("H1: Role-conditioned prompts with restricted tool subsets will")
print("    reduce tool-selection errors (fewer wrong tool calls)")
print("H2: BOM/Cross-module accuracy should improve because irrelevant")
print("    tools are excluded from the prompt")
print("H3: Accounting (Gemma4) should improve because the prompt")
print("    focuses on just 4 accounting tools instead of 30+")
print()
print("=== Experiment Protocol ===")
print("1. For each query in Condition B:")
print("   a. Identify the query's role from ROLE_QUERIES")
print("   b. Generate a role-specific system prompt (tool subset)")
print("   c. Send query through /api/chat with modified prompt")
print("   d. Record pass/fail + response time")
print("2. Compare Condition A vs Condition B results")
print("3. Statistical test: McNemar's test (paired binary outcomes)")
print("4. Effect size: Cohen's g for paired proportions")
print()
print("Expected outcome:")
print("  - If role conditioning helps: Condition B > 93.3%")
print("  - If role conditioning hurts: Condition B < 93.3%")
print("  - If no difference: Both ~93.3% (suggests tool subset alone")
print("    doesn't explain the accuracy)")
print()
print("Note: Current SYSTEM_PROMPT is already generic (no role conditioning).")
print("The original 30-query eval was done with ALL tools available.")
print("Condition B restricts tools PER ROLE.")
