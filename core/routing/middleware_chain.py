import asyncio
from typing import Dict, List, Callable, Any, Optional
from fastapi import Request, Response
from abc import ABC, abstractmethod

class BaseMiddleware(ABC):
    """
    Classe base para middlewares do TagonPy
    """
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    async def before_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Executado antes do processamento da rota
        Retorna dados que serão passados para o contexto do componente
        """
        pass
    
    @abstractmethod
    async def after_request(self, request: Request, response_data: Dict) -> Optional[Dict[str, Any]]:
        """
        Executado após o processamento da rota
        Pode modificar a resposta
        """
        pass

class MiddlewareChain:
    """
    Gerenciador da cadeia de middlewares
    Executa middlewares em ordem específica
    """
    
    def __init__(self):
        self.middlewares: Dict[str, BaseMiddleware] = {}
        self.execution_order: List[str] = []
    
    def register_middleware(self, middleware: BaseMiddleware, priority: int = 50):
        """
        Registra um middleware na cadeia
        
        Args:
            middleware: Instância do middleware
            priority: Prioridade de execução (menor = primeiro)
        """
        self.middlewares[middleware.name] = middleware
        
        # Insere na posição correta baseado na prioridade
        inserted = False
        for i, name in enumerate(self.execution_order):
            existing_priority = getattr(self.middlewares[name], 'priority', 50)
            if priority < existing_priority:
                self.execution_order.insert(i, middleware.name)
                inserted = True
                break
        
        if not inserted:
            self.execution_order.append(middleware.name)
        
        print(f"🔧 Middleware '{middleware.name}' registrado (prioridade: {priority})")
    
    async def execute_before(self, request: Request, middleware_names: List[str]) -> Dict[str, Any]:
        """
        Executa fase 'before' dos middlewares especificados
        """
        context = {}
        
        for name in middleware_names:
            if name in self.middlewares:
                try:
                    result = await self.middlewares[name].before_request(request)
                    if result:
                        context.update(result)
                except Exception as e:
                    print(f"⚠️ Erro no middleware {name} (before): {str(e)}")
        
        return context
    
    async def execute_after(self, request: Request, response_data: Dict, middleware_names: List[str]) -> Dict[str, Any]:
        """
        Executa fase 'after' dos middlewares especificados
        """
        context = {}
        
        # Executa em ordem reversa para after
        for name in reversed(middleware_names):
            if name in self.middlewares:
                try:
                    result = await self.middlewares[name].after_request(request, response_data)
                    if result:
                        context.update(result)
                except Exception as e:
                    print(f"⚠️ Erro no middleware {name} (after): {str(e)}")
        
        return context
    
    def get_middleware_info(self) -> Dict:
        """
        Retorna informações sobre middlewares registrados
        """
        return {
            "total": len(self.middlewares),
            "execution_order": self.execution_order,
            "middlewares": list(self.middlewares.keys())
        }