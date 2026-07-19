from typing import List
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import func,select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.permissions import PermissionChecker
from app.models.user import User
from app.models.accounting import ChartAccount,JournalEntry,JournalEntryLine,JournalEntryStatus
from app.schemas import accounting as schemas
router=APIRouter()
@router.get('/accounts',response_model=List[schemas.AccountOut])
async def accounts(db:AsyncSession=Depends(get_db),current_user:User=Depends(PermissionChecker('manage_company'))): return (await db.execute(select(ChartAccount).where(ChartAccount.company_id==current_user.company_id,ChartAccount.is_active==True).order_by(ChartAccount.code))).scalars().all()
@router.post('/accounts',response_model=schemas.AccountOut)
async def create_account(data:schemas.AccountIn,db:AsyncSession=Depends(get_db),current_user:User=Depends(PermissionChecker('manage_company'))):
    if await db.scalar(select(ChartAccount.id).where(ChartAccount.company_id==current_user.company_id,ChartAccount.code==data.code)): raise HTTPException(409,'El código contable ya existe')
    item=ChartAccount(**data.model_dump(),company_id=current_user.company_id,created_by_id=current_user.id);db.add(item);await db.commit();await db.refresh(item);return item
@router.get('/journals',response_model=List[schemas.JournalOut])
async def journals(db:AsyncSession=Depends(get_db),current_user:User=Depends(PermissionChecker('manage_company'))): return (await db.execute(select(JournalEntry).options(selectinload(JournalEntry.lines)).where(JournalEntry.company_id==current_user.company_id).order_by(JournalEntry.created_at.desc()))).scalars().all()
@router.post('/journals',response_model=schemas.JournalOut)
async def create_journal(data:schemas.JournalIn,db:AsyncSession=Depends(get_db),current_user:User=Depends(PermissionChecker('manage_company'))):
    if len(data.lines)<2 or any((x.debit>0)==(x.credit>0) for x in data.lines): raise HTTPException(400,'Cada línea requiere solo débito o crédito y al menos dos líneas')
    if abs(sum(x.debit for x in data.lines)-sum(x.credit for x in data.lines))>.00001: raise HTTPException(400,'El asiento no está balanceado')
    ids={x.account_id for x in data.lines}; found=(await db.execute(select(ChartAccount.id).where(ChartAccount.id.in_(ids),ChartAccount.company_id==current_user.company_id))).scalars().all()
    if len(found)!=len(ids): raise HTTPException(404,'Cuenta contable no encontrada')
    entry=JournalEntry(reference=data.reference,memo=data.memo,status=JournalEntryStatus.POSTED,company_id=current_user.company_id,created_by_id=current_user.id);db.add(entry);await db.flush()
    for line in data.lines: db.add(JournalEntryLine(**line.model_dump(),entry_id=entry.id,company_id=current_user.company_id))
    await db.commit();await db.refresh(entry,attribute_names=['lines']);return entry
@router.get('/trial-balance')
async def trial_balance(db:AsyncSession=Depends(get_db),current_user:User=Depends(PermissionChecker('manage_company'))):
    rows=await db.execute(select(ChartAccount.code,ChartAccount.name,func.coalesce(func.sum(JournalEntryLine.debit),0),func.coalesce(func.sum(JournalEntryLine.credit),0)).outerjoin(JournalEntryLine,JournalEntryLine.account_id==ChartAccount.id).outerjoin(JournalEntry,JournalEntry.id==JournalEntryLine.entry_id).where(ChartAccount.company_id==current_user.company_id).group_by(ChartAccount.id,ChartAccount.code,ChartAccount.name).order_by(ChartAccount.code))
    return [{'code':c,'name':n,'debit':float(d),'credit':float(cr),'balance':float(d-cr)} for c,n,d,cr in rows.all()]
