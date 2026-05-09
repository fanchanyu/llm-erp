# Role as Variable: An LLM-Powered ERP System for Discrete Manufacturing

**Target Journal:** Journal of Management Studies (JMS)

**Abstract.** Enterprise Resource Planning (ERP) systems are indispensable for modern manufacturing operations, yet their complexity, embodied in the T-code paradigm of SAP and comparable menu architectures, imposes a steep learning curve that constrains adoption, especially among small and medium enterprises (SMEs). Gartner's 2024 survey reports that 47% of organizations identify user adoption difficulty as the primary barrier to ERP value realization. This paper explores whether large language models (LLMs), when embedded within a structured role-based architecture, can reduce this friction by enabling natural language interaction across the full manufacturing lifecycle. We present an end-to-end LLM-ERP system built on a core methodological thesis: **role definition constitutes variable definition**. Seven user archetypes (Factory Director, Production Controller, Warehouse Keeper, Purchasing Agent, Quality Inspector, Accountant, Sales Manager) are formalized as variables that condition the entire system, including interface composition, LLM tool access, constraint enforcement, and cross-functional event routing. The system spans eight domain modules (Inventory, Purchasing, BOM, Dispatch, Quality, Accounting, CRM, and a cross-cutting Event Engine), implements 37 LLM-callable function tools governed by 23 proactive business rule constraints, and supports multi-provider LLM backends (Anthropic, OpenAI, DeepSeek, local models). In a preliminary 30-query experimental evaluation across all domains, the system yielded 93.3% functional accuracy on the test queries with DeepSeek (8.6s average response time) and 83.3% with Gemma4 8B (11.4s). Findings suggest that single-domain operational queries are robust to model size, while cross-module task composition remains the primary challenge. This preliminary evaluation suggests that LLM-ERP warrants further investigation through larger-scale studies and controlled user experiments. The system is released as open-source to support independent replication and extension.

**Keywords:** Enterprise Resource Planning, Large Language Models, Human-Computer Interaction, Manufacturing, Natural Language Interfaces

---

## 1. Introduction

Enterprise Resource Planning (ERP) systems serve as the operational backbone of modern manufacturing organizations, integrating inventory management, procurement, production scheduling, quality control, financial accounting, and customer relationship management into a unified platform (Davenport, 1998; Hitt et al., 2002). The strategic importance of ERP has grown substantially over the past three decades, with the global ERP market projected to exceed USD 100 billion by 2026 (Gartner, 2024). Organizations that successfully implement ERP report improvements in operational efficiency, data visibility, and decision-making responsiveness (Bendoly & Jacobs, 2022; Cotteleer & Bendoly, 2006).

Yet the same integration that makes ERP powerful also makes it difficult to use. The dominant paradigm, transactional menu navigation often formalized through systems such as SAP's T-code architecture, requires users to memorize hundreds of command codes and navigate deeply nested menu hierarchies to perform even routine operations. A warehouse keeper releasing materials to production must locate the correct transaction code (MB1A in SAP), select the appropriate movement type (261), enter the work order reference, specify the material number and quantity, and confirm postings, a sequence that demands substantial procedural training. Gartner's 2024 ERP Adoption Survey found that 47% of organizations identify user adoption difficulty as the primary barrier to realizing ERP value, and 38% report that training time for new users exceeds three months. For small and medium enterprises (SMEs), which constitute over 90% of manufacturing firms globally (OECD, 2023), these training burdens are especially acute: dedicated ERP specialists are often unavailable, and generalist staff must divide their time between production duties and system operation (Buonanno et al., 2005; Schlichter & Kraemmergaard, 2010).

Several lines of research have sought to address ERP usability challenges. Prior work in human-computer interaction for ERP has examined task-technology fit (Gattiker & Goodhue, 2005), organizational alignment during implementation (Hong & Kim, 2002), and cultural adaptation of interface conventions (Soh et al., 2000). These studies have advanced understanding of organizational-level adoption but have largely treated interface complexity as a fixed property to be managed through training, documentation, and change management rather than redesigned at the interaction layer. More recently, natural language interfaces (NLIs) for databases, exemplified by NL2SQL systems such as Spider (Yu et al., 2018) and WikiSQL (Zhong et al., 2017), have demonstrated that structured queries can be synthesized from natural language with high accuracy. However, these systems address single-turn, read-only data retrieval rather than the write-intensive, multi-step, cross-functional workflows that characterize manufacturing ERP operations. The gap between database query synthesis and full-lifecycle ERP interaction remains substantial.

The emergence of large language models with function-calling capabilities (Schick et al., 2023; Yao et al., 2023) has opened a new design space. LLMs can classify user intent, select and invoke structured tools, and generate context-aware natural language responses, making them candidates for ERP interaction layers that reduce or eliminate menu navigation. Early explorations have applied LLMs to enterprise sub-tasks such as report generation (Li et al., 2024), inventory querying (Wu et al., 2024), and workflow automation trigger classification (Qian et al., 2024). Framework-level contributions, including AutoGen (Wu et al., 2023), MetaGPT (Hong et al., 2024), and HuggingGPT (Shen et al., 2024), have established multi-agent architectures for task decomposition, yet these systems target general-purpose software development and data analysis rather than the domain-specific constraints, role hierarchies, and event-driven coordination that characterize manufacturing ERP. To our knowledge, no prior work has constructed an end-to-end LLM-ERP system that spans the full manufacturing lifecycle, from procurement through production, quality, and financial closure, with structured constraint enforcement and cross-functional event propagation.

In this paper, we present an LLM-powered ERP system designed for discrete manufacturing operations. The system makes four contributions:

1. **Role-as-variable methodology.** We formalize seven user archetypes as structured variables that condition the entire system stack: interface composition, LLM tool access, constraint scope, and event routing. This approach treats role definition as a design primitive rather than a post-hoc access control layer, enabling systematic experimentation across role conditions.

2. **End-to-end manufacturing coverage.** The system implements eight domain modules spanning the full manufacturing lifecycle (Inventory, Purchasing, BOM, Dispatch, Quality, Accounting, CRM, Event Engine) with 37 LLM-callable function tools and 23 proactive business rule constraints. This work presents an initial effort toward an LLM-ERP system that covers procurement-to-closure workflows within a single architecture.

3. **Event-driven cross-functional coordination.** A publish-subscribe event engine with 12 event types and role-based routing operationalizes the cross-functional visibility requirement of manufacturing operations: every action triggers appropriate notifications across roles, from floor-level task assignments to executive exception alerts.

4. **Experimental evaluation and open-source release.** We present a preliminary experimental evaluation of the system on 30 natural language queries spanning all domains and two LLM providers (DeepSeek cloud and Gemma4 local), yielding 93.3% functional accuracy on the test set with DeepSeek. The complete system, including source code, database schema, evaluation scripts, and documentation, is released as open-source to support independent replication and community extension.

The remainder of this paper is organized as follows. Section 2 reviews related work across three dimensions: ERP system limitations, human-computer interaction in ERP, and LLM applications in enterprise software, and identifies the research gap. Section 3 describes the system architecture and the role-as-variable methodology in detail. Section 4 presents the experimental evaluation, including accuracy results, multi-provider comparison, and failure analysis. Section 5 discusses limitations and outlines directions for future work. Section 6 concludes the paper.

---

## 2. Related Work

### 2.1 ERP System Limitations

The academic literature on ERP systems has extensively documented the tension between integration benefits and operational complexity. Davenport (1998) identified this tension early, noting that ERP systems impose standardized processes that may conflict with existing organizational practices. Subsequent empirical work has confirmed that implementation complexity, particularly the need for extensive user training and process re-engineering, is a consistent predictor of ERP project difficulty (Umble et al., 2003; Motwani et al., 2005).

**Training burden.** The T-code paradigm, while enabling efficient operation for expert users, creates a significant training barrier for new and infrequent users. SAP's transaction codes number over 100,000 across all modules (SAP, 2023), and even within a single manufacturing plant, a warehouse keeper may need to memorize 15–30 transaction codes for routine operations. Gartner (2024) reports that organizations spend an average of 18–25% of their ERP project budget on training, with new users requiring 3–6 months to reach operational proficiency. For SMEs, these training costs are disproportionately burdensome (Buonanno et al., 2005).

