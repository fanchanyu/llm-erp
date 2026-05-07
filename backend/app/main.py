from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.api import chat, inventory, purchase, bom, dispatch, events, accounting, quality, dashboard, reports
from app.event_engine import init_event_engine, get_notifications, count_unread
from app.event_engine.role_config import Role


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB tables + event engine. Shutdown: cleanup if needed."""
    await init_db()
    init_event_engine()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}
