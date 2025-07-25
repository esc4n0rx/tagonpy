from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from fastapi import Request

class BaseMiddleware(ABC):
    """
    Classe base abstrata para todos os middlewares do TagonPy
    Define interface padrão que todos os middlewares devem implementar
    """
    
    def __init__(self, name: str, priority: int = 50):
        self.name = name
        self.priority = priority
        self.enabled = True
    
    @abstractmethod
    async def before_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Executado antes do processamento da rota
        
        Args:
            request: Objeto Request do FastAPI
            
        Returns:
            Dict opcional com dados para injetar no contexto do componente
        """
        pass
    
    @abstractmethod
    async def after_request(self, request: Request, response_data: Dict) -> Optional[Dict[str, Any]]:
        """
        Executado após o processamento da rota
        
        Args:
            request: Objeto Request do FastAPI
            response_data: Dados da resposta processada
            
        Returns:
            Dict opcional com dados adicionais
        """
        pass
    
    # NOVO: Método para compatibilidade com router_manager
    async def __call__(self, request: Request, phase: str = "before", response_data: Dict = None) -> Optional[Dict[str, Any]]:
        """
        Método callable para compatibilidade com router_manager
        """
        try:
            if phase == "before":
                return await self.before_request(request)
            elif phase == "after":
                return await self.after_request(request, response_data or {})
            else:
                return {}
        except Exception as e:
            print(f"⚠️ Erro no middleware {self.name}: {str(e)}")
            return {}
    
    def enable(self):
        """Habilita o middleware"""
        self.enabled = True
        print(f"✅ Middleware '{self.name}' habilitado")
    
    def disable(self):
        """Desabilita o middleware"""
        self.enabled = False
        print(f"❌ Middleware '{self.name}' desabilitado")
    
    def __str__(self):
        return f"Middleware({self.name}, priority={self.priority}, enabled={self.enabled})"