**Static scheduling and limited decision support.** Production scheduling within traditional ERP systems tends to be rule-based and static: Master Production Schedule (MPS) and Material Requirements Planning (MRP) runs are typically executed in batch mode, and rescheduling in response to disruptions (machine breakdown, material shortage, urgent order insertion) requires manual intervention through transaction codes such as MD04 (Stock/Requirements List) or CO02 (Change Production Order). The cognitive load of comparing rescheduling alternatives (right-shift vs. route-change vs. expedite) falls entirely on the production controller, who must mentally simulate the consequences of each option across order priorities, capacity constraints, and material availability. Decision support research has proposed optimization-based approaches (Kreipl & Dickersbach, 2008; Gupta et al., 2022), but these remain separate from the primary ERP interface, requiring context switching.

**Fragmented visibility across functions.** A defining characteristic of manufacturing ERP is that operational events have cross-functional consequences. A material receipt event triggers inventory value updates (Finance), inspection order creation (Quality), and PO status change (Purchasing). In traditional ERP, visibility into these downstream effects requires navigating between modules (MM → QM → FI → MM), often through separate transaction codes with inconsistent navigation patterns. Research on ERP data quality highlights that fragmented visibility contributes to decision latency and coordination failures (Xu et al., 2002; Haug et al., 2009).

**SME-specific challenges.** SMEs face additional constraints that compound ERP difficulty: limited IT staff, smaller training budgets, and lower tolerance for operational disruption during implementation (Schlichter & Kraemmergaard, 2010; Deep et al., 2008). Cloud-based ERP alternatives (e.g., Odoo, SAP Business One) have reduced the cost barrier but have not addressed the interaction complexity barrier: the same T-code and menu-navigation paradigms persist in simplified form. The net effect is that many SMEs restrict ERP usage to a subset of modules and a small pool of trained operators, underutilizing the system's integration potential (Haddara & Elragal, 2015).

### 2.2 Human-Computer Interaction in ERP

Research at the intersection of HCI and ERP has examined how system design interacts with organizational context, user capability, and task requirements.

**Cultural and organizational fit.** Soh et al. (2000) investigated ERP implementation in nine organizations across seven countries, finding that mismatches between package design assumptions and local organizational practices, including authority structures, reporting conventions, and role definitions, were a primary source of implementation difficulty. Their work suggests that role-adaptive interfaces, which adjust to local role conventions, may improve fit. Hong & Kim (2002) formalized this as the organizational fit of ERP, showing that the alignment between ERP functionality and organizational structure predicts implementation success. Our role-as-variable approach extends this insight by making role adaptation an explicit architectural property rather than a customization layer.

**Post-implementation use.** Gattiker & Goodhue (2005) studied ERP use in manufacturing settings after the implementation phase, finding that task-technology fit (Goodhue & Thompson, 1995), the degree to which system features match user task requirements, is the primary predictor of individual performance impact. Their survey of 86 manufacturing plants found that users who perceived higher fit reported better decision-making quality and operational efficiency. This provides theoretical grounding for role-conditioned interface design: if task requirements differ by role, and fit depends on the match between system features and task requirements, then role-specific feature subsets should improve fit.

**Natural language and ERP.** The prospect of natural language interaction with ERP has been explored in prototype form. Engels & Leiner (2003) demonstrated a natural language query interface for an SAP system using a domain-specific grammar, achieving 78% accuracy on a limited set of read queries. More recently, work on voice-enabled ERP interfaces (Szałek et al., 2021) has examined speech-based interaction for warehouse operations, finding that hands-free operation improves picking efficiency by 12–18% in controlled studies. These efforts, while demonstrating feasibility, have been limited to single-module, read-only, or single-role settings. The present work extends natural language ERP interaction to write operations, cross-module workflows, and role-conditioned behavior within a unified architecture.

### 2.3 LLMs in Enterprise Software

The application of LLMs to enterprise software has accelerated rapidly since 2023, spanning several complementary research directions.

**Tool-use architectures.** Toolformer (Schick et al., 2023) introduced the paradigm of self-supervised learning for API tool use, enabling LLMs to decide when to call external tools (e.g., calculator, calendar, search) and how to interpret results. ReAct (Yao et al., 2023) extended this with an interleaved reasoning-and-action framework that improves both interpretability and accuracy on multi-step tasks. These architectural contributions provide the foundation for LLM-ERP systems: our tool dispatch pipeline adopts a ReAct-inspired pattern in which the LLM classifies intent, selects tools, executes against domain services, and generates responses in a unified loop, with the addition of a proactive constraint layer that intercepts invalid operations before execution.

**Multi-agent systems.** The emergence of multi-agent LLM frameworks, including AutoGen (Wu et al., 2023), MetaGPT (Hong et al., 2024), and HuggingGPT (Shen et al., 2024), has demonstrated that task decomposition across specialized agents improves performance on complex, multi-step problems. AutoGen enables flexible agent conversations with configurable termination conditions; MetaGPT assigns software engineering roles (product manager, architect, engineer, tester) to different LLM agents for collaborative code generation; HuggingGPT routes sub-tasks to domain-specific Hugging Face models. These frameworks suggest a natural mapping to ERP: different roles could be served by agents with specialized tool sets and domain knowledge. Our current architecture employs a single LLM with role-conditioned prompting and tool subsetting rather than separate agent instances, but the multi-agent architecture is a natural extension identified in our future work.

**NL2SQL and enterprise data interaction.** The NL2SQL benchmark suite (Yu et al., 2018; Zhong et al., 2017) has established standard metrics for evaluating natural language query synthesis on relational databases. Subsequent work has extended NL2SQL to context-dependent queries (Suhr et al., 2020), multi-table joins (Wang et al., 2020), and question decomposition (Zhou et al., 2023). While NL2SQL research provides relevant metrics and techniques, it addresses a fundamentally different problem setting: read-only queries over static database schemas. ERP interaction requires write operations with constraint enforcement, multi-step workflows with intermediate state, cross-functional event propagation, and role-conditioned behavior, capabilities that extend beyond the NL2SQL paradigm.

**Emerging ERP-LLM work.** Industrial and academic efforts have begun to integrate LLMs with ERP systems. SAP has introduced Joule, a generative AI copilot for SAP S/4HANA that supports natural language querying of selected business data (SAP, 2024). Wu et al. (2024) proposed a framework for LLM-based inventory query in supply chain contexts, achieving 91% accuracy on 100 queries. Li et al. (2024) explored LLM-generated management reports from ERP data, focusing on narrative synthesis rather than interactive operation. These efforts, while indicative of growing interest, target narrow sub-domains rather than the full lifecycle coverage, role-conditioned architecture, and structured constraint enforcement that the present work seeks to provide.

### 2.4 Research Gap

The preceding review identifies a clear gap at the intersection of three research areas. First, ERP usability research has established the importance of task-technology fit and organizational alignment but has not addressed the interaction layer itself: users of SAP, Odoo, and comparable systems still navigate T-code menus regardless of organizational fit. Second, HCI research on natural language interfaces for ERP has been limited to single-module, read-only, or single-role settings, without addressing write operations, cross-functional workflows, or role-conditioned system behavior. Third, LLM research in enterprise software has produced promising tool-use and multi-agent architectures, but prior work has not constructed an end-to-end system that spans the full manufacturing lifecycle with structured constraint enforcement and cross-functional event propagation.

The specific gap we address is this: **no prior system integrates LLM-based natural language interaction with formal role definitions, proactive constraint enforcement, and event-driven cross-functional coordination across the full manufacturing ERP lifecycle.** Prior systems address fragments of this design space: NL2SQL for read queries, multi-agent frameworks for task decomposition, or single-module LLM prototypes for inventory or report generation, but none combine all elements within a single architecture validated on write-intensive manufacturing workflows. The present work contributes an end-to-end system that fills this gap, with an explicit methodological commitment to treating role definitions as formal system variables that condition all channels of interaction.

---

## 3. Methodology

The core methodological thesis of this work is that **role definition constitutes variable definition** (角色定義即變數定義): the seven user archetypes we specify are not merely design heuristics but formal variables that govern system behavior end-to-end: from interface composition and LLM response generation to event routing and permission scoping. This section describes the system architecture (3.1), defines the archetype variables (3.2), details the eight domain modules (3.3–3.4), presents the LLM orchestrator and constraint engine (3.5), the event-driven coordination layer (3.6), the war room visualization (3.7), and implementation specifics (3.8).

