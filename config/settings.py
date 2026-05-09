"""Pydantic settings for the aws-billing app."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str

    keycloak_discovery_url: str = ""
    keycloak_client_id: str = ""
    keycloak_client_secret: str = ""
    keycloak_viewer_group: str = "aws-billing-viewers"
    keycloak_admin_group: str = "aws-billing-admins"

    session_secret: str = "dev-not-for-production"

    aws_profile_org: str = "org"
    aws_profile_separate: str = "tony"

    auth_enabled: bool = True
    dev_user_email: str = "dev@local"
    dev_user_name: str = "Dev User"
    dev_user_is_admin: bool = True

    healthcheck_url: str = ""

    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
