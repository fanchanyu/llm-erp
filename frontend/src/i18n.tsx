import { createContext, useContext, useState, ReactNode } from 'react'

type Lang = 'zh' | 'en'

const TRANS: Record<string, { zh: string; en: string }> = {
  // Header
  'app.title': { zh: 'LLM-ERP', en: 'LLM-ERP' },
  'app.subtitle': { zh: '人機協同智慧製造系統', en: 'Human-Machine Collaborative Smart Manufacturing' },
  
  // Nav
  'nav.diagram': { zh: '🧭 關聯圖', en: '🧭 Diagram' },
  'nav.chat': { zh: '💬 對話', en: '💬 Chat' },
  'nav.dashboard': { zh: '📊 儀表板', en: '📊 Dashboard' },
  'nav.lang': { zh: 'EN', en: '中文' },

  // Diagram
  'diagram.title': { zh: 'ERP 系統關聯圖', en: 'ERP System Diagram' },
  'diagram.subtitle': { zh: '點擊節點查看可執行的操作', en: 'Click a node to see available actions' },
  'diagram.hint': { zh: '🖱️ 點擊任一節點查看可執行的操作', en: '🖱️ Click any node to explore' },
  'diagram.legend': { zh: '🟢 點擊節點 → 建議提問', en: '🟢 Click node → suggested prompts' },
  'diagram.empty': { zh: '← 點擊左側節點\n查看可執行的操作', en: '← Click a node\non the left' },
  'diagram.actions': { zh: '▼ 可操作', en: '▼ Actions' },

  // Diagram - Node labels (use in diagram + panel)
  'node.suppliers': { zh: '供應商', en: 'Suppliers' },
  'node.purchase': { zh: '採購管理', en: 'Purchase' },
  'node.inventory': { zh: '庫存管理', en: 'Inventory' },
  'node.bom': { zh: 'BOM 物料清單', en: 'BOM' },
  'node.products': { zh: '產品定義', en: 'Products' },
  'node.orders': { zh: '工單管理', en: 'Prod. Orders' },
  'node.dispatch': { zh: '派工排程', en: 'Dispatch' },
  'node.workcenters': { zh: '工作站', en: 'Work Centers' },
  'node.quality': { zh: '品質管理 (QC)', en: 'Quality' },
  'node.accounting': { zh: '會計財務', en: 'Accounting' },
  'node.you_can_say': { zh: '📌 你可以這樣說：', en: '📌 Try asking:' },

  // Chat
  'chat.connected': { zh: '已連線 · DeepSeek', en: 'Connected · DeepSeek' },
  'chat.thinking': { zh: 'DeepSeek 思考中...', en: 'DeepSeek is thinking...' },
  'chat.clear': { zh: '✕ 清除對話', en: '✕ Clear chat' },
  'chat.placeholder': { zh: '輸入你的需求，例如：庫存還有多少 M6 螺絲？', en: 'Ask me anything... e.g., "How many M6 screws in stock?"' },
  'chat.send': { zh: '送出 →', en: 'Send →' },
  'chat.welcome': {
    zh: '👋 你好！我是 LLM-ERP 助手。你可以問我：\n\n• 「庫存還有多少 M6 螺絲？」\n• 「幫我向大明螺絲買 500 顆 M6」\n• 「ASM-001 用哪些料？」\n• 「做 5 台 CNC-001，料夠不夠？」',
    en: '👋 Hello! I am your LLM-ERP assistant. Try asking:\n\n• "How many M6 screws are in stock?"\n• "Create a PO for 500 M6 screws from DaMing" \n• "Show me the BOM for ASM-001"\n• "Are there enough materials for 5 CNC-001?"',
  },
  'chat.reset': {
    zh: '👋 對話已重置。有什麼我可以幫你的？',
    en: '👋 Chat reset. How can I help you?',
  },
  'chat.error': { zh: '❌ 錯誤：', en: '❌ Error: ' },
  'chat.fail': { zh: '連線失敗', en: 'Connection failed' },
  'chat.processed': { zh: '處理完成', en: 'Done' },
  
  // Dashboard
  'dashboard.title': { zh: '📊 儀表板', en: '📊 Dashboard' },
  'dashboard.coming': { zh: '儀表板功能開發中...', en: 'Dashboard coming soon...' },

  // Status
  'status.draft': { zh: '草稿', en: 'Draft' },
  'status.released': { zh: '已釋出', en: 'Released' },
  'status.dispatched': { zh: '已派工', en: 'Dispatched' },
  'status.in_progress': { zh: '進行中', en: 'In Progress' },
  'status.completed': { zh: '已完成', en: 'Completed' },
  'status.cancelled': { zh: '已取消', en: 'Cancelled' },
  'status.idle': { zh: '閒置', en: 'Idle' },
  'status.running': { zh: '運行中', en: 'Running' },
  'status.down': { zh: '故障', en: 'Down' },
  'status.maintenance': { zh: '保養中', en: 'Maintenance' },
  // Diagram node statuses
  'status.suppliers': { zh: '2 家', en: '2 vendors' },
  'status.one_po': { zh: '1 張', en: '1 order' },
  'status.twelve_items': { zh: '12 項', en: '12 items' },
  'status.two_boms': { zh: '2 組', en: '2 sets' },
  'status.two_products': { zh: '2 項', en: '2 products' },
  'status.one_order': { zh: '1 張', en: '1 order' },
  'status.pending_dispatch': { zh: '待派工', en: 'Pending' },
  'status.six_wc': { zh: '6 台', en: '6 units' },
  'status.pending_nc': { zh: '2 NC 待處理', en: '2 NCs Open' },
  'status.one_entry': { zh: '1 筆傳票', en: '1 Entry' },
}

interface LangCtx {
  lang: Lang
  setLang: (l: Lang) => void
  t: (key: string) => string
}

const LangContext = createContext<LangCtx>({
  lang: 'zh',
  setLang: () => {},
  t: (k) => TRANS[k]?.zh ?? k,
})

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>('zh')
  
  const t = (key: string): string => {
    const entry = TRANS[key]
    if (!entry) return key
    return entry[lang] ?? key
  }

  return (
    <LangContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LangContext.Provider>
  )
}

export function useTranslation() {
  return useContext(LangContext)
}
