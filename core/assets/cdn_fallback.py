from typing import Dict, Any, Optional
import asyncio
import aiohttp
from pathlib import Path

class TailwindCDNManager:
    """
    Gerenciador de Tailwind CSS via CDN
    Fornece fallback quando compilação local falha
    """
    
    def __init__(self):
        self.cdn_urls = {
            "tailwind_play": "https://cdn.tailwindcss.com",
            "tailwind_official": "https://unpkg.com/tailwindcss@^4.0/dist/tailwind.min.css",
            "jsdelivr": "https://cdn.jsdelivr.net/npm/tailwindcss@4.1.11/tailwind.min.css"
        }
        self.custom_config = {
            "theme": {
                "extend": {
                    "colors": {
                        "tagonpy": {
                            "50": "#f0f9ff",
                            "500": "#3b82f6", 
                            "900": "#1e3a8a"
                        }
                    }
                }
            },
            "darkMode": "class"
        }
        self.is_available = True
        self.selected_strategy = "cdn_play"  # Padrão: Tailwind Play CDN
    
    async def check_cdn_availability(self) -> Dict[str, Any]:
        """
        Verifica disponibilidade dos CDNs do Tailwind
        """
        print("🌐 Verificando disponibilidade dos CDNs...")
        
        results = {}
        
        for name, url in self.cdn_urls.items():
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                    if name == "tailwind_play":
                        # Tailwind Play CDN não tem endpoint específico para testar
                        results[name] = {"available": True, "method": "script"}
                    else:
                        # Testa CDNs de CSS
                        async with session.head(url) as response:
                            results[name] = {
                                "available": response.status == 200,
                                "method": "css_link"
                            }
            except Exception as e:
                print(f"⚠️ CDN {name} indisponível: {str(e)}")
                results[name] = {"available": False, "error": str(e)}
        
        # Escolhe o melhor CDN disponível
        if results.get("tailwind_play", {}).get("available"):
            self.selected_strategy = "cdn_play"
            print("✅ Usando Tailwind Play CDN (script)")
        elif results.get("tailwind_official", {}).get("available"):
            self.selected_strategy = "cdn_official"
            print("✅ Usando Tailwind Official CDN (css)")
        elif results.get("jsdelivr", {}).get("available"):
            self.selected_strategy = "cdn_jsdelivr" 
            print("✅ Usando JSDelivr CDN (css)")
        else:
            self.is_available = False
            print("❌ Nenhum CDN do Tailwind disponível")
        
        return results
    
    def get_cdn_html_injection(self) -> str:
        """
        Retorna HTML para injetar Tailwind via CDN
        """
        if not self.is_available:
            return "<!-- Tailwind CDN não disponível -->"
        
        if self.selected_strategy == "cdn_play":
            # Tailwind Play CDN com configuração customizada
            return f'''
<!-- Tailwind CSS via CDN (Play) -->
<script src="{self.cdn_urls['tailwind_play']}"></script>
<script>
    tailwind.config = {self._get_config_js()};
    console.log('🎨 Tailwind CSS carregado via CDN (Play)');
</script>
'''
        elif self.selected_strategy == "cdn_official":
            return f'''
<!-- Tailwind CSS via CDN (Official) -->
<link href="{self.cdn_urls['tailwind_official']}" rel="stylesheet">
<script>
    console.log('🎨 Tailwind CSS carregado via CDN (Official)');
</script>
'''
        elif self.selected_strategy == "cdn_jsdelivr":
            return f'''
<!-- Tailwind CSS via CDN (JSDelivr) -->
<link href="{self.cdn_urls['jsdelivr']}" rel="stylesheet">
<script>
    console.log('🎨 Tailwind CSS carregado via CDN (JSDelivr)');
</script>
'''
        
        return "<!-- CDN strategy não reconhecida -->"
    
    def _get_config_js(self) -> str:
        """
        Converte configuração Python para JavaScript
        """
        import json
        return json.dumps(self.custom_config)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Status do gerenciador CDN
        """
        return {
            "available": self.is_available,
            "selected_strategy": self.selected_strategy,
            "cdn_urls": self.cdn_urls,
            "custom_config": self.custom_config
        }