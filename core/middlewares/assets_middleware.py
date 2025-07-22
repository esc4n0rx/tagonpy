from typing import Dict, Any, Optional
from fastapi import Request

from .base_middleware import BaseMiddleware

class AssetsMiddleware(BaseMiddleware):
    """
    Middleware para injetar assets (CSS/JS) nas páginas com suporte CDN
    """
    
    def __init__(self, asset_builder=None):
        super().__init__("assets", priority=20)
        self.asset_builder = asset_builder
    
    async def before_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Injeta informações de assets no contexto com suporte CDN
        """
        if not self.asset_builder:
            return {
                "assets": {
                    "tailwind_css": "",
                    "css_url": "/assets/css/output.css",
                    "has_tailwind": False,
                    "should_use_cdn": True,
                    "cdn_html": self._get_fallback_cdn_html()
                }
            }
        
        # Verifica se deve usar CDN
        should_use_cdn = self.asset_builder.should_use_cdn()
        
        if should_use_cdn:
            # Usa CDN
            cdn_html = self.asset_builder.get_cdn_html()
            return {
                "assets": {
                    "tailwind_css": "",
                    "css_url": "/assets/css/output.css",
                    "has_tailwind": True,
                    "should_use_cdn": True,
                    "cdn_html": cdn_html
                }
            }
        else:
            # Usa CSS local compilado
            compiled_css = self.asset_builder.get_compiled_css()
            return {
                "assets": {
                    "tailwind_css": compiled_css,
                    "css_url": self.asset_builder.get_css_url(),
                    "has_tailwind": bool(compiled_css),
                    "should_use_cdn": False,
                    "cdn_html": ""
                }
            }
    
    def _get_fallback_cdn_html(self) -> str:
        """CDN de emergência quando asset_builder não está disponível"""
        return '''
<!-- Tailwind CSS via CDN (Fallback de Emergência) -->
<script src="https://cdn.tailwindcss.com"></script>
<script>
    tailwind.config = {
        theme: {
            extend: {
                colors: {
                    'tagonpy': {
                        50: '#f0f9ff',
                        500: '#3b82f6',
                        900: '#1e3a8a'
                    }
                }
            }
        },
        darkMode: 'class'
    };
    console.log('🎨 Tailwind CSS carregado via CDN (Emergency Fallback)');
</script>
'''
    
    async def after_request(self, request: Request, response_data: Dict) -> Optional[Dict[str, Any]]:
        """
        Processa resposta após injeção de assets
        """
        return {}