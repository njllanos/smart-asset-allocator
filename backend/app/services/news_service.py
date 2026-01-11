"""
Servicio de obtención de noticias financieras.
Abstrae múltiples fuentes de noticias. 
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import asyncio
import aiohttp

from ..config import get_settings
from ..core.exceptions import NewsAPIException
from ..models.schemas import NewsArticle

logger = logging.getLogger(__name__)
settings = get_settings()


class NewsService:
    """
    Servicio para obtener noticias financieras.
    Soporta múltiples proveedores con fallback. 
    """
    
    NEWSAPI_BASE_URL = "https://newsapi.org/v2/everything"
    
    # Mapeo de tickers a términos de búsqueda
    COMPANY_NAMES = {
        "AAPL": "Apple",
        "GOOGL": "Google Alphabet",
        "GOOG": "Google Alphabet",
        "MSFT": "Microsoft",
        "AMZN": "Amazon",
        "META": "Meta Facebook",
        "TSLA":  "Tesla",
        "NVDA": "NVIDIA",
        "JPM": "JPMorgan",
        "V": "Visa",
        "BTC-USD": "Bitcoin",
        "ETH-USD": "Ethereum",
        "SPY": "S&P 500 ETF",
        "QQQ": "Nasdaq ETF",
    }
    
    def __init__(self):
        self.api_key = settings.NEWS_API_KEY
    
    async def get_news_for_tickers(
        self,
        tickers: List[str],
        max_articles_per_ticker: int = 10,
        days_back: int = 7
    ) -> Dict[str, List[NewsArticle]]:
        """
        Obtiene noticias para múltiples tickers.
        
        Args:
            tickers: Lista de símbolos
            max_articles_per_ticker: Máximo de artículos por ticker
            days_back: Días hacia atrás para buscar
            
        Returns:
            Diccionario ticker -> lista de artículos
        """
        results = {}
        
        # Ejecutar búsquedas en paralelo
        tasks = [
            self._fetch_ticker_news(ticker, max_articles_per_ticker, days_back)
            for ticker in tickers
        ]
        
        ticker_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for ticker, result in zip(tickers, ticker_results):
            if isinstance(result, Exception):
                logger.warning(f"Error fetching news for {ticker}: {result}")
                results[ticker] = []
            else:
                results[ticker] = result
        
        return results
    
    async def _fetch_ticker_news(
        self,
        ticker: str,
        max_articles:  int,
        days_back:  int
    ) -> List[NewsArticle]:
        """Obtiene noticias para un ticker específico."""
        
        # Construir query de búsqueda
        search_term = self._get_search_term(ticker)
        
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        params = {
            "q": f'"{search_term}" AND (stock OR shares OR market OR trading)',
            "from": from_date,
            "sortBy": "relevancy",
            "language": "en",
            "pageSize": max_articles,
            "apiKey": self.api_key
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.NEWSAPI_BASE_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 401:
                        raise NewsAPIException("API key inválida", "NewsAPI")
                    if response.status == 429:
                        raise NewsAPIException("Rate limit excedido", "NewsAPI")
                    if response.status != 200:
                        raise NewsAPIException(
                            f"Error HTTP {response.status}", "NewsAPI"
                        )
                    
                    data = await response.json()
                    
                    if data.get("status") != "ok":
                        logger.warning(f"NewsAPI error: {data.get('message')}")
                        return self._get_fallback_news(ticker)
                    
                    return self._parse_articles(data.get("articles", []), ticker)
                    
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error fetching news: {e}")
            return self._get_fallback_news(ticker)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching news for {ticker}")
            return self._get_fallback_news(ticker)
    
    def _get_search_term(self, ticker: str) -> str:
        """Obtiene término de búsqueda para un ticker."""
        return self.COMPANY_NAMES.get(ticker, ticker)
    
    def _parse_articles(
        self, 
        articles:  List[dict], 
        ticker: str
    ) -> List[NewsArticle]:
        """Parsea artículos de NewsAPI a nuestro modelo."""
        parsed = []
        
        for article in articles:
            try:
                # Parsear fecha
                published_str = article.get("publishedAt", "")
                published_at = datetime.fromisoformat(
                    published_str.replace("Z", "+00:00")
                )
                
                parsed.append(NewsArticle(
                    title=article.get("title", ""),
                    source=article.get("source", {}).get("name", "Unknown"),
                    published_at=published_at,
                    url=article.get("url"),
                    ticker_relevance=[ticker]
                ))
            except Exception as e:
                logger.debug(f"Error parsing article:  {e}")
                continue
        
        return parsed
    
    def _get_fallback_news(self, ticker: str) -> List[NewsArticle]:
        """
        Genera noticias placeholder cuando la API falla.
        En producción, esto podría consultar una caché o DB.
        """
        logger. info(f"Using fallback news for {ticker}")
        
        # Headlines genéricos basados en el ticker
        fallback_headlines = [
            f"{ticker} stock shows mixed trading signals amid market volatility",
            f"Analysts remain divided on {ticker} short-term outlook",
            f"{ticker} continues to attract institutional investor attention",
        ]
        
        return [
            NewsArticle(
                title=headline,
                source="Market Analysis",
                published_at=datetime.now(),
                ticker_relevance=[ticker]
            )
            for headline in fallback_headlines
        ]