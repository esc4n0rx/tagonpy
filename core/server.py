import os
import asyncio
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import uvicorn
import time

# NOVO: Imports do sistema de assets
from core.assets import AssetBuilder
from core.routing import RouterManager
from core.middlewares import LoggingMiddleware, CorsMiddleware, AuthMiddleware, AssetsMiddleware

class TagonFileHandler(FileSystemEventHandler):
    """Handler para monitorar mudanças em arquivos .tg, .css e assets"""
    
    def __init__(self, server_instance):
        self.server = server_instance
        self.last_modified = {}
        self.debounce_time = 0.5
    
    def on_modified(self, event):
        """Callback quando um arquivo é modificado"""
        if not event.is_directory and (
            event.src_path.endswith('.tg') or 
            event.src_path.endswith('.css') or 
            event.src_path.endswith('.py') or
            'assets/' in event.src_path  # NOVO: monitora pasta assets
        ):
            current_time = time.time()
            
            if (event.src_path not in self.last_modified or 
                current_time - self.last_modified[event.src_path] > self.debounce_time):
                
                self.last_modified[event.src_path] = current_time
                file_name = os.path.basename(event.src_path)
                file_ext = os.path.splitext(event.src_path)[1]
                
                # NOVO: Detecta mudanças no CSS de assets
                if 'assets/' in event.src_path and file_ext == '.css':
                    print(f"🎨 Tailwind CSS modificado: {file_name}")
                    # Envia evento específico para CSS
                    asyncio.create_task(self.server.broadcast_css_update())
                elif file_ext == '.css':
                    print(f"🎨 CSS modificado: {file_name}")
                    asyncio.create_task(self.server.broadcast_reload())
                elif file_ext == '.tg':
                    print(f"🏷️ Componente modificado: {file_name}")
                    asyncio.create_task(self.server.broadcast_reload())
                else:
                    print(f"🔄 Arquivo modificado: {file_name}")
                    asyncio.create_task(self.server.broadcast_reload())

