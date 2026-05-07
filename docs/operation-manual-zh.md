# LLM-ERP 系統操作手冊

> 以大語言模型驅動的智慧企業資源規劃系統  
> 版本：v0.1.0 | 更新日期：2026-05-07

---

## 1. 系統概述

LLM-ERP 是一套開源的智慧 ERP 系統，讓使用者透過**自然語言**管理整個工廠流程，不需要記憶 T-code 或點選單。系統涵蓋 7 大模組：

| 模組 | 代碼 | 核心功能 |
|------|:----:|----------|
| 📦 庫存管理 | MM | 料號管理、庫存查詢、入出庫異動、儲位追蹤 |
| 📋 採購管理 | PP | 供應商管理、採購單生命週期、供應商評分 |
| 📐 BOM 工程 | ENG | 產品結構管理、多階展開、缺料檢查 |
| ⚙️ 生產派工 | MFG | 工單管理、機台排程、動態重排程（3 策略） |
| ✅ 品質管理 | QM | 檢驗單管理、不合格品(NC)追蹤、矯正措施(CAPA) |
| 💰 會計財務 | FI | 會計科目、傳票/分錄、AR 逾期管理、月結 |
| 🏭 戰情室 | — | SVG 價值流儀表板、即時事件動畫、跨螢幕顯示 |

---

## 2. 安裝需求

### 硬體需求

| 配置 | 最低 | 建議 |
|------|:----:|:----:|
| RAM | 4 GB | 16 GB（含本地 LLM） |
| CPU | 2 cores | 8 cores |
| 本地 LLM | — | 16 GB RAM + GPU (可選) |

### 軟體需求

- Python 3.11+
- Node.js 18+
- (選用) Docker Desktop — 用 PostgreSQL 正式環境
- (選用) Ollama — 本地 LLM 推理

---

## 3. 安裝步驟

### 3.1 下載專案

```bash
git clone https://github.com/pujy1978/llm-erp.git
cd llm-erp
```

### 3.2 後端設定

```bash
cd backend
cp .env.example .env
# 編輯 .env，填入你用的 LLM Provider 的 API Key
```

**`.env` 檔案說明：**

| 變數 | 說明 | 範例 |
|------|------|------|
| `LLM_PROVIDER` | LLM 提供商 | deepseek / ollama / anthropic / openai |
| `LLM_MODEL` | 模型名稱 | deepseek-chat / gemma4:e4b / claude-sonnet-4 |
| `MAX_TOOL_ROUNDS` | 工具調用輪數 | 5（雲端）/ 8-10（本地） |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | sk-xxxx |

### 3.3 啟動後端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

後端會在 `http://localhost:8000` 啟動。

### 3.4 啟動前端

```bash
cd frontend
npm install
npm run dev
```

前端會在 `http://localhost:5173` 啟動。

### 3.5 啟動本地 LLM（選用）

```bash
# 安裝 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 下載 Gemma4 模型（8B，約 9.6GB）
ollama pull gemma4:e4b

# 確認 Ollama 正在執行
curl http://localhost:11434/api/tags

# 將 .env 設為：
# LLM_PROVIDER=ollama
# LLM_MODEL=gemma4:e4b
# MAX_TOOL_ROUNDS=8
```

---

## 3.6 資料管理（Import / Export / Reset）

LLM-ERP 提供標準化的資料匯入匯出工具，所有資料使用**自然鍵**（料號、供應商名稱、產品編號等）—— 不是 UUID，所以人類可以直接編輯 CSV。

**API Key 永遠不會出現在資料檔中**，只存在於 `.env`。

### 匯入資料

```bash
cd backend

# 匯入內建範例資料（12 張表，71 筆記錄）
python -m scripts.manage_data import scripts/sample_data/

# 或用自己的 CSV
python -m scripts.manage_data import path/to/my-data.csv

# 或匯入整個目錄（自動按依賴順序處理）
python -m scripts.manage_data import path/to/data-dir/

# 乾執行（只驗證，不改資料）
python -m scripts.manage_data import scripts/sample_data/ --dry-run
```

### 匯出資料

```bash
python -m scripts.manage_data export ./backup/
# 輸出：01-parts.csv ~ 12-ar.csv，共 12 張表
```

### 重置資料庫

