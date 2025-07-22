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

# NOVO: Imports do sistema de roteamento
from core.routing import RouterManager
from core.middlewares import LoggingMiddleware, CorsMiddleware, AuthMiddleware

class TagonFileHandler(FileSystemEventHandler):
    """Handler para monitorar mudanças em arquivos .tg e .css"""
    
    def __init__(self, server_instance):
        self.server = server_instance
        self.last_modified = {}
        self.debounce_time = 0.5  # 500ms de debounce
    
    def on_modified(self, event):
        """Callback quando um arquivo é modificado"""
        if not event.is_directory and (
            event.src_path.endswith('.tg') or 
            event.src_path.endswith('.css') or 
            event.src_path.endswith('.py')
        ):
            current_time = time.time()
            
            # Debounce - evita múltiplos reloads
            if (event.src_path not in self.last_modified or 
                current_time - self.last_modified[event.src_path] > self.debounce_time):
                
                self.last_modified[event.src_path] = current_time
                file_name = os.path.basename(event.src_path)
                file_ext = os.path.splitext(event.src_path)[1]
                
                if file_ext == '.css':
                    print(f"🎨 CSS modificado: {file_name}")
                elif file_ext == '.tg':
                    print(f"🏷️ Componente modificado: {file_name}")
                else:
                    print(f"🔄 Arquivo modificado: {file_name}")
                
                print(f"📡 Enviando sinal de reload para {len(self.server.websocket_connections)} cliente(s)")
                
                # Envia sinal de reload para WebSocket
                asyncio.create_task(self.server.broadcast_reload())

class TagonServer:
    """Servidor de desenvolvimento do TagonPy com roteamento avançado"""
    
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
        
        # NOVO: Sistema de roteamento avançado
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
        """NOVO: Configura middlewares do sistema"""
        # Registra middlewares padrão
        logging_middleware = LoggingMiddleware(log_level="INFO")
        cors_middleware = CorsMiddleware()
        auth_middleware = AuthMiddleware()
        
        self.router_manager.middleware_chain.register_middleware(logging_middleware, priority=1)
        self.router_manager.middleware_chain.register_middleware(cors_middleware, priority=5)
        self.router_manager.middleware_chain.register_middleware(auth_middleware, priority=10)
        
        # Registra no router manager
        self.router_manager.register_middleware("logging", logging_middleware.before_request)
        self.router_manager.register_middleware("cors", cors_middleware.before_request)
        self.router_manager.register_middleware("auth", auth_middleware.before_request)
    
    def _setup_api_routes(self):
        """Configura rotas da API de desenvolvimento"""
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket para live reload"""
            await websocket.accept()
            self.websocket_connections.add(websocket)
            client_addr = websocket.client.host if websocket.client else "unknown"
            print(f"🔗 Cliente conectado: {client_addr} (Total: {len(self.websocket_connections)})")
            
            try:
                while True:
                    # Mantém conexão viva com ping
                    await websocket.receive_text()
            except WebSocketDisconnect:
                self.websocket_connections.discard(websocket)
                print(f"❌ Cliente desconectado: {client_addr} (Total: {len(self.websocket_connections)})")
            except Exception as e:
                print(f"🚨 Erro no WebSocket: {e}")
                self.websocket_connections.discard(websocket)
        
        @self.app.get("/api/health")
        async def health_check():
            """Health check avançado"""
            component_files = [f for f in os.listdir(self.components_dir) if f.endswith('.tg')] if os.path.exists(self.components_dir) else []
            page_files = [f for f in os.listdir(self.pages_dir) if f.endswith('.tg')] if os.path.exists(self.pages_dir) else []
            
            return {
                "status": "ok",
                "version": "0.2.0",
                "features": ["advanced_routing", "middlewares", "guards"],
                "websocket_connections": len(self.websocket_connections),
                "directories": {
                    "components": self.components_dir,
                    "pages": self.pages_dir
                },
                "files": {
                    "components": component_files,
                    "pages": page_files
                },
                "routing": self.router_manager.get_routes_info()
            }
        
        @self.app.get("/api/routes")
        async def get_routes_info():
            """NOVO: Informações sobre rotas registradas"""
            return self.router_manager.get_routes_info()
        
        @self.app.get("/api/middlewares")
        async def get_middlewares_info():
            """NOVO: Informações sobre middlewares"""
            return self.router_manager.middleware_chain.get_middleware_info()
        
        @self.app.get("/css/{css_name}")
        async def serve_css(css_name: str):
            """Rota para servir arquivos CSS diretamente (para debug)"""
            css_path = os.path.join(self.components_dir, css_name)
            if os.path.exists(css_path) and css_name.endswith('.css'):
                return FileResponse(css_path, media_type="text/css")
            return {"error": "CSS file not found"}
    
    def _setup_static_files(self):
        """Configura arquivos estáticos"""
        if os.path.exists("public"):
            self.app.mount("/static", StaticFiles(directory="public"), name="static")
    
    def _setup_file_watcher(self):
        """Configura monitoramento de arquivos"""
        self.file_handler = TagonFileHandler(self)
        self.file_observer = Observer()
        
        # Monitora diretório de componentes (.tg e .css)
        if os.path.exists(self.components_dir):
            self.file_observer.schedule(
                self.file_handler, 
                self.components_dir, 
                recursive=True
            )
            print(f"👀 Monitorando: {self.components_dir}/ (arquivos .tg e .css)")
        
        # NOVO: Monitora diretório de páginas
        if os.path.exists(self.pages_dir):
            self.file_observer.schedule(
                self.file_handler, 
                self.pages_dir, 
                recursive=True
            )
            print(f"👀 Monitorando: {self.pages_dir}/ (arquivos .tg)")
        
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
        if not self.websocket_connections:
            print("📡 Nenhum cliente conectado para reload")
            return
        
        disconnected = set()
        successful_broadcasts = 0
        
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text("reload")
                successful_broadcasts += 1
            except Exception as e:
                print(f"🚨 Erro ao enviar reload: {e}")
                disconnected.add(websocket)
        
        # Remove conexões desconectadas
        self.websocket_connections -= disconnected
        
        print(f"📡 Reload enviado para {successful_broadcasts} cliente(s)")
        if disconnected:
            print(f"🧹 Removidas {len(disconnected)} conexão(ões) inválida(s)")
    
    def start(self):
        """MUDANÇA: Inicia o servidor de desenvolvimento (SÍNCRONO)"""
        print(f"""
