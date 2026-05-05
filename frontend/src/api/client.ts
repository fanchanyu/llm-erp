const API_BASE = '/api'

export async function chat(message: string, sessionId?: string) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId }),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function queryStock(params?: { part_no?: string; name?: string; category?: string }) {
  const q = new URLSearchParams()
  if (params?.part_no) q.set('part_no', params.part_no)
  if (params?.name) q.set('name', params.name)
  if (params?.category) q.set('category', params.category)
  const res = await fetch(`${API_BASE}/inventory/stock?${q}`)
  return res.json()
}

export async function listParts(search?: string) {
  const q = search ? `?search=${encodeURIComponent(search)}` : ''
  const res = await fetch(`${API_BASE}/inventory/parts${q}`)
  return res.json()
}

export async function listOrders(status?: string) {
  const q = status ? `?status=${status}` : ''
  const res = await fetch(`${API_BASE}/purchase/orders${q}`)
  return res.json()
}

export async function listProducts(search?: string) {
  const q = search ? `?search=${encodeURIComponent(search)}` : ''
  const res = await fetch(`${API_BASE}/bom/products${q}`)
  return res.json()
}

export async function healthCheck() {
  const res = await fetch('/health')
  return res.json()
}
