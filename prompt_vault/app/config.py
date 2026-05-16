from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Prompt Vault"
    default_page_size: int = 20
    database_url: str = "sqlite:///./data/prompts.db"
    redis_url: str | None = None
    rate_limit_per_minute: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PROMPT_VAULT_",
        extra="ignore",
    )
