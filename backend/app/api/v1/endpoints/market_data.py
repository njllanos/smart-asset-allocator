"""
Endpoints para datos de mercado.
Módulo 1: Ingesta de datos. 
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, Query, HTTPException, status

from ....models.schemas import MarketDataRequest, MarketDataResponse
from ....models.enums import TimeframePreset
from ....services.market_data_service import MarketDataService
from ....core.exceptions import (
    MarketDataException,
    InvalidTickerException,
    InsufficientDataException
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/market-data", tags=["Market Data"])


def get_market_data_service() -> MarketDataService:
    """Dependency injection para MarketDataService."""
    return MarketDataService()


@router.post(
    "/",
    response_model=MarketDataResponse,
    summary="Obtener datos de mercado",
    description="""
    Obtiene datos históricos de mercado para una lista de activos.
    
    Calcula: 
    - Retornos logarítmicos
    - Matriz de covarianza (anualizada)
    - Matriz de correlación
    - Estadísticas por activo (Sharpe, volatilidad, drawdown)
    """
)
async def get_market_data(
    request: MarketDataRequest,
    service: MarketDataService = Depends(get_market_data_service)
) -> MarketDataResponse: 
    """Endpoint principal de datos de mercado."""
    try:
        return await service.get_market_data(
            tickers=request.tickers,
            timeframe=request.timeframe
        )
    except InvalidTickerException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e. message, "details": e.details}
        )
    except InsufficientDataException as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code":  e.code, "message": e.message, "details": e. details}
        )
    except MarketDataException as e: 
        logger.exception(f"Market data error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": e. code, "message": e.message}
        )


@router.get(
    "/quick-stats",
    summary="Estadísticas rápidas",
    description="Obtiene estadísticas básicas para una lista de tickers."
)
async def get_quick_stats(
    tickers: List[str] = Query(
        ..., 
        min_length=1, 
        description="Lista de tickers separados por coma"
    ),
    service: MarketDataService = Depends(get_market_data_service)
):
    """Endpoint ligero para estadísticas rápidas."""
    normalized = [t.upper().strip() for t in tickers]
    
    try:
        result = await service.get_market_data(
            tickers=normalized,
            timeframe=TimeframePreset.ONE_YEAR
        )
        return {
            "tickers": result.tickers,
            "statistics": result.statistics
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/validate-tickers",
    summary="Validar tickers",
    description="Verifica si los tickers existen y tienen datos disponibles."
)
async def validate_tickers(
    tickers: List[str] = Query(... ),
    service: MarketDataService = Depends(get_market_data_service)
):
    """Valida una lista de tickers."""
    import yfinance as yf
    
    results = {}
    normalized = [t.upper().strip() for t in tickers]
    
    for ticker in normalized: 
        try:
            info = yf.Ticker(ticker).info
            results[ticker] = {
                "valid": info.get("regularMarketPrice") is not None,
                "name": info.get("shortName", "Unknown"),
                "type": info.get("quoteType", "Unknown"),
                "currency": info.get("currency", "USD")
            }
        except Exception: 
            results[ticker] = {"valid": False, "error": "Ticker not found"}
    
    return {"results": results}