from fastapi import APIRouter, Depends
from app.api import chat, conversations, inventory, purchase, bom, dispatch, reports, crm_events

router = APIRouter()

# Existing
router.include_router(chat.router, prefix="/api", tags=["chat"])
router.include_router(conversations.router, prefix="/api", tags=["conversations"])
router.include_router(inventory.router, prefix="/api", tags=["inventory"])
router.include_router(purchase.router, prefix="/api", tags=["purchase"])
router.include_router(bom.router, prefix="/api", tags=["bom"])

# NEW: Dispatch
router.include_router(dispatch.router, prefix="/api", tags=["dispatch"])

# NEW: Reports
router.include_router(reports.router, prefix="/api", tags=["reports"])

# NEW: CRM Events
router.include_router(crm_events.router, prefix="/api", tags=["crm"])
