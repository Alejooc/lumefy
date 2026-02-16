from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core import security
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.core.auth import create_access_token
from app.schemas.token import Token

router = APIRouter()

@router.post("/login/access-token", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    # Find user
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }

from pydantic import BaseModel, EmailStr

class Msg(BaseModel):
    msg: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordReset(BaseModel):
    token: str
    new_password: str

from app.services.email import EmailService
from jose import jwt, JWTError

@router.post("/password-recovery/{email}", response_model=Msg)
async def recover_password(email: str, db: AsyncSession = Depends(get_db)) -> Any:
    """
    Password Recovery
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if user:
        # Generate Reset Token (Short lived, 1 hour)
        password_reset_token = create_access_token(
            data={"sub": user.email, "type": "reset"},
            expires_delta=timedelta(hours=1)
        )
        await EmailService.send_reset_password_email(email, password_reset_token)
        
    return {"msg": "If the email exists, a recovery email has been sent."}

@router.post("/reset-password", response_model=Msg)
async def reset_password(
    body: PasswordReset,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Reset Password
    """
    try:
        payload = jwt.decode(body.token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        token_type = payload.get("type")
        
        if not email or token_type != "reset":
             raise HTTPException(status_code=400, detail="Invalid token")
             
    except (JWTError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid or expired token")
        
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    user.hashed_password = security.get_password_hash(body.new_password)
    db.add(user)
    await db.commit()
    
    return {"msg": "Password updated successfully"}
