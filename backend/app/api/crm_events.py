"""
CRM Events API — 客戶互動事件記錄與查詢。

提供建立與查詢客戶互動事件（來電、來訪、備註、電郵、會議等）的 REST 端點。
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.crm_event import CrmEvent

router = APIRouter()


# ─── Schemas ───────────────────────────────────────────────────────


class CrmEventCreate(BaseModel):
    customer_id: int
    event_type: str  # call / visit / note / email / meeting
    description: str
    reference_type: Optional[str] = None
    reference_no: Optional[str] = None
    created_by: Optional[str] = None


class CrmEventResponse(BaseModel):
    id: int
    customer_id: int
    event_type: str
    description: str
    reference_type: Optional[str] = None
    reference_no: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[str] = None


# ─── Endpoints ─────────────────────────────────────────────────────


@router.post("/crm/events", response_model=CrmEventResponse)
async def create_crm_event(
    event: CrmEventCreate,
    db: AsyncSession = Depends(get_db),
):
    """建立一筆客戶互動事件（call / visit / note / email / meeting）。"""
    valid_types = {"call", "visit", "note", "email", "meeting"}
    if event.event_type not in valid_types:
        raise HTTPException(
            status_code=422,
            detail=f"無效的事件類型：{event.event_type}，有效值：{', '.join(sorted(valid_types))}",
        )

    now = datetime.utcnow()
    db_event = CrmEvent(
        customer_id=event.customer_id,
        event_type=event.event_type,
        description=event.description.strip(),
        reference_type=event.reference_type,
        reference_no=event.reference_no,
        created_by=event.created_by,
        created_at=now,
    )
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)

    return CrmEventResponse(
        id=db_event.id,
        customer_id=db_event.customer_id,
        event_type=db_event.event_type,
        description=db_event.description,
        reference_type=db_event.reference_type,
        reference_no=db_event.reference_no,
        created_by=db_event.created_by,
        created_at=db_event.created_at.isoformat() if db_event.created_at else None,
    )


@router.get("/crm/events/{customer_id}", response_model=list[CrmEventResponse])
async def get_crm_events(
    customer_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """查詢指定客戶的所有互動事件，依時間降冪排序。"""
    result = await db.execute(
        select(CrmEvent)
        .where(CrmEvent.customer_id == customer_id)
        .order_by(CrmEvent.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()

    return [
        CrmEventResponse(
            id=r.id,
            customer_id=r.customer_id,
            event_type=r.event_type,
            description=r.description,
            reference_type=r.reference_type,
            reference_no=r.reference_no,
            created_by=r.created_by,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in rows
    ]
