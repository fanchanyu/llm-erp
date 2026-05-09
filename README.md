# LLM-ERP

> Talk to your ERP. Let AI handle the rest.

An open-source, LLM-powered Enterprise Resource Planning system with 8 modules. Manage your factory floor and customer relationships through **natural language** — no menu clicking, no T-codes to memorize.

**English** | [中文](./README-zh.md)

## Features

| | Feature | Description |
|---|---------|-------------|
| 🗣️ | **Bilingual Natural Language** | Chinese OR English. The system auto-detects your language. |
|| 🧠 | **12+ Modules** | Inventory / Purchasing / BOM / Dispatch / Quality / Accounting / CRM / War Room / Leads / Opportunities / Contracts / Decision AAR |
|| 🔒 | **25 Constraint Rules** | Service-Enforcer Pattern — validate every write before execution |
|| ⚡ | **Event-Driven Engine** | Pub/Sub architecture with role-based real-time notifications |
|| 📊 | **War Room Dashboard** | SVG value-stream visualization with live event animations |
|| 📄 | **PDF Report Generation** | Ask "Generate inventory report" — get a formatted PDF |
|| 🤖 | **Multi-Provider** | DeepSeek / Anthropic / OpenAI / Ollama / OpenRouter |
|| 🧑‍💼 | **CRM + Sales Pipeline** | Customer master, leads, opportunities, sales orders, contracts, interaction events |
|| 👥 | **3 Factory Types** | MTO (make-to-order), MTS (make-to-stock), ETO (engineer-to-order) — configurable pipeline, forms, and cash flow rules |
|| 💰 | **Cash Flow Constraints** | Cash position check before PO creation, rush order financial assessment, AR-blocked shipment |
|| 📋 | **Decision Audit + AAR** | Every major decision logged, After Action Review cycle with lessons learned |
|| 📈 | **75-Test Benchmark** | 60 Chinese + 15 English, DeepSeek 90% / Gemma4 local 83% |

---

## 👥 Target Audience (適用對象 / 目標族群)

This system is built for three distinct user groups:

### 🏭 1-1. Manufacturing SMEs (中小型製造業) — 50~500 employees

| Factory Type | Description | Key Pain Points |
|-------------|-------------|-----------------|
| **MTO** (Make-to-Order) 訂單式生產 | 機械加工、模具、零件製造 | Each order differs — drawing management, rush order scheduling, material costing |
| **MTS** (Make-to-Stock) 存貨式生產 | 消費品、電子零件、包材 | Forecast accuracy, stockout vs overstock, bulk contract pricing |
| **ETO** (Engineer-to-Order) 專案式生產 | 自動化設備、特種機械、系統整合 | Long cycle time, milestone billing, change order management, retention tracking |

**If your factory runs on Excel + paper and upgrading to SAP/Oracle/鼎新 costs too much 👉 LLM-ERP fits.**

### 🎯 1-2. Factory Managers & Operations (廠長與營運主管)

- Need **cross-department visibility** (Inventory → Purchase → Production → Quality → Accounting)
- Need **real-time alerts** (not postmortem reports)
- Want **natural language queries** (not menu clicking / T-code memorizing)

### 🔬 1-3. AI / ERP Researchers (學術研究者)

- Validate LLM feasibility in manufacturing ERP
- Multi-agent, function calling, event-driven architecture in industrial scenarios
- **Open-source, reproducible** — full data pipeline included

### ❌ What This System Is NOT

- Not a replacement for SAP/Oracle in large enterprises (it targets SMEs)
- Not a MES/SCADA control layer (Level 2 integration is separate)
- Not a full IFRS accounting system (simplified vouchers for factory use)
- ✅ **It is an LLM-native factory management system** — filling the gap between Excel and million-dollar ERPs

### 🔧 Factory Type Configuration

When you first deploy, set your factory type in the admin panel:

```bash
curl -X POST http://localhost:8000/api/factory/config \
  -H "Content-Type: application/json" \
  -d '{"factory_type": "MTO", "name": "永裕精密工業"}'
```

This adjusts:
- **Pipeline stages** — MTO: 詢價→報價→打樣→接單; MTS: 樣品→量產→補貨; ETO: RFQ→設計→議約→里程碑
- **Sales order forms** — MTO has drawing_no + material_spec; MTS has catalog selector; ETO has milestone lines
- **Cash flow rules** — MTO needs down payment tracking; MTS needs volume discount; ETO needs milestone billing + retention
- **Dashboard widgets** — Each role sees factory-type-relevant data

