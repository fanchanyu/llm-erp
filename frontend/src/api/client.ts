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

// ─── Events / Notifications ─────────────────────────────────────

export async function getNotifications(role?: string) {
  const q = role ? `?role=${role}` : ''
  const res = await fetch(`/api/events/notifications${q}`)
  return res.json()
}

export async function getUnreadCount(role?: string) {
  const q = role ? `?role=${role}` : ''
  const res = await fetch(`/api/events/notifications/unread${q}`)
  return res.json()
}

export async function getActivityFeed(limit = 10) {
  const res = await fetch(`/api/events/activity?limit=${limit}`)
  return res.json()
}

export async function checkConstraints(operation: string, params: any, actorRole = '') {
  const res = await fetch('/api/events/check', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ operation, params, actor_role: actorRole }),
  })
  return res.json()
}

export async function simulateEvent(eventType: string) {
  const res = await fetch(`/api/events/simulate/${eventType}`, { method: 'POST' })
  return res.json()
}

// ─── Dispatch (生產派工) ────────────────────────────────────────

export async function listWorkCenters(status?: string) {
  const q = status ? `?status=${status}` : ''
  const res = await fetch(`${API_BASE}/dispatch/work-centers${q}`)
  return res.json()
}

export async function listDispatchOrders(status?: string) {
  const q = status ? `?status=${status}` : ''
  const res = await fetch(`${API_BASE}/dispatch/orders${q}`)
  return res.json()
}

// ─── Quality (品質) ─────────────────────────────────────────────

export async function listInspections() {
  const res = await fetch(`${API_BASE}/quality/inspections`)
  return res.json()
}

export async function listNCs() {
  const res = await fetch(`${API_BASE}/quality/ncs`)
  return res.json()
}

export async function listCAPAs() {
  const res = await fetch(`${API_BASE}/quality/capas`)
  return res.json()
}

// ─── Accounting (會計) ───────────────────────────────────────────

export async function listAccounts(type?: string) {
  const q = type ? `?account_type=${type}` : ''
  const res = await fetch(`${API_BASE}/accounting/accounts${q}`)
  return res.json()
}

export async function listJournalEntries(period?: string) {
  const q = period ? `?period=${period}` : ''
  const res = await fetch(`${API_BASE}/accounting/entries${q}`)
  return res.json()
}

export async function listAR(status?: string) {
  const q = status ? `?status=${status}` : ''
  const res = await fetch(`${API_BASE}/accounting/ar${q}`)
  return res.json()
}

export async function getAROverdueSummary() {
  const res = await fetch(`${API_BASE}/accounting/ar/overdue-summary`)
  return res.json()
}

export async function listSuppliers(search?: string) {
  const q = search ? `?search=${encodeURIComponent(search)}` : ''
  const res = await fetch(`${API_BASE}/purchase/suppliers${q}`)
  return res.json()
}

// ─── Sales / CRM (業務) ──────────────────────────────────────────

export async function listCustomers(search?: string) {
  const q = search ? `?search=${encodeURIComponent(search)}` : ''
  const res = await fetch(`${API_BASE}/customers${q}`)
  return res.json()
}

export async function createCustomer(data: any) {
  const res = await fetch(`${API_BASE}/customers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function getCustomer(id: number) {
  const res = await fetch(`${API_BASE}/customers/${id}`)
  return res.json()
}

export async function listSalesOrders(status?: string) {
  const q = status ? `?status=${status}` : ''
  const res = await fetch(`${API_BASE}/so${q}`)
  return res.json()
}

export async function createSalesOrder(data: any) {
  const res = await fetch(`${API_BASE}/so`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function getCRMEvents(customerId: number) {
  const res = await fetch(`${API_BASE}/crm/events/${customerId}`)
  return res.json()
}

export async function createCRMEvent(data: any) {
  const res = await fetch(`${API_BASE}/crm/events`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function listConversationSessions() {
  const res = await fetch(`${API_BASE}/conversations/sessions`)
  return res.json()
}

export async function getConversation(sessionId: string) {
  const res = await fetch(`${API_BASE}/conversations/${sessionId}`)
  return res.json()
}

export async function getConversationsByCustomer(customerId: number) {
  const res = await fetch(`${API_BASE}/conversations/by-customer/${customerId}`)
  return res.json()
}
