"""Conversation history API — save, list, load, delete past chats."""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.conversation import ConversationLog

router = APIRouter()


# ─── Schemas ───────────────────────────────────────────────────────

class SaveMessagesRequest(BaseModel):
    session_id: str
    messages: list[dict]  # [{"role": "user"/"assistant", "content": "...", "intent": "..."}]


class SessionSummary(BaseModel):
    session_id: str
    title: str
    message_count: int
    last_message: Optional[str] = None
    updated_at: Optional[str] = None


class ConversationResponse(BaseModel):
    session_id: str
    messages: list[dict]


# ─── Endpoints ─────────────────────────────────────────────────────

@router.post("/conversations/save")
async def save_messages(req: SaveMessagesRequest, db: AsyncSession = Depends(get_db)):
    """Save a batch of messages for a session."""
    now = datetime.utcnow()
    rows = []
    for msg in req.messages:
        rows.append(ConversationLog(
            session_id=req.session_id,
            role=msg.get("role", "user"),
            content=msg.get("content", ""),
            intent=msg.get("intent"),
            created_at=now,
        ))
    db.add_all(rows)
    await db.commit()
    return {"saved": len(rows), "session_id": req.session_id}


@router.get("/conversations/sessions", response_model=list[SessionSummary])
async def list_sessions(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List all conversation sessions with preview info."""
    # Get the latest message per session using max ID approach
    latest_subq = (
        select(
            ConversationLog.session_id,
            func.max(ConversationLog.id).label("max_id"),
            func.count(ConversationLog.id).label("msg_count"),
        )
        .group_by(ConversationLog.session_id)
        .order_by(func.max(ConversationLog.id).desc())
        .limit(limit)
        .subquery()
    )

    # Join to get the actual content of the latest message
    result = await db.execute(
        select(
            ConversationLog.session_id,
            ConversationLog.content,
            ConversationLog.created_at,
            latest_subq.c.msg_count,
        )
        .join(latest_subq, ConversationLog.id == latest_subq.c.max_id)
        .order_by(latest_subq.c.max_id.desc())
    )
    rows = result.all()

    # Build summaries with titles from first user message
    sessions = []
    for row in rows:
        # Get first user message as title
        title_q = await db.execute(
            select(ConversationLog.content)
            .where(
                ConversationLog.session_id == row.session_id,
                ConversationLog.role == "user",
            )
            .order_by(ConversationLog.id.asc())
            .limit(1)
        )
        first_msg = title_q.scalar()
        title = first_msg[:80] + "…" if first_msg and len(first_msg) > 80 else (first_msg or "（空對話）")

        sessions.append(SessionSummary(
            session_id=row.session_id,
            title=title,
            message_count=row.msg_count or 0,
            last_message=row.content[:120] + "…" if row.content and len(row.content) > 120 else row.content,
            updated_at=row.created_at.isoformat() if row.created_at else None,
        ))

    return sessions


@router.get("/conversations/{session_id}", response_model=ConversationResponse)
async def get_conversation(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get full conversation for a session."""
    result = await db.execute(
        select(ConversationLog)
        .where(ConversationLog.session_id == session_id)
        .order_by(ConversationLog.id.asc())
    )
    rows = result.scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail="Session not found")

    return ConversationResponse(
        session_id=session_id,
        messages=[r.to_dict() for r in rows],
    )


@router.delete("/conversations/{session_id}")
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a conversation session."""
    await db.execute(
        delete(ConversationLog).where(ConversationLog.session_id == session_id)
    )
    await db.commit()
    return {"deleted": True, "session_id": session_id}


@router.post("/conversations/clear")
async def clear_all(db: AsyncSession = Depends(get_db)):
    """Clear ALL conversation history."""
    await db.execute(delete(ConversationLog))
    await db.commit()
    return {"deleted": True}


# ─── CRM 整合：依客戶查詢對話 ─────────────────────────────────


@router.get("/conversations/by-customer/{customer_id}")
async def get_conversations_by_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
):
    """查詢指定客戶的所有對話記錄，按 session 分組、依時間降冪排序。"""
    # 查詢該客戶的所有記錄
    result = await db.execute(
        select(ConversationLog)
        .where(ConversationLog.customer_id == customer_id)
        .order_by(ConversationLog.session_id, ConversationLog.id.asc())
    )
    rows = result.scalars().all()

    if not rows:
        return {"customer_id": customer_id, "sessions": []}

    # 按 session_id 分組
    sessions_map = {}
    for r in rows:
        sid = r.session_id
        if sid not in sessions_map:
            sessions_map[sid] = []
        sessions_map[sid].append(r)

    # 取每個 session 的第一則 user 訊息作為標題，並構建回傳格式
    sessions_list = []
    for sid, msgs in sessions_map.items():
        first_user = next(
            (m.content for m in msgs if m.role == "user"),
            "（空對話）",
        )
        title = first_user[:80] + "…" if len(first_user) > 80 else first_user
        sessions_list.append({
            "session_id": sid,
            "title": title,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat()
                    if m.created_at
                    else None,
                }
                for m in msgs
            ],
        })

    # 依最後一則訊息的時間降冪排序
    sessions_list.sort(
        key=lambda s: s["messages"][-1]["created_at"] or "",
        reverse=True,
    )

    return {
        "customer_id": customer_id,
        "sessions": sessions_list,
    }
