from fastapi import APIRouter, Depends
from app.api import chat, inventory, purchase, bom, dispatch, reports

router = APIRouter()

# Existing
router.include_router(chat.router, prefix="/api", tags=["chat"])
router.include_router(inventory.router, prefix="/api", tags=["inventory"])
router.include_router(purchase.router, prefix="/api", tags=["purchase"])
router.include_router(bom.router, prefix="/api", tags=["bom"])

# NEW: Dispatch
router.include_router(dispatch.router, prefix="/api", tags=["dispatch"])

# NEW: Reports
router.include_router(reports.router, prefix="/api", tags=["reports"])
