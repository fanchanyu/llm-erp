# LLM-ERP

> Talk to your ERP. Let AI handle the rest.

An open-source, LLM-powered Enterprise Resource Planning system with 8 modules. Manage your factory floor and customer relationships through **natural language** — no menu clicking, no T-codes to memorize.

## Features

| | Feature | Description |
|---|---------|-------------|
| 🗣️ | **Bilingual Natural Language** | Chinese OR English. The system auto-detects your language. |
| 🧠 | **8 Modules** | Inventory / Purchasing / BOM / Dispatch / Quality / Accounting / CRM / War Room |
| 🔒 | **20 Constraint Rules** | Service-Enforcer Pattern — validate every write before execution |
| ⚡ | **Event-Driven Engine** | Pub/Sub architecture with role-based real-time notifications |
| 📊 | **War Room Dashboard** | SVG value-stream visualization with live event animations |
| 📄 | **PDF Report Generation** | Ask "Generate inventory report" — get a formatted PDF |
| 🤖 | **Multi-Provider** | DeepSeek / Anthropic / OpenAI / Ollama / OpenRouter |
| 🧑‍💼 | **CRM Module** | Customer master, sales orders, opportunity pipeline, interaction events |
| 📈 | **75-Test Benchmark** | 60 Chinese + 15 English, DeepSeek 90% / Gemma4 local 83% |

---

## 🚀 Quick Start (5 minutes)

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
