from typing import Dict, Any, Optional, List
from fastapi import Request

from .base_middleware import BaseMiddleware

class CorsMiddleware(BaseMiddleware):
    """
    Middleware CORS (Cross-Origin Resource Sharing)
    Gerencia políticas de acesso entre origens diferentes
    """
    
    def __init__(self, 
                 allowed_origins: List[str] = ["*"],
                 allowed_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 allowed_headers: List[str] = ["*"],
                 allow_credentials: bool = True):
        super().__init__("cors", priority=5)  # Prioridade muito alta
        self.allowed_origins = allowed_origins
        self.allowed_methods = allowed_methods
        self.allowed_headers = allowed_headers
        self.allow_credentials = allow_credentials
    
    async def before_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Processa headers CORS antes da requisição
        """
        origin = request.headers.get("origin")
        method = request.method
        
        # Verifica se a origem é permitida
        origin_allowed = (
            "*" in self.allowed_origins or
            origin in self.allowed_origins
        )
        
        # Verifica se o método é permitido
        method_allowed = method in self.allowed_methods
        
        cors_data = {
            "origin": origin,
            "origin_allowed": origin_allowed,
            "method_allowed": method_allowed
        }
        
        # Para requisições OPTIONS (preflight)
        if method == "OPTIONS":
            cors_data["is_preflight"] = True
        
        return {"cors": cors_data}
    
    async def after_request(self, request: Request, response_data: Dict) -> Optional[Dict[str, Any]]:
        """
        Adiciona headers CORS à resposta
        """
        origin = request.headers.get("origin")
        
        cors_headers = {}
        
        # Define Access-Control-Allow-Origin
        if "*" in self.allowed_origins:
            cors_headers["Access-Control-Allow-Origin"] = "*"
        elif origin in self.allowed_origins:
            cors_headers["Access-Control-Allow-Origin"] = origin
        
        # Outros headers CORS
        cors_headers.update({
            "Access-Control-Allow-Methods": ", ".join(self.allowed_methods),
            "Access-Control-Allow-Headers": ", ".join(self.allowed_headers),
            "Access-Control-Max-Age": "86400"  # 24 horas
        })
        
        if self.allow_credentials:
            cors_headers["Access-Control-Allow-Credentials"] = "true"
        
        return {"cors_headers": cors_headers}
    
    def add_allowed_origin(self, origin: str):
        """Adiciona uma origem permitida"""
        if origin not in self.allowed_origins:
            self.allowed_origins.append(origin)
            print(f"🌐 Origem '{origin}' adicionada ao CORS")
    
    def remove_allowed_origin(self, origin: str):
        """Remove uma origem permitida"""
        if origin in self.allowed_origins:
            self.allowed_origins.remove(origin)
            print(f"🚫 Origem '{origin}' removida do CORS")