"""
Application configuration using Pydantic Settings
Loads from environment variables with validation
"""

import secrets
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, EmailStr, HttpUrl, PostgresDsn, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # =============================================================================
    # APPLICATION SETTINGS
    # =============================================================================
    APP_NAME: str = "Miasma"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True
    
    # =============================================================================
    # DATABASE CONFIGURATION
    # =============================================================================
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "miasma_user"
    POSTGRES_PASSWORD: str = "your-database-password"
    POSTGRES_DB: str = "miasma_db"
    
    # Database URL (constructed from above)
    DATABASE_URL: Optional[str] = None
    
    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: dict) -> str:
        if isinstance(v, str):
            return v
        return f"postgresql+asyncpg://{values.get('POSTGRES_USER')}:{values.get('POSTGRES_PASSWORD')}@{values.get('POSTGRES_SERVER')}:{values.get('POSTGRES_PORT')}/{values.get('POSTGRES_DB')}"
    
    # Database Pool Settings
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    
    # =============================================================================
    # REDIS CONFIGURATION
    # =============================================================================
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "your-redis-password"
    REDIS_DB: int = 0
    REDIS_URL: Optional[str] = None
    
    @validator("REDIS_URL", pre=True)
    def assemble_redis_connection(cls, v: Optional[str], values: dict) -> str:
        if isinstance(v, str):
            return v
        password = values.get("REDIS_PASSWORD")
        if password:
            return f"redis://:{password}@{values.get('REDIS_HOST')}:{values.get('REDIS_PORT')}/{values.get('REDIS_DB')}"
        return f"redis://{values.get('REDIS_HOST')}:{values.get('REDIS_PORT')}/{values.get('REDIS_DB')}"
    
    # Cache Settings
    CACHE_TTL_SECONDS: int = 300
    SESSION_TTL_SECONDS: int = 86400
    
    # =============================================================================
    # SECURITY SETTINGS
    # =============================================================================
    # CORS Settings
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",
        "http://localhost:5173", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # Password Requirements
    MIN_PASSWORD_LENGTH: int = 8
    REQUIRE_UPPERCASE: bool = True
    REQUIRE_LOWERCASE: bool = True
    REQUIRE_NUMBERS: bool = True
    REQUIRE_SPECIAL_CHARS: bool = True
    
    # =============================================================================
    # WEB SCRAPING CONFIGURATION
    # =============================================================================
    # Selenium Settings
    SELENIUM_HUB_URL: str = "http://selenium:4444/wd/hub"
    CHROME_OPTIONS: str = "--headless,--no-sandbox,--disable-dev-shm-usage,--disable-gpu"
    SELENIUM_TIMEOUT: int = 30
    PAGE_LOAD_TIMEOUT: int = 30
    
    # Use SeleniumBase UC Mode instead of Selenium Hub (needs Chrome + xvfb installed locally)
    USE_STEALTH_DRIVER: bool = True

    # Scraping Behavior
    REQUEST_DELAY_MIN: int = 1
    REQUEST_DELAY_MAX: int = 3
    MAX_RETRIES: int = 3
    CONCURRENT_SCRAPERS: int = 2
    
    # User Agent Settings
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    
    # =============================================================================
    # DATA BROKER SITES CONFIGURATION
    # =============================================================================
    # Enable/Disable specific scrapers
    ENABLE_TRUEPEOPLESEARCH: bool = False  # CAPTCHA blocked
    ENABLE_FASTPEOPLESEARCH: bool = False  # CAPTCHA blocked
    ENABLE_NUWBER: bool = False  # Cloudflare blocked
    ENABLE_CYBERBACKGROUNDCHECKS: bool = False  # Bot detection blocked
    ENABLE_USPHONEBOOK: bool = False  # Cloudflare blocked
    ENABLE_RADARIS: bool = True  # Working with UC mode
    ENABLE_THATSTHEM: bool = True  # Works with UC mode, occasional captcha
    ENABLE_FASTBACKGROUNDCHECK: bool = False  # Cloudflare blocks even UC mode
    ENABLE_VOTERRECORDS: bool = False  # Cloudflare blocks even UC mode
    ENABLE_CYBERBACKGROUNDCHECKS_STEALTH: bool = False  # UC mode variant - needs testing

    # Scraper-specific settings
    WHITEPAGES_API_KEY: Optional[str] = None
    SPOKEO_API_KEY: Optional[str] = None
    
    # =============================================================================
    # DATA GENERATION SETTINGS
    # =============================================================================
    # Fake Data Generation
    FAKER_LOCALE: str = "en_US"
    GENERATE_REALISTIC_ADDRESSES: bool = True
    USE_REAL_ZIPCODES: bool = True
    AVOID_OBVIOUS_FAKE_NAMES: bool = True
    
    # Campaign Settings
    MAX_CAMPAIGNS_PER_USER: int = 10
    MAX_SUBMISSIONS_PER_CAMPAIGN: int = 100
    CAMPAIGN_EXECUTION_DELAY_HOURS: int = 24
    
    # =============================================================================
    # LOGGING CONFIGURATION
    # =============================================================================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "logs/miasma.log"
    LOG_MAX_BYTES: int = 10485760
    LOG_BACKUP_COUNT: int = 5
    
    # Enable specific loggers
    LOG_DATABASE: bool = False
    LOG_SCRAPERS: bool = True
    LOG_CAMPAIGNS: bool = True
    LOG_SECURITY: bool = True
    
    # =============================================================================
    # AWS CONFIGURATION (for production)
    # =============================================================================
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    
    # S3 Configuration
    S3_BUCKET: Optional[str] = None
    S3_REGION: str = "us-east-1"
    
    # SES Configuration
    SES_SENDER_EMAIL: Optional[EmailStr] = None
    SES_REGION: str = "us-east-1"
    
    # =============================================================================
    # MONITORING & ANALYTICS
    # =============================================================================
    # Enable monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 8001
    
    # External monitoring services
    SENTRY_DSN: Optional[str] = None  # Changed from HttpUrl to str
    
    # =============================================================================
    # DEVELOPMENT SETTINGS
    # =============================================================================
    # Only used in development
    DEV_SEED_DATA: bool = True
    DEV_MOCK_SCRAPERS: bool = False
    DEV_BYPASS_RATE_LIMITS: bool = True
    
    # Testing
    TEST_DATABASE_URL: Optional[str] = None
    PYTEST_TIMEOUT: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


# Create global settings instance
settings = Settings()