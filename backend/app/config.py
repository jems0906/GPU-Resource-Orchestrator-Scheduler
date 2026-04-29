from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "GPU Resource Orchestrator"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/gpu_orchestrator"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "change-me-in-production-use-secure-random-string"
    API_KEY_HEADER: str = "X-API-Key"
    DEFAULT_API_KEY: str = "dev-api-key-change-in-production"

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    # AWS Configuration
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGIONS: List[str] = ["us-east-1", "us-west-2", "eu-west-1"]
    AWS_ENABLED: bool = True

    # GCP Configuration
    GCP_PROJECT_ID: Optional[str] = None
    GCP_CREDENTIALS_FILE: Optional[str] = None
    GCP_REGIONS: List[str] = ["us-central1", "us-east1", "europe-west4"]
    GCP_ENABLED: bool = True

    # Azure Configuration
    AZURE_SUBSCRIPTION_ID: Optional[str] = None
    AZURE_TENANT_ID: Optional[str] = None
    AZURE_CLIENT_ID: Optional[str] = None
    AZURE_CLIENT_SECRET: Optional[str] = None
    AZURE_REGIONS: List[str] = ["eastus", "westus2", "westeurope"]
    AZURE_ENABLED: bool = True

    # Scheduler
    SCHEDULER_INTERVAL_SECONDS: float = 2.0
    JOB_TIMEOUT_HOURS: int = 24
    MAX_RETRY_ATTEMPTS: int = 3
    QUEUE_KEY: str = "gpu:job:queue"
    JOB_STATUS_PREFIX: str = "gpu:job:status:"
    JOB_METRICS_PREFIX: str = "gpu:job:metrics:"

    # Cost optimization
    SPOT_DISCOUNT_FACTOR: float = 0.30  # spot instances ~70% cheaper
    SPOT_INTERRUPTION_RATE: float = 0.05  # 5% hourly interruption probability

    # SLA
    SLA_WARNING_THRESHOLD_MINUTES: int = 30
    SLA_QUEUE_TIMEOUT_MINUTES: int = 60

    # Metrics retention
    METRICS_RETENTION_HOURS: int = 72

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
