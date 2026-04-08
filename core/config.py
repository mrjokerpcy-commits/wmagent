from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Anthropic
    anthropic_api_key: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/macro"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "events"

    # Alpaca (paper trading)
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"

    # Risk limits (hardcoded, never overridden by AI)
    max_position_pct: float = 0.02       # 2% per position
    max_daily_loss_pct: float = 0.05     # 5% → pause system
    min_signal_confidence: float = 0.75
    max_correlated_exposure: float = 0.10
    human_approval_threshold: float = 0.05  # require approval if size > 5%

    class Config:
        env_file = ".env"


settings = Settings()
