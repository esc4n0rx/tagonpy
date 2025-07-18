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
from core.renderer import TagonRenderer

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
    """Servidor de desenvolvimento do TagonPy"""
    
    def __init__(self, 
                 host: str = "localhost", 
                 port: int = 3000,
                 components_dir: str = "components"):
        self.host = host
        self.port = port
        self.components_dir = components_dir
        self.app = FastAPI(title="TagonPy Dev Server", docs_url="/docs")
        self.renderer = TagonRenderer(components_dir=components_dir)
        self.websocket_connections = set()
        self.file_observer = None
        
        # Configura rotas
        self._setup_routes()
        self._setup_static_files()
        self._setup_file_watcher()
    
    def _setup_routes(self):
        """Configura as rotas do servidor"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def root():
            """Rota principal - carrega App.tg"""
            return await self.render_component("App.tg")
        
        @self.app.get("/component/{component_name}", response_class=HTMLResponse)
        async def render_component_route(component_name: str):
            """Rota para renderizar componentes específicos"""
            return await self.render_component(component_name)
        
        @self.app.get("/css/{css_name}")
        async def serve_css(css_name: str):
            """Rota para servir arquivos CSS diretamente (para debug)"""
            css_path = os.path.join(self.components_dir, css_name)
            if os.path.exists(css_path) and css_name.endswith('.css'):
                return FileResponse(css_path, media_type="text/css")
            return {"error": "CSS file not found"}
        
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
        
        @self.app.get("/health")
        async def health_check():
            """Health check para debug"""
            component_files = [f for f in os.listdir(self.components_dir) if f.endswith('.tg')] if os.path.exists(self.components_dir) else []
            css_files = [f for f in os.listdir(self.components_dir) if f.endswith('.css')] if os.path.exists(self.components_dir) else []
            
            return {
                "status": "ok",
                "websocket_connections": len(self.websocket_connections),
                "components_dir": self.components_dir,
                "component_files": component_files,
                "css_files": css_files,
                "css_system": "external + inline"
            }
    
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
        
        # Monitora core para mudanças no framework
        if os.path.exists("core"):
            self.file_observer.schedule(
                self.file_handler, 
                "core", 
                recursive=True
            )
            print(f"👀 Monitorando: core/ (arquivos .py)")
    
    async def render_component(self, component_name: str) -> str:
        """
        Renderiza um componente .tg
        
        Args:
            component_name: Nome do arquivo .tg
            
        Returns:
            str: HTML renderizado
        """
        component_path = os.path.join(self.components_dir, component_name)
        
        if not os.path.exists(component_path):
            return self._render_404_page(component_name)
        
        try:
            print(f"🎨 Renderizando componente: {component_name}")
            
            # Renderiza componente
            html = self.renderer.render_component(component_path)
            
            print(f"✅ Componente {component_name} renderizado com sucesso")
            return html
            
        except Exception as e:
            print(f"❌ Erro ao renderizar {component_name}: {str(e)}")
            return self.renderer._render_error_page(str(e))
    
    def _render_404_page(self, component_name: str) -> str:
        """Renderiza página 404"""
        return f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>TagonPy - Componente não encontrado</title>
            <style>
                body {{
                    margin: 0 !important;
                    padding: 0 !important;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
                    background: #0a0a0a !important;
                    color: #ffffff !important;
                    min-height: 100vh !important;
                    display: flex !important;
                    align-items: center !important;
                    justify-content: center !important;
                }}
                .container {{
                    max-width: 600px !important;
                    text-align: center !important;
                    background: rgba(255, 255, 255, 0.05) !important;
                    padding: 50px !important;
                    border-radius: 15px !important;
                    backdrop-filter: blur(10px) !important;
                    border: 1px solid rgba(255, 255, 255, 0.1) !important;
                }}
                h1 {{ 
                    color: #ef4444 !important; 
                    font-size: 3rem !important;
                    margin-bottom: 1rem !important;
                }}
                p {{
                    color: #a0a0a0 !important;
                    font-size: 1.125rem !important;
                    margin: 1rem 0 !important;
                }}
                code {{
                    background: rgba(255, 255, 255, 0.1) !important;
                    padding: 0.25rem 0.5rem !important;
                    border-radius: 4px !important;
                    font-family: 'Monaco', 'Menlo', monospace !important;
                }}
                .suggestion {{
                    background: rgba(59, 130, 246, 0.1) !important;
                    border: 1px solid rgba(59, 130, 246, 0.3) !important;
                    padding: 1rem !important;
                    border-radius: 8px !important;
                    margin-top: 2rem !important;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>404</h1>
                <p>Componente <strong>{component_name}</strong> não encontrado.</p>
                <p>Verifique se o arquivo existe em <code>components/{component_name}</code></p>
                <div class="suggestion">
                    <h3>💡 Dica:</h3>
                    <p>Agora você pode criar arquivos CSS separados!</p>
                    <p>Exemplo: <code>components/App.css</code> para estilos do <code>App.tg</code></p>
                </div>
            </div>
        </body>
        </html>
        """
    
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
        """Inicia o servidor de desenvolvimento"""
        print(f"""
🚀 TagonPy Dev Server v0.1.0

📂 Componentes: {self.components_dir}/
🎨 Sistema CSS: Arquivos externos + inline
🌐 Servidor: http://{self.host}:{self.port}
🔄 Live reload: Ativado (.tg, .css, .py)
📚 API Docs: http://{self.host}:{self.port}/docs
🩺 Health: http://{self.host}:{self.port}/health

💡 Nova funcionalidade: Crie arquivos .css separados!
   Exemplo: App.tg + App.css = ❤️
        """)
        
        # Inicia monitoramento de arquivos
        if self.file_observer:
            self.file_observer.start()
            print("👀 Monitoramento de arquivos iniciado")
        
        try:
            # Inicia servidor
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