class TagonServer:
    """Servidor de desenvolvimento do TagonPy com suporte ao Tailwind CSS"""
    
    def __init__(self, 
                 host: str = "localhost", 
                 port: int = 3000,
                 components_dir: str = "components",
                 pages_dir: str = "pages"):
        self.host = host
        self.port = port
        self.components_dir = components_dir
        self.pages_dir = pages_dir
        
        self.app = FastAPI(title="TagonPy Advanced Server", docs_url="/docs")
        self.websocket_connections = set()
        self.file_observer = None
        
        # NOVO: Sistema de assets com Tailwind
        self.asset_builder = AssetBuilder()
        
        # Sistema de roteamento avançado
        self.router_manager = RouterManager(
            app=self.app,
            pages_dir=pages_dir,
            components_dir=components_dir
        )
        
        # Configura sistemas
        self._setup_middlewares()
        self._setup_static_files()
        self._setup_api_routes()
        self._setup_file_watcher()
    
    def _setup_middlewares(self):
        """MODIFICADO: Configura middlewares incluindo assets"""
        # Registra middlewares padrão
        logging_middleware = LoggingMiddleware(log_level="INFO")
        cors_middleware = CorsMiddleware()
        auth_middleware = AuthMiddleware()
        assets_middleware = AssetsMiddleware(self.asset_builder)  # NOVO
        
        self.router_manager.middleware_chain.register_middleware(logging_middleware, priority=1)
        self.router_manager.middleware_chain.register_middleware(cors_middleware, priority=5)
        self.router_manager.middleware_chain.register_middleware(auth_middleware, priority=10)
        self.router_manager.middleware_chain.register_middleware(assets_middleware, priority=20)  # NOVO
        
        # Registra no router manager
        self.router_manager.register_middleware("logging", logging_middleware.before_request)
        self.router_manager.register_middleware("cors", cors_middleware.before_request)
        self.router_manager.register_middleware("auth", auth_middleware.before_request)
        self.router_manager.register_middleware("assets", assets_middleware.before_request)  # NOVO
    
    def _setup_api_routes(self):
        """MODIFICADO: Configura rotas da API incluindo assets"""
        @self.app.get("/api/assets/diagnostics")
        async def get_full_diagnostics():
            """Diagnóstico completo do sistema de assets"""
            return self.asset_builder.get_diagnostics()
        
        # NOVO: API para testar Node.js
        @self.app.get("/api/system/nodejs")
        async def test_nodejs():
            """Testa disponibilidade do Node.js"""
            try:
                import subprocess
                import platform
                
                is_windows = platform.system().lower() == "windows"
                
                if is_windows:
                    result = subprocess.run(
                        "node --version", 
                        shell=True, 
                        capture_output=True, 
                        text=True, 
                        timeout=10
                    )
                else:
                    result = subprocess.run(
                        ["node", "--version"], 
                        capture_output=True, 
                        text=True, 
                        timeout=10
                    )
                
                return {
                    "available": result.returncode == 0,
                    "version": result.stdout.strip() if result.returncode == 0 else None,
                    "error": result.stderr.strip() if result.returncode != 0 else None,
                    "system": platform.system()
                }
                
            except Exception as e:
                return {
                    "available": False,
                    "version": None,
                    "error": str(e),
                    "system": platform.system()
                }
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket para live reload"""
            await websocket.accept()
            self.websocket_connections.add(websocket)
            client_addr = websocket.client.host if websocket.client else "unknown"
            print(f"🔗 Cliente conectado: {client_addr} (Total: {len(self.websocket_connections)})")
            
            try:
                while True:
                    await websocket.receive_text()
            except WebSocketDisconnect:
                self.websocket_connections.discard(websocket)
                print(f"❌ Cliente desconectado: {client_addr} (Total: {len(self.websocket_connections)})")
            except Exception as e:
                print(f"🚨 Erro no WebSocket: {e}")
                self.websocket_connections.discard(websocket)
        
        @self.app.get("/api/health")
        async def health_check():
            """Health check com status do Tailwind"""
            component_files = [f for f in os.listdir(self.components_dir) if f.endswith('.tg')] if os.path.exists(self.components_dir) else []
            page_files = [f for f in os.listdir(self.pages_dir) if f.endswith('.tg')] if os.path.exists(self.pages_dir) else []
            
            return {
                "status": "ok",
                "version": "0.2.0",
                "features": ["advanced_routing", "middlewares", "guards", "tailwind_css"],  # NOVO
                "websocket_connections": len(self.websocket_connections),
                "directories": {
                    "components": self.components_dir,
                    "pages": self.pages_dir,
                    "assets": "assets"  # NOVO
                },
                "files": {
                    "components": component_files,
                    "pages": page_files
                },
                "routing": self.router_manager.get_routes_info(),
                "assets": self.asset_builder.get_status()  # NOVO
            }
        
        # NOVO: Rota para servir CSS do Tailwind
        @self.app.get("/assets/css/output.css")
        async def serve_compiled_css():
            """Serve CSS compilado do Tailwind"""
            css_content = self.asset_builder.get_compiled_css()
            if css_content:
                return Response(content=css_content, media_type="text/css")
            else:
                return Response(content="/* Tailwind CSS not compiled yet */", media_type="text/css")
        
        # NOVO: API para status do Tailwind
        @self.app.get("/api/assets/status")
        async def get_assets_status():
            """Status detalhado dos assets"""
            return self.asset_builder.get_status()
        
        # NOVO: API para rebuild do Tailwind
        @self.app.post("/api/assets/rebuild")
        async def rebuild_assets():
            """Força rebuild dos assets"""
            try:
                await self.asset_builder.tailwind_manager.build_production()
                return {"status": "success", "message": "Assets rebuilt successfully"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        
        @self.app.get("/api/routes")
        async def get_routes_info():
            """Informações sobre rotas registradas"""
            return self.router_manager.get_routes_info()
        
        @self.app.get("/api/middlewares")
        async def get_middlewares_info():
            """Informações sobre middlewares"""
            return self.router_manager.middleware_chain.get_middleware_info()
    
    def _setup_static_files(self):
        """MODIFICADO: Configura arquivos estáticos incluindo assets"""
        if os.path.exists("public"):
            self.app.mount("/static", StaticFiles(directory="public"), name="static")
        
        # NOVO: Monta diretório de assets
        if os.path.exists("assets"):
            self.app.mount("/assets", StaticFiles(directory="assets"), name="assets")
    
    def _setup_file_watcher(self):
        """MODIFICADO: Configura monitoramento incluindo assets"""
        self.file_handler = TagonFileHandler(self)
        self.file_observer = Observer()
        
        # Monitora diretório de componentes
        if os.path.exists(self.components_dir):
            self.file_observer.schedule(
                self.file_handler, 
                self.components_dir, 
                recursive=True
            )
            print(f"👀 Monitorando: {self.components_dir}/ (arquivos .tg e .css)")
        
        # Monitora diretório de páginas
        if os.path.exists(self.pages_dir):
            self.file_observer.schedule(
                self.file_handler, 
                self.pages_dir, 
                recursive=True
            )
            print(f"👀 Monitorando: {self.pages_dir}/ (arquivos .tg)")
        
        # NOVO: Monitora diretório de assets
        if os.path.exists("assets"):
            self.file_observer.schedule(
                self.file_handler, 
                "assets", 
                recursive=True
            )
            print(f"👀 Monitorando: assets/ (CSS do Tailwind)")
        
        # Monitora core para mudanças no framework
        if os.path.exists("core"):
            self.file_observer.schedule(
                self.file_handler, 
                "core", 
                recursive=True
            )
            print(f"👀 Monitorando: core/ (arquivos .py)")
    
    async def broadcast_reload(self):
        """Envia sinal de reload para todos os WebSockets conectados"""
        await self._broadcast_message("reload")
    
    async def broadcast_css_update(self):
        """NOVO: Envia sinal específico para atualização de CSS"""
        await self._broadcast_message("css-updated")
    
    async def _broadcast_message(self, message: str):
        """Envia mensagem para todos os WebSockets"""
        if not self.websocket_connections:
            print(f"📡 Nenhum cliente conectado para {message}")
            return
        
        disconnected = set()
        successful_broadcasts = 0
        
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(message)
                successful_broadcasts += 1
            except Exception as e:
                print(f"🚨 Erro ao enviar {message}: {e}")
                disconnected.add(websocket)
        
        # Remove conexões desconectadas
        self.websocket_connections -= disconnected
        
        print(f"📡 {message} enviado para {successful_broadcasts} cliente(s)")
        if disconnected:
            print(f"🧹 Removidas {len(disconnected)} conexão(ões) inválida(s)")
    
    def start(self):
        """MODIFICADO: Inicia o servidor com suporte ao Tailwind"""
        print(f"""
