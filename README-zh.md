# LLM-ERP v0.2.0

> 跟你的 ERP 說話，讓 AI 搞定剩下的事。

一套開源的 AI 驅動企業資源規劃系統，涵蓋 **16+ 模組**。透過**自然語言**管理工廠和客戶關係 — 不用點選單、不用背 T-code。

[English](./README.md) | **中文**

---

## ✨ 功能特色

| | 功能 | 說明 |
|---|------|------|
| 🗣️ | **雙語自然語言** | 中英文皆可，系統自動判斷語言回應 |
| 🧠 | **16+ 模組** | 庫存 / 採購 / BOM / 生產 / 品管 / 會計 / CRM / 戰情室 / 組織人事 / 生產製造 / 倉儲物流 / 合規審計 / 安全管理 / Multi-Agent |
| 🔒 | **20 條約束規則** | Service-Enforcer 架構 — 每筆寫入先驗證再執行 |
| ⚡ | **事件驅動引擎** | Pub/Sub 架構，基於角色路由即時通知 |
| 📊 | **戰情室儀表板** | SVG 價值流視覺化 + 即時事件動畫 |
| 📄 | **PDF 報表生成** | 說「幫我產庫存報表」就拿到 PDF |
| 🤖 | **多 LLM Provider** | DeepSeek / Anthropic / OpenAI / Ollama / OpenRouter |
| 🧑‍💼 | **CRM 客戶管理** | 客戶主檔、銷售訂單、商機管理、互動記錄 |
| 🏢 | **組織人事** | 部門管理、RBAC 權限系統、兩層簽核引擎、Session 管理 |
| 🏭 | **生產製造** | MPS 主排程彙總、Shop Floor 控制台、甘特圖、開工/報工 |
| 📦 | **倉儲物流** | 儲位管理、庫存調撥、揀貨任務、週期盤點、自動補貨 |
| 🔍 | **合規審計** | Unified Event Stream、異常偵測、合規規則引擎 |
| 🔒 | **安全管理** | IP 白名單、暴力破解偵測、帳號停用/啟用 |
| 🤖 | **V2 Multi-Agent** | 10 Domain Agents + Intent Router 智能路由 |
| 📈 | **112+ API Benchmark** | 112+ REST API endpoints, 10 Domain Agents, DeepSeek 90% / Gemma4 本地 83% |

---

## 👥 適用對象（Target Audience）

本系統專為以下三類族群設計：

### 🏭 1-1. 中小型製造業（50~500 人）

| 工廠型態 | 說明 | 核心痛點 |
|---------|------|---------|
| **MTO** 訂單式生產 | 機械加工、模具、零件製造 | 每單不同需圖號管理、急單插單、材料成本估算 |
| **MTS** 存貨式生產 | 消費品、電子零件、包材 | 預測不準造成缺料或呆滯、大量合約定價管理 |
| **ETO** 專案式生產 | 自動化設備、特種機械、系統整合 | 週期長、里程碑請款、變更單管理、保留款追蹤 |

**如果你還在用 Excel + 紙本管理工廠，導入 SAP/鼎新又動輒數百萬 👉 LLM-ERP 最適合你。**

### 🎯 1-2. 廠長與營運主管

- 需要跨部門視野（庫存→採購→生產→品管→會計）
- 需要即時異常警示而非事後報表
- 想要用白話文問系統，不用學 T-code 或背選單

### 🔬 1-3. 學術研究人員

- 驗證 LLM 在製造業 ERP 的可行性
- Multi-agent、function calling、event-driven architecture 的工業應用
- **開源、可複製** — 完整資料管線與測試套件

### ❌ 本系統不是什麼

- ❌ 不是大企業用的 SAP/Oracle 替代品（鎖定中小企業）
- ❌ 不是 MES/SCADA 控制層（Level 2 設備整合需另外對接）
- ❌ 不是完整 IFRS 會計系統（工廠用簡化傳票）
- ✅ **是「LLM-native 的工廠管理系統」— 填補 Excel 與百萬 ERP 之間的空缺**

### 🔧 工廠型態設定

首次部署時，在管理後台設定你的工廠型態：

```bash
curl -X POST http://localhost:8000/api/factory/config \
  -H "Content-Type: application/json" \
  -d '{"factory_type": "MTO", "name": "永裕精密工業"}'
```

設定後系統自動調整：
- **Pipeline 階段** — MTO: 詢價→報價→打樣→接單；MTS: 樣品→量產→補貨；ETO: RFQ→設計→議約→里程碑
- **銷售表單欄位** — MTO 有圖號+材質；MTS 有產品目錄選擇；ETO 有里程碑明細
- **現金流規則** — MTO 需預付款管理；MTS 需階梯折扣；ETO 需里程碑請款+保留款
- **儀表板 Widget** — 各角色看到與工廠型態相關的數據

---

## 🚀 快速啟動（5 分鐘）

> **關於 LLM 模型選擇：** 本系統包含 37 個工具定義，雲端模型（DeepSeek、Claude、GPT）完全沒問題。本地小 context 模型（如 Gemma4 8B ~8K tokens）可能無法一次載入全部工具定義，這是該模型本身的限制，非系統問題。建議使用 DeepSeek（$0.5/百萬 token）獲得最佳體驗。

```bash
# 前置需求：Python 3.11+、Node.js 18+、LLM API Key

# 1. 後端設定
cd backend
cp .env.example .env                  # ← 填入你的 LLM API Key（絕不能放到資料檔裡）
pip install -r requirements.txt

# 2. 初始化資料庫（含範例資料）
python -m scripts.manage_data import scripts/sample_data/

# 3. 啟動後端
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 4. （開新終端機）啟動前端
cd frontend
npm install
npm run dev

# 打開 http://localhost:5173 開始用中文管理你的工廠
```

