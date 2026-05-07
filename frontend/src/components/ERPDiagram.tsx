import { useState, useEffect } from 'react'
import { useTranslation } from '../i18n'

interface NodeDef {
  id: string
  labelKey: string
  icon: string
  x: number
  y: number
  color: string
  statusKey: string
  stage: string
  prompts: { zh: string; en: string }[]
}

const STAGE_COLORS: Record<string, string> = {
  source: '#f59e0b',
  plan: '#3b82f6',
  store: '#10b981',
  make: '#ef4444',
  check: '#f43f5e',
  finance: '#fbbf24',
}

const STAGE_LABELS: Record<string, { zh: string; en: string }> = {
  source: { zh: '📥 採購段', en: '📥 Source' },
  plan: { zh: '📋 計劃段', en: '📋 Plan' },
  store: { zh: '📦 倉儲段', en: '📦 Store' },
  make: { zh: '⚙️ 製造段', en: '⚙️ Make' },
  check: { zh: '✅ 檢驗段', en: '✅ Check' },
  finance: { zh: '💰 財務段', en: '💰 Finance' },
}

const NODES: NodeDef[] = [
  // Row 1: Source → Plan → Finance (top)
  {
    id: 'suppliers', labelKey: 'node.suppliers', icon: '🏭',
    x: 80, y: 80, color: STAGE_COLORS.source, statusKey: 'status.suppliers',
    stage: 'source',
    prompts: [
      { zh: '列出所有供應商', en: 'List all suppliers' },
      { zh: '新增供應商「永達五金」', en: 'Add a new supplier' },
      { zh: '大明螺絲的聯絡資訊', en: "Show DaMing Screw's info" },
    ]
  },
  {
    id: 'purchase', labelKey: 'node.purchase', icon: '📋',
    x: 300, y: 80, color: STAGE_COLORS.plan, statusKey: 'status.one_po',
    stage: 'plan',
    prompts: [
      { zh: '查詢所有採購單', en: 'Show all purchase orders' },
      { zh: '向大明螺絲買500顆M6x20', en: 'Create PO for 500 M6x20' },
      { zh: '有哪些未完成的採購單？', en: 'Any pending purchase orders?' },
    ]
  },
  {
    id: 'accounting', labelKey: 'node.accounting', icon: '💰',
    x: 510, y: 80, color: STAGE_COLORS.finance, statusKey: 'status.one_entry',
    stage: 'finance',
    prompts: [
      { zh: '查看最近傳票', en: 'Show recent journal entries' },
      { zh: '應收帳款有哪些？', en: 'List accounts receivable' },
      { zh: '月底結帳進度', en: 'Month-end closing status' },
    ]
  },

  // Row 2: Inventory → BOM (middle)
  {
    id: 'inventory', labelKey: 'node.inventory', icon: '📦',
    x: 80, y: 300, color: STAGE_COLORS.store, statusKey: 'status.twelve_items',
    stage: 'store',
    prompts: [
      { zh: 'M6x20 螺絲庫存', en: 'How many M6x20 in stock?' },
      { zh: '哪些料件低於安全水位？', en: 'Items below safety stock?' },
      { zh: '庫存量前10大物料', en: 'Top 10 items by stock' },
    ]
  },
  {
    id: 'bom', labelKey: 'node.bom', icon: '📐',
    x: 300, y: 300, color: STAGE_COLORS.plan, statusKey: 'status.two_boms',
    stage: 'plan',
    prompts: [
      { zh: '查詢 ASM-001 的 BOM', en: "Show ASM-001's BOM" },
      { zh: 'CNC-001 做5台，展開用料', en: 'Explode BOM for 5x CNC-001' },
      { zh: '做3台 CNC-001 料夠嗎？', en: 'Check shortage for 3x CNC-001' },
    ]
  },

  // Row 3: Dispatch → Quality (bottom)
  {
    id: 'dispatch', labelKey: 'node.dispatch', icon: '⚙️',
    x: 80, y: 500, color: STAGE_COLORS.make, statusKey: 'status.pending_dispatch',
    stage: 'make',
    prompts: [
      { zh: '幫我派工 WO-20260506-001', en: 'Dispatch order WO-001' },
      { zh: '查看目前排程', en: 'Show current schedule' },
      { zh: 'CNC-01故障，往後推2小時', en: 'CNC-01 down, right-shift 2h' },
    ]
  },
  {
    id: 'quality', labelKey: 'node.quality', icon: '✅',
    x: 300, y: 500, color: STAGE_COLORS.check, statusKey: 'status.pending_nc',
    stage: 'check',
    prompts: [
      { zh: '待檢驗批次有哪些？', en: 'Show pending inspections' },
      { zh: '開啟不合格單 NC', en: 'Create non-conformance record' },
      { zh: '缺陷分析 Pareto', en: 'Defect Pareto analysis' },
    ]
  },
]