---

### 3.1 System Architecture Overview

The proposed system follows a **three-tier architecture** designed to decouple natural language interaction from enterprise data operations while maintaining role-consistent behavior across all tiers.

```
┌──────────────────────────────────────────────────────────────────┐
│  Tier 1: Role-Adaptive Frontend (React 18 + TypeScript)          │
│  ┌───────────┐ ┌──────────┐ ┌──────────────┐ ┌────────────────┐ │
│  │ Dashboard │ │ NL Input │ │ Notification │ │ War Room       │ │
│  │ (role-dep)│ │ (CMD)    │ │ (events)     │ │ (multi-screen) │ │
│  └───────────┘ └──────────┘ └──────────────┘ └────────────────┘ │
├──────────────────────────────────────────────────────────────────┤
│  Tier 2: LLM Orchestrator                                         │
│  ┌───────────┐ ┌──────────┐ ┌───────────────┐ ┌────────────────┐ │
│  │ Intent    │ │ Tool     │ │ Proactive      │ │ Constraint     │ │
│  │ Classify  │ │ Dispatch │ │ Analysis       │ │ Enforcement    │ │
│  └───────────┘ └──────────┘ └───────────────┘ └────────────────┘ │
├──────────────────────────────────────────────────────────────────┤
│  Tier 3: Domain Service Layer (FastAPI, 83 endpoints)             │
│  MM │ PP │ BOM │ Dispatch │ QM │ FI │ CRM │ Event Engine         │
├──────────────────────────────────────────────────────────────────┤
│  Database Layer (PostgreSQL/SQLite, 34 tables)                    │
└──────────────────────────────────────────────────────────────────┘
```

**Tier 1: Role-Adaptive Frontend.** A React 18 application that renders dashboard components dynamically based on the authenticated user's role. All 38 widget components belong to a unified library; the role configuration determines which subset is visible, how the natural language input is interpreted, and which notifications appear. The frontend also includes a full-screen War Room display for multi-monitor factory-floor deployment.

**Tier 2: LLM Orchestrator.** A Python-based orchestration layer that (a) classifies natural language input into structured intents using few-shot prompting with role context, (b) injects the relevant subset of 37 function-calling tool definitions, and (c) applies a proactive constraint engine with 23 business rules before executing any write operation. The orchestrator supports a multi-provider adapter (Anthropic, OpenAI, DeepSeek, OpenRouter, Ollama) enabling controlled experimentation across model families.

**Tier 3: Domain Service Layer.** Eight domain modules implemented as FastAPI services, each exposing REST endpoints (83 total across 18 routers) and backed by SQLAlchemy models (34 database tables). A cross-cutting Event Engine implements publish-subscribe coordination across modules, generating 12 event types with role-based routing to three notification channels.

**Design rationale.** This three-tier separation serves three purposes. First, it allows the frontend to be swapped independently of the LLM backend (future work could replace the React frontend with a voice interface without modifying domain logic). Second, the LLM orchestrator acts as an abstraction layer that decouples user-facing language from backend API design: tool definitions are written once and consumed by any LLM provider. Third, the domain service layer enforces data integrity invariants (constraint rules, double-entry accounting) that operate below the LLM's authority: the LLM proposes, the constraint engine disposes.

---

### 3.2 User Archetype Definition

We define **seven user archetypes** for manufacturing ERP operations. Each archetype is characterized along four dimensions: (1) primary operational concern, (2) decision-making level following Anthony's (1965) framework, (3) LLM interaction mode, and (4) notification scope. The formal claim is that role definition constitutes variable definition: each archetype is a **treatment condition** in the experimental sense, parameterizing the entire system from interface to orchestration to event routing.

| Archetype | Role | Concern | Decision Level | LLM Mode | Widgets | Notification Scope |
|-----------|------|---------|---------------|----------|---------|-------------------|
| $U_d$ | Factory Director (廠長) | Plant-wide KPI, exceptions, strategic tradeoffs | **Strategic** | Summarize trends, surface anomalies | 8 | Exceptions only |
| $U_p$ | Production Controller (生管) | Schedule adherence, material shortage, capacity utilization | **Tactical** | What-if simulation, reschedule recommendation | 8 | Production alerts |
| $U_w$ | Warehouse Keeper (倉庫) | Picking, receiving, inventory accuracy | **Operational** | Command-driven, scan-oriented execution | 6 | Task assignments |
| $U_b$ | Purchasing Agent (採購) | PO lifecycle, supplier evaluation, cost optimization | **Tactical** | Multi-vendor comparison, negotiation support | 7 | PO expedite, supply alerts |
| $U_q$ | Quality Inspector (品管) | Inspection, non-conformance tracking, CAPA | **Analytic** | Defect analysis, trend identification | 6 | NC creation, inspection due |
| $U_a$ | Accountant/CFO (會計) | Cash flow, AR/AP, cost analysis, period close | **Strategic/Tactical** | Forecast, payment recommendation, anomaly detection | 8 | Payment due, cash alerts |
| $U_s$ | Sales Manager (業務) | CRM pipeline, customer history, contract lifecycle | **Tactical** | Pipeline analysis, customer history, lead scoring | 7 | Opportunity updates, contract expiry |

**Decision-level taxonomy.** We adopt Anthony's (1965) three-tier framework with one extension:

- **Strategic** ($U_d$, $U_a$): Long-term, aggregate, exception-driven decisions. The LLM summarizes trends, surfaces anomalies, and provides decision support for high-impact choices (capital allocation, factory configuration, pricing strategy). Interaction is analytical and infrequent.
- **Tactical** ($U_p$, $U_b$, $U_s$): Medium-term planning and tradeoff decisions. The LLM facilitates what-if simulation (rescheduling scenarios), multi-option comparison (supplier quotes, routing alternatives), and workflow orchestration (pipeline management). Interaction is periodic and deliberation-oriented.
- **Operational** ($U_w$): Short-term execution and compliance. The LLM functions as a command interpreter: the user issues directives (receive goods, issue materials) and the system executes with minimal deliberation. Interaction is frequent and action-oriented.
- **Analytic** ($U_q$): A pattern-recognition level not fully captured by Anthony's hierarchy. The quality inspector's work is neither purely operational (though inspection execution is) nor tactical (though CAPA planning is); it involves data interpretation and pattern detection. The LLM supports defect trend analysis, pareto identification, and root-cause hypothesis generation.

**LLM interaction modes.** Each role maps to a distinct LLM behavior pattern, implemented through role-conditioned system prompts:

- **Summarize/Surface** (Director): The LLM acts as an executive assistant, proactively highlighting KPI deviations, inventory risks, and quality trends. Responses favor aggregated data and exception reports.
- **What-if/Recommend** (Production Controller, Sales Manager): The LLM simulates alternative scenarios (reschedule options, pipeline projections) and presents tradeoffs. Responses present multiple options with consequences.
- **Command-driven** (Warehouse Keeper): The LLM acts as a transaction processor. Inputs are expected to be direct commands (receive, issue, locate); responses are confirmations with transaction details.
- **Compare/Negotiate** (Purchasing Agent): The LLM surfaces supplier comparisons, price trends, and lead-time data. Responses facilitate informed procurement decisions.
- **Analyze/Trend** (Quality Inspector): The LLM performs pattern analysis on inspection data, NC trends, and CAPA effectiveness. Responses include statistical summaries and anomaly flags.
- **Forecast/Recommend** (Accountant): The LLM provides cash flow projections, aging summaries, and payment recommendations. Responses favor numerical precision and compliance checks.
- **Pipeline/History** (Sales Manager): The LLM tracks lead-to-contract progression, surfaces customer interaction history, and supports opportunity qualification. Responses favor chronological clarity and stage progression.

**Formalization.** Given a widget set $W = \{w_1, w_2, \dots, w_{38}\}$, a tool set $T = \{t_1, t_2, \dots, t_{37}\}$, a permission set $P$, and a role $r \in \{U_d, U_p, U_w, U_b, U_q, U_a, U_s\}$, the role condition $C_r$ is defined as the triple:

$$C_r = (D_r \subset W,\; T_r \subset T,\; P_r \subset P)$$

where $D_r$ is the role-visible dashboard (widget subset), $T_r$ is the role-accessible tool subset, and $P_r$ is the permission scope. The system's response $R$ to input $I$ given role $r$ is:

