#!/usr/bin/env python3
"""Generate 20 scenarios × 3 factory types = 60 simulation datasets for LLM-ERP.
   Factory types: MTO (Make-to-Order), MTS (Make-to-Stock), ETO (Engineer-to-Order)
   Output: JSON file with scenario definitions for the job simulator.
"""
import json, os
from datetime import datetime, timedelta

OUTPUT = os.path.join(os.path.dirname(__file__), "..", "benchmark_scenarios.json")

# ─── 3 Factory Types ───────────────────────────────────────────────
FACTORIES = {
    "MTO": {
        "name": "Make-to-Order (接單生產)",
        "desc": "高混線、低產量、多品種 — 如工具機、特殊設備",
        "n_machines": (50, 200),
        "n_groups": (6, 12),
        "ops_per_order": (5, 15),
        "n_orders": (5, 20),
        "due_date_window": (7, 30),
        "rush_pct": 0.15,
    },
    "MTS": {
        "name": "Make-to-Stock (庫存生產)",
        "desc": "低混線、高產量、少品種 — 如螺絲、標準零件、包材",
        "n_machines": (30, 100),
        "n_groups": (4, 8),
        "ops_per_order": (3, 8),
        "n_orders": (10, 50),
        "due_date_window": (14, 60),
        "rush_pct": 0.05,
    },
    "ETO": {
        "name": "Engineer-to-Order (設計生產)",
        "desc": "極度客製、專案式、高複雜度 — 如自動化設備、專用機",
        "n_machines": (80, 300),
        "n_groups": (8, 15),
        "ops_per_order": (10, 30),
        "n_orders": (3, 10),
        "due_date_window": (30, 90),
        "rush_pct": 0.25,
    },
}

# ─── 20 Scenario Themes ────────────────────────────────────────────
SCENARIOS = [
    # (name_en, name_zh, description, special_condition)
    ("normal_load", "正常負載", "一般生產排程，無特殊事件", {}),
    ("high_load", "高負載", "訂單量為正常 2 倍，產能緊繃", {"load_mult": 2.0}),
    ("low_load", "低負載", "訂單量為正常 50%，產能過剩", {"load_mult": 0.5}),
    ("rush_orders", "急單湧入", "大量急單穿插，需重新排程", {"rush_pct_mult": 3.0}),
    ("bottleneck_shift", "瓶頸機台轉移", "主要瓶頸機台故障，負載轉移", {"bottleneck_fail_pct": 0.3}),
    ("machine_breakdown", "機台故障", "關鍵機台故障 3 天，產能損失", {"breakdown_days": 3}),
    ("material_shortage", "原物料短缺", "關鍵物料延遲到貨 5 天", {"material_delay_days": 5}),
    ("quality_hold", "品質扣留", "批量產品 QC 不合格，全線扣留", {"qc_fail_pct": 0.2}),
    ("supplier_late", "供應商延遲", "T1 供應商全面延遲一週", {"supplier_delay_days": 7}),
    ("labor_shortage", "人力短缺", "產線人員不足，產能降載 30%", {"labor_factor": 0.7}),
    ("seasonal_spike", "季節性高峰", "旺季訂單量暴增 3 倍", {"load_mult": 3.0, "rush_pct_mult": 2.0}),
    ("new_product_ramp", "新產品導入", "新產品上線，良率不穩導致重工", {"rework_pct": 0.3}),
    ("order_cancel", "大量訂單取消", "客戶取消 30% 訂單，需調整排程", {"cancel_pct": 0.3}),
    ("order_split", "訂單分批出貨", "大單拆分為多批，每批間隔 2 天", {"split_batches": 3, "split_gap_days": 2}),
    ("multi_priority", "多級優先權", "訂單分 A/B/C 三級優先權」，A優先生産", {"priority_levels": 3}),
    ("engineering_change", "設變通知", "客戶設變，已投產需調整 BOM", {"eco_pct": 0.2}),
    ("expedite_all", "全面趕工", "所有訂單提前一週交貨", {"expedite_days": -7}),
    ("slow_period", "淡季減產", "訂單量僅正常 30%", {"load_mult": 0.3}),
    ("mix_shift", "產品組合轉換", "產品 A 急降 60%，產品 B 急增 200%", {"mix_shift_pct": 0.6}),
    ("disaster_recovery", "災後復原", "停電 2 天後復工，所有訂單延遲", {"downtime_days": 2}),
]

def generate_scenario(scenario, factory_type, idx):
    """Generate a scenario config dict."""
    f = FACTORIES[factory_type]
    cond = dict(scenario[3])
    
    n_m = f["n_machines"][0] + (f["n_machines"][1] - f["n_machines"][0]) * ((idx % 5) / 4)
    n_g = f["n_groups"][0] + (f["n_groups"][1] - f["n_groups"][0]) * ((idx % 3) / 2)
    load = cond.get("load_mult", 1.0)
    n_o = int((f["n_orders"][0] + (f["n_orders"][1] - f["n_orders"][0]) * 0.5) * load)
    rush = cond.get("rush_pct_mult", 1.0) * f["rush_pct"]
    
    return {
        "id": f"{factory_type}_{idx+1:02d}",
        "factory_type": factory_type,
        "scenario_name_en": scenario[0],
        "scenario_name_zh": scenario[1],
        "description": scenario[2],
        "machine_group_count": int(n_g),
        "total_machines": int(n_m),
        "n_orders": max(3, n_o),
        "ops_per_order": f["ops_per_order"],
        "due_date_window_days": f["due_date_window"],
        "rush_order_pct": round(rush, 2),
        "special_conditions": cond,
        "created_at": datetime.utcnow().isoformat(),
    }

def main():
    scenarios = []
    for factory_type in ["MTO", "MTS", "ETO"]:
        for idx, scenario in enumerate(SCENARIOS):
            s = generate_scenario(scenario, factory_type, idx)
            scenarios.append(s)
    
    output = {
        "meta": {
            "total": len(scenarios),
            "factory_types": list(FACTORIES.keys()),
            "scenarios_per_type": len(SCENARIOS),
            "created_at": datetime.utcnow().isoformat(),
        },
        "factories": FACTORIES,
        "scenarios": scenarios,
    }
    
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已產生 {len(scenarios)} 組模擬情境 ({len(SCENARIOS)} 情境 × {len(FACTORIES)} 工廠型態)")
    print(f"   檔案: {OUTPUT}")
    for ft in FACTORIES:
        count = sum(1 for s in scenarios if s["factory_type"] == ft)
        print(f"   {ft}: {count} 組")

if __name__ == "__main__":
    main()