// Flow connections with direction indicators
const FLOWS = [
  // Material flow (left to right)
  { from: 'suppliers', to: 'purchase', label: '報價→下單' },
  { from: 'purchase', to: 'inventory', label: '進貨入庫' },
  { from: 'inventory', to: 'dispatch', label: '投料生產' },
  { from: 'bom', to: 'dispatch', label: 'BOM指導' },
  { from: 'dispatch', to: 'quality', label: '完工送檢' },

  // Financial flow (top-right crosscut)
  { from: 'purchase', to: 'accounting', label: 'AP入帳' },
  { from: 'inventory', to: 'accounting', label: '庫存評價' },
  { from: 'dispatch', to: 'accounting', label: '成本結轉' },
]

interface Props {
  onPromptSelect: (prompt: string) => void
}

export function ERPDiagram({ onPromptSelect }: Props) {
  const [selected, setSelected] = useState<string | null>(null)
  const [hovered, setHovered] = useState<string | null>(null)
  const [flowAnim, setFlowAnim] = useState<Record<string, boolean>>({})
  const { t, lang } = useTranslation()

  const selNode = selected ? NODES.find(n => n.id === selected) : null

  // Animate flows one by one
  useEffect(() => {
    const timer = setInterval(() => {
      setFlowAnim(prev => {
        const keys = FLOWS.map(f => `${f.from}-${f.to}`)
        const next = { ...prev }
        // Find first not-animated, toggle it
        const firstNotDone = keys.find(k => !next[k])
        if (firstNotDone) {
          next[firstNotDone] = true
        } else {
          // Reset after all done
          keys.forEach(k => { next[k] = false })
        }
        return next
      })
    }, 1200)
    return () => clearInterval(timer)
  }, [])

  return (
    <div className="flex gap-4 h-[calc(100vh-8rem)]">
      {/* Diagram */}
      <div className="flex-1 bg-gray-900 rounded-2xl border border-gray-800 p-4 relative overflow-hidden">
        {/* Header */}
        <div className="absolute top-4 left-6 z-10">
          <h2 className="text-white font-bold text-lg">{t('diagram.title')}</h2>
          <p className="text-gray-500 text-xs">{t('diagram.subtitle')}</p>
        </div>

        {/* Stage labels */}
        <div className="absolute top-3 right-4 z-10 flex gap-3">
          {Object.entries(STAGE_LABELS).map(([key, lbl]) => (
            <span key={key} className="text-[9px] px-2 py-0.5 rounded"
              style={{ background: `${STAGE_COLORS[key]}15`, color: STAGE_COLORS[key], border: `1px solid ${STAGE_COLORS[key]}30` }}>
              {lang === 'zh' ? lbl.zh : lbl.en}
            </span>
          ))}
        </div>

        {/* Value stream direction arrow */}
        <div className="absolute bottom-20 left-1/2 -translate-x-1/2 z-10 flex items-center gap-2 text-[9px] text-gray-600">
          <span>料流方向</span>
          <span className="text-green-400">🏭 ──▶ 📋 ──▶ 📦 ──▶ ⚙️ ──▶ ✅</span>
          <span className="text-amber-400 ml-4">💰 金流橫切</span>
        </div>

        <svg viewBox="0 0 580 620" className="w-full h-full">
          {FLOWS.map(({ from, to, label }) => {
            const f = NODES.find(n => n.id === from)!
            const t2 = NODES.find(n => n.id === to)!
            const isActive = selected === from || selected === to || hovered === from || hovered === to
            const isVertical = Math.abs(f.x - t2.x) < 50
            const isMaterial = ['suppliers','purchase','inventory','dispatch','quality'].includes(from) &&
                             ['suppliers','purchase','inventory','dispatch','quality'].includes(to)
            const flowKey = `${from}-${to}`
            const animating = flowAnim[flowKey]

            // Arrow points
            const x1 = f.x, y1 = f.y + 28
            const x2 = isVertical ? f.x : (from === 'bom' ? f.x + 10 : (from === 'inventory' && to === 'accounting' ? f.x + 85 : t2.x))
            const y2 = isVertical ? t2.y - 10 : t2.y + 28

            return (
              <g key={flowKey}>
                {/* Flow line */}
                <line x1={x1} y1={y1} x2={x2} y2={y2}
                  stroke={isActive || animating ? (isMaterial ? '#34d399' : '#fbbf24') : '#374151'}
                  strokeWidth={isActive || animating ? 2.5 : 1.5}
                  strokeDasharray={isMaterial ? (animating ? 'none' : '4,3') : (animating ? 'none' : '2,4')}
                />
                {/* Arrowhead */}
                <polygon
                  points={`${x2 - 5},${y2 - 14} ${x2 + 5},${y2 - 14} ${x2},${y2 - 2}`}
                  fill={isActive || animating ? (isMaterial ? '#34d399' : '#fbbf24') : '#374151'}
                />
                {/* Flow label */}
                {isActive && (
                  <text x={(x1 + x2) / 2} y={(y1 + y2) / 2 - 6}
                    textAnchor="middle" fill={isMaterial ? '#34d399' : '#fbbf24'}
                    fontSize={7} fontWeight="600"
                    className="select-none"
                  >
                    {label}
                  </text>
                )}
                {/* Flowing dot */}
                {animating && (
                  <circle r="3" fill={isMaterial ? '#34d399' : '#fbbf24'} opacity="0.8">
                    <animateMotion dur="1.2s" repeatCount="1"
                      path={`M${x1},${y1} L${x2},${y2}`}
                    />
                  </circle>
                )}
              </g>
            )
          })}

          {NODES.map(node => {
            const isSel = selected === node.id
            const isHov = hovered === node.id
            return (
              <g
                key={node.id}
                onClick={() => setSelected(isSel ? null : node.id)}
                onMouseEnter={() => setHovered(node.id)}
                onMouseLeave={() => setHovered(null)}
                style={{ cursor: 'pointer' }}
              >
                {/* Stage badge */}
                <rect x={node.x - 82} y={node.y - 16} width={42} height={14} rx={3}
                  fill={node.color} opacity="0.15"
                />
                <text x={node.x - 61} y={node.y - 6} textAnchor="middle" fill={node.color} fontSize={7} fontWeight="600">
                  {lang === 'zh' ? STAGE_LABELS[node.stage]?.zh.slice(2) : STAGE_LABELS[node.stage]?.en.slice(2)}
                </text>

                {/* Glow when selected */}
                {isSel && (
                  <rect x={node.x - 88} y={node.y - 14} width={176} height={56} rx={12}
                    fill="none" stroke={node.color} strokeWidth={2} opacity={0.5} filter="url(#glow)"
                  />
                )}
                {/* Node body */}
                <rect x={node.x - 85} y={node.y - 12} width={170} height={52} rx={10}
                  fill={isSel ? '#1e293b' : isHov ? '#1e293b' : '#111827'}
                  stroke={isSel ? node.color : isHov ? '#4b5563' : '#374151'}
                  strokeWidth={isSel ? 2 : 1.5}
                  className="transition-all duration-200"
                />
                {/* Status badge */}
                <rect x={node.x + 75} y={node.y - 4} width={60} height={18} rx={4} fill={node.color} opacity="0.15"/>
                <text x={node.x + 105} y={node.y + 8} textAnchor="middle" fill={node.color} fontSize={9} fontWeight="600">
                  {t(node.statusKey)}
                </text>
                {/* Icon + Label */}
                <text x={node.x - 70} y={node.y + 16} fontSize={18}>{node.icon}</text>
                <text x={node.x - 40} y={node.y + 8} fill="#f9fafb" fontSize={13} fontWeight="700">
                  {t(node.labelKey)}
                </text>
              </g>
            )
          })}

          <defs>
            <filter id="glow">
              <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
              <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
            </filter>
          </defs>
        </svg>

        {!selected && (
          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-gray-800/80 text-gray-400 text-xs px-4 py-2 rounded-full border border-gray-700">
            {t('diagram.hint')}
          </div>
        )}
      </div>

      {/* Prompt Panel */}
      <div className={`w-80 shrink-0 transition-all duration-300 ${selected ? 'opacity-100' : 'opacity-40 pointer-events-none'}`}>
        <div className="bg-gray-900 rounded-2xl border border-gray-800 h-full p-5 overflow-y-auto">
          {selNode ? (
            <>
              <div className="flex items-center gap-3 mb-4">
                <span className="text-2xl">{selNode.icon}</span>
                <div>
                  <h3 className="text-white font-bold">{t(selNode.labelKey)}</h3>
                  <p className="text-gray-500 text-xs">{t(selNode.statusKey)}</p>
                </div>
              </div>
              {/* Flow context */}
              <div className="mb-3 px-3 py-2 rounded-lg text-[10px]" 
                style={{ background: `${selNode.color}10`, border: `1px solid ${selNode.color}20`, color: selNode.color }}>
                {lang === 'zh' 
                  ? `📍 ${STAGE_LABELS[selNode.stage]?.zh} — ${selNode.stage === 'source' ? '採購源頭管理' : selNode.stage === 'plan' ? '計劃與定義' : selNode.stage === 'store' ? '物料儲存與調撥' : selNode.stage === 'make' ? '生產執行' : selNode.stage === 'check' ? '品質把關' : '財務監控'}`
                  : `📍 ${STAGE_LABELS[selNode.stage]?.en} stage`
                }
              </div>
              <div className="mb-4 p-3 bg-gray-800 rounded-xl">
                <p className="text-gray-400 text-xs mb-1">{t('node.you_can_say')}</p>
                {selNode.prompts.map((p, i) => (
                  <button key={i}
                    onClick={() => onPromptSelect(lang === 'zh' ? p.zh : p.en)}
                    className="block w-full text-left text-sm text-blue-400 hover:text-blue-300 bg-gray-800/50 hover:bg-gray-700/50 rounded-lg px-3 py-2 mb-1.5 transition-all border border-gray-700/50 hover:border-blue-600/50"
                  >
                    💬 {lang === 'zh' ? p.zh : p.en}
                  </button>
                ))}
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-600 text-sm text-center px-4 leading-relaxed">
              {t('diagram.empty')}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
