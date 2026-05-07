# LLM-ERP — LLM-Powered Enterprise Resource Planning

> Talk to your ERP. Let AI handle the rest.

## Stack
- Backend: Python FastAPI + SQLAlchemy + SQLite (dev) / PostgreSQL (prod)
- Frontend: React + TypeScript + Tailwind CSS + Vite
- LLM: Multi-provider (Anthropic / OpenAI / DeepSeek / OpenRouter / Ollama) via function calling
- Event Engine: In-process pub/sub with 10 event types, role-based routing
- Auth: Session-based (Phase 1)

## Architecture
```
User Chat → LLM Orchestrator → Intent Classification → Domain Agent → Tool Call → DB / Event Bus
                                               ↓
                                      Constraint Checker (20 rules)
                                               ↓
                                      Response + Notifications (role-based)
```

## Key Conventions
- Type hints on ALL Python functions
- Pydantic schemas for ALL API inputs/outputs
- One agent per domain in `backend/app/agents/`
- Tool definitions (JSON Schema) in `backend/app/tools/`
- Tests in `backend/tests/` mirror the app structure
- Alembic for all DB migrations
- Every write operation passes through ConstraintBlocked → 422 middleware

## Config
- `.env`: LLM_PROVIDER, LLM_MODEL, API keys, MAX_TOOL_ROUNDS
- `MAX_TOOL_ROUNDS=5` for cloud models, `8-10` for local models

## MVP Modules (Phase 1)
1. **Chat Interface** — Natural language ERP interaction
2. **Inventory** — Query stock, inbound/outbound (4 constraints)
3. **Purchase** — Create and track purchase orders (4 constraints)
4. **BOM** — Bill of Materials management (4 constraints)
5. **Dispatch** — Production scheduling, right-shift/route-change reschedule (4 constraints)
6. **Quality** — Inspection orders, non-conformance tracking, CAPA (2 constraints)
7. **Accounting** — Journal entries, AR aging, month-end close (4 constraints)

## Project Structure
```
llm-erp/
├── backend/           # FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── api/       # REST endpoints (~42 routes)
│   │   ├── agents/    # LLM orchestrator + providers
│   │   ├── services/  # 7 domain services (business logic)
│   │   ├── models/    # SQLAlchemy models (22 tables)
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── tools/     # 27 LLM tool definitions
│   │   └── event_engine/ # pub/sub event bus
│   ├── tests/
│   └── .env
├── frontend/          # React + Vite + Tailwind + i18n
│   └── public/war-room.html
├── evaluation/        # 30-test benchmark + provider comparison
├── paper/             # EAAI manuscript + figures
└── docker-compose.yml

## LLM Agent Pattern
```python
# Each agent follows this pattern:
class InventoryAgent:
    tools = [...]  # JSON Schema tool definitions
    system_prompt = "You are an inventory management assistant..."
    
    def handle(self, intent: str, params: dict) -> str:
        # 1. LLM classifies user intent
        # 2. Extract parameters
        # 3. Call the matching tool function
        # 4. LLM generates natural language response
        ...
```

## Provider Switching
```bash
# To switch LLM provider:
# 1. Edit backend/.env: LLM_PROVIDER=deepseek|ollama|anthropic|openai|openrouter
# 2. Set LLM_MODEL (e.g. deepseek-chat, gemma4:e4b)
# 3. For local models, increase MAX_TOOL_ROUNDS=8
# Backend auto-reloads on .env change (uvicorn --reload)

# Run benchmark:
cd evaluation && python3 run_eval.py --verbose
```
