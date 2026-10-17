"""Application configuration using pydantic-settings.

All settings are read from environment variables.  No secrets are built in.
Auth (Keycloak OIDC), LLM provider endpoints and database paths are
operator-configurable.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for Beacon Forge."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Application
    app_name: str = "Beacon Forge"
    environment: str = "development"
    debug: bool = False

    # API
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # Database
    database_url: str = "sqlite:///./beacon_forge.db"

    # Demo mode — local-only, refuses to start in production.
    demo_mode: bool = False

    # Auth (Keycloak OIDC) — future milestone; currently a simple API-key gate.
    oidc_client_id: str = "beacon-forge"
    oidc_client_secret: str = ""
    api_key: str = ""

    # LLM — optional, opt-in, advisory.
    llm_provider: str = "openai-compatible"
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str | None = None
    llm_api_key: str = ""

    # Domain constants
    goal_budget_tolerance: float = 0.05  # 5 % over-budget allowed on complete
    event_compaction_batch_size: int = 50


settings = Settings()  # type: ignore[assignment]