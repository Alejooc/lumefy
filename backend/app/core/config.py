from pydantic_settings import BaseSettings
from typing import Optional

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
    
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    FIRST_SUPERUSER: str
    FIRST_SUPERUSER_PASSWORD: str

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
