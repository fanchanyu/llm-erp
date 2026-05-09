# CRM Expansion + Factory Profiles — Implementation Plan

> Full implementation: Lead/Opportunity/Contract modules + Cash Flow Scheduling
> + Decision AAR + 3 Factory Types + Bilingual Docs

## Architecture Overview

```
New Modules:
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌───────────┐
│ Phase A  │  │ Phase B  │  │ Phase C  │  │  Phase D     │  │  Phase E  │
│ Lead     │  │ Contract │  │ Rush     │  │  Decision    │  │  Factory  │
│ Oppty    │  │ Pricing  │  │ Order    │  │  Log + AAR   │  │  UI Switch│
│ FactoryCfg│  │         │  │ CashFlow │  │              │  │           │
└──────────┘  └──────────┘  └──────────┘  └──────────────┘  └───────────┘
```

## File Map

### Phase A — Lead + Opportunity + FactoryConfig
- `backend/app/models/lead.py`
- `backend/app/models/opportunity.py`
- `backend/app/models/factory_config.py`
- `backend/app/services/lead_service.py`
- `backend/app/services/opportunity_service.py`
- `backend/app/services/factory_service.py`
- `backend/app/schemas/lead.py`
- `backend/app/schemas/opportunity.py`
- `backend/app/schemas/factory_config.py`
- `backend/app/api/leads.py`
- `backend/app/api/opportunities.py`
- `backend/app/api/factory.py`

### Phase B — Contract + ContractPricing
- `backend/app/models/contract.py`
- `backend/app/services/contract_service.py`
- `backend/app/schemas/contract.py`
- `backend/app/api/contracts.py`

### Phase C — Rush Order + Cash Flow Constraints
- `backend/app/services/rush_order_service.py`
- `backend/app/services/cashflow_service.py`
- (constraint rules added to existing constraint_checker.py)

### Phase D — Decision Audit + AAR
- `backend/app/models/decision_log.py`
- `backend/app/models/after_action_review.py`
- `backend/app/services/decision_service.py`
- `backend/app/schemas/decision.py`
- `backend/app/api/decisions.py`

### Shared Files (wired after subagents complete)
- `backend/app/main.py` — add router imports
- `backend/app/database.py` — add model bases to init_db()
- `backend/app/seed.py` — add seed data
- `backend/app/event_engine/events.py` — add new event types
- `backend/app/event_engine/constraint_checker.py` — add new constraints
- `backend/app/event_engine/role_config.py` — add new widgets, sales role enrichment
- `backend/app/tools/functions.py` — add LLM tools
- `backend/app/agents/orchestrator.py` — add tool registrations + intent routing
- `frontend/src/api/client.ts` — add API functions
- `frontend/src/App.tsx` — add widgets
- `README.md` + `README-zh.md` — target audience update
- `docs/operation-manual-zh.md` + `docs/operation-manual-en.md` — bilingual docs
