.PHONY: dev test seed db

# ─── Development (SQLite dev; PostgreSQL: make db) ──
dev:
	cd backend && uvicorn app.main:app --reload

frontend:
	cd frontend && npm run dev

db:
	docker compose up -d postgres

# ─── Data ──────────────────────────────────────
seed:
	cd backend && python -m app.seed

# ─── Testing ───────────────────────────────────
test:
	cd backend && python -m pytest tests/ -v

# ─── Database Migration ────────────────────────
migrate:
	cd backend && alembic upgrade head

# ─── Sync to Windows D: ───────────────────────
sync:
	rsync -a --delete ~/projects/llm-erp/ /mnt/d/Project/LLM_ERP/
