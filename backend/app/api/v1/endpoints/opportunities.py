from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.permissions import PermissionChecker
from app.models.client import Client
from app.models.opportunity import Opportunity, OpportunityStage
from app.models.user import User
from app.schemas import opportunity as schemas

router = APIRouter()


def _serialize(opportunity: Opportunity) -> dict:
    return {
        "id": opportunity.id,
        "name": opportunity.name,
        "client_id": opportunity.client_id,
        "owner_id": opportunity.owner_id,
        "stage": opportunity.stage,
        "expected_revenue": opportunity.expected_revenue,
        "probability": opportunity.probability,
        "expected_close_date": opportunity.expected_close_date,
        "contact_name": opportunity.contact_name,
        "contact_email": opportunity.contact_email,
        "contact_phone": opportunity.contact_phone,
        "notes": opportunity.notes,
        "lost_reason": opportunity.lost_reason,
        "client_name": opportunity.client.name if opportunity.client else None,
        "owner_name": opportunity.owner.full_name if opportunity.owner else None,
    }


async def _validate_relations(db: AsyncSession, payload: dict, company_id: UUID) -> None:
    client_id = payload.get("client_id")
    if client_id:
        client = await db.scalar(select(Client.id).where(Client.id == client_id, Client.company_id == company_id))
        if not client:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
    owner_id = payload.get("owner_id")
    if owner_id:
        owner = await db.scalar(select(User.id).where(User.id == owner_id, User.company_id == company_id, User.is_active == True))
        if not owner:
            raise HTTPException(status_code=404, detail="Responsable no encontrado")


@router.get("/", response_model=List[schemas.OpportunityOut])
async def read_opportunities(
    stage: OpportunityStage | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_clients")),
) -> Any:
    query = select(Opportunity).options(
        selectinload(Opportunity.client), selectinload(Opportunity.owner)
    ).where(Opportunity.company_id == current_user.company_id, Opportunity.is_active == True)
    if stage:
        query = query.where(Opportunity.stage == stage)
    result = await db.execute(query.order_by(Opportunity.created_at.desc()))
    return [_serialize(item) for item in result.scalars().all()]


@router.post("/", response_model=schemas.OpportunityOut)
async def create_opportunity(
    opportunity_in: schemas.OpportunityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_clients")),
) -> Any:
    payload = opportunity_in.model_dump()
    await _validate_relations(db, payload, current_user.company_id)
    opportunity = Opportunity(
        **payload,
        owner_id=payload.get("owner_id") or current_user.id,
        company_id=current_user.company_id,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(opportunity)
    await db.commit()
    result = await db.execute(select(Opportunity).options(selectinload(Opportunity.client), selectinload(Opportunity.owner)).where(Opportunity.id == opportunity.id))
    return _serialize(result.scalars().one())


@router.put("/{opportunity_id}", response_model=schemas.OpportunityOut)
async def update_opportunity(
    opportunity_id: UUID,
    opportunity_in: schemas.OpportunityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_clients")),
) -> Any:
    result = await db.execute(select(Opportunity).options(selectinload(Opportunity.client), selectinload(Opportunity.owner)).where(
        Opportunity.id == opportunity_id, Opportunity.company_id == current_user.company_id, Opportunity.is_active == True
    ))
    opportunity = result.scalars().first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Oportunidad no encontrada")
    payload = opportunity_in.model_dump(exclude_unset=True)
    await _validate_relations(db, payload, current_user.company_id)
    next_stage = payload.get("stage")
    if next_stage == OpportunityStage.LOST and not (payload.get("lost_reason") or opportunity.lost_reason):
        raise HTTPException(status_code=400, detail="Indica el motivo de pérdida")
    if next_stage == OpportunityStage.WON:
        payload["probability"] = 100.0
    for field, value in payload.items():
        setattr(opportunity, field, value)
    opportunity.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(opportunity)
    return _serialize(opportunity)