```bash
python -m scripts.manage_data reset --force
# 清空所有 22 張表
```

### 查看 Schema

```bash
python -m scripts.manage_data schema
# 列出所有實體的欄位定義
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
| `10-quality.csv` | 檢驗單 | `inspection_no`, `part_no`, `quantity` | parts, purchase-orders |
| `11-accounting.csv` | 會計傳票 | `entry_no`, `description`, `entry_date`, `period`, `line_account_no`, `line_debit`, `line_credit` | accounts |
| `12-ar.csv` | 應收帳款 | `customer_name`, `invoice_no`, `amount`, `due_date` | — |

匯入工具會自動依賴順序處理，跳過已存在的記錄（冪等操作）。

```bash
# 安裝 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 下載 Gemma4 模型（8B，約 9.6GB）
ollama pull gemma4:e4b

# 確認 Ollama 正在執行
curl http://localhost:11434/api/tags

# 將 .env 設為：
# LLM_PROVIDER=ollama
# LLM_MODEL=gemma4:e4b
# MAX_TOOL_ROUNDS=8
```

---

## 4. 使用指南

### 4.1 庫存管理（Inventory）

你可以問任何關於庫存的問題：

| 中文查詢 | 說明 |
|----------|------|
| 「M6x20 螺絲還有多少庫存？」 | 查詢特定料號庫存 |
| 「幫我看一下全部庫存列表」 | 列出所有庫存 |
| 「傳動件有哪些零件？庫存夠嗎？」 | 按分類查詢 |
| 「查一下馬達類零件的庫存狀況」 | 依名稱模糊查詢 |
| 「入庫 M6x20 螺絲 500 顆」 | 入庫作業 |
| 「發料 M6x20 螺絲 100 顆給工單 WO-001」 | 出庫/領料 |

### 4.2 採購管理（Purchase）

| 中文查詢 | 說明 |
|----------|------|
| 「供應商有哪些？查一下大明螺絲」 | 查詢供應商 |
| 「幫我開一張採購單，向大明螺絲買 M6x20 200 顆」 | 建立採購單 |
| 「目前的採購單有哪些？」 | 查詢採購單列表 |
| 「PO-2026-0001 的貨到了嗎？」 | 查詢採購單狀態 |

### 4.3 BOM 與物料管理

| 中文查詢 | 說明 |
|----------|------|
| 「CNC-001 用哪些料？」 | 查詢 BOM 結構 |
| 「CNC-001 的 BOM 展開給我看看」 | BOM 多階展開 |
| 「CNC-001 要做 5 台，料夠不夠？」 | 缺料檢查（核心功能） |

### 4.4 生產派工（Dispatch）

| 中文查詢 | 說明 |
|----------|------|
| 「目前有哪些工單？」 | 查詢工單列表 |
| 「幫我釋出工單 WO-20260506-001」 | 釋出工單 |
| 「CNC-01 故障，往後推 30 分鐘」 | 右移重排程（Right-Shift） |
| 「CNC-01 故障，換到備用機台」 | 替代路徑重排程（Route Change） |
| 「有急單 WO-002，插隊優先處理」 | 急單插隊（Expedite） |

### 4.5 品質管理（Quality）

| 中文查詢 | 說明 |
|----------|------|
| 「新增品檢單 M6x20，批號 LOT-001」 | 建立檢驗單 |
| 「查一下品檢記錄有哪些」 | 查詢檢驗單列表 |
| 「M6x20 有不良品嗎？」 | 查詢不合格品(NC) |
| 「新增 NC，M6x20 尺寸超差，嚴重度=重大」 | 建立不良品記錄 |

### 4.6 會計財務（Accounting）

| 中文查詢 | 說明 |
|----------|------|
| 「有哪些逾期應收帳款？」 | 查詢逾期帳款 |
| 「查一下應收帳款報表」 | 查詢 AR 列表 |
| 「會計科目有哪些？」 | 查詢科目表 |
| 「開傳票：借庫存 1000 貸銀行存款 1000」 | 建立傳票/分錄 |

### 4.7 跨模組查詢

| 中文查詢 | 說明 |
|----------|------|
| 「M6x20 螺絲採購單 PO-0001 的貨到了嗎？入庫了？」 | 採購+庫存 |
| 「我要生產 5 台 CNC-001，先檢查料夠不夠」 | BOM+採購 |

---

## 5. 戰情室（War Room）

戰情室是一個全螢幕的 SVG 價值流儀表板，適合工廠現場多螢幕監控。

**開啟方式：**
```bash
# 前端啟動後，打開瀏覽器：
http://localhost:5173/war-room.html
```

**戰情室功能：**
- 🏭 6 階段水平排列：供應商 → 採購 → 庫存 → 派工 → 品質 → 會計
- 🔵 動畫粒子流：綠色代表物料流、黃色代表金流
- 📡 底部事件串流：即時顯示最近 30 筆事件
- 🔔 節點發光：事件觸發時對應階段發光回饋
- ▶ 模擬事件按鈕：展示用自動模擬事件生成
- 🔄 數據 15 秒自動刷新

---

## 6. Provider 切換

LLM-ERP 支援 5 家 LLM Provider，可隨時切換：

```bash
# 編輯 backend/.env
LLM_PROVIDER=deepseek        # 或 ollama / anthropic / openai / openrouter
LLM_MODEL=deepseek-chat      # 或 gemma4:e4b / claude-sonnet-4 / gpt-4o
MAX_TOOL_ROUNDS=5            # 雲端 5，本地 8-10
```

**切換原則：**
- **雲端 API**（DeepSeek / Claude / GPT）：MAX_TOOL_ROUNDS=5，需要 API Key
- **本地模型**（Ollama / Gemma4）：MAX_TOOL_ROUNDS=8-10，不需要 API Key
- 切換後後端會自動重載（`uvicorn --reload`）

### Provider 效能對比（30 題 Benchmark）

| 指標 | DeepSeek (雲端) | Gemma4 8B (本地 CPU) |
|:-----|:--------------:|:-------------------:|
|| 準確率 | 90% (27/30) | 83% (25/30) |
| 平均回應 | 7.7s | 8.7s |
| 每題成本 | ~$0.002 | 免費 |
| 資料主權 | 外部 API | 完全本地 |

---

## 7. 執行 Benchmark

```bash
cd /mnt/d/Project/LLM_ERP/evaluation

