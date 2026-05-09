# LLM-ERP 測試情境案例（Test Scenario Guide）

> 三種工廠型態 × 完整操作流程 — 讓您快速上手系統
> Version: v0.1.0 | 2026-05-09

---

## 如何使用本指南（How to Use This Guide）

每個情境都是一條**完整業務流程**，從頭到尾。您可以直接複製 curl 指令，或在系統前端輸入對話 LLM。

Three complete walkthroughs covering all 3 factory types. Copy the curl commands or chat with the LLM interface.

---

# 情境一：MTO 訂單式生產 — 機械加工廠接急單
# Scenario 1: MTO Machine Shop — Rush Order Handling

**工廠型態：** 訂單式生產（Make-to-Order）  
**情境：** 永裕精密打電話來說有一批 CNC 零件要插單，三天後就要  
**角色：** 業務 → 生管 → 會計 → 廠長

---

### Step 1: 設定工廠型態（一次性）
```bash
curl -X POST http://localhost:8000/api/factory/config \
  -H "Content-Type: application/json" \
  -d '{"factory_type": "MTO", "name": "永裕精密工業"}'
```

### Step 2: 搜尋既有客戶
**LLM 問法：**「查詢永裕精密的資料」
```bash
curl -s 'http://localhost:8000/api/customers?search=永裕'
```

### Step 3: 新增潛在客戶（如果還沒變成正式客戶）
**LLM 問法：**「幫我建一個新潛在客戶，新光精密，展會來的」
```bash
curl -X POST http://localhost:8000/api/leads \
  -H "Content-Type: application/json" \
  -d '{"company":"新光精密","contact_person":"李經理","phone":"04-12345678","source":"exhibition","score":75}'
```

### Step 4: 新增商機
**LLM 問法：**「建一個 CNC 銑床的商機，金額 150 萬」
```bash
curl -X POST http://localhost:8000/api/opportunities \
  -H "Content-Type: application/json" \
  -d '{"customer_id":1,"name":"CNC銑床年度合約","amount":1500000,"probability":60,"stage":"proposal","expected_close_date":"2026-06-15"}'
```

### Step 5: 查合約 & 急單評估
**LLM 問法：**「永裕精密有合約嗎？」「幫我評估急單，金額 45 萬」
```bash
# 查合約
curl -s 'http://localhost:8000/api/contracts?status=active'

# 急單評估
curl -s 'http://localhost:8000/api/chat' \
  -H "Content-Type: application/json" \
  -d '{"message":"評估急單，金額450000，客戶永裕精密"}'
```

👉 **預期結果：** 系統回傳評估報告：溢價收入、加班成本、延遲罰款、淨效益、建議接/不接

### Step 6: 建立銷售訂單
**LLM 問法：**「幫永裕精密建一張 SO，CNC-001 * 3pcs，單價 1500」
```bash
curl -X POST http://localhost:8000/api/so \
  -H "Content-Type: application/json" \
  -d '{"customer_no":"C001","items":[{"part_no":"CNC-001","quantity":3,"unit_price":1500,"part_name":"CNC加工件"}],"notes":"急單-三天後要"}'
```

### Step 7: 確認 SO（自動開工單）
```bash
curl -X POST http://localhost:8000/api/so/4/confirm
```
👉 **預期結果：** SO 狀態 → `production`，自動建立 ProductionOrder

### Step 8: 記錄決策
**LLM 問法：**「記錄這個急單決策」
```bash
curl -X POST http://localhost:8000/api/decisions \
  -H "Content-Type: application/json" \
  -d '{"decision_type":"rush_order","description":"永裕精密急單-CNC-001*3pcs","department":"sales","actor":"業務-王大明","role":"sales","status":"completed"}'
```

### Step 9: 出貨 → 完成
```bash
curl -X POST http://localhost:8000/api/so/4/ship
curl -X POST http://localhost:8000/api/so/4/deliver
```

### Step 10: 事後回顧（AAR）— 30 天後
**LLM 問法：**「急單回顧，預期利潤3萬，實際1.8萬」
```bash
curl -X POST http://localhost:8000/api/decisions/aar \
  -H "Content-Type: application/json" \
  -d '{"title":"急單回顧-CNC-001","department":"sales","expected_result":"利潤NT$30,000","actual_result":"利潤NT$18,000","variance_analysis":"加班費超出預期40%","root_cause":"溢價1.2x未涵蓋加班","corrective_action":"急單溢價調至1.3x","preventive_action":"建立急單審核門檻","status":"published"}'
```

---

# 情境二：MTS 存貨式生產 — 電子零件廠合約續約
# Scenario 2: MTS Electronics — Contract Renewal & Replenishment

**Factory Type:** Make-to-Stock (MTS)  
**Scenario:** Annual contract with 宏達電子 is expiring; need renewal and restock  
**Roles:** Sales → Warehouse → Production

---

### Step 1: 設定工廠型態
```bash
curl -X POST http://localhost:8000/api/factory/config \
  -H "Content-Type: application/json" \
  -d '{"factory_type": "MTS", "name": "宏達電子"}'
```