🚀 TagonPy Advanced Server v0.2.0

📂 Componentes: {self.components_dir}/
📄 Páginas: {self.pages_dir}/
🛤️ Roteamento: Avançado (file-based)
🔧 Middlewares: Ativados
🛡️ Guards: Ativados
🌐 Servidor: http://{self.host}:{self.port}
🔄 Live reload: Ativado (.tg, .css, .py)
📚 API Docs: http://{self.host}:{self.port}/docs
🩺 Health: http://{self.host}:{self.port}/api/health
🛤️ Rotas: http://{self.host}:{self.port}/api/routes

🆕 NOVO: Sistema de roteamento file-based!
   📁 Crie arquivos .tg em pages/ para novas rotas
   🔗 Parâmetros dinâmicos: [id], [slug]
   🔧 Middlewares por rota via comentários
        """)
        
        # MUDANÇA: Inicializa sistema de roteamento usando run_once
        try:
            # Cria um novo event loop para a inicialização
            import asyncio
            
            # Usa asyncio.run para executar a inicialização
            total_routes = asyncio.run(self._initialize_routing())
            print(f"✅ Sistema de roteamento inicializado: {total_routes} rotas descobertas")
        except Exception as e:
            print(f"❌ Erro ao inicializar roteamento: {str(e)}")
            return
        
        # Inicia monitoramento de arquivos
        if self.file_observer:
            self.file_observer.start()
            print("👀 Monitoramento de arquivos iniciado")
        
        try:
            # MUDANÇA: Inicia servidor de forma síncrona
            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                log_level="info",
                reload=False  # Desabilita reload do uvicorn para usar nosso próprio
            )
        except KeyboardInterrupt:
            print("\n⏹️  Servidor interrompido pelo usuário")
        finally:
            if self.file_observer:
                self.file_observer.stop()
                self.file_observer.join()
                print("👀 Monitoramento de arquivos parado")
    
    async def _initialize_routing(self):
        """NOVO: Método separado para inicialização do roteamento"""
        return await self.router_manager.initialize_routes()