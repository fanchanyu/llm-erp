#!/bin/bash
# 戰情室種子資料 — 第二階段（補 NC + 確認數據）
API="http://localhost:8000/api"

echo "=== 取得料件 ID (直接查 DB) ==="
cd /mnt/d/Project/LLM_ERP/backend
AL_ID=$(python3 -c "import sqlite3; c=sqlite3.connect('llm_erp.db'); print(c.execute(\"SELECT id FROM parts WHERE part_no='AL-001'\").fetchone()[0]); c.close()")
ASM_ID=$(python3 -c "import sqlite3; c=sqlite3.connect('llm_erp.db'); print(c.execute(\"SELECT id FROM parts WHERE part_no='ASM-001'\").fetchone()[0]); c.close()")
RM_ID=$(python3 -c "import sqlite3; c=sqlite3.connect('llm_erp.db'); print(c.execute(\"SELECT id FROM parts WHERE part_no='RM-001'\").fetchone()[0]); c.close()")

echo "  AL-001: $AL_ID"
echo "  ASM-001: $ASM_ID"
echo "  RM-001: $RM_ID"

echo ""
echo "=== 品質異常單 ==="
curl -s -X POST "$API/quality/ncs" \
  -H 'Content-Type: application/json' \
  -d "{\"nc_no\":\"NC-20260513-001\",\"part_id\":\"$AL_ID\",\"defect_code\":\"DIM-OUT\",\"description\":\"鋁板尺寸超差0.5mm\",\"severity\":\"major\",\"created_by\":\"qa\"}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  ✅ NC: {d.get('nc_no','?')}\")" 2>/dev/null

curl -s -X POST "$API/quality/ncs" \
  -H 'Content-Type: application/json' \
  -d "{\"nc_no\":\"NC-20260513-002\",\"part_id\":\"$ASM_ID\",\"defect_code\":\"SUR-SCRATCH\",\"description\":\"總成表面刮傷\",\"severity\":\"minor\",\"created_by\":\"qa\"}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  ✅ NC: {d.get('nc_no','?')}\")" 2>/dev/null

curl -s -X POST "$API/quality/ncs" \
  -H 'Content-Type: application/json' \
  -d "{\"nc_no\":\"NC-20260513-003\",\"part_id\":\"$RM_ID\",\"defect_code\":\"MAT-SOFT\",\"description\":\"鋼板硬度不足HRC32<要求HRC38\",\"severity\":\"critical\",\"created_by\":\"qa\"}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  ✅ NC: {d.get('nc_no','?')}\")" 2>/dev/null

echo ""
echo "=== 模擬更多事件 ==="
for evt in material.received purchase_order.created non_conformance.created material.issued work_order.released payment.received; do
  RESP=$(curl -s -X POST "$API/events/simulate/$evt")
  echo "  ✅ $evt"
  sleep 0.3
done

echo ""
echo "=== 最後確認 ==="
echo "--- 庫存 ---"
curl -s "$API/inventory/stock" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  共 {d.get(\"total\",len(d.get(\"items\",[])))} 項')"
echo "--- 應收帳款 ---"
curl -s "$API/accounting/ar" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  共 {d.get(\"total\",0)} 筆, AR金額總計: NT\${sum(float(i[\"amount\"]) for i in d.get(\"items\",[])):,.0f}')"
echo "--- 品質異常 ---"
curl -s "$API/quality/ncs" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  共 {d.get(\"total\",0)} 筆')"
echo "--- 採購單 ---"
curl -s "$API/purchase/orders" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  共 {d.get(\"total\",0)} 筆')"
echo "--- 事件 ---"
curl -s "$API/events/activity?limit=20" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  共 {len(d.get(\"events\",[]))} 筆')"

echo ""
echo "✅ 戰情室種子資料完成！重整頁面即可查看"