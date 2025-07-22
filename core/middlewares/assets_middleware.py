from typing import Dict, Any, Optional
from fastapi import Request

from .base_middleware import BaseMiddleware

class AssetsMiddleware(BaseMiddleware):
    """
    Middleware para injetar assets (CSS/JS) nas páginas
    """
    
    def __init__(self, asset_builder=None):
        super().__init__("assets", priority=20)
        self.asset_builder = asset_builder
    
    async def before_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Injeta informações de assets no contexto
        """
        if not self.asset_builder:
            return {}
        
        # Obtém CSS compilado do Tailwind
        compiled_css = self.asset_builder.get_compiled_css()
        css_url = self.asset_builder.get_css_url()
        
        return {
            "assets": {
                "tailwind_css": compiled_css,
                "css_url": css_url,
                "has_tailwind": bool(compiled_css)
            }
        }
    
    async def after_request(self, request: Request, response_data: Dict) -> Optional[Dict[str, Any]]:
        """
        Processa resposta após injeção de assets
        """
        return {}