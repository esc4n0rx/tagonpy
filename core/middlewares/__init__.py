"""
TagonPy Middlewares System
Sistema de middlewares para interceptação de requisições
"""

from .base_middleware import BaseMiddleware
from .auth_middleware import AuthMiddleware
from .cors_middleware import CorsMiddleware
from .logging_middleware import LoggingMiddleware
from .assets_middleware import AssetsMiddleware  # NOVO

__all__ = [
    'BaseMiddleware',
    'AuthMiddleware', 
    'CorsMiddleware',
    'LoggingMiddleware',
    'AssetsMiddleware'  # NOVO
]