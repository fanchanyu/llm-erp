import { useState, useEffect } from 'react'
import { RoleProvider, useRole } from './hooks/useRole'
import type { RoleId, WidgetId } from './roles'
import { useTranslation } from './i18n'
import {
  getActivityFeed, getUnreadCount, queryStock,
  listOrders, listSuppliers,
  listInspections, listNCs, listCAPAs,
  listAR, listJournalEntries,
  listWorkCenters, listDispatchOrders,
  listCustomers, listSalesOrders,
  confirmSalesOrder, shipSalesOrder, deliverSalesOrder,
  getCRMEvents, createCRMEvent,
  listConversationSessions, getConversation,
} from './api/client'

// ─── Main App ────────────────────────────────────────────────────
export default function App() {
  return (
    <RoleProvider>
      <AppInner />
    </RoleProvider>
  )
}

function AppInner() {
  const { role, setRole, roleConfig, roleList } = useRole()
  const { lang, setLang } = useTranslation()
  const [notifCount, setNotifCount] = useState(0)
  const [events, setEvents] = useState<any[]>([])
  const [cmd, setCmd] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(true)

  // Fetch notifications count
  useEffect(() => {
    getUnreadCount(role).then(d => {
      if (d?.unread !== undefined) setNotifCount(d.unread)
    })
    const iv = setInterval(() => {
      getUnreadCount(role).then(d => {
        if (d?.unread !== undefined) setNotifCount(d.unread)
      })
    }, 30000)
    return () => clearInterval(iv)
  }, [role])

  // Fetch live events
  useEffect(() => {
    getActivityFeed(8).then(d => {
      if (d?.events) setEvents(d.events)
    })
    const iv = setInterval(async () => {
      const d = await getActivityFeed(8)
      if (d?.events) setEvents(d.events)
    }, 15000)
    return () => clearInterval(iv)
  }, [])

  // Fetch live stock data — used by InventoryChart component
  useEffect(() => {
    // Stock data is fetched directly inside InventoryChart component
  }, [])

  const handleCmd = () => {
    if (!cmd.trim()) return
    alert(`[${roleConfig.label}] 指令: "${cmd}"\n\n(開發中) 將由 LLM 解析意圖並更新儀表板`)
    setCmd('')
  }

  return (
    <div className="min-h-screen bg-[#0a0e17] text-gray-200 flex">
      {/* ── Sidebar ── */}
      <aside className={`${sidebarOpen ? 'w-56' : 'w-16'} bg-[#0d111c] border-r border-gray-800 flex flex-col shrink-0 transition-all duration-200`}>
        {/* Logo */}
        <div className="h-14 flex items-center gap-3 px-4 border-b border-gray-800">
          <div className="w-8 h-8 bg-cyan-400 rounded-lg flex items-center justify-center shrink-0">
            <span className="text-[#0a0e17] font-bold text-sm">E</span>
          </div>
          {sidebarOpen && <span className="text-white font-bold text-sm tracking-tight">LLM-ERP</span>}
        </div>

        {/* Role selector */}
        <div className="px-3 pt-3 pb-2">
          {sidebarOpen && <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-2 px-1">角色切換</div>}
          {roleList.map(r => (
            <button
              key={r.id}
              onClick={() => setRole(r.id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-all mb-0.5 ${
                role === r.id
                  ? 'bg-cyan-500/10 text-cyan-400'
                  : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800/50'
              }`}
              title={lang === 'zh' ? r.label : r.labelEn}
            >
              <span className="text-base shrink-0">{r.icon}</span>
              {sidebarOpen && (
                <>
                  <span className="text-xs font-medium truncate flex-1 text-left">
                    {lang === 'zh' ? r.label : r.labelEn}
                  </span>
                  <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${
                    role === r.id ? 'bg-cyan-500/15 text-cyan-400' : 'bg-gray-800 text-gray-600'
                  }`}>
                    {role === r.id ? '◀' : ''}
                  </span>
                </>
              )}
            </button>
          ))}
        </div>

        {/* Nav */}
        <div className="border-t border-gray-800 my-3 mx-3" />
        <div className="px-3 flex flex-col gap-0.5">
          <NavItem icon="📊" label="儀表板" active />
          <NavItem icon="📖" label="工作日誌" />
          <NavItem icon="⚙️" label="設定" />
        </div>

        {/* Bottom */}
        <div className="mt-auto border-t border-gray-800 p-3 flex flex-col gap-2">
          <div className="flex items-center gap-2 px-2 py-2 bg-[#0f1525] rounded-lg">
            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-cyan-400 to-cyan-600 flex items-center justify-center text-[8px] font-bold text-[#0a0e17] shrink-0">P</div>
            {sidebarOpen && (
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium truncate">Peter 范</div>
                <div className="text-[10px] text-gray-500 truncate">{lang === 'zh' ? roleConfig.label : roleConfig.labelEn}</div>
              </div>
            )}
          </div>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="text-gray-500 hover:text-gray-300 text-[10px] px-2 py-1 rounded hover:bg-gray-800 transition-all"
          >
            {sidebarOpen ? '◀ 收合' : '▶'}
          </button>
        </div>
      </aside>

      {/* ── Main ── */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-12 flex items-center justify-between px-5 border-b border-gray-800 bg-[#0c101c] shrink-0">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5 text-xs text-gray-400">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 inline-block" />
              {new Date().toLocaleDateString('zh-TW', { weekday: 'short', year: 'numeric', month: '2-digit', day: '2-digit' })}
            </span>
            <span className="text-xs text-gray-500">
              <strong className="text-cyan-400">{roleConfig.icon} {lang === 'zh' ? roleConfig.label : roleConfig.labelEn}</strong>
              {' — '}{roleConfig.level}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <button className="relative text-sm" title="通知">
              🔔
              {notifCount > 0 && (
                <span className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-red-500 rounded-full text-[8px] flex items-center justify-center text-white font-bold">
                  {notifCount}
                </span>
              )}
            </button>
            <button
              onClick={() => setLang(lang === 'zh' ? 'en' : 'zh')}
              className="text-[10px] font-bold text-gray-500 hover:text-white px-2 py-1 rounded border border-gray-700 hover:border-gray-500 uppercase tracking-wider transition-all"
            >
              {lang === 'zh' ? 'EN' : '中'}
            </button>
            <span className="text-[10px] text-gray-600">DeepSeek ✓</span>
          </div>
        </header>

        {/* Command bar */}
        <div className="px-5 pt-3 pb-1 shrink-0">
          <div className="flex items-center gap-2 bg-[#141b2d] border border-gray-800 rounded-lg px-3 py-2 transition-all focus-within:border-cyan-500/50">
            <span className="text-gray-500 text-sm">💬</span>
            <input
              value={cmd}
              onChange={e => setCmd(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleCmd()}
              placeholder={`${lang === 'zh' ? '輸入指令…' : 'Enter command…'} (e.g. ${roleConfig.hints[0]})`}
              className="flex-1 bg-transparent outline-none text-xs text-gray-200 placeholder-gray-600"
            />
            <div className="hidden md:flex gap-1.5">
              {roleConfig.hints.slice(0, 3).map((h: string) => (
                  <span
                    key={h}
                    onClick={() => { setCmd(h); handleCmd() }}
                  className="text-[10px] text-gray-600 bg-gray-800/50 px-1.5 py-0.5 rounded cursor-pointer hover:bg-gray-700"
                >
                  {h}
                </span>
              ))}
            </div>
            <kbd className="text-[10px] text-gray-600 bg-gray-800 px-1.5 py-0.5 rounded">⏎</kbd>
          </div>
        </div>

        {/* Dashboard Grid */}
        <div className="flex-1 overflow-y-auto px-5 pb-5">
          <div className="grid grid-cols-12 gap-3 auto-rows-min">
            {/* Always show alert bar */}
            <div className="col-span-12">
              <AlertWidget role={role} />
            </div>

            {/* KPI grid */}
            <div className="col-span-12">
              <KPIWidget role={role} />
            </div>

            {/* Role-specific widgets */}
            {roleConfig.widgets.filter(w => w !== 'alert-bar' && w !== 'kpi-grid' && w !== 'event-flow').map(w => (
              <div key={w} className={getWidgetSpan(w)}>
                <WidgetSlot widgetId={w} role={role} events={events} />
              </div>
            ))}

            {/* Event flow (always at bottom) */}
            <div className="col-span-12">
              <EventFlowWidget events={events} />
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

// ─── Helpers ─────────────────────────────────────────────────────

function getWidgetSpan(w: string): string {
  if (['inventory-chart', 'dispatch-gantt', 'po-table', 'cash-flow', 'nc-list', 'customer-list', 'so-table'].includes(w)) return 'col-span-12 md:col-span-7'
  if (['ai-insights', 'production-insights', 'quality-panel', 'overdue-orders', 'pick-list', 'putaway-queue', 'inspection-queue', 'defect-pareto', 'supplier-list', 'shortage-forecast', 'price-trend', 'ar-aging', 'ap-aging', 'cost-variance', 'gl-journal', 'month-close', 'capa-tracker', 'stock-alerts', 'inventory-search', 'shortage-table', 'capacity-adjust', 'crm-events', 'history-panel'].includes(w)) return 'col-span-12 md:col-span-5'
  return 'col-span-12 md:col-span-6'
}

function WidgetSlot({ widgetId, role: _role, events: _events }: { widgetId: WidgetId; role: RoleId; events: any[] }) {
  switch (widgetId) {
    case 'inventory-chart': return <InventoryChart />
    case 'dispatch-gantt': return <DispatchGantt />
    case 'ai-insights': return <AIInsights role={_role} />
    case 'production-insights': return <ProductionInsights />
    case 'quality-panel': return <QualityPanel />
    case 'overdue-orders': return <OverdueOrders />
    case 'po-table': return <POTable />
    case 'pick-list': return <PickList />
    case 'putaway-queue': return <PutawayQueue />
    case 'inventory-search': return <InventorySearch />
    case 'stock-alerts': return <StockAlerts />
    case 'supplier-list': return <SupplierList />
    case 'shortage-forecast': return <ShortageForecast />
    case 'price-trend': return <PriceTrend />
    case 'inspection-queue': return <InspectionQueue />
    case 'nc-list': return <NCList />
    case 'defect-pareto': return <DefectPareto />
    case 'capa-tracker': return <CAPATracker />
    case 'cash-flow': return <CashFlow />
    case 'ar-aging': return <ARAging />
    case 'ap-aging': return <APAging />
    case 'cost-variance': return <CostVariance />
    case 'gl-journal': return <GLJournal />
    case 'month-close': return <MonthClose />
    case 'shortage-table': return <ShortageTable />
    case 'capacity-adjust': return <CapacityAdjust />
    case 'customer-list': return <CustomerList />
    case 'so-table': return <SalesOrderTable />
    case 'crm-events': return <CRMEvents />
    case 'history-panel': return <HistoryPanel />
    default: return <div className="bg-[#0d111c] border border-gray-800 rounded-lg p-4 text-xs text-gray-500">Widget: {widgetId}</div>
  }
}

// ─── Nav Item ────────────────────────────────────────────────────
function NavItem({ icon, label, active }: { icon: string; label: string; active?: boolean }) {
  return (
    <div className={`flex items-center gap-3 px-3 py-2 rounded-md text-xs cursor-pointer transition-all ${
      active ? 'text-gray-200 bg-gray-800/30' : 'text-gray-600 hover:text-gray-400 hover:bg-gray-800/20'
    }`}>
      <span className="text-base">{icon}</span>
      <span>{label}</span>
    </div>
  )
}

// ─── Widget: Alert Bar ───────────────────────────────────────────
function AlertWidget({ role }: { role: RoleId }) {
  const [alerts, setAlerts] = useState<{icon:string;text:string;action:string}[]>([])
  useEffect(() => {
    fetch(`/api/dashboard/alerts/${role}`).then(r=>r.json()).then(d => {
      if (d?.alerts) setAlerts(d.alerts)
    }).catch(() => {})
  }, [role])
  const a = alerts[0] || { icon: '🟢', text: '無異常', action: '正常' }
  return (
    <div className={`flex items-center gap-3 rounded-lg px-4 py-2.5 ${
      a.icon === '🔴' ? 'bg-red-500/5 border border-red-500/20' :
      a.icon === '🟡' ? 'bg-yellow-500/5 border border-yellow-500/20' :
      'bg-green-500/5 border border-green-500/20'
    }`}>
      <span className="text-lg">{a.icon}</span>
      <span className={`text-xs flex-1 ${
        a.icon === '🔴' ? 'text-red-300/90' : a.icon === '🟡' ? 'text-yellow-300/90' : 'text-green-300/90'
      }`}>{a.text}</span>
      <span className="text-[10px] bg-white/5 px-2 py-1 rounded border border-white/10 cursor-pointer hover:bg-white/10">{a.action}</span>
      {alerts.length > 1 && <span className="text-[10px] text-gray-500">+{alerts.length - 1} 更多</span>}
    </div>
  )
}

// ─── Widget: KPI Grid ────────────────────────────────────────────
function KPIWidget({ role }: { role: RoleId }) {
  const [kpis, setKpis] = useState<{label:string;value:string;color:string;change:string;dir:string}[]>(
    Array(6).fill({label:'載入中',value:'—',color:'#4ade80',change:'',dir:'up'})
  )
  useEffect(() => {
    fetch(`/api/dashboard/kpi/${role}`).then(r=>r.json()).then(d => {
      if (d?.kpis) setKpis(d.kpis)
    }).catch(() => {})
  }, [role])
  return (
    <div className="grid grid-cols-6 gap-2">
      {kpis.map((k: any) => (
        <div key={k.label} className="bg-[#0d111c] border border-gray-800 rounded-lg p-3">
          <div className="text-[10px] text-gray-500 mb-0.5">{k.label}</div>
          <div className="text-lg font-bold" style={{ color: k.color }}>{k.value}</div>
          <div className={`text-[10px] mt-0.5 ${k.dir === 'up' ? 'text-green-400' : k.dir === 'down' ? 'text-red-400' : 'text-yellow-400'}`}>{k.change}</div>
        </div>
      ))}
    </div>
  )
}

// ─── Widget: Inventory Chart (live data) ────────────────────────
function InventoryChart() {
  const [stock, setStock] = useState<any[]>([])
  useEffect(() => {
    queryStock().then(d => {
      if (Array.isArray(d)) setStock(d)
    }).catch(() => {})
  }, [])

  // Sort by quantity descending, take top 10
  const items = [...stock].sort((a: any, b: any) => b.quantity - a.quantity).slice(0, 10)
  const maxQty = Math.max(...items.map((i: any) => i.quantity), 1)

  return (
    <div className="bg-[#0d111c] border border-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] text-gray-500 uppercase tracking-wider">📦 庫存水位 — 前10高風險物料</span>
        <span className="text-[10px] text-cyan-400 cursor-pointer">全部→</span>
      </div>
      <div className="flex items-end gap-1 h-28 relative">
        {items.length === 0 && <div className="text-[10px] text-gray-500 w-full text-center pt-8">載入中…</div>}
        {items.map((item: any, i: number) => {
          const pct = Math.max((item.quantity / maxQty) * 100, 2)
          const isHigh = item.quantity > maxQty * 0.7
          const isLow = item.quantity < maxQty * 0.15
          return (
            <div key={i} className="flex-1 flex flex-col items-center justify-end h-full">
              <div
                className={`w-full rounded-t ${isHigh ? 'bg-red-500/40 border-red-500/30' : isLow ? 'bg-yellow-400/30 border-yellow-500/30' : 'bg-cyan-400/30 border-cyan-500/20'} border-t border-l border-r`}
                style={{ height: `${pct}%`, minHeight: 4 }}
              />
              <span className="text-[7px] text-gray-600 mt-0.5 whitespace-nowrap">{item.name || item.part_no}</span>
            </div>
          )
        })}
        {/* Safety line */}
        <div className="absolute left-0 right-0 top-[30%] border-t border-dashed border-red-500/30" />
        <span className="absolute right-0 top-[28%] text-[7px] text-red-400">安全線</span>
      </div>
      <div className="flex justify-between text-[8px] text-gray-500 mt-2">
        <span className="text-red-400">🔴 超安全庫存 3</span>
        <span className="text-yellow-400">🟡 低於安全線 3</span>
        <span className="text-green-400">🟢 正常 4</span>
      </div>
    </div>
  )
}

// ─── Dispatch Gantt ──────────────────────────────────────
function DispatchGantt() {
  const [wcs, setWcs] = useState<any[]>([])
  const [orders, setOrders] = useState<any[]>([])
  useEffect(() => {
    listWorkCenters().then(d => { if (Array.isArray(d)) setWcs(d) }).catch(() => {})
    listDispatchOrders('dispatched').then(d => { if (Array.isArray(d)) setOrders(d) }).catch(() => {})
  }, [])
  // Build rows from work centers
  const rows = wcs.slice(0, 8).map((wc: any, idx: number) => {
    const wcOrders = orders.filter((o: any) =>
      o.operations?.some((op: any) => op.work_center_id === wc.id)
    )
    const bars = wcOrders.slice(0, 2).map((o: any, i: number) => ({
      left: (idx * 7 + i * 30) % 70,
      w: 20 + (o.operations?.length || 1) * 5,
      color: o.priority === 1 ? '#fbbf24' : '#22d3ee',
      text: o.order_no || '',
    }))
    if (bars.length === 0) bars.push({ left: 10, w: 30, color: '#1e293b', text: '閒置' })
    return { label: wc.name, bars, status: wc.status }
  })
  return (
    <div className="bg-[#0d111c] border border-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] text-gray-500 uppercase tracking-wider">🏭 機台排程 — 即時</span>
        <span className="text-[10px] text-cyan-400 cursor-pointer">🔄 重新排程</span>
      </div>
      <div className="flex flex-col gap-2">
        {rows.map(r => (
          <div key={r.label} className="flex items-center gap-2">
            <span className="w-16 text-[10px] text-gray-400 shrink-0 truncate">{r.label}</span>
            <div className="flex-1 h-4 bg-[#0f1525] rounded relative overflow-hidden">
              {r.bars.map((b, i) => (
                <div key={i} className="absolute h-full rounded flex items-center px-1 text-[7px] text-white font-medium truncate"
                  style={{ left: `${b.left}%`, width: `${b.w}%`, background: b.color }}>
                  {b.text}
                </div>
              ))}
              <div className="absolute top-0 bottom-0 w-px bg-red-500 z-10" style={{ left: '45%' }} />
            </div>
            <span className={`text-[8px] w-10 text-right ${
              r.status === 'down' ? 'text-red-400' : r.status === 'idle' ? 'text-green-400' : 'text-cyan-400'
            }`}>{r.status}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Widget: AI Insights ─────────────────────────────────────────
function AIInsights({ role: _role }: { role: RoleId }) {
  const insights = [
    { icon: '🔴', text: '銅排庫存12%，2天內用完', sug: '緊急採購 / 替代料 / 調單', role: 'director' },
    { icon: '🟡', text: 'WO-003 投料異常 BOM80已開100', sug: '退料20 / 保留轉單 / 核准超發', role: 'director' },
    { icon: '🟡', text: '裝配線A 負載112%，WO-007估延1.5天', sug: '加班2h / 外發 / 調整優先級', role: 'director' },
    { icon: '🟢', text: '良率96.8% ↑1.2% — 銑床改善見效', sug: '建議固化SOP', role: 'director' },
  ]
  return (
    <div className="bg-[#0d111c] border border-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] text-gray-500 uppercase tracking-wider">🧠 AI 主動分析</span>
        <span className="text-[10px] text-cyan-400 cursor-pointer">刷新</span>
      </div>
      <div className="flex flex-col gap-1.5">
        {insights.map((ins, i) => (
          <div key={i} className={`flex gap-2 px-2.5 py-2 rounded-md text-xs cursor-pointer hover:bg-gray-800/30 ${
            ins.icon === '🔴' ? 'bg-red-500/3 border-l-2 border-red-500' :
            ins.icon === '🟡' ? 'bg-yellow-500/3 border-l-2 border-yellow-500' :
            'bg-green-500/3 border-l-2 border-green-500'
          }`}>
            <span>{ins.icon}</span>
            <div>
              <strong className="text-gray-200">{ins.text}</strong>
              <div className="text-[10px] text-gray-500 mt-0.5">💡 {ins.sug}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Production Insights ─────────────────────────────────────────
function ProductionInsights() {
  return <div className="bg-[#0d111c] border border-gray-800 rounded-lg p-4">
    <div className="text-[10px] text-gray-500 uppercase mb-3">🧠 生產AI建議</div>
    <div className="flex flex-col gap-1.5">
      <div className="flex gap-2 px-2.5 py-2 rounded-md text-xs bg-yellow-500/3 border-l-2 border-yellow-500 cursor-pointer hover:bg-gray-800/30">
        <span>🟡</span><div><strong>裝配線A 滿載112%</strong><div className="text-[10px] text-gray-500 mt-0.5">建議：WO-007延1天 或 加班2h</div></div>
      </div>
      <div className="flex gap-2 px-2.5 py-2 rounded-md text-xs bg-yellow-500/3 border-l-2 border-yellow-500 cursor-pointer hover:bg-gray-800/30">
        <span>🟡</span><div><strong>鑽床-01 急單WO-006插隊</strong><div className="text-[10px] text-gray-500 mt-0.5">WO-003 Op2順延30min，交期仍可達</div></div>
      </div>
      <div className="flex gap-2 px-2.5 py-2 rounded-md text-xs bg-green-500/3 border-l-2 border-green-500 cursor-pointer hover:bg-gray-800/30">
        <span>🟢</span><div><strong>銑床-01 提前完工</strong><div className="text-[10px] text-gray-500 mt-0.5">剩餘工時低於預估</div></div>
      </div>
    </div>
  </div>
}

// ─── Quality Panel ───────────────────────────────────────────────
function QualityPanel() {
  return <div className="bg-[#0d111c] border border-gray-800 rounded-lg p-4">
    <div className="flex items-center justify-between mb-3">
      <span className="text-[10px] text-gray-500 uppercase tracking-wider">✅ 品質即時</span>
      <span className="text-[10px] text-cyan-400 cursor-pointer">→</span>
    </div>
    <div className="grid grid-cols-2 gap-2">
      {[
        { v: '96.8%', l: '良率', c: '#4ade80' },
        { v: '7', l: '不合格', c: '#ef4444' },
        { v: '3', l: '待處置NC', c: '#fbbf24' },
        { v: '2', l: 'CAPA', c: '#22d3ee' },
      ].map(q => (
        <div key={q.l} className="bg-[#0f1525] p-2 rounded-lg text-center">
          <div className="text-lg font-bold" style={{ color: q.c }}>{q.v}</div>
          <div className="text-[9px] text-gray-500">{q.l}</div>
        </div>
      ))}
    </div>
  </div>
}

// ─── Overdue Orders ──────────────────────────────────────────────
function OverdueOrders() {
  const [orders, setOrders] = useState<any[]>([])
  useEffect(() => {
    listDispatchOrders().then(d => {
      if (Array.isArray(d)) {
        const today = new Date()
        const overdue = d.filter((o: any) => {
          const dd = o.due_date ? new Date(o.due_date) : null
          return dd && dd < today && o.status !== 'completed' && o.status !== 'cancelled'
        })
        setOrders(overdue.slice(0, 5))
      }
    }).catch(() => {})
  }, [])
  const rows = orders.map((o: any) => {
    const dd = o.due_date ? new Date(o.due_date) : null
    const days = dd ? Math.floor((Date.now() - dd.getTime()) / 86400000) : 0
    return [
      o.order_no,
      o.product_no || o.product_name || '-',
      <span className="text-red-400">{days}天</span>,
      <Tag color="red">逾期待處理</Tag>,
    ]
  })
  return <SimpleTable
    title="⏰ 逾期工單"
    headers={['工單', '品項', '逾期', '原因']}
    rows={rows.length > 0 ? rows : [['暫無', '—', <span className="text-green-400">0天</span>, <Tag color="green">正常</Tag>]]}
  />
}

// ─── PO Table ────────────────────────────────────────────────────
function POTable() {
  const [orders, setOrders] = useState<any[]>([])
  useEffect(() => {
    listOrders().then(d => { if (d?.orders) setOrders(d.orders) }).catch(() => {})
  }, [])
  const rows = orders.slice(0, 5).map((po: any) => [
    po.po_no,
    po.supplier_name,
    po.items?.length > 0 ? `NT${Intl.NumberFormat('zh-TW').format(po.items.reduce((a: number, i: any) => a + (i.unit_price||0)*i.quantity, 0))}` : '-',
    <Tag color={po.status === 'sent' ? 'cyan' : po.status === 'received' ? 'green' : po.status === 'cancelled' ? 'red' : 'yellow'}>{po.status}</Tag>,
  ])
  return <SimpleTable title="📋 採購單" headers={['PO#', '供應商', '金額', '狀態']} rows={rows} action="全部→" />
}

// ─── Pick List ───────────────────────────────────────────────────
function PickList() {
  return <TaskPanel title="📋 今天揀貨任務" tasks={[
    { pri: 'high', text: 'WO-005: 銅排3mm x 120kg', loc: 'A-12-03', time: '08:30' },
    { pri: 'high', text: 'WO-006: 感測器 x 50pcs', loc: 'B-08-01', time: '09:00' },
    { pri: 'med', text: 'WO-003: 底板 x 100pcs', loc: 'A-05-11', time: '10:00' },
    { pri: 'med', text: 'WO-004: 密封圈 x 200pcs', loc: 'C-02-07', time: '10:30' },
    { pri: 'low', text: 'WO-002: 螺絲M6 x 500pcs', loc: 'B-01-22', time: '14:00' },
  ]} />
}

// ─── Putaway Queue ──────────────────────────────────────────────
function PutawayQueue() {
  return <SimpleTable
    title="📥 入庫待辦"
    headers={['單號', '品項', '數量', '位置', '狀態']}
    rows={[
      ['PO-0428', '鋁板6061', '500kg', 'A-01-03', <Tag color="yellow">待上架</Tag>],
      ['PO-0503', '螺絲M6', '2000pcs', 'B-01-22', <Tag color="yellow">待上架</Tag>],
      ['PO-0504', '油壓缸', '10pcs', 'D-03-01', <Tag color="red">待QC</Tag>],
      ['退料', 'WO-003退料', '20pcs', 'A-05-11', <Tag color="cyan">待入庫</Tag>],
    ]}
  />
}

// ─── Inventory Search ───────────────────────────────────────────
function InventorySearch() {
  return <div className="bg-[#0d111c] border border-gray-800 rounded-lg p-4">
    <span className="text-[10px] text-gray-500 uppercase tracking-wider">🔍 庫存查詢</span>
    <div className="flex gap-2 mt-3 mb-2">
      <input placeholder="輸入料號或名稱…" className="flex-1 bg-[#0f1525] border border-gray-800 rounded px-2.5 py-1.5 text-xs text-gray-200 outline-none focus:border-cyan-500/50" />
      <button className="bg-cyan-500 text-[#0a0e17] text-[10px] font-semibold px-2.5 rounded">查詢</button>
    </div>
    <div className="text-[10px] text-gray-500">最近查詢：銅排3mm → A-12-03, 庫存48kg</div>
  </div>
}

// ─── Stock Alerts ───────────────────────────────────────────────
function StockAlerts() {
  const [items, setItems] = useState<any[]>([])
  useEffect(() => {
    queryStock().then(d => {
      if (Array.isArray(d)) {
        // Show items with low stock (bottom 20%)
        const sorted = [...d].sort((a: any, b: any) => a.quantity - b.quantity)
        const low = sorted.slice(0, Math.min(3, sorted.length))
        setItems(low.map((s: any) => ({
          icon: s.quantity < 20 ? '🔴' as const : '🟡' as const,
          text: `${s.part_no || s.name} 庫存 ${s.quantity}${s.unit || ''}`,
          sug: `位置: ${s.location || 'N/A'} | ${s.category || ''}`,
        })))
      }
    }).catch(() => {})
  }, [])
  return <InsightPanel title="⚠️ 庫存預警" items={items.length > 0 ? items : [
    { icon: '🟢', text: '無異常', sug: '所有物料庫存正常' },
  ]} />
}

// ─── Supplier List ──────────────────────────────────────────────
function SupplierList() {
  const [suppliers, setSuppliers] = useState<any[]>([])
  useEffect(() => {
    listSuppliers().then(d => { if (d?.suppliers) setSuppliers(d.suppliers) }).catch(() => {})
  }, [])
  const rows = suppliers.slice(0, 5).map((s: any) => [
    s.name,
    <span className={s.score < 2 ? 'text-red-400' : s.score < 3 ? 'text-yellow-400' : 'text-green-400'}>{s.score}</span>,
    s.phone || '-',
    s.contact || '-',
  ])
  return <SimpleTable title="🏢 供應商評分" headers={['供應商', '評分', '電話', '聯絡人']} rows={rows} />
}

// ─── Shortage Forecast ──────────────────────────────────────────
function ShortageForecast() {
  const [shortages, setShortages] = useState<any[]>([])
  useEffect(() => {
    // Check BOM shortage for both products
    Promise.allSettled([
      fetch('/api/bom/check-shortage', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({product_no:'ASM-001', quantity:10}) }).then(r=>r.json()),
      fetch('/api/bom/check-shortage', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({product_no:'CNC-001', quantity:5}) }).then(r=>r.json()),
    ]).then(results => {
      const all: any[] = []
      results.forEach(r => {
        if (r.status === 'fulfilled' && r.value?.shortages) all.push(...r.value.shortages)
      })
      if (all.length > 0) setShortages(all.slice(0, 5))
    })
  }, [])
  const rows = shortages.map((s: any) => [
    s.part_no,
    <span className="text-red-400">{Math.ceil(s.shortage / s.required * 100)}%</span>,
    `需 ${s.required} / 有 ${s.available}`,
    <span className="text-cyan-400">建議採購</span>,
  ])
  return rows.length > 0
    ? <SimpleTable title="📊 缺料預測" headers={['物料', '缺料比率', '需求量', '建議']} rows={rows} />
    : <SimpleTable title="📊 缺料預測" headers={['物料', '可用天數', '影響工單', '建議']} rows={[
        ['M6x20', <span className="text-green-400">充足</span>, '所有工單', <span className="text-green-400">正常</span>],
      ]} />
}

// ─── Shortage Table (production view) ───────────────────────────
function ShortageTable() {
  return <SimpleTable title="🔴 缺料影響工單" headers={['工單', '缺料', '影響', '預計到料']} rows={[
    ['WO-005', '銅排3mm', '無法開工', <span className="text-yellow-400">05/08</span>],
    ['WO-006', '感測器', 'Op4無法進行', <span className="text-yellow-400">05/07</span>],
  ]} />
}

// ─── Capacity Adjust ────────────────────────────────────────────
function CapacityAdjust() {
  return <div className="bg-[#0d111c] border border-gray-800 rounded-lg p-4">
    <span className="text-[10px] text-gray-500 uppercase tracking-wider">⚡ 產能調整</span>
    <div className="flex flex-col gap-2 mt-3">
      {[
        { label: '裝配線A 加班', detail: '+2h → 多產5台' },
        { label: 'WO-007 外發加工', detail: '協力廠有產能' },
      ].map(c => (
        <div key={c.label} className="flex items-center gap-2 bg-[#0f1525] p-2 rounded-lg">
          <span className="text-xs text-gray-400 flex-1">{c.label}</span>
          <span className="text-[10px] text-yellow-400">{c.detail}</span>
          <span className="text-[10px] text-cyan-400 cursor-pointer">套用</span>
        </div>
      ))}
    </div>
  </div>
}

// ─── Customer List (業務) ────────────────────────────────────────
function CustomerList() {
  const [customers, setCustomers] = useState<any[]>([])
  const [search, setSearch] = useState('')
  useEffect(() => {
    listCustomers(search || undefined).then(d => {
      if (d?.customers) setCustomers(d.customers)
    }).catch(() => {})
  }, [search])
  const levelColor = (lvl: string) => {
    if (lvl === 'A') return 'green'
    if (lvl === 'B') return 'yellow'
    return 'gray'
  }
  const rows = customers.slice(0, 6).map((c: any) => [
    c.customer_no,
    c.name,
    c.contact_person || '-',
    c.phone || '-',
    <Tag color={levelColor(c.level)}>{c.level || 'C'}</Tag>,
  ])
  return (
    <div className="bg-[#0d111c] border border-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] text-gray-500 uppercase tracking-wider">👥 客戶列表</span>
        <span className="text-[10px] text-cyan-400 cursor-pointer">全部→</span>
      </div>
      <div className="flex gap-2 mb-3">
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="搜尋客戶…"
          className="flex-1 bg-[#0f1525] border border-gray-800 rounded px-2.5 py-1.5 text-xs text-gray-200 outline-none focus:border-cyan-500/50"
        />
      </div>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-[9px] text-gray-500 uppercase tracking-wider">
            <th className="text-left pb-2 pr-2 font-medium">客戶編號</th>
            <th className="text-left pb-2 pr-2 font-medium">名稱</th>
            <th className="text-left pb-2 pr-2 font-medium">聯絡人</th>
            <th className="text-left pb-2 pr-2 font-medium">電話</th>
            <th className="text-left pb-2 pr-2 font-medium">等級</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t border-gray-800/50 hover:bg-cyan-500/5">
              {row.map((cell, j) => <td key={j} className="py-2 pr-2 text-gray-300">{cell}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ─── Sales Order Table (業務) ───────────────────────────────────
function SalesOrderTable() {
  const [orders, setOrders] = useState<any[]>([])
  const [acting, setActing] = useState<number | null>(null)

  useEffect(() => {
    listSalesOrders().then(d => { if (d?.orders) setOrders(d.orders) }).catch(() => {})
  }, [])

  const doAction = async (id: number, action: 'confirm' | 'ship' | 'deliver') => {
    setActing(id)
    try {
      if (action === 'confirm') await confirmSalesOrder(id)
      else if (action === 'ship') await shipSalesOrder(id)
      else await deliverSalesOrder(id)
      const d = await listSalesOrders()
      if (d?.orders) setOrders(d.orders)
    } catch (e) { console.error(e) }
    setActing(null)
  }

  return (
    <div className="bg-[#0d111c] border border-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] text-gray-500 uppercase tracking-wider">📋 銷售訂單</span>
        <span className="text-[10px] text-cyan-400 cursor-pointer" onClick={() => listSalesOrders().then(d => { if (d?.orders) setOrders(d.orders) }).catch(() => {})}>🔄 刷新</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-500 border-b border-gray-800">
              <th className="text-left py-2 px-2">SO#</th>
              <th className="text-left py-2 px-2">客戶</th>
              <th className="text-left py-2 px-2">狀態</th>
              <th className="text-right py-2 px-2">金額</th>
              <th className="text-left py-2 px-2">日期</th>
              <th className="text-center py-2 px-2">操作</th>
            </tr>
          </thead>
          <tbody>
            {orders.slice(0, 8).map((so: any) => (
              <tr key={so.id} className="border-b border-gray-800/50 hover:bg-gray-800/20">
                <td className="py-2 px-2 text-gray-200 font-mono">{so.so_no}</td>
                <td className="py-2 px-2 text-gray-300">{so.customer_name || '-'}</td>
                <td className="py-2 px-2">
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                    so.status === 'draft' ? 'bg-gray-700 text-gray-300' :
                    so.status === 'production' || so.status === 'confirmed' ? 'bg-yellow-500/20 text-yellow-400' :
                    so.status === 'shipped' ? 'bg-green-500/20 text-green-400' :
                    'bg-gray-700 text-gray-500'
                  }`}>{so.status}</span>
                </td>
                <td className="py-2 px-2 text-right text-gray-200 font-mono">
                  {so.total_amount ? `NT$${Intl.NumberFormat('zh-TW').format(so.total_amount)}` : '-'}
                </td>
                <td className="py-2 px-2 text-gray-400">{so.created_at?.slice(0, 10)}</td>
                <td className="py-2 px-2 text-center">
                  {so.status === 'draft' && (
                    <button onClick={() => doAction(so.id, 'confirm')} disabled={acting === so.id}
                      className="text-[10px] px-2 py-1 rounded bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 disabled:opacity-40">
                      {acting === so.id ? '⋯' : '確認'}
                    </button>
                  )}
                  {so.status === 'production' && (
                    <button onClick={() => doAction(so.id, 'ship')} disabled={acting === so.id}
                      className="text-[10px] px-2 py-1 rounded bg-green-500/20 text-green-400 hover:bg-green-500/30 disabled:opacity-40">
                      {acting === so.id ? '⋯' : '出貨'}
                    </button>
                  )}
                  {so.status === 'shipped' && (
                    <button onClick={() => doAction(so.id, 'deliver')} disabled={acting === so.id}
                      className="text-[10px] px-2 py-1 rounded bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 disabled:opacity-40">
                      {acting === so.id ? '⋯' : '完成'}
                    </button>
                  )}
                  {(so.status === 'delivered' || so.status === 'cancelled') && (
                    <span className="text-[10px] text-gray-500">—</span>
                  )}
                </td>
              </tr>
            ))}
            {orders.length === 0 && (
              <tr><td colSpan={6} className="text-center py-6 text-gray-500">暫無訂單</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── CRM Events (業務) ──────────────────────────────────────────
function CRMEvents() {
  const [customers, setCustomers] = useState<any[]>([])
  const [selectedCustomerId, setSelectedCustomerId] = useState<number | null>(null)
  const [events, setEvents] = useState<any[]>([])
  const [eventType, setEventType] = useState('note')
  const [eventDesc, setEventDesc] = useState('')
  const [showForm, setShowForm] = useState(false)

  useEffect(() => {
    listCustomers().then(d => {
      if (d?.customers) setCustomers(d.customers)
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (selectedCustomerId) {
      getCRMEvents(selectedCustomerId).then(d => {
        if (Array.isArray(d)) setEvents(d)
        else if (d?.events) setEvents(d.events)
      }).catch(() => {})
    } else {
      setEvents([])
    }
  }, [selectedCustomerId])

  const handleCreateEvent = async () => {
    if (!selectedCustomerId || !eventDesc.trim()) return
    try {
      await createCRMEvent({ customer_id: selectedCustomerId, event_type: eventType, description: eventDesc, created_by: 'user' })
      setEventDesc('')
      setShowForm(false)
      // Refresh
      const d = await getCRMEvents(selectedCustomerId)
      if (Array.isArray(d)) setEvents(d)
      else if (d?.events) setEvents(d.events)
    } catch (e) {
      console.error(e)
    }
  }

  const eventIcons: Record<string, string> = {
    call: '📞', visit: '🤝', note: '📝', email: '📧', meeting: '👥',
  }

  return (
    <div className="bg-[#0d111c] border border-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] text-gray-500 uppercase tracking-wider">📋 CRM 記錄</span>
        {selectedCustomerId && (
          <button onClick={() => setShowForm(!showForm)} className="text-[10px] text-cyan-400 cursor-pointer">
            {showForm ? '取消' : '+ 新增'}
          </button>
        )}
      </div>
      <select
        value={selectedCustomerId ?? ''}
        onChange={e => { setSelectedCustomerId(e.target.value ? Number(e.target.value) : null); setShowForm(false) }}
        className="w-full bg-[#0f1525] border border-gray-800 rounded px-2.5 py-1.5 text-xs text-gray-200 outline-none focus:border-cyan-500/50 mb-3"
      >
        <option value="">選擇客戶…</option>
        {customers.map((c: any) => (
          <option key={c.id} value={c.id}>{c.name} ({c.customer_no})</option>
        ))}
      </select>

      {showForm && (
        <div className="bg-[#0f1525] border border-gray-800 rounded-lg p-3 mb-3">
          <div className="flex gap-2 mb-2">
            {['call', 'visit', 'note', 'email', 'meeting'].map(t => (
              <button
                key={t}
                onClick={() => setEventType(t)}
                className={`text-sm px-2 py-1 rounded ${eventType === t ? 'bg-cyan-500/20 text-cyan-300' : 'bg-gray-800 text-gray-500'}`}
              >
                {eventIcons[t] || '📝'}
              </button>
            ))}
          </div>
          <textarea
            value={eventDesc}
            onChange={e => setEventDesc(e.target.value)}
            placeholder="輸入事件描述…"
            className="w-full bg-[#0d111c] border border-gray-800 rounded px-2 py-1.5 text-xs text-gray-200 outline-none focus:border-cyan-500/50 mb-2 resize-none"
            rows={2}
          />
          <button
            onClick={handleCreateEvent}
            className="bg-cyan-500 text-[#0a0e17] text-[10px] font-semibold px-3 py-1 rounded"
          >
            送出
          </button>
        </div>
      )}

      <div className="flex flex-col gap-1.5 max-h-40 overflow-y-auto">
        {events.length === 0 && (
          <div className="text-[10px] text-gray-500 text-center py-4">無記錄</div>
        )}
        {events.slice(0, 10).map((ev: any, i: number) => (
          <div key={i} className="flex gap-2 px-2 py-1.5 rounded-md text-xs hover:bg-gray-800/20 border-l-2 border-gray-700">
            <span className="text-sm shrink-0">{eventIcons[ev.event_type] || '📝'}</span>
            <div className="flex-1 min-w-0">
              <div className="text-gray-200">{ev.description || ev.event_type}</div>
              <div className="text-[9px] text-gray-500 mt-0.5">
                {ev.created_by ? `${ev.created_by} · ` : ''}
                {ev.created_at ? new Date(ev.created_at).toLocaleString('zh-TW') : ''}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── History Panel (業務) ───────────────────────────────────────
function HistoryPanel() {
  const [sessions, setSessions] = useState<any[]>([])
  const [selectedSession, setSelectedSession] = useState<any | null>(null)
  const [sessionMessages, setSessionMessages] = useState<any[]>([])

  useEffect(() => {
    listConversationSessions().then(d => {
      if (Array.isArray(d)) setSessions(d)
      else if (d?.sessions) setSessions(d.sessions)
    }).catch(() => {})
  }, [])

  const openSession = async (session: any) => {
    setSelectedSession(session)
    try {
      const d = await getConversation(session.session_id || session.id)
      if (d?.messages) setSessionMessages(d.messages)
      else if (Array.isArray(d)) setSessionMessages(d)
      else setSessionMessages([])
    } catch (e) {
      setSessionMessages([])
    }
  }

  return (
    <div className="bg-[#0d111c] border border-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] text-gray-500 uppercase tracking-wider">💬 對話歷史</span>
        {selectedSession && (
          <button onClick={() => { setSelectedSession(null); setSessionMessages([]) }} className="text-[10px] text-cyan-400 cursor-pointer">
            返回列表
          </button>
        )}
      </div>

      {!selectedSession ? (
        <div className="flex flex-col gap-1 max-h-60 overflow-y-auto">
          {sessions.length === 0 && (
            <div className="text-[10px] text-gray-500 text-center py-4">尚無對話</div>
          )}
          {sessions.slice(0, 10).map((s: any, i: number) => (
            <div
              key={s.session_id || s.id || i}
              onClick={() => openSession(s)}
              className="flex items-center gap-2 px-2 py-2 rounded-md text-xs hover:bg-gray-800/30 cursor-pointer border-l-2 border-gray-700"
            >
              <span className="text-sm">💬</span>
              <div className="flex-1 min-w-0">
                <div className="text-gray-200 truncate">{s.title || `Session ${s.session_id?.slice(0, 8) || ''}`}</div>
                <div className="text-[9px] text-gray-500">
                  {s.message_count !== undefined ? `${s.message_count} 則訊息` : ''}
                  {s.last_message_at ? ` · ${new Date(s.last_message_at).toLocaleDateString('zh-TW')}` : ''}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col gap-1.5 max-h-60 overflow-y-auto">
          {sessionMessages.length === 0 && (
            <div className="text-[10px] text-gray-500 text-center py-4">無訊息</div>
          )}
          {sessionMessages.map((msg: any, i: number) => (
            <div key={i} className={`flex gap-2 px-2 py-1.5 rounded-md text-xs ${
              msg.role === 'user' ? 'bg-cyan-500/5 border-l-2 border-cyan-500' : 'bg-[#0f1525] border-l-2 border-gray-700'
            }`}>
              <span className="text-sm shrink-0 mt-0.5">{msg.role === 'user' ? '👤' : '🤖'}</span>
              <div className="flex-1 min-w-0">
                <div className="text-gray-200">{msg.content}</div>
                {msg.created_at && (
                  <div className="text-[9px] text-gray-500 mt-0.5">{new Date(msg.created_at).toLocaleString('zh-TW')}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Price Trend ─────────────────────────────────────────────────
function PriceTrend() {
  return <div className="bg-[#0d111c] border border-gray-800 rounded-lg p-4">
    <span className="text-[10px] text-gray-500 uppercase tracking-wider">📈 採購趨勢</span>
    <div className="flex items-end gap-1 h-12 mt-3">
      {[40,55,35,70,50,80,95].map((h,i) => (
        <div key={i} className="flex-1 bg-cyan-400/30 rounded-t" style={{ height: `${h}%` }} />
      ))}
    </div>
    <div className="flex justify-between text-[8px] text-gray-500 mt-1">
      <span>4月</span><span>5月 ↑42%</span>
    </div>
  </div>
}

// ─── Inspection Queue ────────────────────────────────────────────
function InspectionQueue() {
  const [inspections, setInspections] = useState<any[]>([])
  useEffect(() => {
    listInspections().then(d => {
      if (d?.inspections) setInspections(d.inspections.filter((i: any) => i.status === 'pending'))
    }).catch(() => {})
  }, [])
  const tasks = inspections.slice(0, 5).map((i: any) => ({
    pri: i.po_id ? 'high' as const : 'med' as const,
    text: `${i.inspection_no}: ${i.lot_no || ''} ${i.quantity}${i.unit || 'pcs'}`,
    loc: `到料${i.created_at ? Math.floor((Date.now() - new Date(i.created_at).getTime())/60000) + 'min前' : ''}`,
    time: '',
  }))
  return <TaskPanel title="🔬 待檢驗批次" tasks={tasks} />
}

// ─── NC List ─────────────────────────────────────────────────────
function NCList() {
  const [ncs, setNcs] = useState<any[]>([])
  useEffect(() => {
    listNCs().then(d => { if (Array.isArray(d)) setNcs(d) }).catch(() => {})
  }, [])
  const statusColor = (s: string) => s === 'closed' ? 'green' : s === 'investigating' ? 'yellow' : 'red'
  const rows = ncs.slice(0, 5).map((nc: any) => [
    nc.nc_no,
    nc.part_no || nc.defect_code || '-',
    nc.description?.slice(0, 20) || '',
    <Tag color={statusColor(nc.status)}>{nc.status}</Tag>,
  ])
  return <SimpleTable title="📋 不合格(NC)處理" headers={['NC#', '品項', '缺陷', '狀態']} rows={rows} action="全部→" />
}

// ─── Defect Pareto ──────────────────────────────────────────────
function DefectPareto() {
  return <div className="bg-[#0d111c] border border-gray-800 rounded-lg p-4">
    <span className="text-[10px] text-gray-500 uppercase tracking-wider">📊 缺陷Pareto分析</span>
    <div className="flex items-end gap-1 h-20 mt-3">
      {[
        { h: 100, c: 'bg-red-500/40' }, { h: 75, c: 'bg-red-500/30' },
        { h: 55, c: 'bg-yellow-400/30' }, { h: 40, c: 'bg-yellow-400/30' },
        { h: 30, c: 'bg-cyan-400/25' }, { h: 20, c: 'bg-cyan-400/25' },
        { h: 12, c: 'bg-cyan-400/25' },
      ].map((b,i) => (
        <div key={i} className="flex-1 flex flex-col items-center justify-end h-full">
          <div className={`w-full rounded-t ${b.c}`} style={{ height: `${b.h}%`, minHeight: 3 }} />
        </div>
      ))}
    </div>
    <div className="flex justify-between text-[8px] text-gray-500 mt-1">
      <span>尺寸</span><span>刮傷</span><span>硬度</span><span>平面度</span><span>漏油</span><span>色差</span><span>其他</span>
    </div>
  </div>
}

// ─── CAPA Tracker ────────────────────────────────────────────────
function CAPATracker() {
  const [capas, setCapas] = useState<any[]>([])
  useEffect(() => {
    listCAPAs().then(d => { if (d?.capas) setCapas(d.capas) }).catch(() => {})
  }, [])
  const iconMap: Record<string, string> = { planned: '🟡', in_progress: '🟡', closed: '🟢', open: '🔴' }
  const items = capas.slice(0, 5).map((c: any) => ({
    icon: iconMap[c.status] || '🟡',
    text: `${c.action?.slice(0, 30) || 'CAPA'} — ${c.responsible || ''}`,
    sug: `原因: ${c.root_cause?.slice(0, 20) || '待調查'} | 狀態: ${c.status}`,
  }))
  return <InsightPanel title="🔄 CAPA 追蹤" items={items} />
}

// ─── Cash Flow ───────────────────────────────────────────────────
function CashFlow() {
  return <div className="bg-[#0d111c] border border-gray-800 rounded-lg p-4">
    <span className="text-[10px] text-gray-500 uppercase tracking-wider">💰 現金水位預測</span>
    <div className="relative h-20 mt-3">
      <svg className="w-full h-full" viewBox="0 0 100 60" preserveAspectRatio="none">
        <defs><linearGradient id="cfg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#22d3ee" stopOpacity="0.3"/><stop offset="100%" stopColor="#22d3ee" stopOpacity="0"/></linearGradient></defs>
        <path d="M0,15 L15,18 L30,12 L45,25 L55,35 L70,40 L85,28 L100,20" fill="none" stroke="#22d3ee" strokeWidth="2"/>
        <path d="M0,15 L15,18 L30,12 L45,25 L55,35 L70,40 L85,28 L100,20 L100,60 L0,60 Z" fill="url(#cfg)"/>
      </svg>
      <div className="absolute left-[30%] top-0 bg-red-500/20 text-red-300 text-[8px] px-1.5 py-0.5 rounded">應付NT$250K</div>
      <div className="absolute left-[60%] top-[-4px] bg-green-500/20 text-green-300 text-[8px] px-1.5 py-0.5 rounded">應收NT$180K</div>
      <div className="absolute left-[75%] top-2 bg-yellow-500/20 text-yellow-300 text-[8px] px-1.5 py-0.5 rounded">缺口NT$70K</div>
      <div className="flex justify-between text-[8px] text-gray-500 mt-1">
        <span>W1</span><span>W2</span><span>W3</span><span>W4</span>
      </div>
    </div>
  </div>
}

// ─── AR Aging ────────────────────────────────────────────────────
function ARAging() {
  const [arItems, setArItems] = useState<any[]>([])
  useEffect(() => {
    listAR().then(d => { if (d?.ar) setArItems(d.ar) }).catch(() => {})
    listAR('overdue').then(d => { if (d?.ar) setArItems(prev => [...prev, ...d.ar]) }).catch(() => {})
  }, [])
  const statusColor = (s: string) => s === 'paid' ? 'green' : s === 'overdue' ? 'red' : s === 'open' ? 'yellow' : 'cyan'
  const rows = arItems.slice(0, 5).map((a: any) => [
    a.customer_name,
    `NT${Intl.NumberFormat('zh-TW').format(a.amount)}`,
    a.due_date || '-',
    <Tag color={statusColor(a.status)}>{a.status}</Tag>,
  ])
  return <SimpleTable title="📅 應收帳款" headers={['客戶', '金額', '到期日', '狀態']} rows={rows} action="催收→" />
}

// ─── AP Aging ────────────────────────────────────────────────────
function APAging() {
  const [entries, setEntries] = useState<any[]>([])
  useEffect(() => {
    listJournalEntries().then(d => {
      if (d?.entries) {
        // Filter entries with AP-related description or source
        const ap = d.entries.filter((e: any) =>
          e.description?.includes('PO') || e.source_type === 'PO'
        ).slice(0, 4)
        setEntries(ap)
      }
    }).catch(() => {})
  }, [])
  const rows = entries.map((e: any) => {
    const credit = e.lines?.reduce((s: number, l: any) => s + (l.credit || 0), 0) || 0
    return [
      e.source_id || e.entry_no,
      `NT${Intl.NumberFormat('zh-TW').format(credit)}`,
      e.entry_date || '-',
      <Tag color={e.posted ? 'green' : 'yellow'}>{e.posted ? '已入帳' : '未過帳'}</Tag>,
    ]
  })
  return <SimpleTable title="📅 應付帳款" headers={['單號', '金額', '日期', '狀態']}
    rows={rows.length > 0 ? rows : [['暫無資料', '—', '—', <Tag color="green">正常</Tag>]]} />
}

// ─── Cost Variance ──────────────────────────────────────────────
function CostVariance() {
  const [orders, setOrders] = useState<any[]>([])
  useEffect(() => {
    listDispatchOrders().then(d => {
      if (Array.isArray(d)) setOrders(d.slice(0, 5))
    }).catch(() => {})
  }, [])
  const rows = orders.map((o: any) => {
    const totalSetup = o.operations?.reduce((s: number, op: any) => s + (op.setup_time_min || 0), 0) || 0
    const totalCycle = o.operations?.reduce((s: number, op: any) => s + (op.cycle_time_min || 0), 0) || 0
    const planned = totalSetup + totalCycle * (o.quantity || 1)
    const actual = o.operations?.reduce((s: number, op: any) => s + (op.actual_end && op.actual_start ?
      (new Date(op.actual_end).getTime() - new Date(op.actual_start).getTime()) / 60000 : 0), 0) || planned
    const varPct = planned > 0 ? Math.round((actual - planned) / planned * 100) : 0
    return [
      o.order_no,
      `${planned}min`,
      <span className={varPct > 5 ? 'text-yellow-400' : varPct > 15 ? 'text-red-400' : 'text-green-400'}>{Math.round(actual)}min</span>,
      <span className={varPct > 15 ? 'text-red-400' : varPct > 5 ? 'text-yellow-400' : 'text-green-400'}>
        {varPct > 0 ? `+${varPct}%` : `${varPct}%`}
      </span>,
    ]
  })
  return <SimpleTable title="📊 成本差異分析" headers={['工單', '標準', '實際', '差異']} rows={rows} />
}

// ─── GL Journal ──────────────────────────────────────────────────
function GLJournal() {
  const [entries, setEntries] = useState<any[]>([])
  useEffect(() => {
    listJournalEntries().then(d => {
      if (d?.entries) setEntries(d.entries.slice(0, 5))
    }).catch(() => {})
  }, [])
  const rows = entries.map((e: any) => {
    const total = e.lines?.reduce((s: number, l: any) => s + (l.debit || 0), 0) || 0
    return [
      e.entry_date, e.description?.slice(0, 16) || '',
      <span className="text-green-400">NT${Intl.NumberFormat('zh-TW').format(total)}</span>,
      <Tag color={e.posted ? 'green' : 'yellow'}>{e.posted ? '已過帳' : '草稿'}</Tag>,
    ]
  })
  return <SimpleTable title="📖 最近傳票" headers={['日期', '摘要', '金額', '狀態']} rows={rows} />
}

// ─── Month Close ─────────────────────────────────────────────────
function MonthClose() {
  const [periods, setPeriods] = useState<any[]>([])
  useEffect(() => {
    fetch('/api/accounting/periods').then(r => r.json()).then(d => {
      if (d?.periods) setPeriods(d.periods)
    }).catch(() => {})
  }, [])
  const isCurrentClosed = periods.some((p: any) => p.period === '2026-05' && p.is_closed)
  return <div className="bg-[#0d111c] border border-gray-800 rounded-lg p-4">
    <span className="text-[10px] text-gray-500 uppercase tracking-wider">📌 月底結帳進度</span>
    <div className="flex flex-col gap-2 mt-3">
      {[
        { label: '2026-05 月結', done: isCurrentClosed, pct: isCurrentClosed ? 100 : 15 },
        { label: '成本結轉', done: false, pct: 0 },
        { label: '發票匹配', done: false, pct: 0 },
      ].map(c => (
        <div key={c.label} className="flex items-center gap-2 text-xs">
          <span className={`w-3.5 h-3.5 rounded border flex items-center justify-center text-[8px] ${c.done ? 'bg-cyan-500 border-cyan-500 text-[#0a0e17]' : 'border-gray-600'}`}>
            {c.done ? '✓' : ''}
          </span>
          <span className="flex-1 text-gray-400">{c.label}</span>
          {c.done && <span className="text-green-400">{c.pct}%</span>}
        </div>
      ))}
      <div className="text-[10px] text-gray-500 mt-1">{periods.length > 0 ? `已結 ${periods.length} 個期間` : '2026-05 尚未月結'}</div>
    </div>
  </div>
}

// ─── Event Flow Widget ───────────────────────────────────────────
function EventFlowWidget({ events }: { events: any[] }) {
  const [liveEvents, setLiveEvents] = useState<any[]>(events)
  useEffect(() => {
    if (events.length > 0) {
      setLiveEvents(events)
    } else {
      // Seed some events if empty
      Promise.allSettled([
        fetch('/api/events/simulate/material.received', { method: 'POST' }).then(r => r.json()),
        fetch('/api/events/simulate/material.issued', { method: 'POST' }).then(r => r.json()),
        fetch('/api/events/simulate/purchase_order.created', { method: 'POST' }).then(r => r.json()),
      ]).then(() => {
        getActivityFeed(8).then(d => {
          if (d?.events) setLiveEvents(d.events)
        })
      }).catch(() => {})
    }
  }, [events])

  const actorStyle: Record<string, string> = {
    purchasing: 'bg-cyan-500/10 text-cyan-300',
    production: 'bg-green-500/10 text-green-300',
    warehouse: 'bg-yellow-500/10 text-yellow-300',
    quality: 'bg-orange-500/10 text-orange-300',
    accounting: 'bg-purple-500/10 text-purple-300',
    director: 'bg-pink-500/10 text-pink-300',
    sales: 'bg-blue-500/10 text-blue-300',
  }

  return (
    <div className="bg-[#0d111c] border border-cyan-500/15 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] text-cyan-400 uppercase tracking-wider">⚡ 跨角色事件引擎 — 即時活動</span>
      </div>
      <div className="flex flex-col gap-1.5">
        {liveEvents.slice(0, 6).map((ev: any, i: number) => {
          const role = ev.actor_role || 'system'
          const label = ev.actor_label || role
          const style = actorStyle[role] || 'bg-gray-500/10 text-gray-400'
          return (
            <div key={i} className="flex items-start gap-2.5 px-2 py-1.5 rounded-md text-xs hover:bg-gray-800/20">
              <span className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${
                ev.severity === 'critical' ? 'bg-red-500' :
                ev.severity === 'warning' ? 'bg-yellow-500' : 'bg-cyan-500'
              }`} />
              <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium shrink-0 ${style}`}>
                {label}
              </span>
              <div className="flex-1 min-w-0">
                <strong className="text-gray-200">{ev.event_type || ev.aggregate_id || ev.summary?.split('—')[0]}</strong>
                {' '}{ev.summary || ''}
              </div>
              {ev.targets && <span className="text-[9px] text-gray-500 hidden md:block shrink-0">→ 通知：{ev.targets}</span>}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ─── Shared UI Components ────────────────────────────────────────

function Tag({ color, children }: { color: string; children: React.ReactNode }) {
  const colors: Record<string, string> = {
    red: 'bg-red-500/15 text-red-300',
    yellow: 'bg-yellow-500/15 text-yellow-300',
    green: 'bg-green-500/15 text-green-300',
    cyan: 'bg-cyan-500/15 text-cyan-300',
  }
  return <span className={`px-1.5 py-0.5 rounded text-[9px] font-medium ${colors[color] || colors.green}`}>{children}</span>
}

function SimpleTable({ title, headers, rows, action }: { title: string; headers: string[]; rows: React.ReactNode[][]; action?: string }) {
  return (
    <div className="bg-[#0d111c] border border-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] text-gray-500 uppercase tracking-wider">{title}</span>
        {action && <span className="text-[10px] text-cyan-400 cursor-pointer">{action}</span>}
      </div>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-[9px] text-gray-500 uppercase tracking-wider">
            {headers.map(h => <th key={h} className="text-left pb-2 pr-2 font-medium">{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t border-gray-800/50 hover:bg-cyan-500/5">
              {row.map((cell, j) => <td key={j} className="py-2 pr-2 text-gray-300">{cell}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function TaskPanel({ title, tasks }: { title: string; tasks: { pri: string; text: string; loc: string; time: string }[] }) {
  const priColors: Record<string, string> = { high: 'bg-red-500/15 text-red-300', med: 'bg-yellow-500/15 text-yellow-300', low: 'bg-green-500/15 text-green-300' }
  return (
    <div className="bg-[#0d111c] border border-gray-800 rounded-lg p-4">
      <span className="text-[10px] text-gray-500 uppercase tracking-wider">{title}</span>
      <div className="flex flex-col gap-1.5 mt-3">
        {tasks.map((t, i) => (
          <div key={i} className="flex items-center gap-2 bg-[#0f1525] p-2 rounded-lg border border-gray-800/50">
            <div className="w-3.5 h-3.5 rounded border border-gray-600 shrink-0 cursor-pointer hover:border-cyan-400" />
            <span className={`text-[8px] px-1 py-0.5 rounded font-medium ${priColors[t.pri]}`}>{t.pri === 'high' ? '急' : t.pri === 'med' ? '中' : '低'}</span>
            <span className="text-xs flex-1">{t.text}</span>
            {t.loc && <span className="text-[9px] text-gray-500 hidden md:inline">{t.loc}</span>}
            {t.time && <span className="text-[9px] text-gray-600">{t.time}</span>}
          </div>
        ))}
      </div>
    </div>
  )
}

function InsightPanel({ title, items }: { title: string; items: { icon: string; text: string; sug: string }[] }) {
  return (
    <div className="bg-[#0d111c] border border-gray-800 rounded-lg p-4">
      <span className="text-[10px] text-gray-500 uppercase tracking-wider">{title}</span>
      <div className="flex flex-col gap-1.5 mt-3">
        {items.map((item, i) => (
          <div key={i} className={`flex gap-2 px-2.5 py-2 rounded-md text-xs cursor-pointer hover:bg-gray-800/30 ${
            item.icon === '🔴' ? 'bg-red-500/3 border-l-2 border-red-500' :
            item.icon === '🟡' ? 'bg-yellow-500/3 border-l-2 border-yellow-500' :
            'bg-green-500/3 border-l-2 border-green-500'
          }`}>
            <span>{item.icon}</span>
            <div>
              <strong className="text-gray-200">{item.text}</strong>
              <div className="text-[10px] text-gray-500 mt-0.5">💡 {item.sug}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
