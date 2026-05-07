/* Role configuration for LLM-ERP dashboard.
   Mirrors backend: backend/app/event_engine/role_config.py */

export type RoleId = 'director' | 'production' | 'warehouse' | 'purchasing' | 'quality' | 'accounting' | 'sales'

export interface RoleConfig {
  id: RoleId
  label: string
  labelEn: string
  icon: string
  level: string
  widgets: WidgetId[]
  hints: string[]  // command bar suggestions
}

export type WidgetId =
  | 'alert-bar'
  | 'kpi-grid'
  | 'inventory-chart'
  | 'dispatch-gantt'
  | 'ai-insights'
  | 'overdue-orders'
  | 'po-table'
  | 'quality-panel'
  | 'pick-list'
  | 'putaway-queue'
  | 'inventory-search'
  | 'stock-alerts'
  | 'supplier-list'
  | 'shortage-forecast'
  | 'price-trend'
  | 'inspection-queue'
  | 'nc-list'
  | 'defect-pareto'
  | 'capa-tracker'
  | 'cash-flow'
  | 'ar-aging'
  | 'ap-aging'
  | 'cost-variance'
  | 'gl-journal'
  | 'month-close'
  | 'event-flow'
  | 'production-insights'
  | 'shortage-table'
  | 'capacity-adjust'
  | 'customer-list'
  | 'so-table'
  | 'crm-events'
  | 'history-panel'

export const ROLES: Record<RoleId, RoleConfig> = {
  director: {
    id: 'director',
    label: '廠長',
    labelEn: 'Director',
    icon: '👨‍💼',
    level: '策略級',
    widgets: ['alert-bar', 'kpi-grid', 'inventory-chart', 'ai-insights', 'quality-panel', 'po-table', 'overdue-orders', 'event-flow'],
    hints: ['庫存水位', '本月良率', '逾期工單', '現金流預測'],
  },
  production: {
    id: 'production',
    label: '生管',
    labelEn: 'Production',
    icon: '👨‍🔧',
    level: '戰術級',
    widgets: ['alert-bar', 'kpi-grid', 'dispatch-gantt', 'production-insights', 'shortage-table', 'overdue-orders', 'capacity-adjust', 'event-flow'],
    hints: ['今天排程', '缺料狀況', '急單插隊', '產能分析'],
  },
  warehouse: {
    id: 'warehouse',
    label: '倉庫',
    labelEn: 'Warehouse',
    icon: '📦',
    level: '執行級',
    widgets: ['pick-list', 'putaway-queue', 'inventory-search', 'stock-alerts', 'kpi-grid', 'event-flow'],
    hints: ['今天揀貨', '入庫任務', '查庫存', '呆料清單'],
  },
  purchasing: {
    id: 'purchasing',
    label: '採購',
    labelEn: 'Purchasing',
    icon: '📋',
    level: '戰術級',
    widgets: ['alert-bar', 'kpi-grid', 'po-table', 'supplier-list', 'shortage-forecast', 'price-trend', 'event-flow'],
    hints: ['開採購單', '逾期PO', '供應商評分', '比價建議'],
  },
  quality: {
    id: 'quality',
    label: '品管',
    labelEn: 'Quality',
    icon: '✅',
    level: '分析級',
    widgets: ['inspection-queue', 'nc-list', 'defect-pareto', 'capa-tracker', 'kpi-grid', 'event-flow'],
    hints: ['待檢批次', '不合格單', '缺陷分析', 'CAPA進度'],
  },
  accounting: {
    id: 'accounting',
    label: '會計',
    labelEn: 'Accounting',
    icon: '💰',
    level: '預測級',
    widgets: ['cash-flow', 'ar-aging', 'ap-aging', 'cost-variance', 'gl-journal', 'month-close', 'kpi-grid', 'event-flow'],
    hints: ['現金水位', '應收帳款', '應付到期', '成本差異'],
  },
  sales: {
    id: 'sales',
    label: '業務',
    labelEn: 'Sales',
    icon: '🤝',
    level: '戰術級',
    widgets: ['alert-bar', 'kpi-grid', 'customer-list', 'so-table', 'crm-events', 'history-panel', 'event-flow'],
    hints: ['客戶查詢', '新增訂單', 'CRM記錄', '訂單進度'],
  },
}

export const ROLE_LIST: RoleConfig[] = [
  ROLES.director,
  ROLES.production,
  ROLES.warehouse,
  ROLES.purchasing,
  ROLES.quality,
  ROLES.accounting,
  ROLES.sales,
]
