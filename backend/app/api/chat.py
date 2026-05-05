from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.agents.orchestrator import process_message

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    intent: Optional[str] = None
    session_id: Optional[str] = None


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """主要對話端點 — 接收自然語言，回傳 LLM 處理結果"""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="訊息不可為空")

    result = await process_message(req.message, req.session_id)

    return ChatResponse(
        reply=result.get("reply", "處理完成"),
        intent=result.get("intent"),
        session_id=req.session_id
    )
