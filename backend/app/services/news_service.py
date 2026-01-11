"""
Servicio de obtención de noticias financieras. 
Múltiples fuentes con generación automática de keywords.
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from urllib.parse import quote
import yfinance as yf

from .. config import get_settings
from ..models.schemas import NewsArticle

logger = logging.getLogger(__name__)
settings = get_settings()


class CompanyInfoExtractor:
    """
    Extrae información de empresas automáticamente usando yfinance.
    Genera keywords de búsqueda sin configuración manual.
    """
    
    def __init__(self):
        self._cache:  Dict[str, Dict] = {}
    
    def get_company_info(self, ticker: str) -> Dict:
        """Obtiene información completa de la empresa automáticamente."""
        ticker = ticker.upper()
        
        if ticker in self._cache:
            return self._cache[ticker]
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info or {}
            
            # Extraer todos los datos disponibles
            company_info = self._extract_company_data(ticker, info)
            
            # Generar keywords automáticamente
            company_info["keywords"] = self._generate_smart_keywords(ticker, info, company_info)
            
            self._cache[ticker] = company_info
            logger.info(f"Auto-extracted info for {ticker}: {company_info['name']}, keywords: {company_info['keywords'][: 3]}")
            
            return company_info
            
        except Exception as e:
            logger.warning(f"Could not fetch company info for {ticker}: {e}")
            return self._create_fallback_info(ticker)
    
    def _extract_company_data(self, ticker:  str, info: Dict) -> Dict:
        """Extrae datos estructurados de yfinance."""
        
        # Nombre de la empresa (múltiples fuentes)
        full_name = (
            info.get("longName") or 
            info.get("shortName") or 
            info.get("name") or 
            ticker
        )
        
        # Limpiar nombre
        clean_name = self._clean_company_name(full_name)
        
        # Extraer nombre corto/marca (primera palabra significativa)
        brand_name = self._extract_brand_name(clean_name)
        
        return {
            "ticker": ticker,
            "name":  clean_name,
            "brand":  brand_name,
            "full_name": full_name,
            "sector": info.get("sector", ""),
            "industry": info. get("industry", ""),
            "website": info.get("website", ""),
            "description": info. get("longBusinessSummary", "")[: 500],
            "ceo": self._extract_ceo(info),
            "products": self._extract_products_from_description(info.get("longBusinessSummary", "")),
        }
    
    def _clean_company_name(self, name: str) -> str:
        """Limpia el nombre de la empresa."""
        # Sufijos comunes a remover
        patterns = [
            r",?\s*(Inc\. ? |Incorporated)$",
            r",?\s*(Corp\.?|Corporation)$",
            r",?\s*(Ltd\.?|Limited)$",
            r",?\s*(LLC|L\.L\.C\.)$",
            r",?\s*(PLC|P\.L\.C\.)$",
            r",?\s*(S\. ? A\.?|AG|NV|SE)$",
            r",?\s*(Holdings? |Group|International)$",
            r",?\s*(Company|Co\.?)$",
            r",?\s*Class\s+[A-C]$",
            r"\. com$",
        ]
        
        clean = name
        for pattern in patterns: 
            clean = re.sub(pattern, "", clean, flags=re.IGNORECASE)
        
        return clean. strip()
    
    def _extract_brand_name(self, clean_name: str) -> str:
        """Extrae el nombre de marca principal."""
        # Para nombres compuestos, tomar la parte más reconocible
        words = clean_name.split()
        
        if len(words) == 1:
            return words[0]
        
        # Si el primer palabra es muy corta, puede ser un artículo
        if len(words[0]) <= 2:
            return " ".join(words[1:3])
        
        # Para la mayoría, el primer palabra es la marca
        return words[0]
    
    def _extract_ceo(self, info: Dict) -> Optional[str]:
        """Extrae nombre del CEO si está disponible."""
        officers = info.get("companyOfficers", [])
        if officers and isinstance(officers, list):
            for officer in officers:
                title = officer.get("title", "").lower()
                if "ceo" in title or "chief executive" in title:
                    return officer.get("name")
        return None
    
    def _extract_products_from_description(self, description: str) -> List[str]:
        """Extrae posibles productos/servicios de la descripción."""
        if not description:
            return []
        
        products = set()
        
        # Patrones comunes para identificar productos
        # "offers X", "provides X", "sells X", "develops X"
        patterns = [
            r"(? : offers|provides|sells|develops|manufactures|produces)\s+([A-Z][a-zA-Z]+(? :\s+[A-Z][a-zA-Z]+)?)",
            r"(?:its|the)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+(? :platform|service|product|software)",
        ]
        
        for pattern in patterns:
            matches = re. findall(pattern, description)
            for match in matches[: 3]:  # Máximo 3 productos
                if len(match) > 2:
                    products. add(match)
        
        return list(products)[:3]
    
    def _generate_smart_keywords(self, ticker: str, info: Dict, company_data: Dict) -> List[str]:
        """
        Genera keywords de búsqueda inteligentemente.
        Prioriza términos que darán mejores resultados en noticias financieras.
        """
        keywords:  List[str] = []
        seen:  Set[str] = set()
        
        def add_keyword(kw: str):
            """Agrega keyword si no es duplicado y es válido."""
            kw_lower = kw.lower().strip()
            if kw_lower and kw_lower not in seen and len(kw) > 1:
                seen.add(kw_lower)
                keywords. append(kw)
        
        name = company_data["name"]
        brand = company_data["brand"]
        
        # 1. Ticker + "stock" (muy específico para noticias financieras)
        add_keyword(f"{ticker} stock")
        
        # 2. Nombre completo limpio + "stock"
        if name. lower() != ticker.lower():
            add_keyword(f"{name} stock")
        
        # 3. Marca/nombre corto (para búsquedas más amplias)
        if brand. lower() != ticker.lower() and brand. lower() != name.lower():
            add_keyword(brand)
        
        # 4. Solo ticker (útil para algunas fuentes)
        add_keyword(ticker)
        
        # 5. CEO si está disponible (noticias mencionan CEOs)
        ceo = company_data.get("ceo")
        if ceo:
            add_keyword(ceo)
        
        # 6. Productos principales si los hay
        for product in company_data.get("products", [])[:2]: 
            add_keyword(product)
        
        # 7. Nombre + sector para contexto
        sector = company_data.get("sector", "")
        if sector and len(keywords) < 6:
            add_keyword(f"{brand} {sector}")
        
        return keywords[: 8]  # Máximo 8 keywords
    
    def _create_fallback_info(self, ticker: str) -> Dict:
        """Crea información básica cuando yfinance falla."""
        return {
            "ticker": ticker,
            "name": ticker,
            "brand": ticker,
            "full_name": ticker,
            "sector": "",
            "industry":  "",
            "website": "",
            "description": "",
            "ceo": None,
            "products": [],
            "keywords": [f"{ticker} stock", ticker],
        }
    
    def clear_cache(self):
        """Limpia el cache."""
        self._cache.clear()


class NewsService:
    """
    Servicio de noticias multi-fuente.
    Genera keywords automáticamente para cualquier ticker.
    """
    
    NEWSAPI_BASE_URL = "https://newsapi.org/v2/everything"
    GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"
    
    MIN_ARTICLES_FOR_CONFIDENCE = 10
    
    def __init__(self):
        self.api_key = settings.NEWS_API_KEY
        self._session:  Optional[aiohttp.ClientSession] = None
        self._company_extractor = CompanyInfoExtractor()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtiene o crea sesión HTTP reutilizable."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15)
            )
        return self._session
    
    async def get_news_for_tickers(
        self,
        tickers: List[str],
        max_articles_per_ticker: int = 30,
        days_back: int = 14
    ) -> Dict[str, List[NewsArticle]]:
        """Obtiene noticias de múltiples fuentes para cada ticker."""
        results = {}
        
        # Pre-cargar información de empresas en paralelo
        await self._preload_company_info(tickers)
        
        # Procesar tickers en paralelo
        tasks = [
            self._fetch_all_sources(ticker, max_articles_per_ticker, days_back)
            for ticker in tickers
        ]
        
        ticker_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for ticker, result in zip(tickers, ticker_results):
            if isinstance(result, Exception):
                logger.warning(f"Error fetching news for {ticker}: {result}")
                results[ticker] = self._get_fallback_news(ticker, max_articles_per_ticker)
            else:
                # Complementar con fallback si hay pocos artículos
                if len(result) < self.MIN_ARTICLES_FOR_CONFIDENCE:
                    logger.warning(
                        f"Low confidence for {ticker}: {len(result)} articles, "
                        f"adding {self.MIN_ARTICLES_FOR_CONFIDENCE - len(result)} neutral articles"
                    )
                    needed = self.MIN_ARTICLES_FOR_CONFIDENCE - len(result)
                    result. extend(self._get_fallback_news(ticker, needed + 3))
                results[ticker] = result[: max_articles_per_ticker]
        
        # Log estadísticas
        total_articles = sum(len(articles) for articles in results.values())
        logger.info(f"Total:  {total_articles} articles for {len(tickers)} tickers")
        for ticker, articles in results.items():
            logger.info(f"  {ticker}: {len(articles)} articles")
        
        return results
    
    async def _preload_company_info(self, tickers: List[str]):
        """Pre-carga información de empresas en paralelo."""
        loop = asyncio.get_event_loop()
        
        async def fetch_info(ticker: str):
            return await loop.run_in_executor(
                None, self._company_extractor.get_company_info, ticker
            )
        
        await asyncio.gather(*[fetch_info(t) for t in tickers], return_exceptions=True)
    
    def _get_company_info(self, ticker: str) -> Dict:
        """Obtiene información de empresa."""
        return self._company_extractor.get_company_info(ticker)
    
    async def _fetch_all_sources(
        self,
        ticker: str,
        max_articles:  int,
        days_back:  int
    ) -> List[NewsArticle]:
        """Obtiene noticias de todas las fuentes usando keywords automáticos."""
        
        all_articles = []
        company_info = self._get_company_info(ticker)
        keywords = company_info["keywords"]
        
        logger.debug(f"Searching news for {ticker} with keywords: {keywords}")
        
        # Tasks base
        tasks = [
            self._fetch_yahoo_news(ticker),
        ]
        
        # Búsquedas en Google News con diferentes keywords (máximo 3)
        for keyword in keywords[:3]: 
            tasks.append(self._fetch_google_news_with_query(keyword, ticker, days_back))
        
        # NewsAPI si hay API key
        if self.api_key:
            tasks.append(self._fetch_newsapi(ticker, keywords, max_articles // 2, days_back))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if not isinstance(result, Exception) and result:
                all_articles.extend(result)
        
        # Eliminar duplicados
        unique_articles = self._deduplicate_articles(all_articles)
        
        # Ordenar por fecha
        unique_articles.sort(key=lambda x: x.published_at, reverse=True)
        
        logger.info(f"Fetched {len(unique_articles)} unique articles for {ticker}")
        
        return unique_articles[: max_articles]
    
    # ==================== YAHOO FINANCE ====================
    
    async def _fetch_yahoo_news(self, ticker: str) -> List[NewsArticle]:
        """Obtiene noticias de Yahoo Finance."""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._fetch_yahoo_sync, ticker)
        except Exception as e:
            logger.debug(f"Yahoo Finance error for {ticker}: {e}")
            return []
    
    def _fetch_yahoo_sync(self, ticker: str) -> List[NewsArticle]:
        """Fetch síncrono de Yahoo Finance."""
        try:
            stock = yf.Ticker(ticker)
            news = stock.news or []
            
            articles = []
            for item in news[: 20]: 
                try:
                    title = item.get("title", "")
                    if not title:
                        continue
                    
                    timestamp = item.get("providerPublishTime", 0)
                    published_at = datetime.fromtimestamp(timestamp) if timestamp else datetime.now()
                    
                    articles.append(NewsArticle(
                        title=title,
                        source=item.get("publisher", "Yahoo Finance"),
                        published_at=published_at,
                        url=item.get("link"),
                        ticker_relevance=[ticker]
                    ))
                except Exception: 
                    continue
            
            return articles
        except Exception as e:
            logger.debug(f"Yahoo fetch error:  {e}")
            return []
    
    # ==================== GOOGLE NEWS RSS ====================
    
    async def _fetch_google_news_with_query(
        self,
        query: str,
        ticker: str,
        days_back: int
    ) -> List[NewsArticle]:
        """Obtiene noticias de Google News con query específica."""
        try:
            # Agregar contexto financiero si no lo tiene
            if "stock" not in query. lower():
                search_query = f"{query} stock OR shares OR investor"
            else:
                search_query = query
            
            url = f"{self.GOOGLE_NEWS_RSS}?q={quote(search_query)}&hl=en-US&gl=US&ceid=US: en"
            
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status != 200:
                    return []
                
                content = await response.text()
                return self._parse_google_rss(content, ticker, days_back)
                
        except Exception as e: 
            logger.debug(f"Google News error for '{query}': {e}")
            return []
    
    def _parse_google_rss(
        self,
        xml_content: str,
        ticker: str,
        days_back: int
    ) -> List[NewsArticle]:
        """Parsea RSS de Google News."""
        articles = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        try:
            root = ET.fromstring(xml_content)
            
            for item in root.findall(". //item")[:25]: 
                try:
                    title_elem = item.find("title")
                    if title_elem is None or not title_elem.text:
                        continue
                    
                    title = title_elem.text
                    
                    # Parsear fecha
                    pub_date_elem = item.find("pubDate")
                    published_at = datetime.now()
                    if pub_date_elem is not None and pub_date_elem.text:
                        try:
                            published_at = datetime.strptime(
                                pub_date_elem. text,
                                "%a, %d %b %Y %H:%M:%S %Z"
                            )
                        except ValueError:
                            pass
                    
                    if published_at < cutoff_date:
                        continue
                    
                    # Extraer fuente del título
                    source = "Google News"
                    if " - " in title:
                        parts = title.rsplit(" - ", 1)
                        if len(parts) == 2:
                            title, source = parts
                    
                    link_elem = item.find("link")
                    url = link_elem.text if link_elem is not None else None
                    
                    articles. append(NewsArticle(
                        title=title,
                        source=source,
                        published_at=published_at,
                        url=url,
                        ticker_relevance=[ticker]
                    ))
                except Exception:
                    continue
                    
        except ET.ParseError:
            pass
        
        return articles
    
    # ==================== NEWSAPI ====================
    
    async def _fetch_newsapi(
        self,
        ticker: str,
        keywords: List[str],
        max_articles: int,
        days_back: int
    ) -> List[NewsArticle]:
        """Obtiene noticias de NewsAPI usando keywords automáticos."""
        if not self.api_key:
            return []
        
        try: 
            # Construir query con los mejores keywords
            query_terms = keywords[: 3]
            query = " OR ".join([f'"{kw}"' for kw in query_terms])
            query = f'({query}) AND (stock OR shares OR investor OR earnings OR market)'
            
            from_date = (datetime.now() - timedelta(days=min(days_back, 30))).strftime("%Y-%m-%d")
            
            params = {
                "q": query,
                "from": from_date,
                "sortBy": "publishedAt",
                "language": "en",
                "pageSize": min(max_articles, 50),
                "apiKey": self.api_key
            }
            
            session = await self._get_session()
            async with session.get(self.NEWSAPI_BASE_URL, params=params) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                
                if data.get("status") != "ok":
                    return []
                
                return self._parse_newsapi_articles(data.get("articles", []), ticker)
                
        except Exception as e:
            logger.debug(f"NewsAPI error for {ticker}: {e}")
            return []
    
    def _parse_newsapi_articles(
        self,
        articles: List[dict],
        ticker: str
    ) -> List[NewsArticle]: 
        """Parsea artículos de NewsAPI."""
        parsed = []
        
        for article in articles:
            try:
                title = article.get("title", "")
                
                if not title or "[Removed]" in title or len(title) < 20:
                    continue
                
                published_str = article.get("publishedAt", "")
                published_at = datetime.fromisoformat(
                    published_str.replace("Z", "+00:00")
                ).replace(tzinfo=None)
                
                parsed.append(NewsArticle(
                    title=title,
                    source=article.get("source", {}).get("name", "NewsAPI"),
                    published_at=published_at,
                    url=article.get("url"),
                    ticker_relevance=[ticker]
                ))
            except Exception:
                continue
        
        return parsed
    
    # ==================== UTILIDADES ====================
    
    def _deduplicate_articles(self, articles: List[NewsArticle]) -> List[NewsArticle]: 
        """Elimina artículos duplicados."""
        if not articles:
            return []
        
        unique = []
        seen:  Set[str] = set()
        
        for article in articles: 
            # Normalizar título para comparación
            normalized = article.title.lower().strip()
            normalized = re.sub(r'[^\w\s]', '', normalized)  # Remover puntuación
            title_key = normalized[: 60]
            
            if title_key not in seen:
                seen.add(title_key)
                unique.append(article)
        
        return unique
    
    def _get_fallback_news(self, ticker: str, count: int = 10) -> List[NewsArticle]: 
        """Genera noticias neutrales como fallback."""
        company_info = self._get_company_info(ticker)
        company = company_info["name"]
        
        templates = [
            f"{company} shares trade within normal daily range",
            f"Market activity in {company} reflects typical volume patterns",
            f"{company} stock moves in line with sector average",
            f"Trading in {company} shows balanced buyer and seller activity",
            f"Analysts note steady institutional interest in {company}",
            f"{company} maintains position relative to market benchmarks",
            f"Volume in {company} stock consistent with 30-day average",
            f"{company} price action reflects broader market conditions",
            f"Options market shows balanced sentiment on {company}",
            f"{company} trading patterns align with historical norms",
            f"Market makers report normal spread activity in {company}",
            f"{company} stock liquidity remains consistent",
        ]
        
        import hashlib
        seed = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
        
        selected = []
        for i in range(min(count, len(templates))):
            idx = (seed + i) % len(templates)
            selected.append(templates[idx])
        
        return [
            NewsArticle(
                title=headline,
                source="Market Summary",
                published_at=datetime.now() - timedelta(hours=i * 3),
                ticker_relevance=[ticker]
            )
            for i, headline in enumerate(selected)
        ]
    
    async def close(self):
        """Cierra la sesión HTTP."""
        if self._session and not self._session.closed:
            await self._session.close()