$$R(I, r) = \text{LLM}\big(I \mid \text{prompt}(r),\, \text{tools}(T_r),\, \text{constraints}(C_r)\big)$$

This formalization makes explicit that the role variable $r$ conditions all three channels of system behavior: what the user sees, what the LLM can do, and what constraints apply.

---

### 3.3 Role-Adaptive Interface Design

The frontend implements role adaptation through three mechanisms: a declarative role configuration dictionary, a unified widget library, and role-conditioned system prompts for the LLM.

**Declarative role configuration.** Each role is defined as a TypeScript object specifying widgets, LLM mode, and permissions:

```typescript
const ROLES: Record<Role, RoleConfig> = {
  director: {
    widgets: [
      'alert-bar', 'kpi-grid', 'inventory-chart', 'ai-insights',
      'quality-panel', 'war-room', 'event-flow', 'production-insights'
    ],
    llmMode: 'strategic',
    permissions: ['view-all', 'approve-over-issue', 'approve-capex'],
    kpiMetrics: ['otd-percent', 'inventory-turnover', 'quality-yield',
                 'po-cycle-time', 'capacity-utilization', 'cash-conversion-cycle']
  },
  warehouse: {
    widgets: [
      'pick-list', 'putaway-queue', 'inventory-search', 'stock-alerts',
      'inventory-chart', 'dispatch-gantt'
    ],
    llmMode: 'execution',
    permissions: ['view-inventory', 'receive-stock', 'issue-stock', 'transfer-stock'],
    kpiMetrics: ['inventory-accuracy', 'picking-efficiency', 'receiving-throughput',
                 'stockout-rate', 'turnover-ratio', 'dormant-inventory-pct']
  },
  sales_manager: {
    widgets: [
      'customer-list', 'so-table', 'crm-events', 'history-panel',
      'lead-list', 'opportunity-pipeline', 'contract-list'
    ],
    llmMode: 'pipeline',
    permissions: ['view-customers', 'create-so', 'manage-leads',
                  'manage-opportunities', 'view-contracts'],
    kpiMetrics: ['pipeline-value', 'conversion-rate', 'avg-deal-cycle',
                 'customer-acquisition-cost', 'win-rate', 'contract-renewal-rate']
  },
  // ... production_controller, purchasing_agent, quality_inspector, accountant
};
```

**Widget library.** The system contains 38 widget components organized into 8 functional groups:

- **Core** (5): alert-bar, kpi-grid, inventory-chart, dispatch-gantt, ai-insights
- **Inventory** (4): pick-list, putaway-queue, inventory-search, stock-alerts
- **Purchase** (4): po-table, supplier-list, shortage-forecast, price-trend
- **Quality** (4): inspection-queue, nc-list, defect-pareto, capa-tracker
- **Production** (4): production-insights, shortage-table, capacity-adjust, overdue-orders
- **Finance** (6): cash-flow, ar-aging, ap-aging, cost-variance, gl-journal, month-close
- **CRM** (9): customer-list, so-table, crm-events, history-panel, lead-list, opportunity-pipeline, contract-list, decision-log, aar-list
- **Cross-cutting** (2): event-flow, quality-panel

**Role-conditioned prompting.** The same natural language input produces role-appropriate responses through dynamic system prompt composition. The system prompt template includes:
1. A role-specific preamble ("You are the {role} assistant for a manufacturing ERP system...")
2. Role-specific behavioral guidelines (summarize vs. execute vs. compare)
3. The role-appropriate tool subset (only tools the role has permission to use)
4. Role-specific constraint sensitivity (e.g., the director sees financial constraint warnings; the warehouse keeper sees inventory constraint warnings)

For the query "開採購單" (create purchase order), the system produces:
- **Purchasing Agent** ($U_b$): Form pre-filled with suggested supplier, item, and price based on purchase history, with multi-vendor comparison
- **Factory Director** ($U_d$): PO approval request with cash-flow impact analysis and delivery timeline
- **Accountant** ($U_a$): PO's accounting impact (AP entry, budget consumption, cash position effect)

This single-interface/multiple-context design is the practical expression of the role-as-variable thesis: the input channel is uniform, but the system behavior is conditioned by $C_r$.

---

### 3.4 Domain Module Design

The system is decomposed into **eight domain modules**: seven operational modules plus one cross-cutting Event Engine. Each module follows a consistent pattern: a REST API router (FastAPI), a service layer (business logic), SQLAlchemy models (data persistence), and tool definitions (LLM function-calling interface).

#### 3.4.1 Inventory Module (MM)

Manages parts master data, stock levels, and material movements across storage locations.

**Data model (3 tables):** `parts` (part_no, name, spec, unit, category), `inventory` (part_no, location, quantity, safety_stock, lead_time), `inventory_transactions` (id, part_no, type, quantity, reference, timestamp)

**Core operations:**
- **Part management**: CRUD on parts with specification, category, unit, and preferred location
- **Stock query**: Real-time quantity per part with location-level breakdown
- **Inbound** (material.received): Receives goods against PO, increments stock, triggers quality inspection order
- **Outbound** (material.issued): Issues materials to production or sales, decrements stock, runs constraint checks

**LLM tools (3):** `query_inventory`, `inbound_material`, `outbound_material`

**Constraint rules (5):** INV_NEGATIVE_STOCK (BLOCK), INV_BELOW_SAFETY (WARN), INV_EXPIRED (BLOCK/WARN), INV_DORMANT_1Y (WARN), INV_COUNT_VARIANCE (BLOCK)

#### 3.4.2 Purchasing Module (PP)

Manages the full procurement lifecycle from supplier evaluation to PO closure.

**Data model (2 tables):** `suppliers` (id, name, contact, score, status), `purchase_orders` (id, supplier_id, status, items, total_amount)

**Core operations:**
- **Supplier management**: Score-based vendor evaluation (0–5), contact management, status tracking (active/locked)
- **PO lifecycle**: draft → sent → partially_received → received → closed, with line-item granularity
- **Cross-module integration**: PO receipt triggers inventory inbound (MM) and AP entry (FI)
- **Approval routing**: POs > NT$100K require manager approval; > NT$500K require director approval

**LLM tools (3):** `create_purchase_order`, `query_suppliers`, `query_purchase_orders`

**Constraint rules (4):** PO_OVER_RECEIPT (BLOCK), PO_NEEDS_DIRECTOR/MANAGER (BLOCK/WARN), SUPPLIER_LOCKED/LOW_SCORE (BLOCK/WARN), SUPPLIER_LATE (WARN)

#### 3.4.3 BOM Module (PP)

Manages product structure and material requirement planning.

**Data model (2 tables):** `products` (id, name, type), `bom_items` (id, parent_product_id, component_part_no, quantity)

**Core operations:**
- **Multi-level BOM**: Recursive parent-child structure with quantity-per-unit specification
- **BOM explosion**: Recursive expansion of product structure to yield complete raw material requirements
- **Shortage detection**: Compares exploded BOM requirements against on-hand inventory, returns shortage list with quantities

**LLM tools (3):** `query_bom`, `bom_explode`, `check_stock_shortage`

**Constraint rules (2):** BOM_CIRCULAR (BLOCK), BOM_ACTIVE_EDIT (WARN)

#### 3.4.4 Dispatch Module (PP)

Manages production execution, work center allocation, and dynamic rescheduling.

**Data model (4 tables):** `work_centers` (id, name, status, alternate_group), `production_orders` (id, product_id, quantity, status, priority), `operations` (id, wo_id, sequence, work_center_id, status, start_time, end_time), `dispatch_logs` (id, action, details, timestamp)

**Core operations:**
- **Work center management**: Machines/stations with status (idle/running/down/maintenance) and alternate group assignment for route-change rescheduling
- **Production order lifecycle**: draft → released → dispatched → in_progress → completed → closed
- **Operation sequencing**: Each order has ordered operations assigned to work centers with start/end times
- **Three rescheduling strategies**:
  - *Right-shift*: Shift all unfinished operations on affected work center forward by delay duration; respects capacity constraints
  - *Route change*: Reassign operations to alternate work center in same alternate_group; requires non-empty group and target capacity
  - *Expedite*: Set priority to 1 and re-prioritize dispatch queue; warns if existing orders face significant delay

