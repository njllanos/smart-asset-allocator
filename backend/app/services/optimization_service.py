"""
Servicio de optimización de portafolio.  
Implementa Black-Litterman con PyPortfolioOpt.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pypfopt import (
    BlackLittermanModel,
    EfficientFrontier,
    expected_returns,
    risk_models,
)

from ..config import get_settings
from ..core.exceptions import OptimizationException
from ..models. schemas import (
    OptimizationRequest,
    OptimizationResponse,
    PortfolioAllocation,
    PortfolioMetrics,
    BlackLittermanParams,
    BlackLittermanView,
    TickerSentimentSummary
)
from ..models.enums import TimeframePreset
from .  market_data_service import MarketDataService

logger = logging.getLogger(__name__)
settings = get_settings()


class OptimizationService:
    """
    Servicio de optimización usando Black-Litterman y PyPortfolioOpt.  
    """
    
    # ============================================
    # PARÁMETROS DE AJUSTE DE SENTIMIENTO
    # ============================================
    # Escala:  sentiment_score [-1, 1] * SCALE = view de retorno
    # 0.03 significa que sentimiento de +1. 0 genera view de +3%
    SENTIMENT_TO_RETURN_SCALE = 0.02  # Reducido de 0.05 a 0.03
    
    # Factor de confianza máxima para views de sentimiento
    # Black-Litterman es muy sensible a la confianza
    # Valores bajos = sentimiento ajusta levemente los retornos históricos
    # Valores altos = sentimiento domina sobre retornos históricos
    MAX_SENTIMENT_CONFIDENCE = 0.15  # Máximo 25% de confianza
    
    def __init__(self):
        self.market_data_service = MarketDataService()
        self.tau = 0.05  # Parámetro de incertidumbre Black-Litterman
        
    async def optimize_portfolio(
        self,
        request: OptimizationRequest,
        sentiment_results: Optional[Dict[str, TickerSentimentSummary]] = None
    ) -> OptimizationResponse:
        """
        Optimiza el portafolio usando Black-Litterman.
        """
        logger.info(f"Starting portfolio optimization for {len(request.tickers)} assets")
        logger.info(f"Objective: {request.objective}, Use sentiment: {request.use_sentiment}")
        
        try:
            # Paso 1: Obtener datos de mercado
            prices_df = await self._get_prices(request.tickers, request.timeframe)
            
            # Paso 2: Calcular retornos esperados y covarianza
            mu = expected_returns. mean_historical_return(prices_df)
            cov_matrix = risk_models.sample_cov(prices_df)
            
            # Log de retornos históricos para debug
            logger.info(f"Historical returns: {dict(mu. round(4))}")
            
            # Paso 3: Preparar views para Black-Litterman
            views, view_confidences = self._prepare_views(
                request=request,
                sentiment_results=sentiment_results,
                tickers=request.tickers
            )
            
            # Paso 4: Aplicar Black-Litterman si hay views
            bl_params = None
            posterior_mu = mu  # Default:  usar retornos históricos
            
            if views:
                result = self._apply_black_litterman(
                    cov_matrix=cov_matrix,
                    views=views,
                    view_confidences=view_confidences,
                    market_prior=mu  # Usar retornos históricos como prior
                )
                if result[0] is not None:
                    posterior_mu = result[0]
                    bl_params = result[1]
                    logger.info(f"Posterior returns after BL: {dict(posterior_mu.round(4))}")
            
            # Paso 5: Optimizar
            weights, metrics = self._optimize(
                mu=posterior_mu,
                cov_matrix=cov_matrix,
                objective=request.objective,
                constraints=request.constraints,
                risk_free_rate=request.risk_free_rate,
                target_return=request.target_return,
                target_volatility=request.target_volatility
            )
            
            # Paso 6: Construir respuesta
            allocations = self._build_allocations(weights, posterior_mu)
            
            # Calcular frontera eficiente
            efficient_frontier = self._calculate_efficient_frontier(
                posterior_mu, cov_matrix, request.risk_free_rate
            )
            
            return OptimizationResponse(
                optimization_timestamp=datetime.now(),
                objective_used=request.objective,
                tickers=request.tickers,
                allocations=allocations,
                weights=weights,
                metrics=metrics,
                black_litterman_params=bl_params,
                sentiment_views_used=request.use_sentiment and sentiment_results is not None,
                constraints_applied=request.constraints,
                efficient_frontier=efficient_frontier
            )
            
        except Exception as e:
            logger.exception(f"Optimization failed: {e}")
            raise OptimizationException(
                message=f"Error en optimización: {str(e)}",
                details={"tickers": request.tickers, "objective": request.objective}
            )
    
    async def _get_prices(
        self, 
        tickers: List[str], 
        timeframe: TimeframePreset
    ) -> pd.DataFrame:
        """Obtiene DataFrame de precios históricos."""
        market_data = await self.market_data_service.get_market_data(tickers, timeframe)
        
        days = self.market_data_service. TIMEFRAME_MAPPING[timeframe]
        from datetime import timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        prices_df = self.market_data_service._download_prices(
            tickers, start_date, end_date
        )
        return prices_df
    
    def _prepare_views(
        self,
        request: OptimizationRequest,
        sentiment_results: Optional[Dict[str, TickerSentimentSummary]],
        tickers: List[str]
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Prepara views para Black-Litterman.
        
        IMPORTANTE: Las confianzas deben ser bajas (0.1-0.3) para que
        el sentimiento sea un AJUSTE, no un REEMPLAZO de los retornos históricos.
        """
        views = {}
        confidences = {}
        
        # Prioridad 1: Views manuales
        if request.views:
            for view in request.views:
                if view.ticker in tickers:
                    views[view.ticker] = view.view
                    confidences[view. ticker] = view.confidence
            logger.info(f"Using {len(views)} manual views")
            return views, confidences
        
        # Prioridad 2: Views desde sentiment
        if request.use_sentiment and sentiment_results: 
            for ticker, summary in sentiment_results.items():
                if ticker in tickers:
                    # Convertir sentiment score [-1, 1] a view de retorno
                    # sentiment_score=0.5 * 0.03 = 0.015 (1.5% view)
                    view_return = summary.sentiment_score * self.SENTIMENT_TO_RETURN_SCALE
                    views[ticker] = view_return
                    
                    # ============================================
                    # CÁLCULO DE CONFIANZA (CRÍTICO)
                    # ============================================
                    # Factores: 
                    # 1. Confianza del modelo (0-1)
                    # 2. Cantidad de artículos (más = más confiable)
                    # 3. Magnitud del sentimiento (extremos = menos confiable)
                    
                    base_confidence = summary.confidence_avg
                    
                    # Factor por cantidad de artículos (escala logarítmica)
                    # 5 artículos = 0.5, 10 = 0.7, 20 = 0.85, 30+ = 1.0
                    article_factor = min(np.log10(summary.articles_analyzed + 1) / np.log10(31), 1.0)
                    
                    # Factor por extremidad (sentimientos muy extremos son menos confiables)
                    # score=0 -> factor=1, score=±1 -> factor=0.7
                    extremity_factor = 1.0 - 0.3 * abs(summary.sentiment_score)
                    
                    # Confianza final: limitada por MAX_SENTIMENT_CONFIDENCE
                    raw_confidence = base_confidence * article_factor * extremity_factor
                    final_confidence = min(raw_confidence, self.MAX_SENTIMENT_CONFIDENCE)
                    
                    confidences[ticker] = final_confidence
                    
                    logger.debug(
                        f"{ticker}: sentiment={summary.sentiment_score:.2f}, "
                        f"view={view_return:.4f}, confidence={final_confidence:.3f}"
                    )
            
            logger.info(f"Generated {len(views)} views from sentiment analysis")
            logger.info(f"View confidences: {dict((k, round(v, 3)) for k, v in confidences.items())}")
        
        return views, confidences
    
    def _apply_black_litterman(
        self,
        cov_matrix: pd.DataFrame,
        views: Dict[str, float],
        view_confidences: Dict[str, float],
        market_prior:  pd.Series
    ) -> Tuple[Optional[pd.Series], Optional[BlackLittermanParams]]:
        """
        Aplica modelo Black-Litterman. 
        
        Usa los retornos históricos como prior en lugar de calcular
        retornos implícitos del mercado (más estable para pocos activos).
        """
        tickers = cov_matrix.columns.tolist()
        
        # Filtrar views válidas
        viewdict = {k: v for k, v in views.items() if k in tickers}
        
        if not viewdict:
            return None, None
        
        try:
            # Crear Black-Litterman model
            # Usamos los retornos históricos como pi (prior)
            bl = BlackLittermanModel(
                cov_matrix=cov_matrix,
                pi=market_prior,  # Retornos históricos como prior
                absolute_views=viewdict,
                tau=self.tau,
                omega="idzorek",
                view_confidences=[view_confidences. get(t, 0.1) for t in viewdict. keys()]
            )
            
            # Obtener retornos posteriores
            posterior_returns = bl.bl_returns()
            
            bl_params = BlackLittermanParams(
                tau=self.tau,
                market_implied_returns={t: round(float(v) * 100, 2) for t, v in market_prior.items()},
                posterior_returns={t: round(float(v) * 100, 2) for t, v in posterior_returns.items()},
                views_applied={t: round(v * 100, 2) for t, v in viewdict.items()}
            )
            
            return posterior_returns, bl_params
            
        except Exception as e: 
            logger.warning(f"Black-Litterman failed, using historical returns: {e}")
            return None, None
    
    def _optimize(
        self,
        mu: pd.Series,
        cov_matrix:  pd.DataFrame,
        objective: str,
        constraints,
        risk_free_rate:  float,
        target_return:  Optional[float],
        target_volatility: Optional[float]
    ) -> Tuple[Dict[str, float], PortfolioMetrics]:
        """
        Ejecuta la optimización según el objetivo especificado.
        """
        ef = EfficientFrontier(
            mu, 
            cov_matrix,
            weight_bounds=(constraints.min_weight, constraints.max_weight)
        )
        
        if objective == "max_sharpe": 
            weights = ef.max_sharpe(risk_free_rate=risk_free_rate)
        elif objective == "min_volatility":
            weights = ef.min_volatility()
        elif objective == "efficient_return" and target_return: 
            weights = ef.efficient_return(target_return=target_return)
        elif objective == "efficient_risk" and target_volatility:
            weights = ef.efficient_risk(target_volatility=target_volatility)
        else:
            weights = ef.max_sharpe(risk_free_rate=risk_free_rate)
        
        cleaned_weights = ef.clean_weights(cutoff=0.01)
        
        performance = ef.portfolio_performance(
            verbose=False, 
            risk_free_rate=risk_free_rate
        )
        
        metrics = PortfolioMetrics(
            expected_annual_return=round(performance[0] * 100, 2),
            annual_volatility=round(performance[1] * 100, 2),
            sharpe_ratio=round(performance[2], 3)
        )
        
        return cleaned_weights, metrics
    
    def _build_allocations(
        self, 
        weights: Dict[str, float], 
        expected_returns: pd.Series
    ) -> List[PortfolioAllocation]:
        """Construye lista de asignaciones ordenada por peso."""
        allocations = []
        
        for ticker, weight in weights.items():
            if weight > 0.001: 
                exp_ret = expected_returns. get(ticker, 0)
                allocations.append(PortfolioAllocation(
                    ticker=ticker,
                    weight=round(weight, 4),
                    weight_percent=round(weight * 100, 2),
                    expected_return=round(float(exp_ret) * 100, 2)
                ))
        
        allocations.sort(key=lambda x: x.weight, reverse=True)
        return allocations
    
    def _calculate_efficient_frontier(
        self,
        mu: pd.Series,
        cov_matrix: pd.DataFrame,
        risk_free_rate: float,
        n_points: int = 20
    ) -> List[Dict[str, float]]:
        """Calcula puntos de la frontera eficiente."""
        frontier_points = []
        
        try:
            min_ret = float(mu.min())
            max_ret = float(mu.max())
            
            target_returns = np.linspace(min_ret, max_ret, n_points)
            
            for target in target_returns:
                try:
                    ef = EfficientFrontier(mu, cov_matrix)
                    ef.efficient_return(target_return=target)
                    perf = ef.portfolio_performance(risk_free_rate=risk_free_rate)
                    
                    frontier_points.append({
                        "return": round(perf[0] * 100, 2),
                        "volatility": round(perf[1] * 100, 2),
                        "sharpe": round(perf[2], 3)
                    })
                except Exception: 
                    continue
                    
        except Exception as e:
            logger.warning(f"Could not calculate efficient frontier: {e}")
        
        return frontier_points
    
    def sentiment_to_views(
        self, 
        sentiment_results: Dict[str, TickerSentimentSummary]
    ) -> List[BlackLittermanView]: 
        """Convierte resultados de sentiment a views de Black-Litterman."""
        views = []
        for ticker, summary in sentiment_results. items():
            view_return = summary.sentiment_score * self.SENTIMENT_TO_RETURN_SCALE
            
            article_factor = min(np.log10(summary. articles_analyzed + 1) / np.log10(31), 1.0)
            extremity_factor = 1.0 - 0.3 * abs(summary.sentiment_score)
            confidence = min(
                summary.confidence_avg * article_factor * extremity_factor,
                self.MAX_SENTIMENT_CONFIDENCE
            )
            
            views.append(BlackLittermanView(
                ticker=ticker,
                view=round(view_return, 4),
                confidence=round(confidence, 3)
            ))
        
        return views