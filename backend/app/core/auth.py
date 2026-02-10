from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_db
from app.schemas.token import TokenPayload
from app.models.user import User

from app.models.company import Company
from app.core import security
import uuid
print("DEBUG: AUTH LOADED NEW VERSION")

# Auto error false allows us to handle missing token manually (for dev mode)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/login/access-token", auto_error=False)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    try:
        # DEV MODE: If no token, return first user or create default
        if not token:
            # Check if any user exists
            result = await db.execute(select(User).limit(1))
            user = result.scalars().first()
            if user:
                return user
                
            # Create Default Company
            company = Company(
                name="Lumefy Demo Corp",
                currency="USD",
                tax_id="123456789"
            )
            db.add(company)
            await db.commit()
            await db.refresh(company)
            
            # Check/Create Default Admin Role
            from app.models.role import Role
            result = await db.execute(select(Role).where(Role.name == "Admin"))
            role = result.scalars().first()
            if not role:
                role = Role(name="Admin", description="Super Admin", permissions={"all": True})
                db.add(role)
                await db.commit()
                await db.refresh(role)

            # Create Default Admin User
            user = User(
                email="admin@lumefy.com",
                full_name="Admin User",
                hashed_password=security.get_password_hash("admin"),
                is_active=True,
                company_id=company.id,
                role_id=role.id
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(f"DEV MODE: Created default user {user.email}")
            return user

        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            token_data = TokenPayload(**payload)
        except (JWTError, AttributeError):
            raise credentials_exception
        
        result = await db.execute(select(User).where(User.email == token_data.sub))
        user = result.scalars().first()
        
        if user is None:
            raise credentials_exception
        return user
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Auth Error: {str(e)}")
