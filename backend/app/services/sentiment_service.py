"""
Servicio de análisis de sentimiento con FinBERT. 
Procesa headlines y genera scores para Black-Litterman.
"""
import logging
from typing import Dict, List
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np

from ..config import get_settings
from ..core. exceptions import SentimentAnalysisException
from ..models.schemas import (
    NewsArticle,
    SentimentResult,
    TickerSentimentSummary,
    SentimentAnalysisResponse
)
from ..models.enums import SentimentLabel

logger = logging. getLogger(__name__)
settings = get_settings()


class SentimentService:
    """
    Servicio de análisis de sentimiento usando FinBERT. 
    Implementa lazy loading del modelo y procesamiento por lotes. 
    """
    
    _instance = None
    _model = None
    _tokenizer = None
    _executor = ThreadPoolExecutor(max_workers=2)
    
    # Mapeo de labels de FinBERT
    LABEL_MAP = {
        0: SentimentLabel.POSITIVE,
        1: SentimentLabel.NEGATIVE,
        2: SentimentLabel.NEUTRAL,
    }
    
    # Umbrales para clasificación por score
    BULLISH_THRESHOLD = 0.15       # > 15% score = Bullish
    BEARISH_THRESHOLD = -0.15      # < -15% score = Bearish
    
    def __new__(cls):
        """Singleton pattern para reutilizar modelo cargado."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self. model_name = settings.FINBERT_MODEL
        self.batch_size = settings.SENTIMENT_BATCH_SIZE
        self. device = "cuda" if torch. cuda.is_available() else "cpu"
    
    async def initialize_model(self) -> None:
        """Carga el modelo de forma asíncrona."""
        if self._model is not None:
            return
        
        logger.info(f"Loading FinBERT model:  {self.model_name}")
        
        loop = asyncio. get_event_loop()
        try:
            await loop.run_in_executor(
                self._executor,
                self._load_model_sync
            )
            logger.info(f"Model loaded successfully on {self.device}")
        except Exception as e: 
            logger.exception(f"Failed to load model:  {e}")
            raise SentimentAnalysisException(
                "Error cargando modelo de sentimiento",
                model_error=str(e)
            )
    
    def _load_model_sync(self) -> None:
        """Carga síncrona del modelo (ejecutada en thread pool)."""
        SentimentService._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        SentimentService._model = AutoModelForSequenceClassification.from_pretrained(
            self.model_name
        )
        SentimentService._model.to(self.device)
        SentimentService._model.eval()
    
    async def analyze_sentiment(
        self,
        tickers: List[str],
        news_by_ticker: Dict[str, List[NewsArticle]]
    ) -> SentimentAnalysisResponse:
        """
        Analiza sentimiento para todos los tickers.
        
        Args:
            tickers: Lista de símbolos
            news_by_ticker: Diccionario de noticias por ticker
            
        Returns:
            SentimentAnalysisResponse con análisis completo
        """
        await self.initialize_model()
        
        results: Dict[str, TickerSentimentSummary] = {}
        all_scores = []
        
        for ticker in tickers:
            articles = news_by_ticker.get(ticker, [])
            
            if not articles:
                results[ticker] = self._create_neutral_summary(ticker)
                all_scores.append(0.0)
                continue
            
            # Extraer headlines
            headlines = [article.title for article in articles if article.title]
            
            if not headlines: 
                results[ticker] = self._create_neutral_summary(ticker)
                all_scores.append(0.0)
                continue
            
            # Analizar sentimiento
            sentiment_results = await self._analyze_headlines(headlines)
            
            # Agregar resultados
            summary = self._aggregate_sentiment(ticker, sentiment_results)
            results[ticker] = summary
            all_scores. append(summary.sentiment_score)
        
        # Calcular índice agregado del mercado
        market_index = np.mean(all_scores) if all_scores else 0.0
        
        return SentimentAnalysisResponse(
            analysis_timestamp=datetime.now(),
            tickers_analyzed=tickers,
            results=results,
            market_sentiment_index=round(market_index, 4),
            model_used=self.model_name
        )
    
    async def _analyze_headlines(
        self, 
        headlines:  List[str]
    ) -> List[SentimentResult]: 
        """Analiza una lista de headlines con FinBERT."""
        loop = asyncio.get_event_loop()
        
        all_results = []
        
        for i in range(0, len(headlines), self.batch_size):
            batch = headlines[i:i + self.batch_size]
            
            batch_results = await loop.run_in_executor(
                self._executor,
                self._process_batch_sync,
                batch
            )
            all_results.extend(batch_results)
        
        return all_results
    
    def _process_batch_sync(
        self, 
        headlines: List[str]
    ) -> List[SentimentResult]: 
        """Procesamiento síncrono de un batch (ejecutado en thread pool)."""
        results = []
        
        with torch.no_grad():
            inputs = self._tokenizer(
                headlines,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            ).to(self.device)
            
            outputs = self._model(**inputs)
            probabilities = torch.softmax(outputs.logits, dim=1)
            
            for idx, headline in enumerate(headlines):
                probs = probabilities[idx].cpu().numpy()
                predicted_class = probs.argmax()
                
                results.append(SentimentResult(
                    headline=headline,
                    label=self.LABEL_MAP[predicted_class],
                    confidence=float(probs[predicted_class]),
                    scores={
                        "positive": float(probs[0]),
                        "negative": float(probs[1]),
                        "neutral": float(probs[2])
                    }
                ))
        
        return results
    
    def _aggregate_sentiment(
        self,
        ticker: str,
        results: List[SentimentResult]
    ) -> TickerSentimentSummary: 
        """
        Agrega resultados de sentimiento en un score consolidado.
        
        El score final se calcula como: 
        score = (positive_weighted - negative_weighted) / total
        
        El sentimiento dominante se determina por el SCORE, no por conteo.
        """
        if not results:
            return self._create_neutral_summary(ticker)
        
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        weighted_positive = 0.0
        weighted_negative = 0.0
        total_confidence = 0.0
        
        for result in results:
            confidence = result.confidence
            total_confidence += confidence
            
            if result. label == SentimentLabel. POSITIVE:
                positive_count += 1
                weighted_positive += confidence
            elif result.label == SentimentLabel. NEGATIVE:
                negative_count += 1
                weighted_negative += confidence
            else: 
                neutral_count += 1
        
        total = len(results)
        
        # Score consolidado:  rango [-1, +1]
        if total_confidence > 0:
            sentiment_score = (weighted_positive - weighted_negative) / total_confidence
        else:
            sentiment_score = 0.0
        
        # ============================================
        # CAMBIO PRINCIPAL:  Clasificar por SCORE, no por conteo
        # ============================================
        dominant = self._classify_by_score(sentiment_score)
        
        return TickerSentimentSummary(
            ticker=ticker,
            sentiment_score=round(sentiment_score, 4),
            dominant_sentiment=dominant,
            confidence_avg=round(total_confidence / total, 4),
            articles_analyzed=total,
            positive_ratio=round(positive_count / total, 4),
            negative_ratio=round(negative_count / total, 4),
            neutral_ratio=round(neutral_count / total, 4),
            headlines=results
        )
    
    def _classify_by_score(self, score: float) -> SentimentLabel:
        """
        Clasifica el sentimiento basado en el score agregado.
        
        Umbrales: 
        - Bullish:   score > 0.15 (15%)
        - Bearish: score < -0.15 (-15%)
        - Neutral: entre -0.15 y 0.15
        """
        if score >= self.BULLISH_THRESHOLD:
            return SentimentLabel.POSITIVE
        elif score <= self.BEARISH_THRESHOLD:
            return SentimentLabel.NEGATIVE
        else:
            return SentimentLabel. NEUTRAL
    
    def _create_neutral_summary(self, ticker: str) -> TickerSentimentSummary:
        """Crea un resumen neutral cuando no hay datos."""
        return TickerSentimentSummary(
            ticker=ticker,
            sentiment_score=0.0,
            dominant_sentiment=SentimentLabel.NEUTRAL,
            confidence_avg=0.0,
            articles_analyzed=0,
            positive_ratio=0.0,
            negative_ratio=0.0,
            neutral_ratio=1.0,
            headlines=[]
        )
    
    def get_black_litterman_views(
        self,
        sentiment_results:  Dict[str, TickerSentimentSummary],
        base_view_magnitude: float = 0.05
    ) -> Dict[str, float]:
        """
        Convierte scores de sentimiento en views para Black-Litterman.
        
        El score de sentimiento [-1, +1] se escala a un retorno esperado
        ajustado.  Por ejemplo, un score de +0.5 con magnitud base de 5%
        resulta en una view de +2.5% de retorno esperado adicional. 
        
        Args:
            sentiment_results: Resultados del análisis de sentimiento
            base_view_magnitude: Magnitud máxima del ajuste (default 5%)
            
        Returns: 
            Diccionario ticker -> retorno esperado ajustado
        """
        views = {}
        
        for ticker, summary in sentiment_results.items():
            view = summary.sentiment_score * base_view_magnitude
            views[ticker] = round(view, 6)
        
        return views