### Step 2: 查合約到期
**LLM Query:** "List contracts expiring soon"
```bash
curl -s 'http://localhost:8000/api/contracts?status=active'
```
👉 **Expected:** Contract CT-2026-001 shows end_date 2026-12-31

### Step 3: 建立新合約（續約）
**LLM Query:** "Create a new annual contract for 宏達電子 with pricing"
```bash
curl -X POST http://localhost:8000/api/contracts \
  -H "Content-Type: application/json" \
  -d '{"contract_no":"CT-2027-001","customer_id":2,"type":"annual","start_date":"2027-01-01","end_date":"2027-12-31","status":"active","pricing_json":{"CNC-001":{"unit_price":1350,"min_qty":10,"discount_pct":5}}}'
```

### Step 4: 從目錄建 SO（標準品）
**LLM Query:** "Create SO from catalog for 宏達, CNC-001 * 20pcs"
```bash
curl -X POST http://localhost:8000/api/so \
  -H "Content-Type: application/json" \
  -d '{"customer_no":"C002","items":[{"part_no":"CNC-001","quantity":20,"unit_price":1350,"part_name":"CNC加工件"}],"notes":"2027年度合約第一批"}'
```
👉 **Expected:** Price auto-applied from contract: 1350 (5% off 1500)

### Step 5: 檢查庫存
**LLM Query:** "Check stock for CNC-001"
```bash
curl -s 'http://localhost:8000/api/inventory/stock?part_no=CNC-001'
```
👉 **Expected:** Shows current quantity — may need production if low

### Step 6: 確認 SO → 出貨
```bash
curl -X POST http://localhost:8000/api/so/4/confirm
curl -X POST http://localhost:8000/api/so/4/ship
curl -X POST http://localhost:8000/api/so/4/deliver
```

### Step 7: 自動補貨檢查
**LLM Query:** "Check stock shortage for CNC-001"
```bash
# After shipping, stock drops — system should surface this
curl -s 'http://localhost:8000/api/bom/shortage'
```

### Step 8: 記錄合約續約決策
```bash
curl -X POST http://localhost:8000/api/decisions \
  -H "Content-Type: application/json" \
  -d '{"decision_type":"price_change","description":"宏達電子2027年度合約續約-5%折扣","department":"sales","actor":"業務-王大明","role":"sales"}'
```

---

# 情境三：ETO 專案式生產 — 自動化設備專案管理
# Scenario 3: ETO Automation — Project Milestone Management

**Factory Type:** Engineer-to-Order (ETO)  
**Scenario:** New assembly line automation project for a factory  
**Roles:** Sales → Engineer → Project Manager → Accounting

---

### Step 1: 設定工廠型態
```bash
curl -X POST http://localhost:8000/api/factory/config \
  -H "Content-Type: application/json" \
  -d '{"factory_type": "ETO", "name": "自動化設備事業部"}'
```

### Step 2: 潛在客戶開發（RFQ 階段）
**LLM Query:** "Log a new lead from an exhibition inquiry"
```bash
curl -X POST http://localhost:8000/api/leads \
  -H "Content-Type: application/json" \
  -d '{"company":"大發汽車","contact_person":"陳廠長","phone":"03-5551234","source":"exhibition","score":85,"notes":"自動化裝配線需求 RFQ-2026-001"}'
```

### Step 3: 建立商機（技術討論 → 設計提案）
**LLM Query:** "Create an opportunity for the assembly line project, 5M NTD"
```bash
curl -X POST http://localhost:8000/api/opportunities \
  -H "Content-Type: application/json" \
  -d '{"customer_id":1,"name":"大發汽車裝配線自動化專案","amount":5000000,"probability":40,"stage":"needs_analysis","expected_close_date":"2026-08-30"}'
```

### Step 4: 更新商機階段（議約中）
```bash
curl -X PATCH http://localhost:8000/api/opportunities/1/stage \
  -H "Content-Type: application/json" \
  -d '{"stage":"negotiation","probability":70}'
```

### Step 5: 簽約（里程碑條款）
**LLM Query:** "Create a project contract with milestone billing terms"
```bash
curl -X POST http://localhost:8000/api/contracts \
  -H "Content-Type: application/json" \
  -d '{"contract_no":"CT-2026-P001","customer_id":1,"type":"project","start_date":"2026-06-01","end_date":"2026-12-31","status":"active","payment_terms":"30%簽約+40%交機+20%驗收+10%保留款","pricing_json":{"milestones":[{"name":"簽約","pct":30,"amount":1500000},{"name":"交機","pct":40,"amount":2000000},{"name":"驗收","pct":20,"amount":1000000},{"name":"保留款","pct":10,"amount":500000}]}}'
```

### Step 6: 建立 SO（里程碑明細）
```bash
# 第一批：簽約款
curl -X POST http://localhost:8000/api/so \
  -H "Content-Type: application/json" \
  -d '{"customer_no":"C001","items":[{"part_no":"ETO-ASM-001","quantity":1,"unit_price":1500000,"part_name":"裝配線自動化專案-簽約款"}],"notes":"CT-2026-P001 里程碑1/4"}'
```

