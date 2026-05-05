# LLM-ERP — LLM-Powered Enterprise Resource Planning

> Talk to your ERP. Let AI handle the rest.

## Stack
- Backend: Python FastAPI + SQLAlchemy + PostgreSQL + pgvector
- Frontend: React + TypeScript + Tailwind CSS + Vite
- LLM: Claude API via function calling
- Auth: Session-based (Phase 1)

## Architecture
```
User Chat → LLM Orchestrator → Intent Classification → Domain Agent → Tool Call → DB
```

## Key Conventions
- Type hints on ALL Python functions
- Pydantic schemas for ALL API inputs/outputs
- One agent per domain in `backend/app/agents/`
- Tool definitions (JSON Schema) in `backend/app/tools/`
- Tests in `backend/tests/` mirror the app structure
- Alembic for all DB migrations

## How to Run
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# DB
docker compose up -d postgres
```

## MVP Modules (Phase 1)
1. **Chat Interface** — Natural language ERP interaction
2. **Inventory** — Query stock, inbound/outbound
3. **Purchase** — Create and track purchase orders
4. **BOM** — Bill of Materials management

## Project Structure
```
llm-erp/
├── backend/           # FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── api/       # REST endpoints
│   │   ├── agents/    # LLM agents per domain
│   │   ├── services/  # Business logic
│   │   ├── models/    # SQLAlchemy models
│   │   ├── schemas/   # Pydantic schemas
│   │   └── tools/     # LLM tool definitions
│   └── tests/
├── frontend/          # React + Vite + Tailwind
└── docker-compose.yml
```

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
