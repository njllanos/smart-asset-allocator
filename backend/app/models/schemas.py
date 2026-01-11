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


# ==================== Optimization Schemas ====================

class BlackLittermanView(BaseModel):
    """View individual para Black-Litterman."""
    ticker: str
    view:  float = Field(
        ..., 
        description="Retorno esperado (ej: 0.10 = 10%)"
    )
    confidence: float = Field(
        default=0.5, 
        ge=0.0, 
        le=1.0,
        description="Confianza en el view (0-1)"
    )


class OptimizationConstraints(BaseModel):
    """Restricciones para la optimización."""
    min_weight: float = Field(
        default=0.0, 
        ge=0.0, 
        le=1.0,
        description="Peso mínimo por activo"
    )
    max_weight: float = Field(
        default=1.0, 
        ge=0.0, 
        le=1.0,
        description="Peso máximo por activo"
    )
    sector_constraints: Optional[Dict[str, Dict[str, float]]] = Field(
        default=None,
        description="Restricciones por sector {sector:  {min:  x, max: y}}"
    )
    
    @model_validator(mode='after')
    def validate_weights(self):
        if self.min_weight > self.max_weight:
            raise ValueError("min_weight no puede ser mayor que max_weight")
        return self


class OptimizationRequest(BaseModel):
    """Request para optimización de portafolio."""
    tickers: List[str] = Field(
        ..., 
        min_length=2, 
        max_length=30,
        description="Lista de tickers (mín 2, máx 30)"
    )
    timeframe: TimeframePreset = Field(default=TimeframePreset.THREE_YEARS)
    objective: str = Field(
        default="max_sharpe",
        description="Objetivo:  max_sharpe, min_volatility, efficient_risk, efficient_return"
    )
    use_sentiment: bool = Field(
        default=True,
        description="Incorporar views de sentimiento"
    )
    views: Optional[List[BlackLittermanView]] = Field(
        default=None,
        description="Views manuales (override sentiment)"
    )
    constraints: OptimizationConstraints = Field(
        default_factory=OptimizationConstraints
    )
    risk_free_rate: float = Field(
        default=0.04,
        ge=0.0,
        le=0.2,
        description="Tasa libre de riesgo anual"
    )
    target_return: Optional[float] = Field(
        default=None,
        description="Retorno objetivo para efficient_return"
    )
    target_volatility: Optional[float] = Field(
        default=None,
        description="Volatilidad objetivo para efficient_risk"
    )
    
    @field_validator("tickers")
    @classmethod
    def validate_tickers(cls, v: List[str]) -> List[str]:
        normalized = list(set([t.upper().strip() for t in v]))
        if len(normalized) < 2:
            raise ValueError("Se requieren al menos 2 activos")
        return normalized


class PortfolioAllocation(BaseModel):
    """Asignación de un activo en el portafolio."""
    ticker: str
    weight: float = Field(... , ge=0.0, le=1.0)
    weight_percent: float = Field(..., description="Peso en porcentaje")
    expected_return: float = Field(..., description="Retorno esperado del activo (%)")
    
    
class PortfolioMetrics(BaseModel):
    """Métricas del portafolio optimizado."""
    expected_annual_return: float = Field(... , description="Retorno esperado anual (%)")
    annual_volatility: float = Field(... , description="Volatilidad anual (%)")
    sharpe_ratio: float
    sortino_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None


class BlackLittermanParams(BaseModel):
    """Parámetros usados en Black-Litterman."""
    tau: float = Field(... , description="Parámetro de incertidumbre")
    market_implied_returns: Dict[str, float]
    posterior_returns: Dict[str, float]
    views_applied: Dict[str, float]


class OptimizationResponse(BaseModel):
    """Response de optimización de portafolio."""
    optimization_timestamp: datetime
    objective_used: str
    tickers:  List[str]
    allocations: List[PortfolioAllocation]
    weights: Dict[str, float] = Field(... , description="Pesos por ticker")
    metrics: PortfolioMetrics
    black_litterman_params: Optional[BlackLittermanParams] = None
    sentiment_views_used: bool
    constraints_applied: OptimizationConstraints
    efficient_frontier: Optional[List[Dict[str, float]]] = Field(
        default=None,
        description="Puntos de la frontera eficiente"
    )


# ==================== Risk Analysis Schemas ====================

class PortfolioWeights(BaseModel):
    """Pesos del portafolio para análisis de riesgo."""
    weights: Dict[str, float] = Field(
        ...,
        description="Pesos por ticker (deben sumar ~1.0)"
    )
    
    @model_validator(mode='after')
    def validate_weights(self):
        total = sum(self.weights.values())
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Los pesos deben sumar 1.0, actualmente suman {total:. 4f}")
        if any(w < 0 for w in self.weights.values()):
            raise ValueError("Los pesos no pueden ser negativos")
        return self


