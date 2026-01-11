"""
Router principal API v1.
Agrega todos los endpoints de módulos. 
"""
from fastapi import APIRouter

from .endpoints import market_data, sentiment

api_router = APIRouter()

# Registrar routers de cada módulo
api_router.include_router(market_data.router)
api_router.include_router(sentiment.router)

# Aquí se agregarán los módulos 3 y 4:
# api_router.include_router(optimization.router)
# api_router.include_router(risk. router)
# api_router.include_router(portfolio.router)