🚀 TagonPy Advanced Server v0.2.0 + Tailwind CSS

📂 Componentes: {self.components_dir}/
📄 Páginas: {self.pages_dir}/
🎨 Assets: assets/ (Tailwind CSS)
🛤️ Roteamento: Avançado (file-based)
🔧 Middlewares: Ativados
🛡️ Guards: Ativados
🌐 Servidor: http://{self.host}:{self.port}
🔄 Live reload: Ativado (.tg, .css, .py, assets/)
📚 API Docs: http://{self.host}:{self.port}/docs
🩺 Health: http://{self.host}:{self.port}/api/health
🛤️ Rotas: http://{self.host}:{self.port}/api/routes
🎨 Assets Status: http://{self.host}:{self.port}/api/assets/status

🆕 NOVO: Suporte completo ao Tailwind CSS!
   🎨 Build automático do CSS
   🔄 Live reload para mudanças CSS
   ⚡ Utility-first styling
        """)
        
        # Inicializa sistemas
        try:
            # Inicializa sistema de assets
            print("🎨 Inicializando sistema de assets...")
            asyncio.run(self._initialize_systems())
            print("✅ Sistemas inicializados com sucesso")
        except Exception as e:
            print(f"❌ Erro ao inicializar sistemas: {str(e)}")
            print("⚠️  Continuando sem Tailwind CSS...")
        
        # Inicia monitoramento de arquivos
        if self.file_observer:
            self.file_observer.start()
            print("👀 Monitoramento de arquivos iniciado")
        
        try:
            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                log_level="info",
                reload=False
            )
        except KeyboardInterrupt:
            print("\n⏹️  Servidor interrompido pelo usuário")
        finally:
            # Cleanup
            if self.file_observer:
                self.file_observer.stop()
                self.file_observer.join()
                print("👀 Monitoramento de arquivos parado")
            
            # Para asset builder
            asyncio.run(self._cleanup_systems())
    
    async def _initialize_systems(self):
        """Inicializa todos os sistemas com diagnóstico detalhado"""
        print("🔧 Inicializando sistemas TagonPy...")
        
        try:
            # Inicializa asset builder e Tailwind
            print("🎨 Inicializando sistema de assets...")
            await self.asset_builder.initialize()
            
            # Tenta iniciar modo de desenvolvimento
            success = await self.asset_builder.start_development_mode()
            
            if success:
                print("✅ Sistema de assets iniciado com sucesso")
            else:
                print("⚠️ Sistema de assets iniciado com limitações")
                print("💡 Diagnóstico disponível em: /api/assets/diagnostics")
                
        except Exception as e:
            print(f"⚠️ Erro no sistema de assets: {str(e)}")
            print("💡 TagonPy continuará funcionando normalmente")
        
        # Inicializa sistema de roteamento
        try:
            total_routes = await self.router_manager.initialize_routes()
            print(f"✅ Sistema de roteamento: {total_routes} rotas descobertas")
        except Exception as e:
            print(f"❌ Erro crítico no sistema de roteamento: {str(e)}")
            raise
    
    async def _cleanup_systems(self):
        """NOVO: Cleanup dos sistemas"""
        await self.asset_builder.stop_development_mode()
        print("🧹 Sistemas finalizados")