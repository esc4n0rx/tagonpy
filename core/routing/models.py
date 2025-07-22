"""
TagonPy Routing Models
Modelos de dados para o sistema de roteamento
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional

@dataclass
class RouteConfig:
    """Configuração de uma rota"""
    path: str
    component_path: str
    middlewares: List[str] = None
    guards: List[str] = None
    params: Dict[str, Any] = None
    layout: Optional[str] = None
    
    def __post_init__(self):
        if self.middlewares is None:
            self.middlewares = []
        if self.guards is None:
            self.guards = []
        if self.params is None:
            self.params = {}