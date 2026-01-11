"""
Entry point de la aplicación FastAPI.
Configuración de middleware, CORS, y manejo global de errores.
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .config import get_settings
from .api.v1.router import api_router
from .core.exceptions import SmartAllocatorException
from .services.sentiment_service import SentimentService

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator: 
    """
    Lifecycle manager para startup/shutdown. 
    Precarga recursos costosos como el modelo NLP.
    """
    logger.info("🚀 Starting Smart-Asset Allocator API...")
    
    # Startup:  Precargar modelo de sentimiento (opcional, puede ser lazy)
    if not settings.DEBUG:
        try:
            sentiment_service = SentimentService()
            await sentiment_service.initialize_model()
            logger.info("✅ FinBERT model preloaded")
        except Exception as e: 
            logger.warning(f"⚠️ Model preload failed (will load on first request): {e}")
    
    logger.info("✅ API ready to accept requests")
    
    yield  # La aplicación corre aquí
    
    # Shutdown
    logger.info("🛑 Shutting down Smart-Asset Allocator API...")


# Crear instancia de FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## Smart-Asset Allocator API
    
    Plataforma de optimización de portafolios institucional que combina: 
    
    - **Análisis Cuantitativo**: Modelo Black-Litterman
    - **Inteligencia Artificial**: Análisis de sentimiento con FinBERT
    - **Validación de Riesgo**:  Simulaciones Monte Carlo
    
    ### Módulos: 
    1. 📊 **Market Data**: Datos históricos y matrices de covarianza
    2. 🧠 **Sentiment**:  Análisis NLP de noticias financieras
    3. ⚖️ **Optimization**: Black-Litterman (próximamente)
    4. 📈 **Risk**: Monte Carlo VaR (próximamente)
    """,
    openapi_url=f"{settings. API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Exception Handlers ====================

@app.exception_handler(SmartAllocatorException)
async def smart_allocator_exception_handler(
    request: Request, 
    exc: SmartAllocatorException
) -> JSONResponse:
    """Handler para excepciones de dominio."""
    logger.error(f"Domain exception: {exc. code} - {exc.message}")
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "error":  {
                "code": exc.code,
                "message": exc. message,
                "details": exc.details
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, 
    exc: RequestValidationError
) -> JSONResponse:
    """Handler para errores de validación Pydantic."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ". ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status. HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "errors": errors
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request, 
    exc: Exception
) -> JSONResponse:
    """Handler global para excepciones no manejadas."""
    logger.exception(f"Unhandled exception: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success":  False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred" if not settings.DEBUG else str(exc)
            }
        }
    )


# ==================== Routes ====================

# Incluir API v1
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint con información básica."""
    return {
        "app":  settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "docs":  "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check para load balancers."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION
    }