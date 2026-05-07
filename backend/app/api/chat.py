"""Chat endpoint — processes natural language and auto-saves conversation history."""

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.conversation import ConversationLog
from app.agents.orchestrator import process_message

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    customer_id: Optional[int] = None  # 可選的客戶關聯 ID（CRM 整合用）


class ChatResponse(BaseModel):
    reply: str
    intent: Optional[str] = None
    session_id: Optional[str] = None
    customer_id: Optional[int] = None


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """主要對話端點 — 接收自然語言，回傳 LLM 處理結果，自動存檔對話記錄。"""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="訊息不可為空")

    # 自動產生 session_id（若無提供）
    session_id = req.session_id or str(uuid.uuid4())[:8]

    now = datetime.utcnow()

    # 1. 儲存使用者訊息（含 customer_id，若有提供）
    db.add(ConversationLog(
        session_id=session_id,
        role="user",
        content=req.message.strip(),
        customer_id=req.customer_id,
        created_at=now,
    ))

    # 2. 處理訊息
    result = await process_message(req.message.strip(), session_id)

    # 3. 儲存 AI 回覆（沿用同一 customer_id）
    reply_text = result.get("reply", "處理完成")
    intent = result.get("intent")
    db.add(ConversationLog(
        session_id=session_id,
        role="assistant",
        content=reply_text,
        intent=intent,
        customer_id=req.customer_id,
        created_at=now,
    ))

    await db.commit()

    return ChatResponse(
        reply=reply_text,
        intent=intent,
        session_id=session_id,
        customer_id=req.customer_id,
    )