class RiskAnalysisRequest(BaseModel):
    """Request para análisis de riesgo."""
    tickers: List[str] = Field(..., min_length=1, max_length=30)
    weights: Dict[str, float] = Field(
        ...,
        description="Pesos del portafolio por ticker"
    )
    portfolio_value: float = Field(
        default=100000.0,
        gt=0,
        description="Valor del portafolio en USD"
    )
    timeframe: TimeframePreset = Field(default=TimeframePreset.THREE_YEARS)
    confidence_levels: List[float] = Field(
        default=[0.90, 0.95, 0.99],
        description="Niveles de confianza para VaR"
    )
    simulation_days: int = Field(
        default=252,
        ge=1,
        le=504,
        description="Días a simular (horizonte de riesgo)"
    )
    num_simulations: int = Field(
        default=5000,
        ge=1000,
        le=50000,
        description="Número de simulaciones Monte Carlo"
    )
    
    @field_validator("tickers")
    @classmethod
    def validate_tickers(cls, v:  List[str]) -> List[str]:
        return [t.upper().strip() for t in v]
    
    @model_validator(mode='after')
    def validate_weights_match_tickers(self):
        weight_tickers = set(self.weights.keys())
        request_tickers = set(self. tickers)
        
        # Normalizar keys de weights
        self.weights = {k. upper().strip(): v for k, v in self.weights.items()}
        weight_tickers = set(self.weights.keys())
        
        if weight_tickers != request_tickers:
            missing = request_tickers - weight_tickers
            extra = weight_tickers - request_tickers
            raise ValueError(
                f"Tickers y weights no coinciden.  "
                f"Faltan en weights: {missing}, Extra en weights: {extra}"
            )
        return self


class VaRResult(BaseModel):
    """Resultado de Value at Risk para un nivel de confianza."""
    confidence_level: float = Field(... , description="Nivel de confianza (ej: 0.95)")
    var_percent: float = Field(..., description="VaR como porcentaje del portafolio")
    var_amount: float = Field(..., description="VaR en valor monetario (USD)")
    expected_shortfall: float = Field(
        ..., 
        description="Expected Shortfall (CVaR) en USD"
    )
    es_percent: float = Field(... , description="ES como porcentaje")


class MonteCarloPath(BaseModel):
    """Camino individual de simulación (para visualización)."""
    percentile: str = Field(..., description="Percentil que representa")
    values: List[float] = Field(... , description="Valores del portafolio por día")


class StressScenario(BaseModel):
    """Resultado de un escenario de estrés."""
    scenario_name: str
    description: str
    portfolio_impact_percent: float
    portfolio_impact_amount: float
    var_under_stress: float


class RiskMetrics(BaseModel):
    """Métricas de riesgo del portafolio."""
    # Volatilidad
    daily_volatility: float = Field(... , description="Volatilidad diaria (%)")
    annual_volatility:  float = Field(..., description="Volatilidad anualizada (%)")
    
    # VaR por diferentes métodos
    var_results: List[VaRResult]
    
    # Drawdown
    max_drawdown: float = Field(... , description="Máximo drawdown histórico (%)")
    avg_drawdown: float = Field(... , description="Drawdown promedio (%)")
    
    # Distribución de retornos
    skewness: float = Field(..., description="Asimetría de retornos")
    kurtosis: float = Field(..., description="Curtosis (fat tails)")
    
    # Probabilidades
    prob_loss_1_percent: float = Field(..., description="Prob. de pérdida > 1%")
    prob_loss_5_percent: float = Field(..., description="Prob.  de pérdida > 5%")
    prob_loss_10_percent: float = Field(..., description="Prob. de pérdida > 10%")


class MonteCarloResults(BaseModel):
    """Resultados detallados de simulación Monte Carlo."""
    num_simulations: int
    simulation_days: int
    
    # Estadísticas finales
    mean_final_value: float
    median_final_value: float
    std_final_value: float
    min_final_value: float
    max_final_value:  float
    
    # Percentiles de valor final
    percentile_5: float
    percentile_10: float
    percentile_25: float
    percentile_75: float
    percentile_90: float
    percentile_95: float
    
    # Probabilidades
    prob_profit:  float = Field(..., description="Prob.  de terminar con ganancia")
    prob_loss_gt_10: float = Field(..., description="Prob. de pérdida > 10%")
    prob_loss_gt_20: float = Field(..., description="Prob.  de pérdida > 20%")
    prob_gain_gt_10: float = Field(..., description="Prob. de ganancia > 10%")
    prob_gain_gt_20: float = Field(..., description="Prob. de ganancia > 20%")
    
    # Caminos representativos para visualización
    sample_paths: List[MonteCarloPath]


class RiskAnalysisResponse(BaseModel):
    """Response completo de análisis de riesgo."""
    analysis_timestamp: datetime
    portfolio_value:  float
    tickers: List[str]
    weights: Dict[str, float]
    
    # Métricas principales
    risk_metrics: RiskMetrics
    
    # Resultados Monte Carlo
    monte_carlo:  MonteCarloResults
    
    # Escenarios de estrés
    stress_scenarios: List[StressScenario]
    
    # Contribución al riesgo por activo
    risk_contribution: Dict[str, float] = Field(
        ...,
        description="Contribución al riesgo total por activo (%)"
    )
    
    # Correlaciones
    correlation_matrix: Dict[str, Dict[str, float]]
    
    # Datos históricos para contexto
    historical_start_date: date
    historical_end_date:  date
    trading_days_analyzed: int


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