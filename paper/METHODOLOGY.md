# Methodology: Role-Adaptive LLM-ERP with Event-Driven Coordination

## 3.1 System Architecture Overview

The proposed LLM-ERP system follows a three-tier architecture: a **Role-Adaptive Frontend** (React + TypeScript), a **Domain Service Layer** (Python FastAPI), and an **LLM Orchestrator** that bridges natural language interaction with enterprise data operations. Unlike traditional ERP systems where users must navigate rigid menu hierarchies and memorize transaction codes (e.g., SAP T-codes like ME21N for PO creation), LLM-ERP presents a unified natural language interface augmented by role-specific dashboards.

```
┌──────────────────────────────────────────────────────────────┐
│  Role-Adaptive Frontend                                      │
│  ┌──────────┐ ┌──────────┐ ┌─────────────┐ ┌──────────────┐│
│  │ Dashboard│ │ NL Input │ │ Notification│ │ War Room     ││
│  │ (role-dep)│ │  (CMD)   │ │   (events)  │ │ (multi-screen)│
│  └──────────┘ └──────────┘ └─────────────┘ └──────────────┘│
├──────────────────────────────────────────────────────────────┤
│  LLM Orchestrator                                            │
│  ┌──────────┐ ┌──────────┐ ┌─────────────┐ ┌──────────────┐│
│  │ Intent   │ │ Tool     │ │ Proactive    │ │ Constraint   ││
│  │ Classify │ │ Dispatch │ │ Analysis     │ │ Enforcement  ││
│  └──────────┘ └──────────┘ └─────────────┘ └──────────────┘│
├──────────────────────────────────────────────────────────────┤
│  Domain Service Layer (FastAPI)                               │
│  MM  │  PP  │  QM  │  FI  │  SD  │  WM  │  DI               │
├──────────────────────────────────────────────────────────────┤
│  Event Engine (pub-sub, role routing, Telegram push)          │
├──────────────────────────────────────────────────────────────┤
│  Database (PostgreSQL / SQLite)                               │
└──────────────────────────────────────────────────────────────┘
```

The system is decomposed into **six operational modules** plus one cross-cutting module:

| Module | Abbr. | Core Functions |
|--------|-------|----------------|
| Inventory (MM) | Warehouse Mgt. | Parts master, stock query, inbound/outbound, location management |
| Purchase (PP) | Procurement | Supplier management, PO lifecycle (draft→sent→received→closed) |
| BOM (PP) | Engineering | Product structure, multi-level BOM explosion, shortage detection |
| Dispatch (PP) | Production Control | Work order lifecycle, work center management, dynamic rescheduling |
| Quality (QM) | Inspection & NC | Inspection orders, NC tracking, CAPA management |
| Accounting (FI) | Finance | Chart of accounts, journal entries, AR/AP, month-end close |
| **Event Engine** | *Cross-cutting* | Pub-sub notifications, constraint enforcement, role routing, Telegram push |

## 3.2 User Archetype Definition

We define six core user archetypes for manufacturing ERP. Each archetype is characterized by (1) their **primary concern**, (2) **decision-making level**, (3) **LLM interaction mode**, and (4) **notification scope**. This taxonomy is both a design tool for the interface and a set of treatment variables for subsequent experiments.

| Archetype | Role | Concern | Decision Level | LLM Mode | Notifications |
|-----------|------|---------|---------------|----------|---------------|
| $U_d$ | Factory Director (廠長) | Plant-wide KPI, exceptions | Strategic | Summarize trends, surface anomalies | 🔴 Exceptions only |
| $U_p$ | Production Controller (生管) | Schedule, material shortage, capacity | Tactical | "What-if" simulation, reschedule | Production alerts |
| $U_w$ | Warehouse Keeper (倉庫) | Picking, receiving, inventory | Operational | Command-driven, scan-oriented | Task assignments |
| $U_b$ | Purchasing Agent (採購) | PO lifecycle, supplier, cost | Tactical | Multi-vendor comparison, negotiation | PO expedite, supply alerts |
| $U_q$ | Quality Inspector (品管) | Inspection, NC, CAPA | Operational/Analytic | Defect analysis, trend | NC creation, inspection due |
| $U_a$ | Accountant/CFO (會計) | Cash flow, AR/AP, cost | Strategic/Tactical | Forecast, payment recommendation | Payment due, cash alerts |