# 執行 30 題標準測試
python3 run_eval.py

# 詳細輸出
python3 run_eval.py --verbose

# 指定輸出檔
python3 run_eval.py --output my-results.json
```

---

## 8. 常見問題

### Q: 後端啟動失敗？
A: 確認 `.env` 中有正確的 API Key。確認 `pip install -r requirements.txt` 已執行。

### Q: LLM 回應太慢？
A: DeepSeek 平均 7.7s，屬於正常。如果是本地模型（Gemma4），CPU 推理約 8-10s，有 GPU 可降到 1-3s。

### Q: 查詢結果不對？
A: 嘗試調整 `MAX_TOOL_ROUNDS`（本地模型需要更多輪數）。也可在 system prompt 中增加明確的禁止規則。

### Q: 如何清空資料庫？
A: 使用內建工具：`cd backend && python -m scripts.manage_data reset --force`。
   或直接刪除 `backend/llm_erp.db` 後重新匯入。

### Q: 前端 Vite 抓不到新加的 public 檔案？
A: 重啟 Vite dev server：`Ctrl+C` 後重新 `npm run dev`。

---

## 9. 系統架構快速參考

```
User Chat → LLM Orchestrator → Intent Classification → Domain Agent → Tool Call → DB
                                      ↓
                             Constraint Checker (20 rules)
                                      ↓
                             Response + Notifications (Event Bus)
```

| 層級 | 技術 | 說明 |
|------|------|------|
| 前端 | React 18 + TypeScript + Vite + Tailwind | 角色儀表板、Chat UI、戰情室 |
| 後端 | Python FastAPI + SQLAlchemy | 7 領域服務、42 API 路由 |
| LLM | DeepSeek / Anthropic / OpenAI / Ollama | 27 工具定義、Function Calling |
| 事件 | Pub/Sub Event Bus | 10 事件類型、角色路由通知 |
| 資料庫 | SQLite (dev) / PostgreSQL (prod) | 22 資料表、Alembic 遷移 |

---

*本手冊對應 LLM-ERP v0.1.0。更新日期：2026-05-07。*
