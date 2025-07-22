import os
import asyncio
import platform
from pathlib import Path
from typing import Dict, Optional, List
from .tailwind_manager import TailwindManager

class AssetBuilder:
    """
    Construtor de assets do TagonPy com suporte CDN
    Gerencia CSS, JS e outros recursos estáticos
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.tailwind_manager = TailwindManager(project_root)
        self.is_watching = False
        self.initialization_error = None
        
        print(f"🏗️ Asset Builder inicializado para: {self.project_root.absolute()}")
        
    async def initialize(self):
        """Inicializa o sistema de assets com tratamento de erro robusto"""
        print("🏗️ Inicializando Asset Builder...")
        
        try:
            # Tenta inicializar Tailwind CSS
            await self.tailwind_manager.initialize()
            print("✅ Asset Builder inicializado com sucesso")
            
        except Exception as e:
            # Armazena erro mas não falha completamente
            self.initialization_error = str(e)
            print(f"⚠️ Asset Builder inicializado com limitações: {str(e)}")
            print("💡 TagonPy continuará funcionando com CSS básico")
    
    async def start_development_mode(self):
        """
        Inicia modo de desenvolvimento com watch (com fallback)
        """
        if self.initialization_error:
            print("⚠️ Modo de desenvolvimento limitado devido a erro na inicialização")
            return False
        
        if not self.is_watching:
            print("🔄 Iniciando modo de desenvolvimento...")
            
            try:
                # Inicia watch mode do Tailwind
                await self.tailwind_manager.start_watch_mode()
                self.is_watching = True
                print("✅ Modo de desenvolvimento ativo")
                return True
                
            except Exception as e:
                print(f"⚠️ Erro ao iniciar modo de desenvolvimento: {str(e)}")
                return False
        
        return True
    
    async def stop_development_mode(self):
        """Para o modo de desenvolvimento"""
        if self.is_watching:
            try:
                await self.tailwind_manager.stop_watch_mode()
                self.is_watching = False
                print("⏹️ Modo de desenvolvimento parado")
            except Exception as e:
                print(f"⚠️ Erro ao parar modo de desenvolvimento: {str(e)}")
    
    async def build_production(self):
        """Build de produção (com fallback)"""
        print("🚀 Executando build de produção...")
        
        try:
            if self.initialization_error:
                print("⚠️ Build de produção não disponível devido a erro na inicialização")
                return False
            
            await self.tailwind_manager.build_production()
            print("✅ Build de produção concluído")
            return True
            
        except Exception as e:
            print(f"❌ Erro no build de produção: {str(e)}")
            return False
    
    def get_compiled_css(self) -> str:
        """Retorna CSS compilado pelo Tailwind ou string vazia para usar CDN"""
        try:
            if self.tailwind_manager.should_use_cdn():
                print("🌐 Usando Tailwind via CDN")
                return ""  # Template usará CDN
            
            return self.tailwind_manager.get_css_content()
            
        except Exception as e:
            print(f"⚠️ Erro ao obter CSS compilado: {str(e)}")
            return ""
    
    def should_use_cdn(self) -> bool:
        """Indica se deve usar CDN"""
        try:
            return self.tailwind_manager.should_use_cdn()
        except Exception as e:
            print(f"⚠️ Erro ao verificar CDN status: {str(e)}")
            return True  # Fallback para CDN em caso de erro
    
    def get_cdn_html(self) -> str:
        """Retorna HTML para CDN"""
        try:
            return self.tailwind_manager.get_cdn_html()
        except Exception as e:
            print(f"⚠️ Erro ao obter CDN HTML: {str(e)}")
            return self._get_emergency_cdn_html()
    
    def _get_emergency_cdn_html(self) -> str:
        """CDN de emergência final"""
        return '''
<!-- Tailwind CSS via CDN (Emergency Final Fallback) -->
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
    console.log('🎨 Tailwind CSS carregado via CDN (Emergency Final)');
</script>
'''
    
    def _get_fallback_css(self) -> str:
        """CSS básico de fallback quando Tailwind não está disponível"""
        return """
/* TagonPy Fallback CSS */
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; }
.container { max-width: 1200px; margin: 0 auto; padding: 0 1rem; }
.text-center { text-align: center; }
.flex { display: flex; }
.flex-col { flex-direction: column; }
.items-center { align-items: center; }
.justify-center { justify-content: center; }
.p-4 { padding: 1rem; }
.p-6 { padding: 1.5rem; }
.mb-4 { margin-bottom: 1rem; }
.text-xl { font-size: 1.25rem; }
.text-2xl { font-size: 1.5rem; }
.text-3xl { font-size: 1.875rem; }
.font-bold { font-weight: 700; }
.bg-blue-500 { background-color: #3b82f6; }
.text-white { color: #ffffff; }
.rounded { border-radius: 0.375rem; }
.shadow { box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1); }
.hover\\:bg-blue-600:hover { background-color: #2563eb; }
.transition { transition: all 0.15s ease-in-out; }
"""
    
    def get_css_url(self) -> str:
        """Retorna URL do CSS compilado"""
        return "/assets/css/output.css"
    
    def has_tailwind(self) -> bool:
        """Verifica se Tailwind está disponível e funcionando"""
        return self.initialization_error is None and self.tailwind_manager.is_initialized
    
    def get_status(self) -> Dict:
        """Status detalhado do asset builder com informações de CDN"""
        try:
            tailwind_status = self.tailwind_manager.get_status()
        except Exception as e:
            tailwind_status = {"error": str(e)}
        
        return {
            "asset_builder": {
                "watching": self.is_watching,
                "has_error": self.initialization_error is not None,
                "error_message": self.initialization_error,
                "tailwind_available": self.has_tailwind(),
                "should_use_cdn": self.should_use_cdn(),
                "system_info": {
                    "platform": platform.system(),
                    "python_version": platform.python_version(),
                    "project_root": str(self.project_root.absolute())
                },
                "tailwind": tailwind_status
            }
        }
    
    def get_diagnostics(self) -> Dict:
        """Diagnóstico completo do sistema com informações CDN"""
        try:
            tailwind_diagnostics = self.tailwind_manager.get_status()
        except Exception as e:
            tailwind_diagnostics = {"error": str(e)}
            
        return {
            "system": platform.system(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "project_root": str(self.project_root.absolute()),
            "initialization_error": self.initialization_error,
            "tailwind_manager": tailwind_diagnostics,
            "directories": {
                "assets_exists": self.tailwind_manager.assets_dir.exists(),
                "css_exists": self.tailwind_manager.css_dir.exists(),
                "project_root_exists": self.project_root.exists()
            },
            "cdn_info": {
                "should_use_cdn": self.should_use_cdn(),
                "cdn_html_length": len(self.get_cdn_html()),
                "has_emergency_fallback": True
            }
        }