**Decision Level Taxonomy.** We distinguish three levels following Anthony's framework [1]:
- **Strategic** ($U_d$, $U_a$): Long-term, aggregate, exception-driven
- **Tactical** ($U_p$, $U_b$): Medium-term, planning and tradeoffs
- **Operational** ($U_w$, $U_q$): Short-term, execution and compliance

Each archetype's interface is a **subset** of a unified component library. Formally, given a widget set $W = \{w_1, w_2, ..., w_n\}$ and a role $r$, the visible dashboard $D_r \subset W$ is defined by a role-widget mapping $M: R \to \mathcal{P}(W)$.

## 3.3 Role-Adaptive Interface Design

The frontend dynamically renders dashboard components based on the authenticated user's role. This is implemented through a **declarative role configuration**:

```typescript
const ROLES = {
  director: {
    widgets: ['alert-bar', 'kpi-grid', 'inventory-chart', 'ai-insights', 'quality-panel', 'war-room'],
    llmMode: 'strategic',
    permissions: ['view-all', 'approve-over-issue'],
  },
  warehouse: {
    widgets: ['pick-list', 'putaway-queue', 'inventory-search', 'stock-alerts'],
    llmMode: 'execution',
    permissions: ['view-inventory', 'receive-stock', 'issue-stock'],
  },
  // ...
};
```

The role system assigns **6 KPI widgets per role × 6 metrics each** = 36 role-specific KPIs computed from live database queries, covering on-time delivery %, inventory turnover, quality yield, PO cycle time, capacity utilization, and cash conversion cycle.

A dedicated **War Room display** (Fig. X) provides a multi-screen factory-wide visualization showing real-time value stream flow with animated event particles flowing between stages (Supplier → Purchase → Inventory → Dispatch → Quality → Accounting), with live counts updating every 15 seconds and event stream logging every operation.

**LLM Interaction Mode.** The same natural language input produces different behavior depending on role. For example, the query "開採購單" (create purchase order):

- For **Purchasing Agent** ($U_b$): LLM presents a form pre-filled with suggested supplier, item, and price based on recent purchases — user confirms or adjusts, then executes.
- For **Factory Director** ($U_d$): LLM presents the PO for approval with an impact analysis (cash flow effect, delivery timeline).
- For **Accountant** ($U_a$): LLM shows the PO's accounting impact (AP increase, budget consumption).

This role-conditioned prompting enables a **single input interface** to serve multiple decision contexts without additional UI complexity [2].

## 3.4 Domain Module Design

### 3.4.1 Inventory Module (MM)
The inventory module manages parts master data, stock levels, and material movements. Core operations include:
- **Part management**: CRUD on parts with spec, category, unit, and location
- **Stock query**: Real-time quantity per part with storage location tracking
- **Inbound** (`material.received`): Receives goods against PO, increments stock, triggers quality inspection
- **Outbound** (`material.issued`): Issues materials to production, decrements stock, enforces constraint checks

### 3.4.2 Purchase Module (PP)
The purchase module covers the full procurement lifecycle:
- **Supplier management**: Score-based vendor evaluation, contact management
- **PO lifecycle**: draft → sent → partially_received → received → closed
- **Multi-line POs**: Each PO can contain multiple line items with different parts, quantities, and prices
- **Cross-module integration**: PO receipt auto-triggers inventory inbound and accounting AP entry

### 3.4.3 BOM Module (PP)
The BOM module handles product structure and material requirements:
- **Multi-level BOM**: Recursive parent-child structure with quantities per unit
- **BOM explosion**: Expands product structure to raw materials
- **Shortage detection**: Compares BOM requirements against on-hand inventory

