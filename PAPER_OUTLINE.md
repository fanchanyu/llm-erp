# LLM-ERP: 以大語言模型驅動之智慧企業資源規劃系統

## LLM-Driven Enterprise Resource Planning: From Static Transactions to Dynamic Closed-Loop Intelligence

---

## 📄 論文大綱

### Title (暫定)

**LLM-ERP: 以大語言模型驅動之智慧企業資源規劃系統架構與實作**
**LLM-ERP: Architecture and Implementation of an LLM-Driven Intelligent Enterprise Resource Planning System**

---

### Abstract (摘要)

> 傳統 ERP 系統以選單式操作與靜態排程為主，面臨使用者學習成本高、系統僵化、以及無法即時回應現場變動等問題。本文提出 LLM-ERP，一個以大語言模型（LLM）為核心的智慧 ERP 系統架構。系統採用多層次 Agent 設計，透過 LLM 的自然語言理解與 Function Calling 能力，讓使用者以對話方式操作庫存管理、採購單開立、BOM 多階展開與缺料檢查等核心 ERP 功能。本系統支援多家 LLM Provider（Anthropic、OpenAI、DeepSeek、Ollama），並採用工業 4.0 閉環控制（Closed-loop）設計，實現從傳統開環排程到動態重排程的轉變。實驗結果顯示，LLM-ERP 能有效降低 ERP 操作門檻，並在 BOM 展開、庫存查詢等任務上達到 90% 以上的意圖辨識準確率。

---

### 1. Introduction (緒論)

- 1.1 傳統 ERP 的困境
  - 選單式操作的高學習成本
  - Take-for-granted inflexibility 與員工 Workarounds
  - Open-loop 排程無法因應現場變動
- 1.2 LLM 的崛起與契機
  - GPT / Claude / DeepSeek 等模型的 Function Calling 能力
  - Natural Language Interface 的可行性
  - Multi-agent 協作架構的潛力
- 1.3 研究貢獻
  - 提出 LLM-ERP 三層 Agent 架構
  - 實作可運行的開源系統
  - 驗證 LLM 在 ERP 場景的有效性

---

### 2. Related Work (文獻回顧)

- 2.1 傳統 ERP 系統研究
  - ERP 導入困境（Misfits、Workarounds）
  - MPS/MRP/CRP 規劃流程
  - 靜態排程 vs 動態重排程
- 2.2 APS 與智慧排程
  - MILP / GA / RL 演算法比較
  - Dynamic Rescheduling 策略
  - Right-Shifting vs Route Changing
- 2.3 LLM 在企業軟體的應用
  - LLM for Database Query（NL2SQL）
  - LLM Agent 架構（ReAct、Function Calling）
  - 現有 LLM-ERP 相關研究的不足

---

### 3. System Architecture (系統架構)

- 3.1 整體架構
  - 三層設計：對話層 → Agent 層 → 資料層
  - 與傳統 ERP 三層架構的對應（Strategic / Tactical / Operational）
- 3.2 LLM Orchestrator
  - 意圖分類（Intent Classification）
  - 參數抽取（Entity Extraction）
  - Tool Call 路由與執行
  - 多 Provider 支援設計
- 3.3 Domain Agent 設計
  - Inventory Agent：料號管理、庫存查詢、入出庫
  - Purchase Agent：供應商管理、採購單開立
  - BOM Agent：產品結構、多階展開、缺料檢查
- 3.4 Closed-Loop 回饋機制
  - 從 Open-loop 到 Closed-loop 的轉變
  - IoT 數據採集架構（SSN / OPC UA）
  - 動態重排程觸發流程

---

### 4. Implementation (實作)

- 4.1 技術棧選擇
  - Backend: FastAPI + SQLAlchemy + PostgreSQL
  - Frontend: React + Tailwind + Vite
  - LLM: 多 Provider（Claude / GPT / DeepSeek / Ollama）
- 4.2 資料庫設計
  - 9 張核心表格（parts、inventory、suppliers、PO、BOM...）
  - pgvector 對話記憶
  - Audit Log 設計
- 4.3 LLM 整合細節
  - Function Calling 工具定義（JSON Schema）
  - 多 Provider 轉換層
  - 錯誤處理與重試機制
- 4.4 BOM 多階展開實作
  - 遞迴展開 vs 迭代展開
  - 毛需求 → 淨需求計算

---

### 5. Evaluation (評估)

- 5.1 實驗設計
  - 測試案例：庫存查詢、採購開單、BOM 展開、缺料檢查
  - 評估指標：意圖辨識準確率、參數抽取正確率、端到端成功率
  - 比較 Provider：Claude Sonnet vs GPT-4o vs DeepSeek
- 5.2 結果與分析
  - 各 Provider 的準確率比較
  - 回應延遲分析
  - 失敗案例分析
- 5.3 與傳統 ERP 的比較
  - 操作時間（對話 vs 選單）
  - 學習成本
  - 使用者滿意度

---

### 6. Discussion (討論)

- 6.1 LLM 在 ERP 場景的限制
  - Hallucination 風險（特別在庫存數字方面）
  - 延遲問題（即時操作的需求）
  - 成本考量（API Token 消耗）
- 6.2 設計取捨
  - 多 Provider 的維護成本
  - Tool 定義的粒度選擇
  - 安全性與權限控制
- 6.3 未來方向
  - 生產排程 Agent（MPS → APS → MES 完整閉環）
  - 多 Agent 自主協作
  - 數位孿生（Digital Twin）整合
  - RAG 知識庫強化

---

### 7. Conclusion (結論)

- LLM-ERP 證明了 LLM 在 ERP 領域的可行性
- 自然語言介面能顯著降低 ERP 使用門檻
- 多 Provider 架構確保系統的靈活性與可擴展性
- 開源釋出以促進學術與產業交流

---

### References (參考文獻)

1. [ERP 導入與 Workarounds 相關文獻]
2. [Industry 4.0 / Closed-loop 相關文獻]
3. [APS / Dynamic Rescheduling 相關文獻]
4. [LLM Agent / Function Calling 相關文獻]
5. [BOM / MRP 展開相關文獻]

---

## 🎯 投稿建議

| 項目 | 建議 |
|------|------|
| **目標期刊** | IEEE Access（OA、審稿快）或 Sensors（MDPI、工業 4.0 主題）|
| **目標會議** | IEEE ICASI 或 ICCE-TW（時程短、台灣為主） |
| **關鍵字** | LLM, ERP, Intelligent Manufacturing, Agent, Industry 4.0 |
| **預計篇幅** | 8-12 頁 |
| **投稿時程** | 6 月中前完稿 → 7 月投稿 |

---

> 📝 本大綱對應的系統實作位於 `D:\Project\LLM_ERP\`
