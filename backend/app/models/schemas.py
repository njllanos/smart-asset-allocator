"""
Schemas Pydantic para Request/Response. 
Validación estricta y documentación automática OpenAPI.
"""
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator, model_validator
import re

from .enums import AssetType, SentimentLabel, TimeframePreset


# ==================== Market Data Schemas ====================

class AssetInput(BaseModel):
    """Asset individual para el portafolio."""
    ticker: str = Field(..., min_length=1, max_length=10, description="Símbolo del activo")
    asset_type: AssetType = Field(default=AssetType.STOCK)
    
    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v:  str) -> str:
        """Normaliza y valida el ticker."""
        ticker = v.upper().strip()
        # Patrón:  letras, números, puntos, guiones (para crypto como BTC-USD)
        if not re.match(r"^[A-Z0-9.\-]{1,10}$", ticker):
            raise ValueError(f"Ticker inválido: {ticker}")
        return ticker


class MarketDataRequest(BaseModel):
    """Request para obtener datos de mercado."""
    tickers: List[str] = Field(
        ..., 
        min_length=1, 
        max_length=30,
        description="Lista de tickers (máx 30)"
    )
    timeframe: TimeframePreset = Field(default=TimeframePreset.THREE_YEARS)
    
    @field_validator("tickers")
    @classmethod
    def validate_tickers(cls, v: List[str]) -> List[str]:
        """Normaliza tickers y elimina duplicados."""
        normalized = list(set([t.upper().strip() for t in v]))
        if len(normalized) < 2:
            raise ValueError("Se requieren al menos 2 activos para optimización")
        return normalized


class PriceDataPoint(BaseModel):
    """Punto de datos de precio."""
    date: date
    open: float
    high:  float
    low: float
    close: float
    adj_close: float
    volume:  int


class AssetStatistics(BaseModel):
    """Estadísticas calculadas para un activo."""
    ticker: str
    annualized_return: float = Field(... , description="Retorno anualizado (%)")
    annualized_volatility: float = Field(..., description="Volatilidad anualizada (%)")
    sharpe_ratio: float = Field(..., description="Sharpe Ratio (rf=0)")
    max_drawdown: float = Field(..., description="Máximo Drawdown (%)")
    last_price: float
    price_change_1y: Optional[float] = None


class MarketDataResponse(BaseModel):
    """Response con datos de mercado procesados."""
    tickers: List[str]
    statistics: Dict[str, AssetStatistics]
    covariance_matrix: Dict[str, Dict[str, float]]
    correlation_matrix: Dict[str, Dict[str, float]]
    log_returns_sample: Dict[str, List[float]] = Field(
        ..., 
        description="Últimos 30 retornos logarítmicos"
    )
    data_start_date: date
    data_end_date:  date
    trading_days: int
    

# ==================== Sentiment Schemas ====================

class NewsArticle(BaseModel):
    """Artículo de noticias con metadata."""
    title: str
    source: str
    published_at: datetime
    url: Optional[str] = None
    ticker_relevance: List[str] = Field(default_factory=list)


class SentimentResult(BaseModel):
    """Resultado de análisis de sentimiento para un headline."""
    headline: str
    label: SentimentLabel
    confidence: float = Field(... , ge=0, le=1)
    scores: Dict[str, float] = Field(
        ..., 
        description="Probabilidades para cada clase"
    )


class TickerSentimentSummary(BaseModel):
    """Resumen de sentimiento agregado para un ticker."""
    ticker: str
    sentiment_score: float = Field(
        ..., 
        ge=-1, 
        le=1,
        description="Score consolidado (-1 bearish a +1 bullish)"
    )
    dominant_sentiment: SentimentLabel
    confidence_avg: float
    articles_analyzed: int
    positive_ratio: float
    negative_ratio:  float
    neutral_ratio: float
    headlines:  List[SentimentResult]


class SentimentAnalysisRequest(BaseModel):
    """Request para análisis de sentimiento."""
    tickers: List[str] = Field(... , min_length=1, max_length=30)
    max_articles_per_ticker: int = Field(default=10, ge=1, le=50)
    
    @field_validator("tickers")
    @classmethod
    def normalize_tickers(cls, v:  List[str]) -> List[str]:
        return [t.upper().strip() for t in v]


class SentimentAnalysisResponse(BaseModel):
    """Response completo de análisis de sentimiento."""
    analysis_timestamp: datetime
    tickers_analyzed: List[str]
    results: Dict[str, TickerSentimentSummary]
    market_sentiment_index: float = Field(
        ...,
        description="Índice agregado del mercado (-1 a +1)"
    )
    model_used: str


# ==================== Error Schemas ====================

class ErrorDetail(BaseModel):
    """Detalle de error estructurado."""
    code: str
    message: str
    field: Optional[str] = None


class ErrorResponse(BaseModel):
    """Response de error estándar."""
    success: bool = False
    errors: List[ErrorDetail]
    request_id: Optional[str] = None