### 📋 New in v0.1.0 (2026-05-09)

| Area | Feature | What It Does |
|------|---------|-------------|
| **🎯 Lead Management** | `leads` table | Track prospects by source (web/exhibition/referral/cold-call), score (0-100), status workflow (new→contacted→qualified→converted→lost) |
| **📈 Opportunity Pipeline** | `opportunities` table | Full sales funnel: 6 stages, probability-weighted forecast, win/loss analysis |
| **📝 Contract Management** | `contracts` + `contract_pricing` | Annual/framework/project contracts, auto-pricing on SO, expiry alerts (30d) |
| **💵 Cash Flow Control** | `cashflow_service` | Real-time cash position, 30-day projection, auto-block PO when cash insufficient (+3 new constraints) |
| **⚡ Rush Order Engine** | `rush_order_service` | Financial impact: premium revenue vs overtime cost vs delay penalties → auto-recommend accept/reject |
| **📋 Decision Audit** | `decision_logs` | Auto-log every major decision (rush order, supplier change, schedule change, price change) |
| **🔄 AAR Loop** | `after_action_reviews` | After Action Review: expected vs actual → variance → corrective action → rule update |
| **🏭 3 Factory Types** | `factory_config` | MTO/MTS/ETO — each with custom pipeline, forms, cash flow rules, and dashboard |
| **👤 7th Role: Sales** | `role_config.py` | Sales manager dashboard with Leads, Oppty Pipeline, Contracts, Decision Log, AAR widgets |
| **🧠 37 LLM Tools** | `tools/functions.py` | Up from 27 — covers all new modules + rush order evaluation + cash position |

### 🎬 Quick Start: Test Drive in 60 Seconds

Want to try it right now? After starting the backend, run:

```bash
# 1. Set factory type
curl -X POST http://localhost:8000/api/factory/config \
  -H "Content-Type: application/json" \
  -d '{"factory_type":"MTO","name":"Demo Factory"}'

# 2. Create a lead
curl -X POST http://localhost:8000/api/leads \
  -H "Content-Type: application/json" \
  -d '{"company":"Acme Corp","source":"web","score":80}'

# 3. List leads
curl -s http://localhost:8000/api/leads
```

Or just open the dashboard and ask the LLM: *"Show me my leads"*, *"What's our cash position?"*, *"Evaluate a rush order for 450K"*.

### 📖 Full Walkthrough Guides

See **[docs/test-scenarios.md](docs/test-scenarios.md)** for 3 complete end-to-end scenarios:
- **MTO Machine Shop** — Rush order handling (lead → oppty → contract → rush assessment → SO → AAR)
- **MTS Electronics** — Contract renewal & replenishment (contract check → renewal → catalog SO → auto-replenish)
- **ETO Automation** — Project milestone management (RFQ → design → contract → milestones → billing → AAR)

---

## 🚀 Quick Start (5 minutes)

> **Note on LLM models:** This system includes 37 tool definitions. Cloud models (DeepSeek, Claude, GPT) handle this easily. Local models with small context windows (Gemma4 8B ~8K tokens) may struggle with the full tool set. If using a local model, reduce tool count in `orchestrator.py` or use DeepSeek ($0.5/M tokens).

```bash
# Prerequisites: Python 3.11+, Node.js 18+, and an LLM API key

# 1. Backend setup
cd backend
cp .env.example .env                  # ← Add your LLM API key here (NEVER in data files)
pip install -r requirements.txt

# 2. Initialize database with sample data
python -m scripts.manage_data import scripts/sample_data/

# 3. Start the backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 4. (new terminal) Start the frontend
cd frontend
npm install
npm run dev

# Open http://localhost:5173 and start managing your factory in plain English.
```

**That's it.** No manual table creation, no seed scripts, no complex configuration.

---

## 📂 Data Management (Import / Export / Reset)

All data uses **natural keys** (part numbers, supplier names, product codes) — not UUIDs — so CSV files are human-readable and editable. **API keys are NEVER stored in data files.**

