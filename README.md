# LLM-ERP

> Talk to your ERP. Let AI handle the rest.

一套以 LLM 為核心的智慧企業資源規劃系統（ERP），讓使用者透過自然語言管理庫存、採購、BOM 與生產排程。

## 核心特色

- **🗣️ LLM-First 操作** — 用講話的管工廠，不需要點選單
- **🧠 多 Agent 協作** — 庫存 Agent、採購 Agent、BOM Agent 各自獨立又協同
- **🔁 閉環控制** — 繼承工業 4.0 Closed-loop 架構，即時回饋與動態調整
- **📈 可進化** — 模組化設計，可逐步加入排程、品質、財務等模組
- **✅ ERP 原則對齊** — 嚴格遵循 MPS → MRP → CRP 規劃流程

## 快速開始

```bash
# 1. 啟動 PostgreSQL
docker compose up -d postgres

# 2. 啟動 Backend
cd backend
cp .env.example .env   # 編輯 .env 填入 ANTHROPIC_API_KEY
pip install -r requirements.txt
uvicorn app.main:app --reload

# 3. 啟動 Frontend
cd frontend
npm install
npm run dev
```

## 架構

```
User Chat → LLM Orchestrator → Intent Classification → Domain Agent → Tool Call → DB
```

### 三層架構

| 層級 | 對應 | 說明 |
|------|------|------|
| 🧠 戰略層 | MPS / MRP / CRP | 決定「做什麼、何時做、用什麼做」 |
| ⚙️ 戰術層 | APS / BOM 展開 | 決定「怎麼做最好、資源怎麼分配」 |
| 🏭 執行層 | MES / 庫存異動 | 執行任務 + 即時回饋 |

## 技術棧

- **Backend:** Python FastAPI + SQLAlchemy + PostgreSQL
- **Frontend:** React + TypeScript + Tailwind CSS + Vite
- **LLM:** Anthropic Claude (Function Calling)
- **Vector:** pgvector (對話記憶 & RAG)

## 專案結構

```
llm-erp/
├── backend/
│   ├── app/
│   │   ├── api/        # REST API 端點
│   │   ├── agents/     # LLM Agent (每模組一個)
│   │   ├── services/   # 業務邏輯層
│   │   ├── models/     # SQLAlchemy 資料模型
│   │   ├── schemas/    # Pydantic 驗證 schema
│   │   └── tools/      # LLM function calling 工具
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/ # React 組件
│       ├── hooks/      # 自訂 hooks
│       └── api/        # API client
└── docker-compose.yml
```

## 開發路線圖

- **Phase 1:** Chat UI + 庫存 + 採購 + BOM（MVP）
- **Phase 2:** 生產排程 Agent + 動態重排程 + 報表
- **Phase 3:** 多 Agent 協作 + 數位孿生 + RAG 知識庫
