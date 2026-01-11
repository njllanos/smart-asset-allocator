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