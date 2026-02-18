from pydantic import BaseModel, EmailStr, Field

class UserRegister(BaseModel):
    first_name: str = Field(..., min_length=2)
    last_name: str = Field(..., min_length=2)
    email: EmailStr
    password: str = Field(..., min_length=8)
    company_name: str = Field(..., min_length=3)
