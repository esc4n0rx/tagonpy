import asyncio
from typing import Dict, List, Callable, Any, Optional
from fastapi import Request
from abc import ABC, abstractmethod

class BaseGuard(ABC):
    """
    Classe base para guards de proteção de rota
    """
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    async def can_activate(self, request: Request) -> Dict[str, Any]:
        """
        Verifica se o acesso à rota é permitido
        
        Returns:
            Dict com keys: allowed (bool), message (str), status_code (int)
        """
        pass

class RouteGuard:
    """
    Gerenciador de guards de proteção de rotas
    """
    
    def __init__(self):
        self.guards: Dict[str, BaseGuard] = {}
    
    def register_guard(self, guard: BaseGuard):
        """
        Registra um guard de proteção
        """
        self.guards[guard.name] = guard
        print(f"🛡️ Guard '{guard.name}' registrado")
    
    async def check_guards(self, request: Request, guard_names: List[str]) -> Dict[str, Any]:
        """
        Verifica todos os guards especificados para uma rota
        
        Returns:
            Dict com resultado da verificação
        """
        for guard_name in guard_names:
            if guard_name in self.guards:
                try:
                    result = await self.guards[guard_name].can_activate(request)
                    if not result.get("allowed", True):
                        return result
                except Exception as e:
                    print(f"⚠️ Erro no guard {guard_name}: {str(e)}")
                    return {
                        "allowed": False,
                        "message": f"Guard execution error: {str(e)}",
                        "status_code": 500
                    }
        
        return {"allowed": True}
    
    def get_guards_info(self) -> Dict:
        """
        Retorna informações sobre guards registrados
        """
        return {
            "total": len(self.guards),
            "guards": list(self.guards.keys())
        }