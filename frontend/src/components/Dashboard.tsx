import { useEffect, useState } from 'react'
import { healthCheck, listParts, listOrders, listProducts } from '../api/client'

export function Dashboard() {
  const [health, setHealth] = useState<string>('檢查中...')
  const [partCount, setPartCount] = useState(0)
  const [orderCount, setOrderCount] = useState(0)
  const [productCount, setProductCount] = useState(0)

  useEffect(() => {
    healthCheck().then(r => setHealth(r.status || 'ok')).catch(() => setHealth('離線'))
    listParts().then(r => setPartCount(r.total || 0)).catch(() => {})
    listOrders().then(r => setOrderCount(r.total || 0)).catch(() => {})
    listProducts().then(r => setProductCount(r.total || 0)).catch(() => {})
  }, [])

  const cards = [
    { label: '系統狀態', value: health, color: health === 'ok' ? 'text-green-600' : 'text-red-600', bg: 'bg-green-50' },
    { label: '料號總數', value: partCount.toString(), color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: '採購單', value: orderCount.toString(), color: 'text-purple-600', bg: 'bg-purple-50' },
    { label: '產品數', value: productCount.toString(), color: 'text-orange-600', bg: 'bg-orange-50' },
  ]

  return (
    <div>
      <h2 className="text-lg font-bold text-gray-900 mb-4">📊 系統儀表板</h2>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {cards.map((card, i) => (
          <div key={i} className={`${card.bg} rounded-xl p-4 border border-gray-100`}>
            <div className="text-xs text-gray-500 mb-1">{card.label}</div>
            <div className={`text-2xl font-bold ${card.color}`}>{card.value}</div>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="font-bold text-gray-900 mb-3">🚀 快速開始</h3>
        <div className="space-y-2 text-sm text-gray-600">
          <p>1️⃣ 前往 <strong>💬 對話</strong> 頁面，用自然語言操作 ERP</p>
          <p>2️⃣ 範例查詢：</p>
          <ul className="list-disc list-inside pl-4 space-y-1 text-gray-500">
            <li><code className="text-xs bg-gray-100 px-1 rounded">庫存還有多少 M6 螺絲？</code></li>
            <li><code className="text-xs bg-gray-100 px-1 rounded">幫我向大明螺絲買 500 顆 M6，單價 0.5 元</code></li>
            <li><code className="text-xs bg-gray-100 px-1 rounded">A 產品要做 100 台，料夠不夠？</code></li>
          </ul>
        </div>
      </div>
    </div>
  )
}
