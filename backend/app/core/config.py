from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, Union

class Settings(BaseSettings):
    PROJECT_NAME: str = "Lumefy"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: str
    DATABASE_URL: Optional[str] = None
    
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:4200", "http://localhost:3000"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, list[str]]) -> list[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v
    
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    ENVIRONMENT: str = "development"  # development | production
    FRONTEND_URL: str = "http://localhost:4200"
    
    FIRST_SUPERUSER: str
    FIRST_SUPERUSER_PASSWORD: str

    # Email Settings
    MAIL_USERNAME: str = "admin@lumefy.com"
    MAIL_PASSWORD: str = "change-me"
    MAIL_FROM: str = "admin@lumefy.com"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_FROM_NAME: str = "Lumefy Support"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
