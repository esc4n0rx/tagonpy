import os
import asyncio
from typing import Dict, List, Optional, Callable, Any
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.routing import APIRoute
from pathlib import Path
import re

from .models import RouteConfig
from .middleware_chain import MiddlewareChain
from .dynamic_params import DynamicParams
from ..renderer import TagonRenderer

class RouterManager:
    """
    Gerenciador central do sistema de roteamento avançado
    Responsável por descobrir, registrar e executar rotas
    """
    
    def __init__(self, 
                 app: FastAPI,
                 pages_dir: str = "pages",
                 components_dir: str = "components"):
        self.app = app
        self.pages_dir = pages_dir
        self.components_dir = components_dir
        self.renderer = TagonRenderer(components_dir=components_dir)
        
        # Sistemas internos
        self.middleware_chain = MiddlewareChain()
        self.dynamic_params = DynamicParams()
        
        # Registry de rotas descobertas
        self.routes_registry: Dict[str, RouteConfig] = {}
        self.middleware_registry: Dict[str, Callable] = {}
        self.guard_registry: Dict[str, Callable] = {}
        
        print(f"🛤️ RouterManager inicializado")
        print(f"📂 Diretório de páginas: {pages_dir}")
        print(f"📦 Diretório de componentes: {components_dir}")
    
    async def initialize_routes(self):
        """
        Inicializa o sistema de rotas
        Descobre e registra todas as rotas automaticamente
        """
        print(f"🔍 Descobrindo rotas em {self.pages_dir}/...")
        
        # Import aqui para evitar circular import
        from .route_discovery import RouteDiscovery
        self.route_discovery = RouteDiscovery(self.pages_dir)
        
        # Descobre todas as rotas baseadas em arquivos
        discovered_routes = await self.route_discovery.discover_routes()
        
        print(f"📋 Encontradas {len(discovered_routes)} rotas:")
        
        # Registra cada rota descoberta
        for route_config in discovered_routes:
            await self._register_route(route_config)
            print(f"  ✅ {route_config.path} -> {route_config.component_path}")
        
        print(f"🚀 Sistema de roteamento inicializado com sucesso!")
        return len(discovered_routes)
    
    async def _register_route(self, config: RouteConfig):
        """
        Registra uma rota individual no FastAPI
        """
        # Armazena no registry
        self.routes_registry[config.path] = config
        
        # Cria handler assíncrono para a rota
        async def route_handler(request: Request):
            return await self._handle_route_request(request, config)
        
        # Converte parâmetros dinâmicos para formato FastAPI
        fastapi_path = self._convert_dynamic_path(config.path)
        
        # Registra no FastAPI
        self.app.add_api_route(
            path=fastapi_path,
            endpoint=route_handler,
            methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
            name=f"tagonpy_route_{config.path.replace('/', '_')}"
        )
    
    def _convert_dynamic_path(self, tagonpy_path: str) -> str:
        """
        Converte rotas TagonPy ([param]) para formato FastAPI ({param})
        
        Exemplo: /user/[id] -> /user/{id}
        """
        # Converte [param] para {param}
        fastapi_path = re.sub(r'\[([^\]]+)\]', r'{\1}', tagonpy_path)
        return fastapi_path
    
    async def _handle_route_request(self, request: Request, config: RouteConfig):
        """
        Manipula uma requisição para uma rota específica
        Executa middlewares, guards e renderiza o componente
        """
        try:
            print(f"🌐 Processando requisição: {request.method} {request.url.path}")
            
            # 1. Extrai parâmetros dinâmicos da URL
            route_params = dict(request.path_params)
            query_params = dict(request.query_params)
            
            # 2. Executa middlewares pré-processamento
            middleware_context = await self._execute_middlewares(
                request, config, "before"
            )
            
            # 3. Executa guards (proteção de rota)
            guard_result = await self._execute_guards(request, config)
            if not guard_result.get("allowed", True):
                raise HTTPException(
                    status_code=guard_result.get("status_code", 403),
                    detail=guard_result.get("message", "Access denied")
                )
            
            # 4. Prepara contexto do componente
            component_context = {
                "request": request,
                "params": route_params,
                "query": query_params,
                "middleware_data": middleware_context,
                **config.params
            }
            
            # 5. Renderiza o componente
            html_content = await self._render_component(
                config.component_path, 
                component_context
            )
            
            # 6. Executa middlewares pós-processamento
            await self._execute_middlewares(
                request, config, "after", 
                response_data={"html": html_content}
            )
            
            # 7. Retorna resposta HTML
            return Response(
                content=html_content,
                media_type="text/html",
                status_code=200
            )
            
        except Exception as e:
            print(f"❌ Erro na rota {config.path}: {str(e)}")
            # Renderiza página de erro personalizada
            return await self._render_error_response(e, config)
    
    async def _execute_middlewares(self, 
                                   request: Request, 
                                   config: RouteConfig, 
                                   phase: str,
                                   response_data: Dict = None):
        """
        Executa middlewares registrados para a rota
        """
        context = {}
        
        for middleware_name in config.middlewares:
            if middleware_name in self.middleware_registry:
                middleware = self.middleware_registry[middleware_name]
                try:
                    result = await middleware(request, phase, response_data)
                    if result:
                        context.update(result)
                except Exception as e:
                    print(f"⚠️ Erro no middleware {middleware_name}: {str(e)}")
        
        return context
    
    async def _execute_guards(self, request: Request, config: RouteConfig):
        """
        Executa guards de proteção para a rota
        """
        for guard_name in config.guards:
            if guard_name in self.guard_registry:
                guard = self.guard_registry[guard_name]
                try:
                    result = await guard(request)
                    if not result.get("allowed", True):
                        return result
                except Exception as e:
                    print(f"⚠️ Erro no guard {guard_name}: {str(e)}")
                    return {"allowed": False, "message": "Guard execution error"}
        
        return {"allowed": True}
    
    async def _render_component(self, component_path: str, context: Dict):
        """
        Renderiza um componente com contexto específico da rota
        """
        try:
            # Usa o renderer existente com contexto expandido
            return self.renderer.render_component_with_context(
                component_path, context
            )
        except Exception as e:
            print(f"❌ Erro ao renderizar componente {component_path}: {str(e)}")
            raise
    
    async def _render_error_response(self, error: Exception, config: RouteConfig):
        """
        Renderiza resposta de erro personalizada
        """
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>TagonPy - Erro na Rota</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    background: #0a0a0a; 
                    color: white;
                    padding: 2rem;
                    text-align: center;
                }}
                .error-container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background: rgba(239, 68, 68, 0.1);
                    padding: 2rem;
                    border-radius: 15px;
                    border: 1px solid rgba(239, 68, 68, 0.3);
                }}
            </style>
        </head>
        <body>
            <div class="error-container">
                <h1>⚠️ Erro na Rota</h1>
                <p><strong>Rota:</strong> {config.path}</p>
                <p><strong>Componente:</strong> {config.component_path}</p>
                <p><strong>Erro:</strong> {str(error)}</p>
            </div>
        </body>
        </html>
        """
        
        return Response(
            content=error_html,
            media_type="text/html",
            status_code=500
        )
    
    def register_middleware(self, name: str, middleware: Callable):
        """
        Registra um middleware personalizado
        """
        self.middleware_registry[name] = middleware
        print(f"🔧 Middleware '{name}' registrado")
    
    def register_guard(self, name: str, guard: Callable):
        """
        Registra um guard de proteção
        """
        self.guard_registry[name] = guard
        print(f"🛡️ Guard '{name}' registrado")
    
    def get_routes_info(self) -> Dict:
        """
        Retorna informações sobre todas as rotas registradas
        """
        return {
            "total_routes": len(self.routes_registry),
            "routes": [
                {
                    "path": config.path,
                    "component": config.component_path,
                    "middlewares": config.middlewares,
                    "guards": config.guards
                }
                for config in self.routes_registry.values()
            ],
            "middlewares": list(self.middleware_registry.keys()),
            "guards": list(self.guard_registry.keys())
        }