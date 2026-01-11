"""
Configuración centralizada de la aplicación. 
Gestión de variables de entorno con validación. 
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Configuración de la aplicación con validación Pydantic."""
    
    # API Configuration
    APP_NAME: str = "Smart-Asset Allocator"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # External APIs
    NEWS_API_KEY:  str = Field(default="", description="NewsAPI. org API Key")
    
    # Model Configuration
    FINBERT_MODEL:  str = "ProsusAI/finbert"
    SENTIMENT_BATCH_SIZE: int = 16
    
    # Market Data Configuration
    DEFAULT_HISTORY_YEARS: int = 3
    TRADING_DAYS_PER_YEAR: int = 252
    
    # Monte Carlo Configuration
    MC_SIMULATIONS: int = 5000
    MC_TRADING_DAYS: int = 252
    
    # Cache Configuration
    CACHE_TTL_SECONDS: int = 3600  # 1 hour
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW:  int = 60  # seconds
    
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Singleton para configuración."""
    return Settings()