**LLM tools (10):** `create_work_center`, `create_production_order`, `release_order`, `dispatch_order`, `query_work_orders`, `add_operation`, `right_shift_reschedule`, `route_change_reschedule`, `expedite_order`, `set_work_center_status`

**Constraint rules (3):** WO_NOT_READY (BLOCK), WO_CLOSE_VARIANCE (WARN), WO_RUSH_CASCADE (WARN)

#### 3.4.5 Quality Module (QM)

Implements a closed-loop quality management system linking inspection, non-conformance tracking, and corrective/preventive action.

**Data model (4 tables):** `inspection_orders` (id, reference, status, inspector), `inspection_results` (id, inspection_id, values, pass), `non_conformances` (id, defect_code, severity, root_cause, status), `capa_records` (id, nc_id, action_plan, deadline, status)

**Quality workflow state machine:**
1. Goods received → Auto-create inspection_order (status: pending)
2. Inspector records results → Pass → auto-close; Fail → auto-create NC
3. NC created → Lock associated stock lot (prevents use of non-conforming materials)
4. CAPA issued → Engineering investigates root cause, implements corrective/preventive action
5. CAPA verified → NC closed, stock unlocked or scrapped
6. Recurring defects: Same defect ≥3× in 3 months triggers mandatory CAPA; ≥5× triggers Material Review Board (MRB)

**LLM tools (4):** `query_inspections`, `create_inspection`, `query_ncs`, `create_nc`

**Constraint rules (3):** QC_PENDING/REJECTED (BLOCK), NC_LOT_BLOCKED (BLOCK), QC_RECURRING_MRB (WARN)

#### 3.4.6 Accounting Module (FI)

Provides double-entry bookkeeping, accounts receivable/payable aging, and period-end closing.

**Data model (5 tables):** `accounts` (code, name, type, balance), `journal_entries` (entry_no, description, date, posted), `journal_lines` (account_id, debit, credit, reference), `accounts_receivable` (invoice_no, amount, paid, due_date, status), `month_end_closes` (period, status)

**Core operations:**
- **Chart of accounts**: Hierarchical account structure (asset/liability/equity/revenue/expense) with running balances
- **Journal posting**: Double-entry enforced at database level (sum(debits) = sum(credits)); closed periods reject all postings
- **AR aging**: Dynamic computation (current, 1–30d overdue, 31–60d overdue, 60d+ overdue); >60d blocks further shipments
- **Month-end close**: Sequential closure process with posting block on closed periods

**LLM tools (4):** `query_accounts`, `query_ar`, `check_ar_overdue`, `create_journal_entry`

**Constraint rules (6):** FI_MONTH_CLOSED (BLOCK), FI_DOUBLE_ENTRY (WARN), AR_BLOCK_SHIPMENT/OVERDUE_WARN (BLOCK/WARN), CASH_INSUFFICIENT/TIGHT (BLOCK/WARN), RUSH_NEGATIVE/LOW_MARGIN (BLOCK/WARN), CONTRACT_INACTIVE/EXPIRING (BLOCK/WARN)

#### 3.4.7 CRM Module (SD)

Manages the end-to-end customer lifecycle from lead acquisition through sales order fulfillment and after-action review.

**Data model (6 tables):** `customers` (id, name, contact), `leads` (id, customer, status), `opportunities` (id, customer, stage, value), `crm_events` (id, customer, type, description), `contracts` (id, customer, status, pricing), `contract_pricing` (part_no, unit_price, min_qty, discount_pct)

**Lead-to-contract pipeline:**
```
Lead (new → contacted → qualified → converted/lost)
  ↓ on converted
Customer
  ↓
Opportunity (qualification → needs_analysis → proposal → negotiation → closed_won/lost)
  ↓ on closed_won
Contract (draft → active → expired/terminated)
  ├── ContractPricing (per-part unit prices with quantity discounts)
  ↓
Sales Order (draft → confirmed → production → shipped → delivered/cancelled)
  ├── on confirm → auto-create Dispatch Work Order
  ├── on ship → auto-deduct inventory
  └── on deliver → update AR, trigger event
```

**Decision support loop:**
```
Decision Log (pending → in_review → completed)
  ↓
After Action Review (draft → published → implemented)
  ├── expected_result vs actual_result
  ├── root_cause / corrective_action / preventive_action
  └── lessons_learned → feeds back into system rules
```

**LLM tools (10):** `query_customers`, `query_sales_orders`, `create_customer_event`, `query_leads`, `query_opportunities`, `query_contracts`, `query_decisions`, `evaluate_rush_order`, `check_cash_position`, `generate_report`

**Constraint rules (2):** AR_BLOCK_SHIPMENT/OVERDUE_WARN (shared with FI), CONTRACT_INACTIVE/EXPIRING (shared with FI)

#### 3.4.8 Event Engine (Cross-cutting)

The Event Engine is described in detail in Section 3.6; we note here its role as the eighth module: a cross-cutting coordination layer that connects all seven operational modules through a publish-subscribe event bus.

---

### 3.5 LLM Orchestrator with Proactive Constraint Enforcement

The LLM Orchestrator is the central intelligence layer, responsible for intent classification, tool dispatch, and constraint-aware response generation.

#### 3.5.1 Intent Classification Pipeline

User natural language input undergoes a structured classification process:

1. **Input preprocessing**: The raw text is normalized (traditional Chinese normalization for Mandarin input, whitespace normalization).
2. **Few-shot classification**: The LLM receives a system prompt containing role context, a list of registered intents with examples, and the user's input. The role context conditions the classifier toward role-relevant intents: a warehouse keeper's "list stock" maps to `QUERY_INVENTORY`, while an accountant's "list stock" maps to `GET_INVENTORY_VALUE`.
3. **Structured output**: The classifier produces a JSON object:

```json
{
  "intent": "ISSUE_MATERIAL",
  "parameters": {
    "work_order": "WO-20260509-003",
    "material": "底板",
    "quantity": 100,
    "role": "warehouse_keeper"
  },
  "confidence": 0.92
}
```

4. **Tool injection**: Based on the classified intent, the relevant subset of the 37 tool definitions (as JSON Schema arrays) is injected into the LLM context. This selective injection keeps context windows manageable: accounting queries only see accounting tools, not production scheduling tools.
5. **Tool execution → response generation**: The LLM calls the appropriate tool function, the backend executes it against the database, and the LLM generates a natural language response incorporating the results.

#### 3.5.2 Tool Dispatch (37 Tools Across 8 Domains)

| Domain | Tools | Description |
|--------|-------|-------------|
| Inventory | 3 | query_inventory, inbound_material, outbound_material |
| BOM | 3 | query_bom, bom_explode, check_stock_shortage |
| Production | 10 | create_work_center, create_production_order, release_order, dispatch_order, query_work_orders, add_operation, right_shift_reschedule, route_change_reschedule, expedite_order, set_work_center_status |
| Purchase | 3 | create_purchase_order, query_suppliers, query_purchase_orders |
| Quality | 4 | query_inspections, create_inspection, query_ncs, create_nc |
| Accounting | 4 | query_accounts, query_ar, check_ar_overdue, create_journal_entry |
| CRM | 10 | query_customers, query_sales_orders, create_customer_event, query_leads, query_opportunities, query_contracts, query_decisions, evaluate_rush_order, check_cash_position, generate_report |
| **Total** | **37** | |

Each tool is defined as a JSON Schema function-calling specification with typed parameters, required fields, and descriptive comments. Tool definitions are dynamically composed: the orchestrator injects only tools relevant to the classified intent, with role-based filtering (a warehouse keeper cannot call `create_journal_entry`).

#### 3.5.3 Proactive Constraint Engine (23 Rules)

Before executing any write operation, the orchestrator invokes the constraint engine via an `enforce()` function that checks the proposed operation against 23 business rules organized by module. Each rule returns a `ConstraintVerdict` with pass/fail status, severity (BLOCK or WARN), and structured resolution suggestions.

**Enforcement severity:**

| Type | Behavior | Count |
|------|----------|-------|
| **BLOCK** | Operation rejected with structured error message | 11 |
| **WARN** | Operation proceeds; warning surfaces in response | 10 |
| **BLOCK/WARN** | Conditional — severity depends on threshold | 2 |

**Module-wise rule summary:**

