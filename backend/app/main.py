import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from app.config import settings
from app.database import init_db
from app.api import chat, inventory, purchase, bom, dispatch, events, accounting, quality, dashboard, reports, conversations, customers, sales_orders, crm_events, factory, leads, opportunities, contracts, decisions, organization, production, warehouse, compliance, security_mgmt, mps
from app.event_engine import init_event_engine, get_notifications, count_unread
from app.event_engine.role_config import Role
from app.auth_middleware import AuthMiddleware
from app.audit_middleware import AuditMiddleware
from app.response import add_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB tables + event engine. Shutdown: cleanup if needed."""
    await init_db()
    init_event_engine()
    yield


app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan)

# Global exception handlers — consistent error format
add_exception_handlers(app)

# Auth middleware — validates tokens on all API routes
app.add_middleware(AuthMiddleware)
# Audit middleware — logs all write operations
app.add_middleware(AuditMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(inventory.router, prefix="/api", tags=["inventory"])
app.include_router(purchase.router, prefix="/api", tags=["purchase"])
app.include_router(bom.router, prefix="/api", tags=["bom"])
app.include_router(dispatch.router, prefix="/api", tags=["dispatch"])
app.include_router(events.router, prefix="/api", tags=["events"])
app.include_router(accounting.router, prefix="/api", tags=["accounting"])
app.include_router(quality.router, prefix="/api", tags=["quality"])
app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
app.include_router(reports.router, prefix="/api", tags=["reports"])
app.include_router(conversations.router, prefix="/api", tags=["conversations"])
app.include_router(customers.router, prefix="/api", tags=["customers"])
app.include_router(sales_orders.router, prefix="/api", tags=["sales_orders"])
app.include_router(crm_events.router, prefix="/api", tags=["crm"])
app.include_router(factory.router, prefix="/api", tags=["factory"])
app.include_router(leads.router, prefix="/api", tags=["leads"])
app.include_router(opportunities.router, prefix="/api", tags=["opportunities"])
app.include_router(contracts.router, prefix="/api", tags=["contracts"])
app.include_router(decisions.router, prefix="/api", tags=["decisions"])
app.include_router(organization.router, prefix="/api", tags=["organization"])
app.include_router(production.router, prefix="/api", tags=["production"])
app.include_router(warehouse.router, prefix="/api", tags=["warehouse"])
app.include_router(compliance.router, prefix="/api", tags=["compliance"])
app.include_router(security_mgmt.router, prefix="/api", tags=["security"])
app.include_router(mps.router, prefix="/api", tags=["mps"])


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}

@app.get("/war-room", response_class=HTMLResponse)
@app.get("/war-room.html", response_class=HTMLResponse)
async def war_room():
    path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "public", "war-room.html")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("<h1>war-room.html not found</h1>", status_code=404)

@app.get("/war-room-en", response_class=HTMLResponse)
async def war_room_en():
    path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "public", "war-room-en.html")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("<h1>war-room-en.html not found</h1>", status_code=404)
