// Role-based dashboard configurations for LLM-ERP
// Each role has: widgets, permissions, LLM interaction mode

const ROLES = {
  director: {
    label: '廠長',
    labelEn: 'Factory Director',
    icon: '👨‍💼',
    widgets: ['alert-bar', 'kpi-grid', 'inventory-chart', 'ai-insights', 'quality-panel'],
    llmMode: 'strategic',       // trend analysis, exception summary
    permissions: ['view-all', 'approve-over-issue', 'approve-po-above-100k'],
    notification: ['urgent-only']  // only 🔴 alerts
  },
  production: {
    label: '生管',
    labelEn: 'Production Controller',
    icon: '👨‍🔧',
    widgets: ['dispatch-gantt', 'overdue-orders', 'ai-insights', 'inventory-chart'],
    llmMode: 'tactical',        // what-if simulation, reschedule
    permissions: ['view-production', 'edit-schedule', 'release-wo', 'hold-wo'],
    notification: ['all-production']  // all production alerts
  },
  warehouse: {
    label: '倉庫',
    labelEn: 'Warehouse Keeper',
    icon: '📦',
    widgets: ['pick-list', 'putaway-queue', 'inventory-search', 'stock-alerts'],
    llmMode: 'execution',       // scan-driven, command-oriented
    permissions: ['view-inventory', 'receive-stock', 'issue-stock', 'transfer-stock', 'cycle-count'],
    notification: ['pick-task', 'receipt-task']  // only task notifications
  },
  purchasing: {
    label: '採購',
    labelEn: 'Purchasing Agent',
    icon: '📋',
    widgets: ['po-table', 'supplier-list', 'shortage-forecast', 'price-trend'],
    llmMode: 'tactical',        // multi-vendor comparison, negotiation support
    permissions: ['create-po', 'edit-po', 'view-suppliers', 'approve-po-below-100k'],
    notification: ['po-expedite', 'supplier-late', 'shortage-alert']
  },
  quality: {
    label: '品管',
    labelEn: 'Quality Inspector',
    icon: '✅',
    widgets: ['inspection-queue', 'nc-list', 'defect-pareto', 'capa-tracker'],
    llmMode: 'analytic',        // defect pattern analysis, root cause
    permissions: ['create-nc', 'disposition-nc', 'view-inspection-results', 'close-nc'],
    notification: ['new-nc', 'urgent-inspection', 'capa-due']
  },
  accounting: {
    label: '會計',
    labelEn: 'Accountant/CFO',
    icon: '💰',
    widgets: ['cash-flow', 'ar-aging', 'ap-aging', 'cost-variance', 'gl-journal', 'month-close'],
    llmMode: 'predictive',      // cash forecast, payment recommendations
    permissions: ['view-financial', 'approve-payment', 'cost-close', 'view-gl'],
    notification: ['payment-due', 'invoice-mismatch', 'cash-low', 'ar-overdue']
  }
};

// Widget definitions with component types and data sources
const WIDGETS = {
  'alert-bar':        { type: 'alert', dataSource: 'alert-service', refreshMs: 30000 },
  'kpi-grid':         { type: 'kpi', dataSource: 'kpi-service', refreshMs: 60000 },
  'inventory-chart':  { type: 'chart', chartType: 'bar', dataSource: 'inventory-service' },
  'dispatch-gantt':   { type: 'gantt', dataSource: 'dispatch-service', refreshMs: 30000 },
  'overdue-orders':   { type: 'table', dataSource: 'order-service', refreshMs: 60000 },
  'ai-insights':      { type: 'insight', dataSource: 'llm-orchestrator', refreshMs: 120000 },
  'quality-panel':    { type: 'grid', dataSource: 'quality-service', refreshMs: 60000 },
  'po-table':         { type: 'table', dataSource: 'purchase-service', refreshMs: 60000 },
  'pick-list':        { type: 'task-list', dataSource: 'warehouse-service', refreshMs: 15000 },
  'putaway-queue':    { type: 'task-list', dataSource: 'warehouse-service', refreshMs: 15000 },
  'inventory-search': { type: 'search', dataSource: 'inventory-service' },
  'stock-alerts':     { type: 'alert', dataSource: 'inventory-service', refreshMs: 30000 },
  'supplier-list':    { type: 'table', dataSource: 'purchase-service' },
  'shortage-forecast':{ type: 'chart', chartType: 'line', dataSource: 'mrp-service' },
  'price-trend':      { type: 'chart', chartType: 'line', dataSource: 'purchase-service' },
  'inspection-queue': { type: 'task-list', dataSource: 'quality-service', refreshMs: 15000 },
  'nc-list':          { type: 'table', dataSource: 'quality-service' },
  'defect-pareto':    { type: 'chart', chartType: 'pareto', dataSource: 'quality-service' },
  'capa-tracker':     { type: 'kanban', dataSource: 'quality-service' },
  'cash-flow':        { type: 'chart', chartType: 'area', dataSource: 'finance-service' },
  'ar-aging':         { type: 'table', dataSource: 'finance-service' },
  'ap-aging':         { type: 'table', dataSource: 'finance-service' },
  'cost-variance':    { type: 'table', dataSource: 'finance-service' },
  'gl-journal':       { type: 'table', dataSource: 'finance-service' },
  'month-close':      { type: 'checklist', dataSource: 'finance-service' }
};
