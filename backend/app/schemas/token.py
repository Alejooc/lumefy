from typing import Optional
from pydantic import BaseModel

class Token(BaseModel):
    access_token: Optional[str] = None
    token_type: str = "bearer"
    mfa_required: bool = False
    mfa_challenge: Optional[str] = None

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    auth_version: Optional[int] = None
