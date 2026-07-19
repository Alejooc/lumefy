import enum, uuid
from sqlalchemy import Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

class AccountType(str, enum.Enum):
    ASSET='ASSET'; LIABILITY='LIABILITY'; EQUITY='EQUITY'; INCOME='INCOME'; EXPENSE='EXPENSE'
class JournalEntryStatus(str, enum.Enum):
    DRAFT='DRAFT'; POSTED='POSTED'; CANCELLED='CANCELLED'
class ChartAccount(BaseModel):
    __tablename__='chart_accounts'
    code: Mapped[str]=mapped_column(String, index=True)
    name: Mapped[str]=mapped_column(String)
    account_type: Mapped[AccountType]=mapped_column(Enum(AccountType))
class JournalEntry(BaseModel):
    __tablename__='journal_entries'
    reference: Mapped[str]=mapped_column(String, nullable=True)
    memo: Mapped[str]=mapped_column(String, nullable=True)
    status: Mapped[JournalEntryStatus]=mapped_column(Enum(JournalEntryStatus), default=JournalEntryStatus.DRAFT)
    lines=relationship('JournalEntryLine', cascade='all, delete-orphan')
class JournalEntryLine(BaseModel):
    __tablename__='journal_entry_lines'
    entry_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey('journal_entries.id'),index=True)
    account_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey('chart_accounts.id'))
    debit: Mapped[float]=mapped_column(Float,default=0)
    credit: Mapped[float]=mapped_column(Float,default=0)
    account=relationship('ChartAccount')
