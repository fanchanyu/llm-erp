# LLM-ERP

> Talk to your ERP. Let AI handle the rest.

一個以 LLM 驅動的開源智慧企業資源規劃系統（ERP）。支援 7 大模組，使用者透過自然語言管理整個工廠流程。

## 核心特色

- **🗣️ Natural Language Interface** — 用講話的管工廠，不需要點選單或 T-code
- **🧠 7 模組** — 庫存 / 採購 / BOM / 派工 / 品質 / 會計 / 戰情室
- **🔒 20 條約束規則** — Service-Enforcer Pattern，寫入前強制驗證
- **⚡ 事件驅動引擎** — Pub/Sub 架構，跨角色即時通知
- **📊 戰情室 War Room** — SVG 價值流儀表板 + 即時事件動畫
- **🤖 Multi-Provider** — 支援 DeepSeek / Anthropic / OpenAI / Ollama
- **📈 30 題 Benchmark: 90% (DeepSeek) / 93% (Gemma4 local)**

## 快速開始

```bash
# 1. 啟動 Backend (開發環境用 SQLite，零依賴)
cd backend
cp .env.example .env   # 編輯 .env 填入 LLM API Key
pip install -r requirements.txt
uvicorn app.main:app --reload

# 2. 啟動 Frontend
cd frontend
npm install
npm run dev

# 3. 對話測試
# 打開 http://localhost:5173 開始用自然語言操作 ERP
```

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

## Provider 切換

```bash
# 編輯 backend/.env
LLM_PROVIDER=deepseek|ollama|anthropic|openai|openrouter
LLM_MODEL=deepseek-chat|gemma4:e4b|claude-sonnet-4|gpt-4o
MAX_TOOL_ROUNDS=5       # cloud=5, local=8-10

# 執行 Benchmark
cd evaluation && python3 run_eval.py --verbose
```

## 論文

投稿 **Engineering Applications of AI (EAAI, Elsevier, IF 7.5)**

- 論文全文: `paper/llm-erp-eaai.md`
- 30 題 Benchmark: DeepSeek 27/30 (90%) / Gemma4 28/30 (93%)
- 74 篇驗證文獻

## 技術棧

- **Backend:** Python FastAPI + SQLAlchemy + SQLite (dev) / PostgreSQL (prod)
- **Frontend:** React 18 + TypeScript + Tailwind CSS + Vite + i18n
- **LLM:** DeepSeek / Anthropic Claude / OpenAI GPT / Ollama (local)
- **Event:** In-process pub/sub bus, role-based routing
