"""Contract API endpoints with real DB integration."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services import contract_service as svc
from app.schemas.contract import (
    ContractCreate,
    ContractUpdate,
    ContractResponse,
    ContractPricingResponse,
)

router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.get("", response_model=dict)
async def list_contracts(
    customer_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    contracts, total = await svc.list_contracts(db, customer_id, status, skip, limit)
    return {
        "contracts": [
            ContractResponse(
                id=c.id,
                contract_no=c.contract_no,
                customer_id=c.customer_id,
                type=c.type,
                start_date=c.start_date,
                end_date=c.end_date,
                pricing_json=c.pricing_json,
                payment_terms=c.payment_terms,
                status=c.status,
                auto_renew=c.auto_renew,
                notes=c.notes,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in contracts
        ],
        "total": total,
    }


@router.post("", response_model=ContractResponse, status_code=201)
async def create_contract(
    data: ContractCreate,
    db: AsyncSession = Depends(get_db),
):
    contract = await svc.create_contract(
        db,
        contract_no=data.contract_no,
        customer_id=data.customer_id,
        type=data.type,
        start_date=data.start_date,
        end_date=data.end_date,
        pricing_json=data.pricing_json,
        payment_terms=data.payment_terms,
        status=data.status,
        auto_renew=data.auto_renew,
        notes=data.notes,
    )
    return ContractResponse(
        id=contract.id,
        contract_no=contract.contract_no,
        customer_id=contract.customer_id,
        type=contract.type,
        start_date=contract.start_date,
        end_date=contract.end_date,
        pricing_json=contract.pricing_json,
        payment_terms=contract.payment_terms,
        status=contract.status,
        auto_renew=contract.auto_renew,
        notes=contract.notes,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
):
    contract = await svc.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(404, f"Contract not found: {contract_id}")
    return ContractResponse(
        id=contract.id,
        contract_no=contract.contract_no,
        customer_id=contract.customer_id,
        type=contract.type,
        start_date=contract.start_date,
        end_date=contract.end_date,
        pricing_json=contract.pricing_json,
        payment_terms=contract.payment_terms,
        status=contract.status,
        auto_renew=contract.auto_renew,
        notes=contract.notes,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )


@router.patch("/{contract_id}", response_model=ContractResponse)
async def update_contract(
    contract_id: int,
    data: ContractUpdate,
    db: AsyncSession = Depends(get_db),
):
    contract = await svc.update_contract(
        db,
        contract_id,
        contract_no=data.contract_no,
        customer_id=data.customer_id,
        type=data.type,
        start_date=data.start_date,
        end_date=data.end_date,
        pricing_json=data.pricing_json,
        payment_terms=data.payment_terms,
        status=data.status,
        auto_renew=data.auto_renew,
        notes=data.notes,
    )
    if not contract:
        raise HTTPException(404, f"Contract not found: {contract_id}")
    return ContractResponse(
        id=contract.id,
        contract_no=contract.contract_no,
        customer_id=contract.customer_id,
        type=contract.type,
        start_date=contract.start_date,
        end_date=contract.end_date,
        pricing_json=contract.pricing_json,
        payment_terms=contract.payment_terms,
        status=contract.status,
        auto_renew=contract.auto_renew,
        notes=contract.notes,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )


@router.delete("/{contract_id}", status_code=204)
async def delete_contract(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
):
    deleted = await svc.delete_contract(db, contract_id)
    if not deleted:
        raise HTTPException(404, f"Contract not found: {contract_id}")
    return None


@router.get("/{contract_id}/pricing/{part_no}", response_model=ContractPricingResponse)
async def get_contract_pricing(
    contract_id: int,
    part_no: str,
    db: AsyncSession = Depends(get_db),
):
    pricing = await svc.get_pricing(db, contract_id, part_no)
    if not pricing:
        raise HTTPException(
            404,
            f"No pricing found for part '{part_no}' in contract {contract_id}",
        )
    return ContractPricingResponse(**pricing)
