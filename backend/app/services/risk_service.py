"""
Servicio de análisis de riesgo. 
Implementa simulaciones Monte Carlo y cálculo de VaR/CVaR.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from ..config import get_settings
from ..core.exceptions import RiskAnalysisException
from ..models.schemas import (
    RiskAnalysisRequest,
    RiskAnalysisResponse,
    RiskMetrics,
    VaRResult,
    MonteCarloResults,
    MonteCarloPath,
    StressScenario
)
from ..models.enums import TimeframePreset
from . market_data_service import MarketDataService

logger = logging.getLogger(__name__)
settings = get_settings()


class RiskService:
    """
    Servicio para análisis de riesgo de portafolios.
    
    Implementa: 
    - Value at Risk (VaR) - Histórico, Paramétrico, Monte Carlo
    - Expected Shortfall (CVaR)
    - Simulaciones Monte Carlo
    - Análisis de escenarios de estrés
    - Métricas de riesgo (volatilidad, drawdown, etc.)
    """
    
    # Escenarios de estrés predefinidos
    STRESS_SCENARIOS = [
        {
            "name": "market_crash_2008",
            "description": "Crisis financiera 2008 (-50% mercado)",
            "market_shock": -0.50,
            "volatility_multiplier": 3.0
        },
        {
            "name": "covid_crash_2020",
            "description":  "Crash COVID-19 Marzo 2020 (-34%)",
            "market_shock":  -0.34,
            "volatility_multiplier": 4.0
        },
        {
            "name": "moderate_correction",
            "description": "Corrección moderada (-15%)",
            "market_shock":  -0.15,
            "volatility_multiplier": 1.5
        },
        {
            "name": "severe_recession",
            "description": "Recesión severa (-40%)",
            "market_shock": -0.40,
            "volatility_multiplier": 2.5
        },
        {
            "name":  "flash_crash",
            "description":  "Flash crash (-10% en un día)",
            "market_shock": -0.10,
            "volatility_multiplier": 5.0
        }
    ]
    
    def __init__(self):
        self.market_data_service = MarketDataService()
        
    async def analyze_risk(
        self,
        request: RiskAnalysisRequest
    ) -> RiskAnalysisResponse:
        """
        Ejecuta análisis completo de riesgo para un portafolio.
        
        Args:
            request:  Parámetros del análisis
            
        Returns: 
            RiskAnalysisResponse con todas las métricas
        """
        logger.info(f"Starting risk analysis for {len(request.tickers)} assets")
        logger.info(f"Portfolio value: ${request.portfolio_value:,.2f}")
        
        try:
            # Paso 1: Obtener datos históricos
            prices_df, log_returns = await self._get_historical_data(
                request.tickers, 
                request.timeframe
            )
            
            # Paso 2: Calcular retornos del portafolio
            portfolio_returns = self._calculate_portfolio_returns(
                log_returns, 
                request. weights
            )
            
            # Paso 3: Calcular matriz de covarianza
            cov_matrix = log_returns.cov() * settings.TRADING_DAYS_PER_YEAR
            corr_matrix = log_returns.corr()
            
            # Paso 4: Ejecutar simulaciones Monte Carlo
            mc_results, simulated_paths = self._run_monte_carlo(
                portfolio_returns=portfolio_returns,
                portfolio_value=request.portfolio_value,
                num_simulations=request.num_simulations,
                simulation_days=request.simulation_days
            )
            
            # Paso 5: Calcular VaR y métricas de riesgo
            risk_metrics = self._calculate_risk_metrics(
                portfolio_returns=portfolio_returns,
                portfolio_value=request.portfolio_value,
                confidence_levels=request.confidence_levels,
                simulated_final_values=simulated_paths[: , -1]
            )
            
            # Paso 6: Calcular contribución al riesgo
            risk_contribution = self._calculate_risk_contribution(
                weights=request.weights,
                cov_matrix=cov_matrix
            )
            
            # Paso 7: Análisis de escenarios de estrés
            stress_results = self._run_stress_scenarios(
                weights=request.weights,
                portfolio_value=request.portfolio_value,
                cov_matrix=cov_matrix,
                mean_returns=log_returns.mean() * settings.TRADING_DAYS_PER_YEAR
            )
            
            return RiskAnalysisResponse(
                analysis_timestamp=datetime.now(),
                portfolio_value=request.portfolio_value,
                tickers=request.tickers,
                weights=request.weights,
                risk_metrics=risk_metrics,
                monte_carlo=mc_results,
                stress_scenarios=stress_results,
                risk_contribution=risk_contribution,
                correlation_matrix=corr_matrix. to_dict(),
                historical_start_date=prices_df.index. min().date(),
                historical_end_date=prices_df.index. max().date(),
                trading_days_analyzed=len(prices_df)
            )
            
        except Exception as e:
            logger.exception(f"Risk analysis failed: {e}")
            raise RiskAnalysisException(
                message=f"Error en análisis de riesgo: {str(e)}",
                details={"tickers": request.tickers}
            )
    
    async def _get_historical_data(
        self,
        tickers: List[str],
        timeframe: TimeframePreset
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Obtiene precios y retornos históricos."""
        days = self. market_data_service. TIMEFRAME_MAPPING[timeframe]
        from datetime import timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        prices_df = self.market_data_service._download_prices(
            tickers, start_date, end_date
        )
        
        log_returns = self.market_data_service._calculate_log_returns(prices_df)
        
        return prices_df, log_returns
    
    def _calculate_portfolio_returns(
        self,
        log_returns: pd.DataFrame,
        weights: Dict[str, float]
    ) -> pd.Series:
        """Calcula serie de retornos del portafolio."""
        weights_series = pd.Series(weights)
        # Asegurar mismo orden
        weights_series = weights_series[log_returns.columns]
        
        portfolio_returns = (log_returns * weights_series).sum(axis=1)
        return portfolio_returns
    
    def _run_monte_carlo(
        self,
        portfolio_returns: pd.Series,
        portfolio_value: float,
        num_simulations: int,
        simulation_days: int
    ) -> Tuple[MonteCarloResults, np.ndarray]:
        """
        Ejecuta simulación Monte Carlo.
        
        Usa Geometric Brownian Motion (GBM):
        S(t) = S(0) * exp((μ - σ²/2)*t + σ*W(t))
        """
        logger.info(f"Running {num_simulations} Monte Carlo simulations...")
        
        # Parámetros del modelo
        mu = portfolio_returns.mean()  # Drift diario
        sigma = portfolio_returns.std()  # Volatilidad diaria
        
        # Generar caminos aleatorios
        np.random.seed(42)  # Para reproducibilidad
        
        # Random shocks
        Z = np.random.standard_normal((num_simulations, simulation_days))
        
        # Calcular retornos simulados (GBM)
        daily_returns = (mu - 0.5 * sigma**2) + sigma * Z
        
        # Construir caminos de precios
        cumulative_returns = np.cumsum(daily_returns, axis=1)
        simulated_paths = portfolio_value * np.exp(cumulative_returns)
        
        # Agregar valor inicial
        simulated_paths = np.column_stack([
            np.full(num_simulations, portfolio_value),
            simulated_paths
        ])
        
        # Estadísticas de valores finales
        final_values = simulated_paths[:, -1]
        
        # Calcular percentiles
        percentiles = np. percentile(final_values, [5, 10, 25, 50, 75, 90, 95])
        
        # Probabilidades
        prob_profit = np.mean(final_values > portfolio_value)
        prob_loss_gt_10 = np. mean(final_values < portfolio_value * 0.90)
        prob_loss_gt_20 = np.mean(final_values < portfolio_value * 0.80)
        prob_gain_gt_10 = np. mean(final_values > portfolio_value * 1.10)
        prob_gain_gt_20 = np. mean(final_values > portfolio_value * 1.20)
        
        # Extraer caminos representativos para visualización
        sample_paths = self._extract_sample_paths(simulated_paths, simulation_days)
        
        results = MonteCarloResults(
            num_simulations=num_simulations,
            simulation_days=simulation_days,
            mean_final_value=round(float(np.mean(final_values)), 2),
            median_final_value=round(float(np.median(final_values)), 2),
            std_final_value=round(float(np.std(final_values)), 2),
            min_final_value=round(float(np. min(final_values)), 2),
            max_final_value=round(float(np.max(final_values)), 2),
            percentile_5=round(float(percentiles[0]), 2),
            percentile_10=round(float(percentiles[1]), 2),
            percentile_25=round(float(percentiles[2]), 2),
            percentile_75=round(float(percentiles[4]), 2),
            percentile_90=round(float(percentiles[5]), 2),
            percentile_95=round(float(percentiles[6]), 2),
            prob_profit=round(float(prob_profit), 4),
            prob_loss_gt_10=round(float(prob_loss_gt_10), 4),
            prob_loss_gt_20=round(float(prob_loss_gt_20), 4),
            prob_gain_gt_10=round(float(prob_gain_gt_10), 4),
            prob_gain_gt_20=round(float(prob_gain_gt_20), 4),
            sample_paths=sample_paths
        )
        
        return results, simulated_paths
    
    def _extract_sample_paths(
        self,
        simulated_paths: np.ndarray,
        simulation_days: int,
        num_sample_points: int = 50
    ) -> List[MonteCarloPath]:
        """Extrae caminos representativos para visualización."""
        # Reducir puntos para visualización
        step = max(1, simulation_days // num_sample_points)
        indices = list(range(0, simulated_paths.shape[1], step))
        
        # Calcular percentiles en cada punto temporal
        paths = []
        percentile_labels = [
            ("p5", 5), ("p25", 25), ("median", 50), ("p75", 75), ("p95", 95)
        ]
        
        for label, p in percentile_labels:
            values = [
                round(float(np.percentile(simulated_paths[:, i], p)), 2)
                for i in indices
            ]
            paths.append(MonteCarloPath(percentile=label, values=values))
        
        return paths
    
    def _calculate_risk_metrics(
        self,
        portfolio_returns: pd.Series,
        portfolio_value: float,
        confidence_levels: List[float],
        simulated_final_values: np.ndarray
    ) -> RiskMetrics:
        """Calcula métricas de riesgo completas."""
        
        # Volatilidad
        daily_vol = portfolio_returns.std()
        annual_vol = daily_vol * np.sqrt(settings.TRADING_DAYS_PER_YEAR)
        
        # VaR para cada nivel de confianza
        var_results = []
        for cl in confidence_levels:
            var_result = self._calculate_var(
                portfolio_returns=portfolio_returns,
                portfolio_value=portfolio_value,
                confidence_level=cl,
                simulated_values=simulated_final_values
            )
            var_results. append(var_result)
        
        # Drawdown
        cumulative = (1 + portfolio_returns).cumprod()
        rolling_max = cumulative.expanding().max()
        drawdowns = (cumulative - rolling_max) / rolling_max
        max_dd = drawdowns.min()
        avg_dd = drawdowns[drawdowns < 0].mean() if len(drawdowns[drawdowns < 0]) > 0 else 0
        
        # Momentos de la distribución
        skewness = float(stats.skew(portfolio_returns))
        kurtosis = float(stats.kurtosis(portfolio_returns))
        
        # Probabilidades de pérdida
        prob_loss_1 = float(np.mean(portfolio_returns < -0.01))
        prob_loss_5 = float(np.mean(portfolio_returns < -0.05))
        prob_loss_10 = float(np.mean(portfolio_returns < -0.10))
        
        return RiskMetrics(
            daily_volatility=round(daily_vol * 100, 4),
            annual_volatility=round(annual_vol * 100, 2),
            var_results=var_results,
            max_drawdown=round(max_dd * 100, 2),
            avg_drawdown=round(avg_dd * 100, 2) if avg_dd else 0,
            skewness=round(skewness, 4),
            kurtosis=round(kurtosis, 4),
            prob_loss_1_percent=round(prob_loss_1, 4),
            prob_loss_5_percent=round(prob_loss_5, 4),
            prob_loss_10_percent=round(prob_loss_10, 4)
        )
    
    def _calculate_var(
        self,
        portfolio_returns: pd.Series,
        portfolio_value: float,
        confidence_level: float,
        simulated_values: np.ndarray
    ) -> VaRResult:
        """
        Calcula VaR usando método Monte Carlo.
        
        VaR = Valor en riesgo al nivel de confianza especificado
        ES = Expected Shortfall (promedio de pérdidas más allá del VaR)
        """
        alpha = 1 - confidence_level
        
        # VaR Monte Carlo (basado en simulaciones)
        losses = portfolio_value - simulated_values
        var_amount = float(np.percentile(losses, confidence_level * 100))
        var_percent = var_amount / portfolio_value
        
        # Expected Shortfall (CVaR)
        tail_losses = losses[losses >= var_amount]
        es_amount = float(np.mean(tail_losses)) if len(tail_losses) > 0 else var_amount
        es_percent = es_amount / portfolio_value
        
        return VaRResult(
            confidence_level=confidence_level,
            var_percent=round(var_percent * 100, 2),
            var_amount=round(var_amount, 2),
            expected_shortfall=round(es_amount, 2),
            es_percent=round(es_percent * 100, 2)
        )
    
    def _calculate_risk_contribution(
        self,
        weights: Dict[str, float],
        cov_matrix: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Calcula la contribución marginal al riesgo de cada activo.
        
        Risk Contribution = w_i * (Σ * w)_i / σ_p
        """
        tickers = list(weights.keys())
        w = np.array([weights[t] for t in tickers])
        
        # Asegurar orden correcto en cov_matrix
        cov = cov_matrix.loc[tickers, tickers]. values
        
        # Volatilidad del portafolio
        port_var = w @ cov @ w
        port_vol = np.sqrt(port_var)
        
        # Contribución marginal
        marginal_contrib = cov @ w
        risk_contrib = w * marginal_contrib / port_vol
        
        # Normalizar a porcentaje
        total_contrib = np.sum(risk_contrib)
        risk_contrib_pct = risk_contrib / total_contrib * 100
        
        return {t: round(float(rc), 2) for t, rc in zip(tickers, risk_contrib_pct)}
    
    def _run_stress_scenarios(
        self,
        weights: Dict[str, float],
        portfolio_value: float,
        cov_matrix: pd. DataFrame,
        mean_returns:  pd.Series
    ) -> List[StressScenario]:
        """Ejecuta escenarios de estrés predefinidos."""
        results = []
        
        tickers = list(weights.keys())
        w = np.array([weights[t] for t in tickers])
        
        for scenario in self. STRESS_SCENARIOS:
            # Impacto del shock de mercado
            # Asumimos beta promedio de 1.0 para simplificar
            shock = scenario["market_shock"]
            
            # El impacto varía por activo basado en su volatilidad relativa
            cov = cov_matrix.loc[tickers, tickers].values
            asset_vols = np.sqrt(np.diag(cov))
            avg_vol = np.mean(asset_vols)
            
            # Ajustar shock por volatilidad relativa
            asset_shocks = shock * (asset_vols / avg_vol)
            
            # Impacto en el portafolio
            portfolio_impact = float(np.sum(w * asset_shocks))
            portfolio_impact_amount = portfolio_value * portfolio_impact
            
            # VaR bajo estrés (volatilidad aumentada)
            stressed_vol = np.sqrt(w @ cov @ w) * scenario["volatility_multiplier"]
            var_stress = portfolio_value * stressed_vol * 1.645  # 95% VaR
            
            results.append(StressScenario(
                scenario_name=scenario["name"],
                description=scenario["description"],
                portfolio_impact_percent=round(portfolio_impact * 100, 2),
                portfolio_impact_amount=round(portfolio_impact_amount, 2),
                var_under_stress=round(var_stress, 2)
            ))
        
        return results
    
    async def quick_var(
        self,
        tickers: List[str],
        weights: Dict[str, float],
        portfolio_value: float,
        confidence_level: float = 0.95,
        timeframe: TimeframePreset = TimeframePreset.FIVE_YEARS
    ) -> Dict: 
        """
        Cálculo rápido de VaR sin simulación Monte Carlo completa.
        Usa método paramétrico (más rápido).
        """
        _, log_returns = await self._get_historical_data(tickers, timeframe)
        portfolio_returns = self._calculate_portfolio_returns(log_returns, weights)
        
        # VaR paramétrico
        mu = portfolio_returns.mean()
        sigma = portfolio_returns.std()
        
        # Asumiendo distribución normal
        z_score = stats.norm.ppf(1 - confidence_level)
        var_1day = portfolio_value * (mu - z_score * sigma)
        
        return {
            "var_1day_percent": round(-z_score * sigma * 100, 2),
            "var_1day_amount": round(var_1day, 2),
            "var_10day_amount": round(var_1day * np.sqrt(10), 2),
            "confidence_level": confidence_level,
            "method": "parametric"
        }