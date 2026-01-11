"""
Endpoints para análisis de sentimiento. 
Módulo 2: Motor de sentimiento NLP.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

from ....models.schemas import (
    SentimentAnalysisRequest,
    SentimentAnalysisResponse
)
from ....services.news_service import NewsService
from ....services.sentiment_service import SentimentService
from ....core.exceptions import SentimentAnalysisException, NewsAPIException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sentiment", tags=["Sentiment Analysis"])


def get_news_service() -> NewsService:
    """Dependency injection para NewsService."""
    return NewsService()


def get_sentiment_service() -> SentimentService:
    """Dependency injection para SentimentService (singleton)."""
    return SentimentService()


@router.post(
    "/analyze",
    response_model=SentimentAnalysisResponse,
    summary="Analizar sentimiento de mercado",
    description="""
    Analiza el sentimiento de noticias recientes para los tickers especificados.
    
    Proceso:
    1. Obtiene noticias recientes de cada ticker
    2. Procesa headlines con FinBERT
    3. Agrega scores en un sentiment_score consolidado [-1, +1]
    4. Genera views para el modelo Black-Litterman
    
    **Nota**: La primera llamada puede tardar más debido a la carga del modelo. 
    """
)
async def analyze_sentiment(
    request: SentimentAnalysisRequest,
    news_service: NewsService = Depends(get_news_service),
    sentiment_service: SentimentService = Depends(get_sentiment_service)
) -> SentimentAnalysisResponse:
    """Endpoint principal de análisis de sentimiento."""
    
    logger.info(f"Sentiment analysis requested for:  {request.tickers}")
    
    try:
        # Paso 1: Obtener noticias
        news_by_ticker = await news_service. get_news_for_tickers(
            tickers=request. tickers,
            max_articles_per_ticker=request.max_articles_per_ticker
        )
        
        total_articles = sum(len(articles) for articles in news_by_ticker.values())
        logger.info(f"Retrieved {total_articles} articles for analysis")
        
        # Paso 2: Analizar sentimiento
        result = await sentiment_service.analyze_sentiment(
            tickers=request.tickers,
            news_by_ticker=news_by_ticker
        )
        
        logger.info(
            f"Analysis complete. Market index: {result.market_sentiment_index}"
        )
        
        return result
        
    except SentimentAnalysisException as e:
        logger.error(f"Sentiment analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": e.code, "message": e.message, "details": e.details}
        )
    except NewsAPIException as e:
        logger.warning(f"News API error: {e}")
        # Continuar con análisis usando fallback news
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": e. code, "message": e.message}
        )


@router.get(
    "/views/{ticker}",
    summary="Obtener view para un ticker",
    description="Retorna el sentiment score convertido a view de Black-Litterman."
)
async def get_ticker_view(
    ticker: str,
    news_service: NewsService = Depends(get_news_service),
    sentiment_service: SentimentService = Depends(get_sentiment_service)
):
    """Obtiene view de Black-Litterman para un solo ticker."""
    ticker = ticker.upper().strip()
    
    # Obtener noticias
    news = await news_service.get_news_for_tickers(
        tickers=[ticker],
        max_articles_per_ticker=15
    )
    
    # Analizar
    result = await sentiment_service. analyze_sentiment(
        tickers=[ticker],
        news_by_ticker=news
    )
    
    # Convertir a view
    views = sentiment_service.get_black_litterman_views(result. results)
    
    summary = result.results. get(ticker)
    
    return {
        "ticker": ticker,
        "sentiment_score": summary.sentiment_score if summary else 0,
        "black_litterman_view": views.get(ticker, 0),
        "dominant_sentiment": summary.dominant_sentiment if summary else "neutral",
        "articles_analyzed": summary.articles_analyzed if summary else 0
    }


@router.post(
    "/warmup",
    summary="Precalentar modelo",
    description="Carga el modelo FinBERT en memoria para reducir latencia."
)
async def warmup_model(
    background_tasks: BackgroundTasks,
    sentiment_service: SentimentService = Depends(get_sentiment_service)
):
    """Precarga el modelo de forma asíncrona."""
    
    async def _warmup():
        await sentiment_service.initialize_model()
    
    background_tasks.add_task(_warmup)
    
    return {
        "status": "warming_up",
        "message": "Model loading initiated in background"
    }


@router.get(
    "/health",
    summary="Health check del servicio de sentimiento"
)
async def sentiment_health(
    sentiment_service: SentimentService = Depends(get_sentiment_service)
):
    """Verifica estado del servicio y modelo."""
    model_loaded = sentiment_service._model is not None
    
    return {
        "status":  "healthy" if model_loaded else "initializing",
        "model_loaded": model_loaded,
        "model_name": sentiment_service. model_name,
        "device": sentiment_service.device
    }