| Module | Rules | BLOCK | WARN | Conditional |
|--------|-------|-------|------|-------------|
| Inventory (MM) | 5 | 2 | 2 | 1 |
| Purchase (PP) | 4 | 1 | 1 | 2 |
| BOM (PP) | 2 | 1 | 1 | 0 |
| Dispatch (PP) | 3 | 1 | 2 | 0 |
| Quality (QM) | 3 | 2 | 1 | 0 |
| Finance (FI) | 6 | 2 | 2 | 2 |
| **Total** | **23** | **9** | **9** | **5** |

**Example enforcement: inventory outbound:**

```
Input: Issue 100 units of part "底板" to work order WO-20260509-003
Constraint checks:
  ✓ INV_NEGATIVE_STOCK: on-hand = 120, request = 100 → PASS
  ✓ INV_EXPIRED: lot F20250401 expires 2026-06-01 → PASS (not expired)
  ⚠ INV_BELOW_SAFETY: after issue, on-hand = 20, safety = 30 → WARN
     Safety stock 30, remaining 20 (33% below). Consider reorder.
Result: Operation proceeds with warning. Response includes resolution suggestion.
```

**When constraint violations occur, the LLM surfaces structured responses:**

```
⚠️ 出庫超過庫存量：要求 100，可用 80
   建議：① 出庫 80，不足部分先開採購單
         ② 檢查是否有在途訂單預計本週入庫
```

This transforms the LLM from a passive query interface into an **active decision support partner**: the system not only prevents invalid operations but suggests alternatives and quantifies tradeoffs.

---

### 3.6 Event Engine

A key design requirement derived from factory operations is that every decision affects multiple roles. When a warehouse keeper receives material, the purchasing agent needs confirmation (delivery complete), the quality inspector needs to act (inspection pending), and the accountant needs to record (inventory asset increase). The Event Engine coordinates these cross-functional effects through a publish-subscribe architecture.

#### 3.6.1 Event Model

```python
@dataclass
class DomainEvent:
    event_type: str              # e.g., "material.received"
    category: EventCategory      # MATERIAL | PRODUCTION | PURCHASE | QUALITY | FINANCE | SYSTEM
    severity: EventSeverity      # INFO | WARNING | CRITICAL
    actor_role: str              # who triggered the event
    aggregate_id: str            # referenced object (PO-001, WO-001)
    aggregate_type: str          # "purchase_order", "work_order"
    payload: dict                # business data
    metadata: dict               # routing instructions
```

#### 3.6.2 Twelve Event Types

| Event Type | Category | Default Severity | Description |
|-----------|----------|-----------------|-------------|
| material.received | MATERIAL | INFO | Goods received against PO |
| material.issued | MATERIAL | INFO/WARNING | Material issued to production |
| purchase_order.created | PURCHASE | INFO | New purchase order created |
| work_order.released | PRODUCTION | INFO | Work order released to production |
| non_conformance.created | QUALITY | CRITICAL/WARNING | Non-conformance report created |
| payment.due | FINANCE | WARNING | Payment approaching due date |
| receivable.overdue | FINANCE | CRITICAL/WARNING | Accounts receivable becomes overdue |
| cash.projected | FINANCE | INFO/WARNING | Cash position projection generated |
| cash.alert_low | FINANCE | CRITICAL | Cash balance below threshold |
| rush_order.assessed | PRODUCTION | INFO/WARNING | Rush order evaluation completed |
| decision.made | SYSTEM | INFO | Strategic decision recorded |
| decision.aar_completed | SYSTEM | INFO | After-action review completed |

#### 3.6.3 Role Routing Matrix

Each event type has a predefined subscription list that operationalizes the cross-functional visibility requirement:

| Event Type | Notified Roles | Rationale |
|-----------|---------------|-----------|
| material.received | Purchasing, Quality, Accounting | Confirm delivery, trigger inspection, record asset |
| material.issued | Warehouse, Accounting | Decrement stock, record WIP cost |
| purchase_order.created | Accounting, Warehouse | Reserve budget, prepare for receipt |
| work_order.released | Warehouse | Reserve materials for production |
| non_conformance.created | Production, Director | Initiate rework, escalate quality issue |
| payment.due | Director, Purchasing | Approve payment, coordinate with supplier |
| receivable.overdue | Director | Escalate collection |
| stock.below_safety | Purchasing, Production, Director | Trigger replenishment, adjust schedule |
| capacity.overloaded | Production, Director | Reschedule or add capacity |
| decision.made | All roles (summary) | Organizational transparency |
| cash.alert_low | Director, Accountant | Immediate liquidity action |
| rush_order.assessed | Production, Sales, Director | Coordinate rush execution |

#### 3.6.4 Notification Channels

Events are delivered through three channels:

1. **In-app notification panel**: Real-time panel with read/unread tracking, severity color coding (INFO=blue, WARNING=yellow, CRITICAL=red), and clickable links to referenced objects (PO-001 opens the PO detail view).
2. **War Room event stream**: Live scrolling feed at the bottom of the multi-screen War Room display, showing the 30 most recent events with animated transition.
3. **Telegram push**: Outbound push notifications to configured chat groups (via a Telegram bot gateway), enabling mobile awareness for managers who are not at their workstation.

---

### 3.7 War Room Display

The War Room is a full-screen HTML dashboard designed for multi-monitor factory floor deployment, serving as the system's real-time visualization layer.

**Design principles:**
- **Dark theme with grid background**: Optimized for continuous display in low-light factory environments
- **SVG-based flow diagram**: Six operational stages arranged left-to-right (Supplier → Purchase → Inventory → Dispatch → Quality → Accounting) with animated material flow (green particles) and finance flow (yellow particles)
- **Auto-simulation**: Every 25 seconds, the display generates a random business event (PO created, goods received, NC created) to demonstrate event flow even when no live operations are occurring
- **Live count tiles**: Each stage shows real-time counts (active POs, inventory items, work orders, pending inspections, open AR invoices) refreshed every 15 seconds from 7 API endpoints
- **Event stream**: Bottom panel shows a scrolling log of the 30 most recent events with severity indicators and timestamps
- **Event flow animation**: New events appear as floating cards that animate along SVG flow paths between stages, with the target stage glowing briefly on arrival

The display is accessible at `/war-room.html` via the Vite dev server and supports full-screen (F11) operation on any connected monitor.

---

### 3.8 Implementation Details

The system is implemented as a full-stack web application with the following technology stack:

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Frontend | React + TypeScript | 18.x | Role-adaptive dashboard rendering |
| Build | Vite | Latest | Fast development and production builds |
| Styling | Tailwind CSS | 3.x | Responsive, maintainable UI |
| Backend | Python FastAPI | 0.110+ | REST API, service layer, event engine |
| ORM | SQLAlchemy | 2.0+ | Database abstraction and migrations |
| Database (dev) | SQLite | 3.x | Development and testing |
| Database (prod) | PostgreSQL + pgvector | 16.x | Production with vector search support |
| LLM providers | Anthropic, OpenAI, DeepSeek, OpenRouter, Ollama | — | Multi-provider adapter |
| Auth | Session-based | Phase 1 | Role-based authentication |

**Key implementation patterns:**

- **Type hints on all Python functions**: Enables static analysis and IDE support for the 83-endpoint API surface
- **Pydantic schemas for all API inputs/outputs**: Runtime validation of all request/response data
- **One agent per domain**: Each domain module has a dedicated agent class (`InventoryAgent`, `PurchaseAgent`, etc.) with its own tool definitions
- **Tool definitions as JSON Schema**: Tools are defined in Python and serialized to JSON Schema for LLM function calling
- **Constraint enforcement middleware**: Every write operation passes through a `ConstraintBlocked → 422` middleware that intercepts constraint violations before reaching the database
- **Alembic for schema migrations**: All 34 tables version-controlled through migration scripts
- **MAX_TOOL_ROUNDS=5**: Configurable limit (5 for cloud models, 8–10 for local models) to prevent infinite tool call loops

**Configuration**: The system uses a `.env` file for provider selection (`LLM_PROVIDER`, `LLM_MODEL`), API keys, and tool round limits. Backend auto-reloads on `.env` changes (uvicorn `--reload`), enabling rapid experimentation across providers.

**Open-source philosophy**: The system is designed for reproducibility and community adoption. All source code, evaluation data, and documentation are available at the repository (URL to be published upon acceptance).