```bash
cd backend

# Import sample data (12 tables, 70 records)
python -m scripts.manage_data import scripts/sample_data/

# Import your own CSV
python -m scripts.manage_data import path/to/my-data.csv

# Import a directory (auto-sorted by dependency order)
python -m scripts.manage_data import path/to/data-dir/

# Dry run (validate format without modifying DB)
python -m scripts.manage_data import scripts/sample_data/ --dry-run

# Export all data to CSV
python -m scripts.manage_data export ./backup/

# Reset database (clears all 22 tables)
python -m scripts.manage_data reset --force

# View entity schemas
python -m scripts.manage_data schema
```

### CSV Schema Reference

| File | Entity | Required Fields | Depends On |
|------|--------|----------------|:----------:|
| `01-parts.csv` | Parts Master | `part_no`, `name`, `unit` | — |
| `02-suppliers.csv` | Suppliers | `name` | — |
| `03-products.csv` | Products | `product_no`, `name` | — |
| `04-work-centers.csv` | Work Centers | `name` | — |
| `05-accounts.csv` | Chart of Accounts | `account_no`, `name`, `type`, `normal_balance` | — |
| `06-inventory.csv` | Stock Levels | `part_no`, `location`, `quantity` | parts |
| `07-bom.csv` | Bill of Materials | `product_no`, `part_no`, `quantity`, `level` | products, parts |
| `08-purchase-orders.csv` | Purchase Orders | `po_no`, `supplier_name`, `item_part_no`, `item_quantity` | suppliers, parts |
| `09-production-orders.csv` | Production Orders | `order_no`, `product_no`, `quantity`, `due_date` | products |
| `10-quality.csv` | Inspection Orders | `inspection_no`, `part_no`, `quantity` | parts |
| `11-accounting.csv` | Journal Entries | `entry_no`, `description`, `entry_date`, `period`, `line_account_no`, `line_debit`, `line_credit` | accounts |
| `12-ar.csv` | Accounts Receivable | `customer_name`, `invoice_no`, `amount`, `due_date` | — |
| `13-customers.csv` | Customers | `customer_no`, `name`, `contact_person`, `level` | — |
| `14-sales-orders.csv` | Sales Orders | `so_no`, `customer_no`, `item_part_no`, `item_quantity`, `unit_price` | customers |

---

## System Architecture

```
User Chat → LLM Orchestrator → Intent Classification → Domain Agent → Tool Call → DB / Event Bus
                                      ↓
                             Constraint Checker (20 rules)
                                      ↓
                             Response + Notifications (role-based)
```

8 domain services + event engine + 22 tables + 27 LLM Tools

| Module | Features | Constraints |
|--------|----------|:-----------:|
| 📦 Inventory | Part management, stock query, inbound/outbound transactions | 4 |
| 📋 Purchasing | Supplier management, PO lifecycle, supplier scoring | 4 |
| 📐 BOM | Multi-level BOM explosion, shortage checking, MRP | 4 |
| ⚙️ Dispatch | Work order management, machine scheduling, dynamic rescheduling | 4 |
| ✅ Quality | Inspection orders, non-conformance tracking, CAPA | 2 |
| 💰 Accounting | Chart of accounts, journal entries, AR aging, month-end close | 4 |
| 🤝 CRM | Customer management, opportunity pipeline, sales order lifecycle, lead tracking | 4 |
| 🏭 War Room | SVG value-stream dashboard, real-time event animations | — |

---

## Provider Switching

```bash
# Edit backend/.env
LLM_PROVIDER=deepseek|ollama|anthropic|openai|openrouter
LLM_MODEL=deepseek-chat|gemma4:e4b|claude-sonnet-4|gpt-4o
MAX_TOOL_ROUNDS=5       # cloud=5, local=8-10

# Run the 30-test benchmark
cd evaluation && python3 run_eval.py --verbose
```

### Benchmark Results

| Provider | Pass Rate | Avg Time | Notes |
|----------|:---------:|:--------:|:------|
| DeepSeek Chat | 27/30 (90%) | 7.7s | Cloud API, default config |
| Gemma4 (8B Q4_K_M) | 25/30 (83%) | 16.4s | Local CPU, max_rounds=8 |

---

## Tech Stack

- **Backend:** Python FastAPI + SQLAlchemy + SQLite (dev) / PostgreSQL (prod)
- **Frontend:** React 18 + TypeScript + Tailwind CSS + Vite + i18n
- **LLM:** DeepSeek / Anthropic Claude / OpenAI GPT / Ollama (local) / OpenRouter
- **Event:** In-process pub/sub bus, role-based routing
