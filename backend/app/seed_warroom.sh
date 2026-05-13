#!/bin/bash
# 戰情室完整種子資料 — 直接 call API
# Usage: bash backend/app/seed_warroom.sh

API="http://localhost:8000/api"
echo "===== 戰情室種子資料 ====="

# ── 1. 新增料件 ──
echo ""
echo "--- 1. 料件 ---"
PARTS=(
  '{"part_no":"AL-001","name":"鋁板6061","unit":"pcs","category":"raw_material","spec":"600x400x3mm"}'
  '{"part_no":"ST-002","name":"不鏽鋼管","unit":"pcs","category":"raw_material","spec":"OD50x3mmx3000mm"}'
  '{"part_no":"CP-001","name":"銅排","unit":"pcs","category":"raw_material","spec":"100x10x3000mm"}'
  '{"part_no":"SF-001","name":"驅動軸-半成品","unit":"pcs","category":"semi","spec":"調質處理"}'
  '{"part_no":"ASM-001","name":"減速機總成","unit":"pcs","category":"finished","spec":"成品"}'
)
for p in "${PARTS[@]}"; do
  RESP=$(curl -s -X POST "$API/inventory/parts" -H 'Content-Type: application/json' -d "$p")
  PN=$(echo "$p" | python3 -c "import sys,json; print(json.load(sys.stdin)['part_no'])")
  if echo "$RESP" | grep -q '"id":'; then
    echo "  ✅ $PN"
  else
    echo "  ⚠️  $PN (可能已存在)"
  fi
done

# ── 2. 庫存入庫 ──
echo ""
echo "--- 2. 庫存 ---"
STOCK=(
  '{"part_no":"AL-001","quantity":500,"location":"WH-01"}'
  '{"part_no":"ST-002","quantity":200,"location":"WH-01"}'
  '{"part_no":"CP-001","quantity":150,"location":"WH-01"}'
)
for s in "${STOCK[@]}"; do
  RESP=$(curl -s -X POST "$API/inventory/inbound" -H 'Content-Type: application/json' -d "$s")
  PN=$(echo "$s" | python3 -c "import sys,json; print(json.load(sys.stdin)['part_no'])")
  if echo "$RESP" | grep -q '"success":true\|"id":'; then
    echo "  ✅ $PN 入庫"
  else
    echo "  ⚠️  $PN: $RESP"
  fi
done

# ── 3. 採購單 ──
echo ""
echo "--- 3. 採購單 ---"
curl -s -X POST "$API/api/purchase/orders" \
  -H 'Content-Type: application/json' \
  -d '{
    "supplier_name":"大發鋼鐵",
    "items":[
      {"part_no":"AL-001","quantity":500,"unit_price":85.0,"expected_delivery":"2026-06-01"},
      {"part_no":"CP-001","quantity":100,"unit_price":45.0,"expected_delivery":"2026-06-05"}
    ],
    "ordered_by":"admin",
    "notes":"戰情室示範採購"
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  ✅ PO: {d.get('po_no','?')} ({d.get('status','?')})\")" 2>/dev/null || echo "  ⚠️  PO error"

curl -s -X POST "$API/api/purchase/orders" \
  -H 'Content-Type: application/json' \
  -d '{
    "supplier_name":"永裕五金",
    "items":[
      {"part_no":"ST-002","quantity":300,"unit_price":120.0,"expected_delivery":"2026-06-10"}
    ],
    "ordered_by":"purchaser",
    "notes":"緊急採購"
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  ✅ PO: {d.get('po_no','?')} ({d.get('status','?')})\")" 2>/dev/null || echo "  ⚠️  PO error"

# ── 4. 品質異常單 ──
echo ""
echo "--- 4. 品質異常 ---"
# Get the part IDs
PART_IDS_RAW=$(curl -s "$API/inventory/parts" | python3 -c "
import sys,json
d=json.load(sys.stdin)
items = d.get('items', d.get('data', d if isinstance(d,list) else []))
if not items and isinstance(d,dict):
  items = [v for k,v in d.items() if isinstance(v,list) and k in ('items','data','parts','results')]
if not items:
  items = [d]
for p in items:
  if isinstance(p,dict) and 'id' in p:
    print(f\"{p.get('part_no','?')}|{p['id']}\")
")
echo "  Parts: $(echo "$PART_IDS_RAW" | wc -l) found"

# Create NCs
AL_ID=$(echo "$PART_IDS_RAW" | grep "^AL-001" | cut -d'|' -f2)
ASM=$(echo "$PART_IDS_RAW" | grep "^ASM-001" | cut -d'|' -f2)

if [ -n "$AL_ID" ]; then
  curl -s -X POST "$API/api/quality/ncs" \
    -H 'Content-Type: application/json' \
    -d "{\"nc_no\":\"NC-20260513-001\",\"part_id\":\"$AL_ID\",\"defect_code\":\"DIM-OUT\",\"description\":\"鋁板尺寸超差0.5mm\",\"severity\":\"major\",\"created_by\":\"qa\"}" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  ✅ NC: {d.get('nc_no','?')} ({d.get('severity','?')})\")" 2>/dev/null
fi

if [ -n "$ASM" ]; then
  curl -s -X POST "$API/api/quality/ncs" \
    -H 'Content-Type: application/json' \
    -d "{\"nc_no\":\"NC-20260513-002\",\"part_id\":\"$ASM\",\"defect_code\":\"SUR-SCRATCH\",\"description\":\"總成表面刮傷\",\"severity\":\"minor\",\"created_by\":\"qa\"}" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  ✅ NC: {d.get('nc_no','?')} ({d.get('severity','?')})\")" 2>/dev/null
fi

# ── 5. 應收帳款 ──
echo ""
echo "--- 5. 應收帳款 ---"
curl -s -X POST "$API/api/accounting/ar" \
  -H 'Content-Type: application/json' \
  -d '{"customer_name":"鴻海精密","invoice_no":"INV-202605-001","amount":1250000,"due_date":"2026-06-15"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  ✅ AR: {d.get('customer_name','?')} NT\${d.get('amount',0):,.0f}\")" 2>/dev/null

curl -s -X POST "$API/api/accounting/ar" \
  -H 'Content-Type: application/json' \
  -d '{"customer_name":"台達電子","invoice_no":"INV-202605-002","amount":680000,"due_date":"2026-06-20"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  ✅ AR: {d.get('customer_name','?')} NT\${d.get('amount',0):,.0f}\")" 2>/dev/null

curl -s -X POST "$API/api/accounting/ar" \
  -H 'Content-Type: application/json' \
  -d '{"customer_name":"廣達電腦","invoice_no":"INV-202605-003","amount":920000,"due_date":"2026-05-30"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  ✅ AR: {d.get('customer_name','?')} NT\${d.get('amount',0):,.0f}\")" 2>/dev/null

# ── 6. 模擬事件 ──
echo ""
echo "--- 6. 模擬事件 ---"
for evt in material.received purchase_order.created non_conformance.created material.issued; do
  RESP=$(curl -s -X POST "$API/api/events/simulate/$evt")
  echo "  ✅ $evt → $(echo $RESP | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('emitted','?'))" 2>/dev/null)"
  sleep 0.5
done

echo ""
echo "===== 完成! 重整戰情室即可看到數據 ====="
