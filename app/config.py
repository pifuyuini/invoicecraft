from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "InvoiceCraft"
    session_cookie: str = "session"
    secret_key: str = "dev-secret-key-change-me"
    database_url: str = "sqlite:///./data/app.db"
    base_url: str = "http://localhost:8000"

    billing_enabled: bool = False
    database_backup_dir: str = "data/backups"
    free_invoice_limit: int = 5
    pro_price_monthly_id: str = ""
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""

    @property
    def stripe_configured(self) -> bool:
        return bool(self.stripe_secret_key and self.pro_price_monthly_id)


settings = Settings()
