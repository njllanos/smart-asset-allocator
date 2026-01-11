"""
Endpoints para optimización de portafolio. 
Módulo 3: Optimización Black-Litterman. 
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from ....models.schemas import (
    OptimizationRequest,
    OptimizationResponse,
    SentimentAnalysisRequest
)
from ....services.optimization_service import OptimizationService
from ....services.sentiment_service import SentimentService
from ....services.news_service import NewsService
from ....core.exceptions import OptimizationException, SmartAllocatorException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/optimization", tags=["Portfolio Optimization"])


def get_optimization_service() -> OptimizationService:
    """Dependency injection para OptimizationService."""
    return OptimizationService()


def get_sentiment_service() -> SentimentService:
    """Dependency injection para SentimentService."""
    return SentimentService()


def get_news_service() -> NewsService:
    """Dependency injection para NewsService."""
    return NewsService()


@router.post(
    "/optimize",
    response_model=OptimizationResponse,
    summary="Optimizar portafolio",
    description="""
    Optimiza un portafolio usando el modelo Black-Litterman. 
    
    ## Proceso: 
    1. **Datos de mercado**: Obtiene precios históricos y calcula covarianza
    2. **Views**:  Si `use_sentiment=true`, analiza noticias para generar views
    3. **Black-Litterman**: Combina retornos implícitos con views
    4. **Optimización**: Encuentra pesos óptimos según el objetivo
    
    ## Objetivos disponibles:
    - `max_sharpe`: Maximiza el ratio de Sharpe (riesgo-retorno)
    - `min_volatility`: Minimiza la volatilidad del portafolio
    - `efficient_return`: Minimiza volatilidad para un retorno objetivo
    - `efficient_risk`: Maximiza retorno para una volatilidad objetivo
    
    ## Views: 
    - **Automáticos**: Generados desde análisis de sentimiento de noticias
    - **Manuales**: Especificados en el campo `views` del request
    """
)
async def optimize_portfolio(
    request: OptimizationRequest,
    optimization_service: OptimizationService = Depends(get_optimization_service),
    sentiment_service:  SentimentService = Depends(get_sentiment_service),
    news_service: NewsService = Depends(get_news_service)
) -> OptimizationResponse:
    """Endpoint principal de optimización."""
    
    logger.info(f"Optimization requested:  {request.tickers}, objective={request.objective}")
    
    sentiment_results = None
    
    # Obtener sentiment si está habilitado y no hay views manuales
    if request.use_sentiment and not request.views:
        try:
            logger.info("Fetching sentiment for views...")
            
            # Obtener noticias
            news_by_ticker = await news_service. get_news_for_tickers(
                tickers=request.tickers,
                max_articles_per_ticker=25
            )
            
            # Analizar sentimiento
            sentiment_response = await sentiment_service.analyze_sentiment(
                tickers=request.tickers,
                news_by_ticker=news_by_ticker
            )
            
            sentiment_results = sentiment_response.results
            logger.info(f"Sentiment analysis complete for {len(sentiment_results)} tickers")
            
        except Exception as e: 
            logger.warning(f"Sentiment analysis failed, proceeding without views: {e}")
            sentiment_results = None
    
    try:
        # Ejecutar optimización
        result = await optimization_service.optimize_portfolio(
            request=request,
            sentiment_results=sentiment_results
        )
        
        logger.info(
            f"Optimization complete.  "
            f"Expected return: {result.metrics.expected_annual_return}%, "
            f"Sharpe:  {result.metrics.sharpe_ratio}"
        )
        
        return result
        
    except OptimizationException as e: 
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message":  e.message, "details": e.details}
        )
    except SmartAllocatorException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message}
        )


@router.post(
    "/optimize/no-sentiment",
    response_model=OptimizationResponse,
    summary="Optimizar sin análisis de sentimiento",
    description="Optimización rápida usando solo datos históricos (sin Black-Litterman views)."
)
async def optimize_without_sentiment(
    request: OptimizationRequest,
    optimization_service: OptimizationService = Depends(get_optimization_service)
) -> OptimizationResponse:
    """Optimización sin sentiment para respuestas más rápidas."""
    
    # Forzar use_sentiment a False
    request.use_sentiment = False
    
    result = await optimization_service.optimize_portfolio(
        request=request,
        sentiment_results=None
    )
    
    return result


@router.get(
    "/objectives",
    summary="Listar objetivos de optimización",
    description="Retorna los objetivos de optimización disponibles con descripciones."
)
async def list_objectives():
    """Lista objetivos disponibles."""
    return {
        "objectives": [
            {
                "id": "max_sharpe",
                "name": "Maximizar Sharpe Ratio",
                "description": "Encuentra el portafolio con mejor relación riesgo-retorno",
                "requires":  None
            },
            {
                "id": "min_volatility",
                "name": "Minimizar Volatilidad",
                "description": "Encuentra el portafolio con menor riesgo posible",
                "requires": None
            },
            {
                "id": "efficient_return",
                "name": "Retorno Eficiente",
                "description": "Minimiza volatilidad para alcanzar un retorno objetivo",
                "requires": "target_return"
            },
            {
                "id": "efficient_risk",
                "name":  "Riesgo Eficiente", 
                "description": "Maximiza retorno para un nivel de volatilidad objetivo",
                "requires": "target_volatility"
            }
        ]
    }


@router.post(
    "/views/from-sentiment",
    summary="Generar views desde sentiment",
    description="Analiza sentiment y retorna views formateados para Black-Litterman."
)
async def generate_views_from_sentiment(
    tickers: list[str],
    optimization_service: OptimizationService = Depends(get_optimization_service),
    sentiment_service: SentimentService = Depends(get_sentiment_service),
    news_service: NewsService = Depends(get_news_service)
):
    """Genera views desde análisis de sentimiento."""
    
    # Normalizar tickers
    tickers = [t.upper().strip() for t in tickers]
    
    # Obtener noticias
    news_by_ticker = await news_service.get_news_for_tickers(
        tickers=tickers,
        max_articles_per_ticker=25
    )
    
    # Analizar sentimiento
    sentiment_response = await sentiment_service.analyze_sentiment(
        tickers=tickers,
        news_by_ticker=news_by_ticker
    )
    
    # Convertir a views
    views = optimization_service.sentiment_to_views(sentiment_response.results)
    
    return {
        "tickers": tickers,
        "views": [v.model_dump() for v in views],
        "market_sentiment_index": sentiment_response.market_sentiment_index,
        "interpretation": {
            "positive_view": "Retorno esperado positivo (bullish)",
            "negative_view": "Retorno esperado negativo (bearish)",
            "confidence":  "Nivel de certeza en el view (0-1)"
        }
    }