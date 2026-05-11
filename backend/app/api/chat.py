"""
Chat API — V1 Legacy + V2 Multi-Agent with RBAC integration.

- POST /chat: V1 legacy endpoint (monolithic orchestrator)
- POST /chat-v2: V2 multi-domain agent with RBAC
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.conversation import ConversationLog
from app.agents.orchestrator import process_message as v1_process
from app.agents_v2.engine import process_message as v2_process

router = APIRouter(tags=["chat"])


# ─── Schemas (shared by V1 and V2) ──────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    customer_id: Optional[int] = None


class ChatResponse(BaseModel):
    reply: str
    intent: Optional[str] = None
    session_id: Optional[str] = None
    customer_id: Optional[int] = None


class ChatV2Response(BaseModel):
    reply: str
    agent: str = "auto"
    session_id: str = ""


# ═══════════════════════════════════════════════════════════════════
# V1 LEGACY CHAT — existing mono-orchestrator
# ═══════════════════════════════════════════════════════════════════

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """V1 Legacy: mono-orchestrator with auto-save conversation history."""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="訊息不可為空")

    session_id = req.session_id or str(uuid.uuid4())[:8]
    now = datetime.utcnow()

    # Save user message
    db.add(ConversationLog(
        session_id=session_id, role="user",
        content=req.message.strip(),
        customer_id=req.customer_id, created_at=now,
    ))

    # Process via V1 orchestrator
    result = await v1_process(req.message.strip(), session_id)
    reply_text = result.get("reply", "處理完成")
    intent = result.get("intent")

    # Save assistant reply
    db.add(ConversationLog(
        session_id=session_id, role="assistant",
        content=reply_text, intent=intent,
        customer_id=req.customer_id, created_at=now,
    ))
    await db.commit()

    return ChatResponse(reply=reply_text, intent=intent,
                        session_id=session_id, customer_id=req.customer_id)


# ═══════════════════════════════════════════════════════════════════
# V2 MULTI-AGENT CHAT — domain agents with RBAC
# ═══════════════════════════════════════════════════════════════════

@router.post("/chat-v2", response_model=ChatV2Response)
async def chat_v2(
    req: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """V2 Multi-Agent Chat with RBAC — routes to the right domain agent."""
    user_info = getattr(request.state, "user", None)
    if not user_info or not user_info.get("is_authenticated"):
        raise HTTPException(401, "Not authenticated")

    user_context = {
        "user_id": user_info.get("user_id", ""),
        "employee_id": user_info.get("employee_id", ""),
        "name": user_info.get("name", ""),
        "roles": user_info.get("roles", []),
        "permissions": user_info.get("permissions", []),
        "department": user_info.get("department", ""),
    }

    # Save user message
    session_id = req.session_id or str(uuid.uuid4())[:8]
    db.add(ConversationLog(
        session_id=session_id, role="user",
        content=req.message.strip(),
        created_at=datetime.utcnow(),
    ))

    # Process through multi-agent engine
    reply = await v2_process(req.message, user_context, [])

    # Save assistant reply
    db.add(ConversationLog(
        session_id=session_id, role="assistant",
        content=reply, created_at=datetime.utcnow(),
    ))
    await db.commit()

    return ChatV2Response(reply=reply, agent="auto", session_id=session_id)
