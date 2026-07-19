from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from app.models.accounting import AccountType, JournalEntryStatus
class AccountIn(BaseModel): code:str; name:str; account_type:AccountType
class AccountOut(AccountIn): id:UUID
class JournalLineIn(BaseModel): account_id:UUID; debit:float=Field(default=0,ge=0); credit:float=Field(default=0,ge=0)
class JournalIn(BaseModel): reference:Optional[str]=None; memo:Optional[str]=None; lines:List[JournalLineIn]
class JournalOut(JournalIn): id:UUID; status:JournalEntryStatus
