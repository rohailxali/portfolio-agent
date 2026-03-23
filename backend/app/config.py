from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "Portfolio Agent"
    environment: str = "development"
    debug: bool = False
    secret_key: str
    allowed_origins: list[str] = ["http://localhost:3000"]

    # Database
    database_url: str
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    session_ttl_seconds: int = 3600

    # JWT
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # LLM
    anthropic_api_key: str
    agent_model: str = "claude-sonnet-4-20250514"
    agent_max_tokens: int = 4096

    # Portfolio site
    portfolio_url: str

    # GitHub
    github_token: str
    github_repo: str  # owner/repo
    github_workflow_id: str = "deploy.yml"
    github_default_branch: str = "main"

    # Vercel (optional)
    vercel_token: str = ""
    vercel_project_id: str = ""

    # Notifications
    sendgrid_api_key: str = ""
    notification_email_from: str = ""
    notification_email_to: str = ""
    slack_webhook_url: str = ""
    discord_webhook_url: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()