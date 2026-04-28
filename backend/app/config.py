"""Application configuration via pydantic-settings.

All values loaded from environment variables or backend/.env file.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://discharge_app_role:PASSWORD@localhost:5432/your_db"
    app_schema: str = "discharge_app"

    # Entra ID (Azure AD) OAuth
    auth_client_id: str = ""
    auth_client_secret: str = ""
    auth_tenant_id: str = ""
    auth_redirect_uri: str = "https://citadelbmi001.citadelhealth.local/auth/callback"
    auth_allowed_domains: str = "citadelhealth.com,aylohealth.com"

    # Session
    session_secret: str = "dev-secret-change-in-production"
    session_max_age_seconds: int = 28800  # 8 hours

    # CORS
    cors_origins: str = "https://citadelbmi001.citadelhealth.local"

    # Auth stub (development only — bypasses Entra ID)
    auth_stub_enabled: bool = False
    auth_stub_email: str = "dev@citadelhealth.com"
    auth_stub_name: str = "Dev User"
    auth_stub_role: str = "manager"

    @property
    def allowed_domains_list(self) -> list[str]:
        return [d.strip() for d in self.auth_allowed_domains.split(",") if d.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def token_endpoint(self) -> str:
        return f"https://login.microsoftonline.com/{self.auth_tenant_id}/oauth2/v2.0/token"

    @property
    def jwks_uri(self) -> str:
        return f"https://login.microsoftonline.com/{self.auth_tenant_id}/discovery/v2.0/keys"


@lru_cache
def get_settings() -> Settings:
    return Settings()