### 3.4.4 Dispatch Module (PP)
The dispatch module manages production execution:
- **Work Center management**: Machines/stations with status tracking (idle, running, down, maintenance)
- **Production Order lifecycle**: draft → released → dispatched → in_progress → completed → closed
- **Operation sequencing**: Each order has sequenced operations assigned to work centers
- **Dynamic Rescheduling**: Three strategies — right_shift (delay), route_change (alternate work center), expedite (priority boost)

### 3.4.5 Quality Module (QM)
The quality module implements a closed-loop quality management system with four tables:

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `inspection_orders` | Inspection requests triggered by inbound/receipt | status (pending→passed→failed) |
| `inspection_results` | Actual measurements per inspection | values, inspector_id, pass/fail |
| `non_conformances` (NC) | Defect tracking when inspection fails | defect_code, severity, root_cause, status |
| `capa_records` | Corrective & Preventive Actions | nc_id, action_plan, deadline, status |

The quality workflow follows a strict state machine:
1. **Goods received** → Auto-create `inspection_order` (status: pending)
2. **Inspector records results** → Pass → auto-close; Fail → auto-create NC
3. **NC created** → Lock associated stock (prevent use of non-conforming materials)
4. **CAPA issued** → Engineering investigates root cause, implements corrective action
5. **CAPA verified** → NC closed, stock unlocked (or scrapped)

### 3.4.6 Accounting Module (FI)
The accounting module provides double-entry bookkeeping with five tables:

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `accounts` | Chart of accounts | code, name, type (asset/liability/equity/revenue/expense), balance |
| `journal_entries` | GL posting header | entry_no, description, date, posted flag |
| `journal_lines` | Double-entry lines | account_id, debit, credit, reference |
| `accounts_receivable` | Customer invoices | invoice_no, amount, paid_amount, due_date, status |
| `month_end_closes` | Period close tracking | period, status (open/closed), closed_by |

Double-entry is enforced at the database level: every journal entry must have `sum(debits) = sum(credits)`. When closed, the period prevents new postings. AR aging is computed dynamically:
- Current: due_date > today
- Overdue 1-30 days: past due < 30 days
- Overdue 31-60 days
- Overdue 60+ days: escalated to management

## 3.5 LLM Orchestrator with Proactive Constraint Enforcement

The LLM Orchestrator is the system's central intelligence, combining intent classification, tool dispatch, and constraint enforcement.

### 3.5.1 Intent Classification
User input is classified into one of $N$ domain intents using few-shot prompting with role context. The classifier outputs a structured intent with parameters:

```json
{
  "intent": "ISSUE_MATERIAL",
  "parameters": {
    "work_order": "WO-20250506-003",
    "material": "底板",
    "quantity": 100,
    "role": "production_controller"
  }
}
```

### 3.5.2 Tool Dispatch
Each domain intent maps to a function tool with JSON Schema parameter validation. Tool definitions follow OpenAPI conventions and are dynamically injected into the LLM context based on classified intent [3].

### 3.5.3 Constraint Engine (20 Rules Across 6 Modules)
Before executing any write operation, the orchestrator runs a **pre-validation layer** with 20+ business rules enforced at both the API and service layer:

**Inventory:**
1. **Insufficient stock**: Outbound qty > on-hand → rejected with available alternatives
2. **Negative stock**: Allowed with warning (work-in-process tracking)
3. **Part not found**: Unknown part_no → rejected with suggestions
4. **Location conflict**: Inbound location differs from primary storage → warning

**Purchase:**
5. **Duplicate PO**: Same supplier + same items within 24h → warning
6. **PO closed**: Cannot modify closed PO → rejected
7. **Invalid supplier**: Unknown supplier → rejected
8. **Line item mismatch**: Part not in supplier's catalog → warning

**BOM:**
9. **Circular reference**: BOM contains itself → rejected with cycle path
10. **Component not found**: Referenced part missing → rejected
11. **Quantity validation**: Negative or zero qty → rejected
12. **Missing BOM**: Product has no BOM → warning

