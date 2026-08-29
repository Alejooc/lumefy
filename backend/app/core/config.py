from pydantic_settings import BaseSettings
from pydantic import EmailStr, Field, field_validator, model_validator
from cryptography.fernet import Fernet
from typing import Optional, Union
from urllib.parse import urlsplit

class Settings(BaseSettings):
    PROJECT_NAME: str = "Jaofy"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: str
    DATABASE_URL: Optional[str] = None
    
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    BACKEND_CORS_ORIGIN_REGEX: Optional[str] = r"^https?://([a-z0-9-]+\.)*localhost(?::\d+)?$"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, list[str]]) -> list[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v
    
    SECRET_KEY: str
    CREDENTIAL_ENCRYPTION_KEY: Optional[str] = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    ENVIRONMENT: str = "development"  # development | production
    SQL_ECHO: bool = False
    FRONTEND_URL: str = "http://localhost:4200"
    PLATFORM_STOREFRONT_DOMAIN: Optional[str] = None
    NPM_PROVISIONING_ENABLED: bool = False
    NPM_API_URL: Optional[str] = None
    NPM_IDENTITY: Optional[str] = None
    NPM_PASSWORD: Optional[str] = None
    NPM_FORWARD_SCHEME: str = "http"
    NPM_STOREFRONT_HOST: str = "lumefy-storefront-1"
    NPM_STOREFRONT_PORT: int = Field(default=3000, ge=1, le=65535)
    NPM_BACKEND_HOST: str = "backend"
    NPM_BACKEND_PORT: int = Field(default=8000, ge=1, le=65535)
    NPM_VERIFY_SSL: bool = True
    NPM_REQUEST_TIMEOUT_SECONDS: int = Field(default=30, ge=5, le=120)
    NPM_CERTIFICATE_TIMEOUT_SECONDS: int = Field(default=900, ge=60, le=900)
    NPM_PROVISIONING_MAX_ATTEMPTS: int = Field(default=3, ge=1, le=10)
    # NPM runs Certbot as a single process and rejects concurrent issuances.
    NPM_PROVISIONING_CONCURRENCY: int = Field(default=1, ge=1, le=1)
    NPM_PROVISIONING_POLL_SECONDS: float = Field(default=2, ge=0.5, le=60)
    NPM_PROVISIONING_STALE_MINUTES: int = Field(default=30, ge=20, le=120)
    INTEGRATION_ALLOW_PRIVATE_NETWORKS: bool = False
    INTEGRATION_REQUEST_TIMEOUT_SECONDS: int = Field(default=30, ge=1, le=120)
    # External providers are outside of our control. Keep transient failures
    # bounded and avoid loading an unexpectedly large response into memory.
    INTEGRATION_RETRY_ATTEMPTS: int = Field(default=2, ge=0, le=5)
    INTEGRATION_RETRY_BASE_SECONDS: float = Field(default=0.5, ge=0, le=10)
    INTEGRATION_RETRY_MAX_SECONDS: float = Field(default=8, ge=0, le=60)
    INTEGRATION_MAX_RESPONSE_BYTES: int = Field(default=20 * 1024 * 1024, ge=1024, le=100 * 1024 * 1024)
    
    FIRST_SUPERUSER: str
    FIRST_SUPERUSER_PASSWORD: str

    # Email Settings
    MAIL_USERNAME: str = "admin@jaofy.com"
    MAIL_PASSWORD: str = "change-me"
    MAIL_FROM: EmailStr = "admin@jaofy.com"
    MAIL_PORT: int = Field(default=587, ge=1, le=65535)
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_FROM_NAME: str = "Jaofy Support"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.MAIL_STARTTLS and self.MAIL_SSL_TLS:
            raise ValueError("MAIL_STARTTLS and MAIL_SSL_TLS cannot both be enabled")
        if self.ENVIRONMENT.lower() != "production":
            return self
        insecure_fragments = ("replace-with", "change-me", "admin123", "tu_clave")
        production_values = {
            "SECRET_KEY": (self.SECRET_KEY, 32),
            "POSTGRES_PASSWORD": (self.POSTGRES_PASSWORD, 12),
            "FIRST_SUPERUSER_PASSWORD": (self.FIRST_SUPERUSER_PASSWORD, 12),
        }
        for field_name, (value, minimum_length) in production_values.items():
            if len(value) < minimum_length or any(
                fragment in value.lower() for fragment in insecure_fragments
            ):
                raise ValueError(f"{field_name} is not safe for production")
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL is required in production")
        if not self.CREDENTIAL_ENCRYPTION_KEY:
            raise ValueError("CREDENTIAL_ENCRYPTION_KEY is required in production")
        try:
            Fernet(self.CREDENTIAL_ENCRYPTION_KEY.encode("ascii"))
        except (ValueError, TypeError) as exc:
            raise ValueError("CREDENTIAL_ENCRYPTION_KEY must be a valid Fernet key") from exc
        if self.CREDENTIAL_ENCRYPTION_KEY == self.SECRET_KEY:
            raise ValueError("CREDENTIAL_ENCRYPTION_KEY must be different from SECRET_KEY")
        if not self.MAIL_SERVER.strip():
            raise ValueError("MAIL_SERVER is required in production")
        if self.USE_CREDENTIALS:
            smtp_values = {
                "MAIL_USERNAME": (self.MAIL_USERNAME, 3),
                "MAIL_PASSWORD": (self.MAIL_PASSWORD, 12),
            }
            for field_name, (value, minimum_length) in smtp_values.items():
                if len(value) < minimum_length or any(
                    fragment in value.lower() for fragment in insecure_fragments
                ):
                    raise ValueError(f"{field_name} is not safe for production")
            if not (self.MAIL_STARTTLS or self.MAIL_SSL_TLS):
                raise ValueError("Authenticated SMTP must use TLS in production")
        if (self.MAIL_STARTTLS or self.MAIL_SSL_TLS) and not self.VALIDATE_CERTS:
            raise ValueError("SMTP certificates must be validated in production")
        if self.NPM_PROVISIONING_ENABLED:
            npm_values = {
                "NPM_API_URL": self.NPM_API_URL,
                "NPM_IDENTITY": self.NPM_IDENTITY,
                "NPM_PASSWORD": self.NPM_PASSWORD,
                "NPM_STOREFRONT_HOST": self.NPM_STOREFRONT_HOST,
                "NPM_BACKEND_HOST": self.NPM_BACKEND_HOST,
            }
            for field_name, value in npm_values.items():
                if not value or not str(value).strip():
                    raise ValueError(f"{field_name} is required when NPM provisioning is enabled")
            if self.NPM_FORWARD_SCHEME not in {"http", "https"}:
                raise ValueError("NPM_FORWARD_SCHEME must be http or https")
            parsed_npm_url = urlsplit(str(self.NPM_API_URL))
            if parsed_npm_url.scheme not in {"http", "https"} or not parsed_npm_url.hostname:
                raise ValueError("NPM_API_URL must be an absolute HTTP(S) URL")
            if any(fragment in str(self.NPM_PASSWORD).lower() for fragment in insecure_fragments):
                raise ValueError("NPM_PASSWORD is not safe for production")
        return self

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
