"""
Enumeraciones del dominio financiero.
"""
from enum import Enum


class AssetType(str, Enum):
    """Tipos de activos soportados."""
    STOCK = "stock"
    ETF = "etf"
    CRYPTO = "crypto"


class SentimentLabel(str, Enum):
    """Etiquetas de sentimiento FinBERT."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class TimeframePreset(str, Enum):
    """Presets de períodos históricos."""
    ONE_YEAR = "1y"
    THREE_YEARS = "3y"
    FIVE_YEARS = "5y"
    MAX = "max"


class OptimizationObjective(str, Enum):
    """Objetivos de optimización disponibles."""
    MAX_SHARPE = "max_sharpe"
    MIN_VOLATILITY = "min_volatility"
    MAX_RETURN = "max_return"
    EFFICIENT_RISK = "efficient_risk"
    EFFICIENT_RETURN = "efficient_return"


class RiskModel(str, Enum):
    """Modelos de riesgo para covarianza."""
    SAMPLE = "sample"
    LEDOIT_WOLF = "ledoit_wolf"
    SEMICOVARIANCE = "semicovariance"


class VaRMethod(str, Enum):
    """Métodos para calcular Value at Risk."""
    HISTORICAL = "historical"
    PARAMETRIC = "parametric"
    MONTE_CARLO = "monte_carlo"


class ConfidenceLevel(str, Enum):
    """Niveles de confianza estándar para VaR."""
    CL_90 = "90"
    CL_95 = "95"
    CL_99 = "99"