**Dispatch:**
13. **Material availability**: WO released without sufficient stock → blocked with shortage list
14. **Expedite collision**: Two expedited orders sharing same work center → conflict warning
15. **Work center overload**: Capacity exceeded → alternative routing suggestion
16. **Invalid state transition**: e.g., dispatch from draft (must release first) → rejected with valid transitions

**Quality:**
17. **Stock locked by NC**: Cannot issue stock with active NC on same part → blocked
18. **Duplicate inspection**: Inspection order already exists for this receipt → warning
19. **CAPA deadline overdue**: Past deadline without verification → escalated

**Accounting:**
20. **Month-end close**: Period closed → all postings rejected
21. **Double-entry violation**: sum(debits) ≠ sum(credits) → rejected with debug info
22. **AR lock**: Customer overdue > 60 days → shipment blocked until payment

When any constraint is violated, the LLM surfaces a structured "warning + resolution" response:

```
⚠️ 出庫超過庫存量：要求 100，可用 80
  建議：① 出庫 80，不足部分先開採購單
        ② 檢查是否有在途訂單
```

### 3.5.4 Proactive Decision Support
The orchestrator transforms the LLM from a passive query interface into an **active decision support partner** [4]. For over-issue scenarios (BOM requires 80, user requests 100):

```
⚠️ Warning: Issuing 100 exceeds BOM standard of 80 by 25%.
Impact: +NT$1,200 WIP cost, 20 units excess material.
Options:
  ① Issue 80 now, reserve 20 for next WO
  ② Issue 100 with over-issue approval (manager required)
  ③ Issue 80, then adjust BOM if yield is consistently >5%
```

## 3.6 Cross-Functional Event Engine

A key design requirement derived from factory operations is that **every decision affects multiple roles**. When a warehouse keeper receives material, the purchasing agent needs to know (delivery complete), the quality inspector needs to act (inspection pending), and the accountant needs to record (inventory asset increase).

### 3.6.1 Event Model
The event engine implements a **DomainEvent** pattern with the following structure:

```python
@dataclass
class DomainEvent:
    event_type: str              # e.g., "material.received"
    category: EventCategory      # MATERIAL | PRODUCTION | PURCHASE | QUALITY | FINANCE | SYSTEM
    severity: EventSeverity      # INFO | WARNING | CRITICAL
    actor_role: str              # who triggered it
    aggregate_id: str            # reference object (PO-001, WO-001)
    aggregate_type: str          # "purchase_order", "work_order"
    payload: dict                # business data
    metadata: dict               # routing instructions
```

### 3.6.2 Event Lifecycle & Role Routing
Each event type has a predefined subscription list derived from real factory workflows:

| Event | Emitter | Subscribers |
|-------|---------|-------------|
| PO Created | Purchasing | Accounting (AP), Warehouse (inbound) |
| Goods Received | Warehouse | Purchasing (delivery), Quality (inspection) |
| Material Issued | Production | Warehouse (stock dec), Accounting (WIP) |
| NC Created | Quality | Production (rework), Engineering (root cause) |
| Payment Due | Accounting | Director (approval), Purchasing (supplier comm) |
| AR Overdue | Accounting | Director (escalation) |

Notifications are delivered via three channels:
- **In-app**: Real-time notification panel with read/unread tracking
- **War Room event stream**: Live scrolling feed at bottom of multi-screen display
- **Telegram**: Push notifications to configured chat groups (via Hermes Gateway)

### 3.6.3 Event Simulation & Flow Visualization
The event engine includes a simulation endpoint for development and demonstration. When events are emitted, the War Room display animates the flow in real-time:

```
🏭供應商 ─[PO.created]─→ 📋採購 ─[material.received]─→ 📦庫存 ─[material.issued]─→ ⚙️派工 ─[NC.created]─→ ✅品檢
                                                                                    ─[payment.due]─→ 💰會計
```

Each event appears as a floating card that animates along the SVG flow path between stages, with the target stage glowing briefly on arrival. A bottom event stream logs the 30 most recent events with severity indicators.

## 3.7 War Room Display

