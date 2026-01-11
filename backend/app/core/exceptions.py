"""
Excepciones personalizadas del dominio. 
Manejo estructurado de errores. 
"""
from typing import Optional, Dict, Any


class SmartAllocatorException(Exception):
    """Excepción base de la aplicación."""
    
    def __init__(
        self, 
        message: str, 
        code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self. code = code
        self.details = details or {}
        super().__init__(self.message)


class MarketDataException(SmartAllocatorException):
    """Error al obtener datos de mercado."""
    
    def __init__(self, message: str, ticker: Optional[str] = None):
        super().__init__(
            message=message,
            code="MARKET_DATA_ERROR",
            details={"ticker": ticker} if ticker else {}
        )


class InvalidTickerException(SmartAllocatorException):
    """Ticker inválido o no encontrado."""
    
    def __init__(self, ticker: str):
        super().__init__(
            message=f"Ticker no válido o sin datos: {ticker}",
            code="INVALID_TICKER",
            details={"ticker": ticker}
        )


class InsufficientDataException(SmartAllocatorException):
    """Datos históricos insuficientes."""
    
    def __init__(self, ticker: str, required_days: int, available_days: int):
        super().__init__(
            message=f"Datos insuficientes para {ticker}: {available_days}/{required_days} días",
            code="INSUFFICIENT_DATA",
            details={
                "ticker": ticker,
                "required_days": required_days,
                "available_days": available_days
            }
        )


class SentimentAnalysisException(SmartAllocatorException):
    """Error en análisis de sentimiento."""
    
    def __init__(self, message: str, model_error: Optional[str] = None):
        super().__init__(
            message=message,
            code="SENTIMENT_ERROR",
            details={"model_error": model_error} if model_error else {}
        )


class NewsAPIException(SmartAllocatorException):
    """Error al obtener noticias."""
    
    def __init__(self, message: str, source: str):
        super().__init__(
            message=message,
            code="NEWS_API_ERROR",
            details={"source": source}
        )


class RateLimitException(SmartAllocatorException):
    """Rate limit excedido."""
    
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message=f"Rate limit excedido.  Reintentar en {retry_after}s",
            code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after}
        )