from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import chat, inventory, purchase, bom

app = FastAPI(title=settings.app_name, version="0.1.0")

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


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}