**就這樣。** 不需要手動建表、不用跑 Seed 腳本、不用複雜設定。

---

## 📂 資料管理（匯入 / 匯出 / 重置）

所有資料使用**自然鍵**（料號、供應商名稱、產品編號）— 不是 UUID，所以 CSV 人類可直接編輯。**API Key 永遠不會出現在資料檔中。**

```bash
cd backend

# 匯入範例資料（12 張表，70 筆記錄）
python -m scripts.manage_data import scripts/sample_data/

# 匯入自己的 CSV
python -m scripts.manage_data import path/to/my-data.csv

# 匯入整個目錄（自動依賴順序處理）
python -m scripts.manage_data import path/to/data-dir/

# 乾執行（只驗證不改 DB）
python -m scripts.manage_data import scripts/sample_data/ --dry-run

# 匯出全部資料到 CSV
python -m scripts.manage_data export ./backup/

# 重置資料庫（清空所有 22 張表）
python -m scripts.manage_data reset --force

# 查看 Entity Schema
python -m scripts.manage_data schema
```

### CSV Schema 速查表

| 檔案 | 實體 | 必要欄位 | 依賴 |
|------|------|----------|:----:|
| `01-parts.csv` | 料號主檔 | `part_no`, `name`, `unit` | — |
| `02-suppliers.csv` | 供應商 | `name` | — |
| `03-products.csv` | 產品 | `product_no`, `name` | — |
| `04-work-centers.csv` | 工作站 | `name` | — |
| `05-accounts.csv` | 會計科目 | `account_no`, `name`, `type`, `normal_balance` | — |
| `06-inventory.csv` | 庫存量 | `part_no`, `location`, `quantity` | parts |
| `07-bom.csv` | BOM 表 | `product_no`, `part_no`, `quantity`, `level` | products, parts |
| `08-purchase-orders.csv` | 採購單 | `po_no`, `supplier_name`, `item_part_no`, `item_quantity` | suppliers, parts |
| `09-production-orders.csv` | 工單 | `order_no`, `product_no`, `quantity`, `due_date` | products |
| `10-quality.csv` | 檢驗單 | `inspection_no`, `part_no`, `quantity` | parts |
| `11-accounting.csv` | 會計傳票 | `entry_no`, `description`, `entry_date`, `period`, `line_account_no`, `line_debit`, `line_credit` | accounts |
| `12-ar.csv` | 應收帳款 | `customer_name`, `invoice_no`, `amount`, `due_date` | — |
| `13-customers.csv` | 客戶主檔 | `customer_no`, `name`, `contact_person`, `level` | — |
| `14-sales-orders.csv` | 銷售訂單 | `so_no`, `customer_no`, `item_part_no`, `item_quantity`, `unit_price` | customers |

匯入工具會自動依依賴順序處理，跳過已存在的記錄（冪等操作）。

---

## 🏗️ 系統架構

```
User Chat → LLM Orchestrator → Intent Classification → Domain Agent → Tool Call → DB / Event Bus
                                     ↓
                            Constraint Checker (20 rules)
                                     ↓
                            Response + Notifications (role-based)
```

8 個領域服務 + 事件引擎 + 22 張資料表 + 27 個 LLM 工具

| 模組 | 功能 | 約束規則 |
|------|------|:--------:|
| 📦 庫存管理 | 料號管理、庫存查詢、入出庫異動 | 4 |
| 📋 採購管理 | 供應商管理、採購單生命週期、供應商評分 | 4 |
| 📐 BOM 工程 | 多階 BOM 展開、缺料檢查、MRP | 4 |
| ⚙️ 生產派工 | 工單管理、機台排程、動態重排程（3 策略） | 4 |
| ✅ 品質管理 | 檢驗單管理、不合格品(NC)追蹤、矯正措施(CAPA) | 2 |
| 💰 會計財務 | 會計科目、傳票/分錄、AR 逾期管理、月結 | 4 |
| 🤝 CRM 客戶管理 | 客戶主檔分級、銷售訂單 SO、客戶互動記錄 | 4 |
| 🏭 戰情室 | SVG 價值流儀表板、即時事件動畫、跨螢幕顯示 | — |

---

## 🔄 Provider 切換

```bash
# 編輯 backend/.env
LLM_PROVIDER=deepseek|ollama|anthropic|openai|openrouter
LLM_MODEL=deepseek-chat|gemma4:e4b|claude-sonnet-4|gpt-4o
MAX_TOOL_ROUNDS=5       # 雲端=5，本地=8-10

# 執行 30 題 Benchmark
cd evaluation && python3 run_eval.py --verbose
```

### Benchmark 結果

| Provider | 通過率 | 平均時間 | 備註 |
|----------|:------:|:--------:|------|
| DeepSeek Chat | 27/30 (90%) | 7.7s | 雲端 API，預設配置 |
| Gemma4 (8B Q4_K_M) | 25/30 (83%) | 16.4s | 本地 CPU，max_rounds=8 |

---

## 🛠️ 技術棧

- **後端：** Python FastAPI + SQLAlchemy + SQLite（開發）/ PostgreSQL（正式）
- **前端：** React 18 + TypeScript + Tailwind CSS + Vite + i18n
- **LLM：** DeepSeek / Anthropic Claude / OpenAI GPT / Ollama（本地）/ OpenRouter
- **事件：** In-process pub/sub 匯流排，基於角色路由

---

## 📘 操作手冊

詳細操作指南請見：

- [中文版操作手冊](./docs/operation-manual-zh.md) — 完整功能介紹、使用場景、CRM 流程
- [英文版操作手冊](./docs/operation-manual-en.md) — English operation manual

---

*Built with Hermes Agent*