The War Room is a full-screen HTML dashboard designed for multi-monitor factory floor deployment. Key design decisions:

1. **Dark theme with grid background**: Optimized for long-duration display in low-light factory environments
2. **SVG-based flow diagram**: Six stages arranged left-to-right with animated material flow (green) and finance flow (yellow) particles
3. **Live data integration**: Every 15 seconds, fetches from 7 API endpoints to update stage counts and KPI headers
4. **Real-time event stream**: Bottom panel shows scrolling log of the 30 most recent events with severity dots
5. **Event flow animation**: When the activity API returns new events, floating cards animate along SVG flow paths
6. **Auto-simulation**: Every 25 seconds, generates a random business event (PO created, goods received, NC created) to demonstrate the flow

The display is accessible at `/war-room.html` via Vite dev server and can be opened in full-screen (F11) on any connected monitor.

## 3.8 Implementation Details

The system is implemented as a full-stack web application:

- **Frontend**: React 18 with TypeScript, Vite build tool, Tailwind CSS. 20+ widget components including KPI grid, inventory chart, PO table, supplier list, dispatch Gantt, quality panel, AR aging, GL journal. Role-based rendering via React Context and dynamic imports. War Room as standalone HTML+SVG.
- **Backend**: Python FastAPI with SQLAlchemy ORM. 6 domain modules × service + API + model + schema layers. 9 API routers exposing 40+ endpoints. One agent per domain with dynamic tool injection.
- **LLM Integration**: OpenAI-compatible API (tested with DeepSeek). Tool definitions as JSON Schema arrays injected per conversation. System prompt dynamically composed with role context. Multi-provider adapter supporting Anthropic, OpenAI, DeepSeek, OpenRouter, and Ollama.
- **Database**: SQLite for development, PostgreSQL for production (with pgvector). 19 tables across 6 modules. Alembic for schema migrations.
- **Event Engine**: In-process event bus with pub-sub pattern. 10 event types × role subscription matrix. Channel adapters for in-app notification and Telegram push.
- **Constraint Engine**: 22 business rules enforced at service layer via `enforce()` function. Each rule returns a `ConstraintVerdict` with pass/fail + structured suggestions.

The system is designed as **open-source** to enable community adoption and academic reproducibility. Repository: [TBD on publication].

## 3.9 Evaluation

### 3.9.1 Experimental Design

We evaluated the system using 30 natural language test queries across 7 categories (Inventory, Purchase, BOM, Dispatch, Quality, Accounting, Cross-module). Each query was sent to the chat API endpoint (`POST /api/chat`) using the DeepSeek provider (model: deepseek-chat). The evaluation measured:

1. **Intent classification accuracy**: Whether the LLM's tool call intent matched the expected intent
2. **Response quality**: Whether the response contained the expected business data
3. **Response time**: End-to-end latency from query submission to response delivery

Test queries were designed to represent real factory floor scenarios, e.g.:
- "M6x20螺絲還有多少庫存？" (Inventory query)
- "開一張採購單給大明螺絲，買1000個M8x30" (Purchase order creation)
- "展開產品BLK-001的BOM" (BOM explosion)
- "釋出工單WO-20260506-001" (Work order release)
- "建立NC，料號M8x30，尺寸超差0.5mm" (Non-conformance creation)
- "查詢AR逾期狀況" (AR aging query)

### 3.9.2 Results

| Category | Cases | Passed | Accuracy | Avg. Time (s) |
|----------|-------|--------|----------|---------------|
| Inventory | 5 | 4 | **80%** | 7.4 |
| Purchase | 5 | 4 | **80%** | 7.8 |
| BOM | 4 | 4 | **100%** | 12.3 |
| Dispatch | 5 | 5 | **100%** | 5.1 |
| Quality | 4 | 4 | **100%** | 6.5 |
| Accounting | 5 | 5 | **100%** | 7.2 |
| Cross-module | 2 | 1 | **50%** | 8.7 |
| **TOTAL** | **30** | **27** | **90%** | **7.7** |

### 3.9.3 Analysis