---


## 4. Experimental Evaluation

### 4.1 Experimental Design

We present a preliminary evaluation of the system using 30 natural language test queries across seven categories (Inventory, Purchase, BOM, Dispatch, Quality, Accounting, Cross-module). Each query was sent to the chat API endpoint (`POST /api/chat`) with the DeepSeek provider (model: `deepseek-chat`; max tool rounds: 5). The evaluation measured three dimensions:

1. **Functional accuracy**: Whether the LLM's tool call sequence matched the expected intent and whether the response contained the correct business data as validated against the database state
2. **Response time**: End-to-end latency from query submission to response delivery, measured in seconds
3. **Error type classification**: For failed cases, we classified the failure into one of: tool selection error, parameter extraction error, multi-turn exhaustion, or correct-but-incomplete

Test queries were designed to represent real factory floor scenarios drawn from the three supported factory types (MTO, MTS, ETO):

| Domain | Sample Query | Equivalent SAP T-Code |
|--------|-------------|----------------------|
| Inventory | "M6x20螺絲還有多少庫存？" (How much M6x20 screw inventory?) | MMBE |
| Purchase | "開一張採購單給大明螺絲，買1000個M8x30" (Create PO for 1000 M8x30 from Daming Screw) | ME21N |
| BOM | "展開產品BLK-001的BOM" (Explode BOM for product BLK-001) | CS12 |
| Dispatch | "釋出工單WO-20260506-001" (Release work order WO-20260506-001) | CO02 |
| Quality | "建立NC，料號M8x30，尺寸超差0.5mm" (Create NC for part M8x30, dimension deviation 0.5mm) | QA32 |
| Accounting | "查詢AR逾期狀況" (Query AR overdue status) | FBL5N |
| Cross-module | "M8x30庫存不足，幫我開採購單補足到安全庫存" (M8x30 stock insufficient, create PO to replenish to safety stock level) | Multi-step |

The evaluation was conducted against a fixed test database with known state, enabling deterministic pass/fail determination. Each test was executed twice to verify consistency.

---

### 4.2 Results

#### 4.2.1 Primary Results (DeepSeek Cloud)

| Category | Cases | Passed | Accuracy | Avg Time (s) |
|----------|:-----:|:------:|:--------:|:------------:|
| Inventory | 5 | 5 | 100% | 8.2 |
| Purchase | 5 | 5 | 100% | 7.6 |
| BOM | 4 | 3 | 75% | 13.1 |
| Dispatch | 5 | 5 | 100% | 7.2 |
| Quality | 4 | 4 | 100% | 7.9 |
| Accounting | 5 | 5 | 100% | 8.7 |
| Cross-module | 2 | 1 | 50% | 9.7 |
| **Total** | **30** | **28** | **93.3%** | **8.6** |

**Interpretation.** The overall accuracy of 93.3% (28/30) in this preliminary evaluation suggests that LLM function calling is a viable paradigm for routine ERP operations across most domains. Five of seven categories yielded perfect accuracy, indicating that single-domain, single-step operational queries are well within current LLM capabilities when backed by well-structured tool definitions and constraint enforcement.

#### 4.2.2 Category-Level Analysis

**Strong performers (100%: Inventory, Purchase, Dispatch, Quality, Accounting):** These five categories share a common characteristic: they involve single-step tool calls with unambiguous parameter mapping. "Release work order" maps directly to `release_order(wo_id)`. "Create NC" maps to `create_nc(part_no, defect, severity)`. The tool definitions for these operations have few optional parameters and clear natural language keywords, reducing ambiguity in both classification and parameter extraction.

**Good performer (75%: BOM):** The single failure in BOM involved the `check_stock_shortage` tool. The LLM consumed three tool rounds on auxiliary validation (querying inventory, verifying product existence) before calling the primary explosion tool, exhausting the 5-round limit. This is a tool-calling efficiency issue rather than a comprehension failure; raising the round limit to 8 resolved the query in a separate test.

**Weak performer (50%: Cross-module):** Cross-module workflows that require composing multiple tool calls across domains, such as "check shortage → if insufficient, create PO", remain challenging. The LLM correctly called `check_stock_shortage` but returned the shortage report verbatim rather than composing the follow-up PO creation. This pattern aligns with known limitations in LLM tool composition (Yao et al., 2023) and suggests that a planner-agent architecture would improve multi-step performance.

#### 4.2.3 Response Time Analysis

Average response time was 8.6 seconds per query, dominated by LLM inference latency.

- **Fastest category**: Dispatch (7.2s), single-tool operations with deterministic parameters
- **Slowest category**: BOM (13.1s), multi-level database recursion combined with LLM processing and tool-calling overhead
- **Single-turn queries** (no tool calls, e.g., "show my KPIs"): ~3 seconds
- **Multi-turn tool workflows**: 10–15 seconds, proportional to number of tool calls

The average of 8.6 seconds compares favorably to traditional ERP operation times, which range from 30–120 seconds for experienced users navigating menu hierarchies and 2–5 minutes for new users. This suggests a meaningful efficiency improvement for routine operations, though the comparison is preliminary and does not account for task complexity differences.

---

### 4.3 Multi-Provider Comparison

To assess provider sensitivity, we repeated the 30-test evaluation with **Gemma4 (8B, local CPU via Ollama)**, a smaller, locally-hosted model representing the data-sovereignty and cost-efficiency end of the spectrum.

| Category | DeepSeek Accuracy | Gemma4 Accuracy | Delta |
|----------|:-----------------:|:---------------:|:-----:|
| Inventory | 100% | 100% | 0% |
| Purchase | 100% | 100% | 0% |
| BOM | 75% | 100% | +25% |
| Dispatch | 100% | 100% | 0% |
| Quality | 100% | 100% | 0% |
| Accounting | 100% | 40% | −60% |
| Cross-module | 50% | 0% | −50% |
| **Total** | **93.3%** | **83.3%** | **−10.0%** |

**Aggregate metrics:**

| Metric | DeepSeek | Gemma4 (8B CPU) |
|--------|:--------:|:--------------:|
| Overall accuracy | 93.3% | 83.3% |
| Avg response time | 8.6s | 11.4s |
| Cost per query | ~$0.002 | Free |
| Data sovereignty | External API | Fully local |
| Weakest module | Cross-module (50%) | Accounting (40%) |

**Interpretation.** The comparison yields three preliminary findings:

1. **Simple domains are model-agnostic.** Inventory, Purchase, Dispatch, and Quality yielded 100% accuracy with both providers, suggesting that single-step operational queries are robust to model size when tool definitions are clearly specified. This is encouraging for local deployment scenarios where data sovereignty is prioritized.

2. **Complex domains reveal model capability gaps.** Accounting queries (40% for Gemma4 vs. 100% for DeepSeek) and cross-module workflows (0% vs. 50%) show significant degradation with the smaller model. The 8B parameter model struggled with multi-step reasoning, parameter composition (matching invoice details to journal entry fields), and tool selection when multiple similar tools were available.

3. **Latency tradeoffs.** Gemma4 (8B, CPU) averaged 11.4s vs. DeepSeek's 8.6s, with accounting queries taking 39s on average, including timeouts on three of five cases. Local deployment on GPU hardware would likely narrow this gap.

---

### 4.4 Failure Analysis

We analyze the 2 DeepSeek failures and 5 Gemma4 failures across both evaluations.

#### 4.4.1 DeepSeek Failure Cases

**Failure 1: BOM shortage check (accuracy cost: 25% of BOM category).**
- **Query**: "檢查BLK-001的物料短缺狀況" (Check material shortage for BLK-001)
- **Expected**: Call `bom_explode(product_id)` → then `check_stock_shortage(parts_list)` → return shortage report
- **Observed**: LLM called `query_inventory` three times with different filters, then `query_bom`, then attempted `check_stock_shortage`, reached 5-round limit before completion
- **Root cause**: Tool selection ambiguity: the LLM attempted manual verification steps instead of trusting the dedicated shortage tool. This is a **round-limit exhaustion** failure rather than a comprehension failure; raising MAX_TOOL_ROUNDS to 8 yields correct behavior.

