"""
Endpoints para análisis de riesgo. 
Módulo 4: Simulaciones Monte Carlo y VaR. 
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query

from .... models.schemas import (
    RiskAnalysisRequest,
    RiskAnalysisResponse,
    OptimizationRequest
)
from ....models.enums import TimeframePreset
from ....services.risk_service import RiskService
from .... services.optimization_service import OptimizationService
from ....core.exceptions import RiskAnalysisException, SmartAllocatorException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/risk", tags=["Risk Analysis"])


def get_risk_service() -> RiskService:
    """Dependency injection para RiskService."""
    return RiskService()


def get_optimization_service() -> OptimizationService:
    """Dependency injection para OptimizationService."""
    return OptimizationService()


@router.post(
    "/analyze",
    response_model=RiskAnalysisResponse,
    summary="Análisis completo de riesgo",
    description="""
    Ejecuta análisis completo de riesgo para un portafolio.
    
    ## Incluye:
    - **Value at Risk (VaR)**: Pérdida máxima esperada a diferentes niveles de confianza
    - **Expected Shortfall (CVaR)**: Pérdida promedio en el peor escenario
    - **Simulación Monte Carlo**: Miles de escenarios futuros posibles
    - **Análisis de estrés**: Impacto de crisis históricas
    - **Contribución al riesgo**: Qué activo aporta más riesgo
    
    ## Parámetros importantes:
    - `num_simulations`: Más simulaciones = más precisión (default: 5000)
    - `simulation_days`: Horizonte de predicción (default: 252 = 1 año)
    - `confidence_levels`: Niveles para VaR (default: 90%, 95%, 99%)
    """
)
async def analyze_risk(
    request: RiskAnalysisRequest,
    risk_service: RiskService = Depends(get_risk_service)
) -> RiskAnalysisResponse:
    """Endpoint principal de análisis de riesgo."""
    
    logger.info(
        f"Risk analysis requested for {len(request.tickers)} assets, "
        f"portfolio value: ${request.portfolio_value:,.2f}"
    )
    
    try:
        result = await risk_service.analyze_risk(request)
        
        logger.info(
            f"Risk analysis complete.  "
            f"VaR 95%: ${result.risk_metrics.var_results[1]. var_amount:,.2f}"
        )
        
        return result
        
    except RiskAnalysisException as e:
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
    "/analyze-optimized",
    response_model=RiskAnalysisResponse,
    summary="Analizar riesgo de portafolio optimizado",
    description="""
    Primero optimiza el portafolio y luego ejecuta análisis de riesgo.
    Combina los módulos de optimización y riesgo en un solo endpoint.
    """
)
async def analyze_optimized_portfolio_risk(
    tickers: List[str] = Query(..., min_length=2, description="Lista de tickers"),
    portfolio_value: float = Query(default=100000.0, gt=0),
    timeframe: TimeframePreset = Query(default=TimeframePreset.THREE_YEARS),
    objective:  str = Query(default="max_sharpe"),
    num_simulations: int = Query(default=5000, ge=1000, le=50000),
    risk_service: RiskService = Depends(get_risk_service),
    optimization_service: OptimizationService = Depends(get_optimization_service)
) -> RiskAnalysisResponse: 
    """Optimiza y luego analiza riesgo."""
    
    # Normalizar tickers
    tickers = [t.upper().strip() for t in tickers]
    
    logger.info(f"Optimizing and analyzing risk for:  {tickers}")
    
    # Paso 1: Optimizar portafolio
    opt_request = OptimizationRequest(
        tickers=tickers,
        timeframe=timeframe,
        objective=objective,
        use_sentiment=False  # Rápido, sin sentiment
    )
    
    opt_result = await optimization_service.optimize_portfolio(
        request=opt_request,
        sentiment_results=None
    )
    
    # Paso 2: Usar pesos optimizados para análisis de riesgo
    risk_request = RiskAnalysisRequest(
        tickers=tickers,
        weights=opt_result.weights,
        portfolio_value=portfolio_value,
        timeframe=timeframe,
        num_simulations=num_simulations
    )
    
    result = await risk_service.analyze_risk(risk_request)
    
    return result


@router.get(
    "/var/quick",
    summary="Cálculo rápido de VaR",
    description="VaR paramétrico rápido sin simulación Monte Carlo completa."
)
async def quick_var(
    tickers: List[str] = Query(..., min_length=1),
    weights: List[float] = Query(..., min_length=1),
    portfolio_value: float = Query(default=100000.0, gt=0),
    confidence_level:  float = Query(default=0.95, ge=0.9, le=0.99),
    timeframe: TimeframePreset = Query(default=TimeframePreset. THREE_YEARS),
    risk_service: RiskService = Depends(get_risk_service)
):
    """Endpoint rápido para VaR paramétrico."""
    
    # Validar que tickers y weights tengan misma longitud
    if len(tickers) != len(weights):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tickers y weights deben tener la misma longitud"
        )
    
    # Normalizar
    tickers = [t.upper().strip() for t in tickers]
    
    # Normalizar weights si no suman 1
    total_weight = sum(weights)
    if not (0.99 <= total_weight <= 1.01):
        weights = [w / total_weight for w in weights]
    
    weights_dict = dict(zip(tickers, weights))
    
    result = await risk_service.quick_var(
        tickers=tickers,
        weights=weights_dict,
        portfolio_value=portfolio_value,
        confidence_level=confidence_level,
        timeframe=timeframe
    )
    
    return result


@router.get(
    "/stress-scenarios",
    summary="Listar escenarios de estrés",
    description="Retorna los escenarios de estrés disponibles."
)
async def list_stress_scenarios():
    """Lista escenarios de estrés predefinidos."""
    return {
        "scenarios": [
            {
                "id": s["name"],
                "description": s["description"],
                "market_shock": f"{s['market_shock']*100:. 0f}%",
                "volatility_increase": f"{s['volatility_multiplier']:.1f}x"
            }
            for s in RiskService.STRESS_SCENARIOS
        ]
    }


@router.get(
    "/metrics/explanation",
    summary="Explicación de métricas de riesgo",
    description="Documentación de las métricas calculadas."
)
async def explain_metrics():
    """Explica las métricas de riesgo."""
    return {
        "metrics": {
            "VaR (Value at Risk)": {
                "description": "Pérdida máxima esperada con cierto nivel de confianza",
                "example": "VaR 95% de $5,000 significa que hay 95% de probabilidad de no perder más de $5,000",
                "interpretation": "Menor es mejor"
            },
            "Expected Shortfall (CVaR)": {
                "description": "Pérdida promedio cuando se supera el VaR",
                "example": "Si VaR 95% es $5,000 y ES es $7,500, cuando pierdes más de $5,000, en promedio pierdes $7,500",
                "interpretation": "Menor es mejor, más conservador que VaR"
            },
            "Volatilidad":  {
                "description": "Desviación estándar de los retornos",
                "example":  "Volatilidad anual de 20% significa que el retorno típicamente varía ±20% del promedio",
                "interpretation": "Menor significa menos riesgo pero también menos oportunidad"
            },
            "Max Drawdown": {
                "description": "Máxima caída desde un pico hasta un valle",
                "example": "-30% significa que en el peor momento perdiste 30% desde el máximo",
                "interpretation": "Menor es mejor"
            },
            "Sharpe Ratio": {
                "description": "Retorno ajustado por riesgo",
                "example": "Sharpe de 1.0 significa 1% de retorno extra por cada 1% de volatilidad",
                "interpretation":  "> 1.0 es bueno, > 2.0 es excelente"
            },
            "Skewness": {
                "description": "Asimetría de la distribución de retornos",
                "example": "Negativo indica más eventos de pérdida extrema",
                "interpretation": "Positivo es preferible"
            },
            "Kurtosis": {
                "description": "Grosor de las colas de la distribución",
                "example": "Alto indica más eventos extremos (fat tails)",
                "interpretation":  "Menor indica distribución más normal"
            }
        }
    }