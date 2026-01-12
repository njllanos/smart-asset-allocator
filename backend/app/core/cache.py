# backend/app/core/cache.py

import asyncio
from functools import wraps
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Tuple, List

def make_hashable(value):
    """Convierte listas y diccionarios en tuplas hashables recursivamente."""
    if isinstance(value, list):
        return tuple(make_hashable(v) for v in value)
    elif isinstance(value, dict):
        return tuple(sorted((k, make_hashable(v)) for k, v in value.items()))
    return value

class AsyncTTLChecker:
    """Caché simple en memoria para funciones asíncronas con TTL."""
    
    def __init__(self, ttl_seconds: int = 3600):
        self.cache: Dict[Tuple, Any] = {}
        self.timestamps: Dict[Tuple, datetime] = {}
        self.ttl = ttl_seconds

    def __call__(self, func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 1. Ignorar 'self' (el primer argumento si es un método de clase)
            start_index = 1 if args and hasattr(args[0], '__class__') else 0
            clean_args = args[start_index:]
            
            # 2. Convertir argumentos a hashables (List -> Tuple)
            key_args = tuple(make_hashable(arg) for arg in clean_args)
            key_kwargs = tuple(sorted((k, make_hashable(v)) for k, v in kwargs.items()))
            
            # 3. Crear la clave única
            key = (func.__name__, key_args, key_kwargs)
            
            now = datetime.now()
            
            # 4. Verificar caché
            if key in self.cache:
                timestamp = self.timestamps[key]
                if now - timestamp < timedelta(seconds=self.ttl):
                    return self.cache[key]
            
            # 5. Ejecutar y guardar
            result = await func(*args, **kwargs)
            self.cache[key] = result
            self.timestamps[key] = now
            return result
            
        return wrapper

cache_response = AsyncTTLChecker(ttl_seconds=3600)