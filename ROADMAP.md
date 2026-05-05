# LLM-ERP 開發路線圖

> 從 MVP 到開源專案 → 學術論文

---

## 🚀 Phase 1 — MVP 啟動（明天）

### 啟動步驟

```bash
# 1. 設定 LLM API Key
cd D:\Project\LLM_ERP\backend
cp .env.example .env
# 編輯 .env，填入 ANTHROPIC_API_KEY=sk-xxxx

# 2. 啟動 PostgreSQL
docker compose up -d postgres

# 3. 安裝並啟動 Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# 4. 安裝並啟動 Frontend
cd frontend
npm install
npm run dev
```

### 驗收清單

- [ ] `GET /health` → `{"status": "ok"}`
- [ ] `POST /api/chat` → LLM 有回應
- [ ] `POST /api/inventory/parts` → 可以新增料號
- [ ] `GET /api/inventory/stock` → 查庫存
- [ ] `POST /api/purchase/orders` → 開採購單
- [ ] `GET /api/bom/explode` → BOM 展開
- [ ] Frontend Chat UI 可對話

---

## 🔧 Phase 2 — 功能補強（未來 1-2 週）

| 優先級 | 功能 | 預計工時 |
|--------|------|---------|
| P0 | Production排程 Agent（MPS → APS） | 2 天 |
| P0 | 動態重排程模組（Right-Shift / Route Changing） | 2 天 |
| P1 | RAG 知識庫（SOP、工程規範查詢） | 1 天 |
| P1 | Dashboard 圖表（庫存趨勢、採購狀態） | 1 天 |
| P2 | 多 Agent 協作（採購 Agent 自動補貨） | 2 天 |
| P2 | 使用者權限管理 | 1 天 |

---

## 📖 Phase 3 — 期刊論文（同步進行）

| 階段 | 內容 | 時程 |
|------|------|------|
| 大綱 | 確定論文結構、關鍵貢獻 | 明天完成 |
| 文獻回顧 | ERP + LLM 現有研究整理 | 3 天 |
| 系統設計 | LLM-ERP 架構圖 + Agent 設計 | 3 天 |
| 實作驗證 | 用案例展示系統有效性 | 5 天 |
| 投稿 | 選定期刊 + 完稿 | 2 週 |

---

## 🌐 Phase 4 — 開源（論文完成後）

- [ ] 選 License（MIT）
- [ ] 寫好英文 README
- [ ] 補 CONTRIBUTING.md
- [ ] 推上 GitHub
- [ ] 寫 Medium / 知乎介紹文
- [ ] 投稿到 Hacker News

---

## 📊 技術債務 / 注意事項

1. **安全性** — 上 GitHub 前確保 .env 在 .gitignore
2. **測試覆蓋率** — Phase 2 補到 70%+
3. **文件** — API 文件用 FastAPI 自動生成的 Swagger
4. **LLM 成本** — 建議開發期用 Ollama（本地），正式用 Claude
