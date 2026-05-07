# LLM-ERP — Natural Language Factory Management

> Talk to your ERP. Let AI handle the rest.

一個以 LLM 驅動的開源智慧企業資源規劃系統（ERP）。支援 7 大模組，使用者透過**自然語言**管理整個工廠流程。

## 核心特色

| | 特色 | 說明 |
|---|------|------|
| 🗣️ | **Natural Language** | 用講話的管工廠，不需要點選單或 T-code |
| 🧠 | **7 模組** | 庫存 / 採購 / BOM / 派工 / 品質 / 會計 / 戰情室 |
| 🔒 | **20 條約束規則** | Service-Enforcer Pattern，寫入前強制驗證 |
| ⚡ | **事件驅動引擎** | Pub/Sub 架構，跨角色即時通知 |
| 📊 | **戰情室 War Room** | SVG 價值流儀表板 + 即時事件動畫 |
| 🤖 | **Multi-Provider** | 支援 DeepSeek / Anthropic / OpenAI / Ollama / OpenRouter |
| 📈 | **Benchmark 30 題** | DeepSeek 90% / Gemma4 local 83% |

---

## 🚀 Quick Start（5 分鐘上路）

```bash
# 0. 需求
# Python 3.11+, Node.js 18+
# 一個 LLM API Key（DeepSeek / OpenAI / Anthropic 任選）
# 或本機 Ollama 跑 Gemma4 也行

# 1. 安裝 Backend
cd backend
cp .env.example .env          # ← 編輯 .env，填入你的 LLM API Key（不填進任何資料檔）
pip install -r requirements.txt

# 2. 初始化資料庫 + 匯入範例資料
python -m scripts.manage_data import scripts/sample_data/

# 3. 啟動 Backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 4. (另一個終端) 啟動 Frontend
cd frontend
npm install
npm run dev
# 打開 http://localhost:5173 開始用自然語言操作 ERP
```

**就這麼簡單。** 不需要手動建資料表、不用跑 seed script、沒有複雜設定。

---

## 📂 資料管理（匯入 / 匯出 / 重置）

任何資料都可以透過標準 CSV 格式匯入匯出。**資料檔永遠不包含 API Key**。

```bash
cd backend

# 匯入範例資料（12 張表，71 筆記錄）
python -m scripts.manage_data import scripts/sample_data/

# 匯入你自己的 CSV 資料
python -m scripts.manage_data import path/to/my-data.csv

# 匯入整個目錄（自動按依賴順序處理）
python -m scripts.manage_data import path/to/data-dir/

# 乾執行（驗證格式，不改資料庫）
python -m scripts.manage_data import scripts/sample_data/ --dry-run

# 匯出所有資料到 CSV
python -m scripts.manage_data export ./my-backup/

# 重置資料庫（清空所有 22 張表）
python -m scripts.manage_data reset --force

# 查看所有實體的 Schema 定義
python -m scripts.manage_data schema
```

### CSV 格式一覽

| 檔案 | 實體 | 必要欄位 |
|------|------|----------|
| `01-parts.csv` | 料號主檔 | `part_no`, `name`, `unit` |
| `02-suppliers.csv` | 供應商 | `name` |
| `03-products.csv` | 產品 | `product_no`, `name` |
| `04-work-centers.csv` | 工作站 | `name` |
| `05-accounts.csv` | 會計科目 | `account_no`, `name`, `type`, `normal_balance` |
| `06-inventory.csv` | 庫存量 | `part_no`, `location`, `quantity` |
| `07-bom.csv` | BOM 表 | `product_no`, `part_no`, `quantity`, `level` |
| `08-purchase-orders.csv` | 採購單 | `po_no`, `supplier_name`, `item_part_no`, `item_quantity` |
| `09-production-orders.csv` | 工單 | `order_no`, `product_no`, `quantity`, `due_date` |
| `10-quality.csv` | 檢驗單 | `inspection_no`, `part_no`, `quantity` |
| `11-accounting.csv` | 會計傳票 | `entry_no`, `description`, `entry_date`, `period`, `line_account_no`, `line_debit`, `line_credit` |
| `12-ar.csv` | 應收帳款 | `customer_name`, `invoice_no`, `amount`, `due_date` |

每一筆都使用**自然鍵**（料號、供應商名稱、產品編號）—— 不是 UUID，所以人類可以直接編輯 CSV。

---

## 系統架構

```
User Chat → LLM Orchestrator → Intent Classification → Domain Agent → Tool Call → DB / Event Bus
                                      ↓
                             Constraint Checker (20 rules)
                                      ↓
                             Response + Notifications (role-based)
```

7 領域服務 + 事件引擎 + 22 資料表 + 27 LLM Tools

| 模組 | 功能 | 約束 |
|------|------|:----:|
| 📦 庫存 | 料號管理、庫存查詢、入出庫異動 | 4 |
| 📋 採購 | 供應商管理、採購單生命週期 | 4 |
| 📐 BOM | 多階展開、缺料檢查、物料需求 | 4 |
| ⚙️ 派工 | 工單管理、機台排程、動態重排程 | 4 |
| ✅ 品質 | 檢驗單、不合格品(NC)、矯正措施(CAPA) | 2 |
| 💰 會計 | 會計科目、傳票、AR逾期、月結 | 4 |
| 🏭 戰情室 | SVG 價值流即時儀表板 | — |

---

## Provider 切換

```bash
# 編輯 backend/.env
LLM_PROVIDER=deepseek|ollama|anthropic|openai|openrouter
LLM_MODEL=deepseek-chat|gemma4:e4b|claude-sonnet-4|gpt-4o
MAX_TOOL_ROUNDS=5       # cloud=5, local=8-10

# 執行 Benchmark（測試 LLM 在 30 題 ERP 場景的表現）
cd evaluation && python3 run_eval.py --verbose
```

### Benchmark 結果

| Provider | 通過率 | 平均回應時間 | 備註 |
|----------|:------:|:-----------:|:----:|
| DeepSeek Chat | 27/30 (90%) | 7.7s | 雲端，預設配置 |
| Gemma4 (8B Q4_K_M) | 25/30 (83%) | 16.4s | 本機 CPU，max_rounds=8 |

---

## 論文

投稿 **Engineering Applications of AI (EAAI, Elsevier, IF 7.5)**

- 論文全文: `paper/llm-erp-eaai.md`
- 30 題 Benchmark + Provider 對比 + 事件引擎評估
- 74 篇驗證文獻

---

## 技術棧

- **Backend:** Python FastAPI + SQLAlchemy + SQLite (dev) / PostgreSQL (prod)
- **Frontend:** React 18 + TypeScript + Tailwind CSS + Vite + i18n
- **LLM:** DeepSeek / Anthropic Claude / OpenAI GPT / Ollama (local) / OpenRouter
- **Event:** In-process pub/sub bus, role-based routing
