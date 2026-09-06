from sqlalchemy import String, ForeignKey, Boolean, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import uuid
from datetime import datetime
# Import Role to ensure visibility for relationship mapping
from app.models.role import Role
from app.core.encrypted_types import EncryptedCredential

class User(BaseModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    full_name: Mapped[str] = mapped_column(String, nullable=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    # Platform-account MFA is opt-in for existing users and only enforced for
    # superusers by the login flow. Secrets and recovery codes are encrypted at
    # rest; they are never included in the user response schema.
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_secret_encrypted: Mapped[str] = mapped_column(EncryptedCredential(), nullable=True)
    mfa_recovery_codes_encrypted: Mapped[str] = mapped_column(EncryptedCredential(), nullable=True)
    mfa_last_used_step: Mapped[int] = mapped_column(Integer, nullable=True)
    mfa_enabled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    mfa_challenge_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    mfa_challenge_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    # Incrementing this value invalidates every JWT issued for the user.
    auth_token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=True)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    
    # Relationships
    role = relationship(Role, lazy="joined")
    company = relationship("app.models.company.Company", back_populates="users", lazy="joined", foreign_keys=[company_id])
    notifications = relationship("app.models.notification.Notification", back_populates="user", cascade="all, delete-orphan")