**Failure 2: Cross-module shortage→PO (accuracy cost: 50% of Cross-module category).**
- **Query**: "M8x30庫存不足，幫我開採購單補足到安全庫存" (M8x30 stock insufficient, create PO to replenish to safety stock level)
- **Expected**: Call `check_stock_shortage` → if shortage identified, call `create_purchase_order`
- **Observed**: LLM called `check_stock_shortage` correctly, computed the shortage quantity, but returned the report as a natural language response without calling `create_purchase_order`
- **Root cause**: The LLM treated the analysis step as the terminal action. The query's implicit "and then create" was interpreted as "check and report." This is a **task decomposition** failure: the LLM identified the problem but did not autonomously execute the follow-up. A multi-agent architecture with a planner that decomposes "check and fix" into sequential sub-tasks would likely resolve this.

#### 4.4.2 Gemma4 Failure Cases

Gemma4 failed on 5 of 30 cases, all in Accounting (3) and Cross-module (2). The accounting failures shared a common pattern: the 8B model struggled with financial domain terminology and parameter composition. In `create_journal_entry` calls, it omitted required fields (debit account code, credit amount) or mismatched account types. The cross-module failures mirrored DeepSeek's but were more severe: the model could not decompose the multi-step workflow at all, returning generic responses ("I cannot complete this multi-step operation").

#### 4.4.3 Cross-Provider Pattern

A consistent pattern across both providers is that **task composition** (chaining multiple tool calls to achieve a goal) is the primary failure mode. Single-tool queries yield near-perfect accuracy on the test queries regardless of model size, while multi-step workflows degrade proportionally with model capability. This suggests that the marginal value of larger models for ERP applications lies primarily in cross-module orchestration rather than single-domain execution.

---


---

## 5. Discussion and Limitations

The results presented in Section 4 suggest that LLM-based natural language interaction is a viable paradigm for routine ERP operations. The overall accuracy of 93.3% (DeepSeek) across 30 queries spanning eight domains indicates that single-domain, single-step operational queries can be handled reliably when backed by well-structured tool definitions, role-conditioned prompting, and proactive constraint enforcement. The multi-provider comparison further suggests that simple domains (Inventory, Purchase, Dispatch, Quality) are robust to model size, yielding 100% accuracy with both a cloud model and an 8B local model, which is encouraging for deployment scenarios where data sovereignty, latency, or cost considerations favor local inference.

This is a preliminary evaluation based on a limited test set. We identify **eight limitations** that bound the generalizability of our findings and inform future research directions:

**L1: Limited evaluation scale.** The 30-query test set, while covering all domains, is not exhaustive. Edge cases (boundary conditions, exception paths, concurrent operations, system recovery scenarios) are underrepresented. A larger evaluation with 200+ queries and stratified sampling per module and role would yield more robust accuracy estimates and identify module-specific failure modes that may not appear in a smaller sample.

**L2: Single database snapshot.** All evaluations were conducted against a fixed test database with known state and modest data volume. Real-world ERP databases are orders of magnitude larger (thousands of parts, hundreds of active orders, multi-year transaction histories), which may affect LLM performance through increased ambiguity in entity resolution, parameter extraction, and context management.

**L3: Limited provider comparison.** The multi-provider comparison includes only two models (DeepSeek Cloud, a proprietary API-based model, and Gemma4 8B, a locally-hosted open-weight model). A more comprehensive benchmark across models, including Claude (Sonnet, Opus), GPT (4o, 4.1), and additional local models (Llama 3, Qwen 2.5, Mistral), would establish the performance frontier and identify model-specific capability gaps.

**L4: Single-turn evaluation only.** All test queries were evaluated as isolated, single-turn interactions. Real ERP usage is inherently multi-turn: users refine queries, correct mistakes, and chain operations in conversational sequences. Multi-turn accuracy, context retention, and conversational coherence remain unassessed.

**L5: No user study.** Technical accuracy is a necessary but not sufficient condition for practical utility. User acceptance, task completion time, error rate, subjective satisfaction (System Usability Scale), and learning curve acceleration can only be measured through controlled human-subject experiments. A between-subjects study comparing LLM-ERP against a conventional ERP interface (e.g., Odoo) for standardized manufacturing tasks, with participants representing each of the seven archetype roles, would provide the behavioral evidence needed to complement the technical findings.

**L6: Hallucination risk.** All responses in our evaluation were verified against database state and found to contain valid data. However, LLMs are capable of numerical hallucination, reporting plausible but incorrect stock counts, financial figures, or schedule dates, even when tool calls succeed. The constraint engine catches structural violations (negative stock, double-entry imbalance, closed-period postings) but cannot detect factually incorrect values that pass structural validation. Retrieval-augmented generation (RAG) guardrails, confidence thresholding, and explicit verification prompts are needed as additional safeguards.

**L7: Single-factory type.** The system was designed around the workflows of discrete manufacturing (MTO, MTS, ETO). Applicability to process manufacturing (chemical, pharmaceutical, food), batch production, or service operations has not been assessed. The factory type configuration system supports adaptation to alternative manufacturing paradigms, but cross-type validation studies are needed.

**L8: Reproducibility constraints.** While the system is released as open-source to support independent replication, LLM API dependencies (DeepSeek, Anthropic, OpenAI, OpenRouter) introduce external sources of variability. Changes to model versions, API behavior, or pricing may affect both performance and reproducibility over time. Local model evaluation (Gemma4 via Ollama) partially mitigates this concern but introduces its own hardware-dependency issues.

---

## 6. Conclusion and Future Work

We have presented a preliminary LLM-powered ERP system for discrete manufacturing that operationalizes the thesis that role definition constitutes variable definition. By formalizing seven user archetypes as structured system variables that condition interface composition, LLM tool access, constraint scope, and event routing, the system provides a unified architecture for natural language interaction across the full manufacturing lifecycle. The system implements eight domain modules with 37 LLM-callable tools, 23 proactive business rule constraints, and an event engine with 12 event types and role-based routing across three notification channels.

A 30-query experimental evaluation across all domains yielded 93.3% functional accuracy with DeepSeek (8.6s average response time) and 83.3% with Gemma4 8B (11.4s). Results suggest that single-domain, single-step operational queries are robust to model size, yielding 100% accuracy with both providers on five of seven categories. Cross-module task composition, chaining multiple tool calls across domains, emerged as the primary failure mode, consistent with known LLM limitations in multi-step planning (Yao et al., 2023). The system is released as open-source to support independent replication and community-driven extension.

**Future work proceeds along five directions:**

1. **Larger-scale evaluation.** We plan to extend the evaluation to 200+ queries with stratified sampling per module and per role, including edge cases, exception paths, and concurrent operation scenarios. This larger corpus would support more granular accuracy estimates and module-specific failure profiling.

2. **Controlled user study.** A between-subjects experiment comparing LLM-ERP against a conventional ERP interface (e.g., Odoo) for standardized manufacturing tasks is planned, with 14–20 participants representing all seven archetype roles. Dependent measures would include task completion time, error rate, SUS score, and learning curve slope across repeated sessions.

3. **Multi-agent orchestration.** The single-LLM architecture with role-conditioned prompting could be extended to a multi-agent system in which each role is served by a dedicated agent instance with specialized tool sets, system prompts, and memory. This approach, inspired by AutoGen (Wu et al., 2023) and MetaGPT (Hong et al., 2024), may improve performance on cross-module workflows by enabling agent specialization and inter-agent delegation.

4. **RAG guardrails for hallucination mitigation.** Retrieval-augmented generation, grounding LLM responses in retrieved database records with explicit confidence scoring, could reduce hallucination risk in numerical outputs. We plan to implement RAG guardrails that verify tool call outputs against database state before response generation, flagging discrepancies above configured thresholds.

5. **Cross-factory validation.** The system's factory type configuration (MTO/MTS/ETO) should be validated across additional manufacturing contexts, including process manufacturing, batch production, and repair/overhaul operations. Cross-type validation studies would establish boundary conditions for the role-as-variable methodology and identify domain-specific adaptations.

In summary, this work provides preliminary evidence that LLM-based natural language interaction, when embedded within a structured role-based architecture with proactive constraint enforcement, can serve as a viable interaction layer for manufacturing ERP operations. The role-as-variable methodology offers a design framework that aligns system behavior with organizational role structure, potentially reducing training burden and enabling broader ERP adoption, particularly among SMEs. We release all artifacts as open-source to invite independent evaluation, replication, and extension by the research and practitioner communities.