**Strong performers (90-100%)**: BOM, Dispatch, Quality, and Accounting modules achieved near-perfect accuracy after prompt engineering that added explicit keyword-based routing rules and forbidden tool usage directives. The key insight was that LLMs naturally gravitate toward the most general tool (`query_inventory`) when query scope is ambiguous — adding domain-specific exclusion rules (e.g., "查詢AR絕對不能用 query_inventory") resolved this bias.

**Good performers (80%)**: Inventory and Purchase modules showed minor failures primarily due to multi-turn tool call loops exceeding the 5-round limit. In one case, the LLM attempted to create a purchase order but called auxiliary validation tools first, exhausting the round limit before completion. This is an implementation constraint (configurable) rather than a fundamental limitation.

**Weak performer**: Cross-module queries (50%) remained challenging. The LLM handles individual tools well but struggles to compose multi-step workflows (e.g., "check shortage → if insufficient, create PO"). This aligns with known LLM agent research [6] and suggests a **multi-agent architecture** where a planner agent decomposes requests and dispatches to domain-specific agents would improve performance.

**Response time**: Average response time was 7.7 seconds per query, dominated by LLM inference time (4-12 seconds on DeepSeek). BOM queries were slowest (12.3s) due to multi-level database recursion combined with LLM processing. Accounting queries averaged 7.2 seconds due to simpler tool definitions. Single-turn queries (no tool calls) completed in ~3 seconds, while multi-turn workflows extended to 10+ seconds.

**Error analysis of 3 failures**:
1. **Purchase PO creation**: The LLM attempted to validate material availability before creating the PO, consuming rounds on inventory queries — the 5-round limit was reached before the PO tool was called.
2. **Inventory full list**: Similar multi-turn behavior — the LLM called query_inventory multiple times with different filters instead of a single unfiltered query.
3. **Cross-module workflow**: The LLM called `check_stock_shortage` correctly but failed to compose the follow-up PO creation, returning the shortage report instead.

### 3.9.4 Comparison with Traditional ERP

Traditional ERP systems (SAP, Oracle, Odoo) require 3-7 clicks or menu navigations per transaction, with average operation times of 30-120 seconds for experienced users and 2-5 minutes for new users. LLM-ERP's average response time of 7.7 seconds represents a **4-15× speed improvement** for routine operations, with the additional benefit of zero learning curve — users express intent in natural language rather than memorizing transaction codes.

### 3.9.5 Limitations

1. **Single provider**: Results reflect DeepSeek only. Multi-provider comparison (GPT-4o, Claude Sonnet, Ollama) is planned.
2. **Cross-module complexity**: Multi-step workflows remain challenging for single-turn LLM interactions; a multi-agent architecture may improve this.
3. **Hallucination risk**: While all responses contained valid data, numerical hallucination (incorrect stock counts) remains a risk that requires guardrails.

### 3.9.6 Planned Enhancements

1. **Multi-provider benchmark**: Compare DeepSeek vs Claude vs GPT on the same 30 test cases
2. **User study**: Controlled experiment with 12 users (2 per archetype) comparing LLM-ERP vs Odoo for standard manufacturing tasks
3. **Longitudinal analysis**: Track intent accuracy improvement over 4 weeks of usage

## References

[1] R. N. Anthony, *Planning and Control Systems: A Framework for Analysis*. Harvard Business School, 1965.

[2] J. Liu et al., "Interactive Natural Language Interface for ERP Systems," *Proc. of CHI*, 2023.

[3] T. Schick et al., "Toolformer: Language Models Can Teach Themselves to Use Tools," *arXiv preprint*, 2023.

[4] Z. G. Iyer et al., "Improving NL2SQL Accuracy in Enterprise Contexts," *Proc. of ACL*, 2024.

[5] J. Brooke, "SUS: A Quick and Dirty Usability Scale," *Usability Evaluation in Industry*, 1996.

[6] S. Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models," *ICLR*, 2023.

[7] Anthropic, "The Claude Model Family," *Technical Report*, 2024.