### Step 7: 完工後 AAR 決策回顧
**LLM Query:** "AAR for the automation project — delivery was 2 weeks late"
```bash
curl -X POST http://localhost:8000/api/decisions/aar \
  -H "Content-Type: application/json" \
  -d '{"title":"大發汽車專案交期回顧","department":"production","expected_result":"2026-10-31前交機","actual_result":"2026-11-14交機","variance_analysis":"設計變更2次，採購長交期料延遲3週","root_cause":"客戶規格變更未及時通知採購","corrective_action":"建立設計變更通知流程","preventive_action":"長交期料提前下單","status":"implemented"}'
```

### Step 8: 查詢決策紀錄
**LLM Query:** "Show all decisions for the production department"
```bash
curl -s 'http://localhost:8000/api/decisions?department=production'
```

---

## 🧪 驗證所有 API 端點（Smoke Test）

在開始用之前，跑這個快速檢測確保一切正常：

```bash
#!/bin/bash
echo "=== 1. Health Check ==="
curl -s http://localhost:8000/health | python3 -c "import sys,json;d=json.load(sys.stdin);print('OK' if d.get('status')=='ok' else 'FAIL')"

echo "=== 2. Factory Config ==="
curl -s -X POST http://localhost:8000/api/factory/config \
  -H "Content-Type: application/json" \
  -d '{"factory_type":"MTO","name":"測試工廠"}' | python3 -c "import sys,json;d=json.load(sys.stdin);print(f'OK: {d.get(\"factory_type\")}' if d.get('id') else 'FAIL')"

echo "=== 3. Create Lead ==="
curl -s -X POST http://localhost:8000/api/leads \
  -H "Content-Type: application/json" \
  -d '{"company":"測試公司","source":"web","score":50}' | python3 -c "import sys,json;d=json.load(sys.stdin);print(f'OK: {d.get(\"company\")}' if d.get('id') else 'FAIL')"

echo "=== 4. Create Opportunity ==="
curl -s -X POST http://localhost:8000/api/opportunities \
  -H "Content-Type: application/json" \
  -d '{"customer_id":1,"name":"測試商機","amount":100000,"probability":50,"stage":"proposal","expected_close_date":"2026-07-01"}' | python3 -c "import sys,json;d=json.load(sys.stdin);print(f'OK: {d.get(\"name\")}' if d.get('id') else 'FAIL')"

echo "=== 5. Create Contract ==="
curl -s -X POST http://localhost:8000/api/contracts \
  -H "Content-Type: application/json" \
  -d '{"contract_no":"CT-TEST-001","customer_id":1,"type":"annual","start_date":"2026-01-01","end_date":"2026-12-31","status":"active"}' | python3 -c "import sys,json;d=json.load(sys.stdin);print(f'OK: {d.get(\"contract_no\")}' if d.get('id') else 'FAIL')"

echo "=== 6. Create Decision Log ==="
curl -s -X POST http://localhost:8000/api/decisions \
  -H "Content-Type: application/json" \
  -d '{"decision_type":"other","description":"測試決策","department":"sales","actor":"測試員","role":"sales"}' | python3 -c "import sys,json;d=json.load(sys.stdin);print(f'OK: {d.get(\"decision_type\")}' if d.get('id') else 'FAIL')"

echo "=== 7. Create AAR ==="
curl -s -X POST http://localhost:8000/api/decisions/aar \
  -H "Content-Type: application/json" \
  -d '{"title":"測試回顧","department":"sales","expected_result":"A","actual_result":"B","variance_analysis":"測試","root_cause":"測試","corrective_action":"測試","preventive_action":"測試","status":"draft"}' | python3 -c "import sys,json;d=json.load(sys.stdin);print(f'OK: {d.get(\"title\")}' if d.get('id') else 'FAIL')"

echo "=== 8. Customer + SO (legacy check) ==="
curl -s 'http://localhost:8000/api/customers?limit=1' | python3 -c "import sys,json;d=json.load(sys.stdin);print(f'OK: {len(d.get(\"customers\",[]))} customers' if d.get('customers') else 'Data empty')"

echo ""
echo "✅ Smoke test complete!"
```

---

## LLM 對話指令速查表（Quick Reference）

| 你要做什麼 | 直接對 LLM 說 |
|-----------|--------------|
| 查客戶 | 「查詢永裕精密的資料」 |
| 查潛在客戶 | 「有哪些潛在客戶」「查詢開發中的客戶」 |
| 查商機 | 「商機 Pipeline 有哪些」「目前的漏鬥狀況」 |
| 查合約 | 「有哪些有效合約」「永裕的合約什麼時候到期」 |
| 查決策 | 「業務部門最近的決策」「過去的急單紀錄」 |
| 查回顧 | 「AAR 有哪些」「上個月的決策回顧」 |
| 查現金 | 「公司現金水位多少」「錢夠不夠開 PO」 |
| 評估急單 | 「幫我評估這個急單，金額45萬」 |
| 設工廠型態 | 「設定為 MTO 型工廠」 |
| 查庫存 | 「CNC-001 還有多少庫存」 |
