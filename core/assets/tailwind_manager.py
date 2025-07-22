import os
import json
import subprocess
import asyncio
import platform
from pathlib import Path
from typing import Optional, Dict, Any
import shutil

class TailwindManager:
    """
    Gerenciador do Tailwind CSS para TagonPy
    Handles installation, configuration, and building of Tailwind CSS
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.assets_dir = self.project_root / "assets"
        self.css_dir = self.assets_dir / "css"
        self.config_file = self.assets_dir / "tailwind.config.js"
        self.input_css = self.css_dir / "input.css"
        self.output_css = self.css_dir / "output.css"
        self.package_json = self.project_root / "package.json"
        
        # Windows compatibility
        self.is_windows = platform.system().lower() == "windows"
        self.shell = self.is_windows  # Use shell=True on Windows
        
        self.is_initialized = False
        self.build_process: Optional[asyncio.subprocess.Process] = None
        
        print(f"🔧 Sistema detectado: {platform.system()}")
        print(f"📁 Diretório do projeto: {self.project_root.absolute()}")
        
    async def initialize(self):
        """
        Inicializa o Tailwind CSS no projeto
        """
        print("🎨 Inicializando Tailwind CSS...")
        
        # Verifica se Node.js está instalado
        node_check = await self._check_node()
        if not node_check["available"]:
            error_msg = f"Node.js não encontrado. Detalhes: {node_check['error']}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
        
        print(f"✅ Node.js encontrado: {node_check['version']}")
        
        # Cria estrutura de diretórios
        await self._create_directory_structure()
        
        # Cria package.json se não existir
        await self._create_package_json()
        
        # Instala Tailwind CSS
        await self._install_tailwind()
        
        # Cria arquivos de configuração
        await self._create_config_files()
        
        # Build inicial
        await self._initial_build()
        
        self.is_initialized = True
        print("✅ Tailwind CSS inicializado com sucesso!")
        
    async def _check_node(self) -> Dict[str, Any]:
        """Verifica se Node.js está instalado (versão corrigida para Windows)"""
        try:
            print("🔍 Verificando Node.js...")
            
            # Tenta executar node --version
            if self.is_windows:
                # No Windows, usa shell=True e tenta diferentes comandos
                cmd = "node --version"
                result = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=True
                )
            else:
                # Unix/Linux/macOS
                result = await asyncio.create_subprocess_exec(
                    "node", "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                version = stdout.decode().strip()
                print(f"✅ Node.js detectado: {version}")
                return {
                    "available": True,
                    "version": version,
                    "error": None
                }
            else:
                error = stderr.decode().strip()
                print(f"❌ Erro ao executar node: {error}")
                return {
                    "available": False,
                    "version": None,
                    "error": error
                }
                
        except Exception as e:
            print(f"❌ Exceção ao verificar Node.js: {str(e)}")
            return {
                "available": False,
                "version": None,
                "error": str(e)
            }
    
    async def _create_directory_structure(self):
        """Cria estrutura de diretórios necessária"""
        print("📂 Criando estrutura de diretórios...")
        self.assets_dir.mkdir(exist_ok=True)
        self.css_dir.mkdir(exist_ok=True)
        print(f"✅ Diretórios criados: {self.assets_dir}")
    
    async def _create_package_json(self):
        """Cria package.json se não existir"""
        if self.package_json.exists():
            print("📦 package.json já existe")
            return
            
        print("📦 Criando package.json...")
        package_config = {
            "name": "tagonpy-project",
            "version": "1.0.0",
            "description": "TagonPy project with Tailwind CSS",
            "scripts": {
                "build-css": "tailwindcss -i ./assets/css/input.css -o ./assets/css/output.css",
                "watch-css": "tailwindcss -i ./assets/css/input.css -o ./assets/css/output.css --watch",
                "build-css-prod": "tailwindcss -i ./assets/css/input.css -o ./assets/css/output.css --minify"
            },
            "devDependencies": {}
        }
        
        with open(self.package_json, 'w', encoding='utf-8') as f:
            json.dump(package_config, f, indent=2)
        
        print("✅ package.json criado")
    
    async def _install_tailwind(self):
        """Instala Tailwind CSS via npm (versão corrigida para Windows)"""
        print("⬇️ Instalando Tailwind CSS...")
        
        try:
            if self.is_windows:
                # Windows: usar shell=True
                cmd = "npm install -D tailwindcss"
                print(f"🔧 Executando: {cmd}")
                
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    cwd=self.project_root,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=True
                )
            else:
                # Unix/Linux/macOS
                process = await asyncio.create_subprocess_exec(
                    "npm", "install", "-D", "tailwindcss",
                    cwd=self.project_root,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore').strip()
                print(f"❌ Erro no stdout: {stdout.decode('utf-8', errors='ignore')}")
                print(f"❌ Erro no stderr: {error_msg}")
                raise Exception(f"Erro ao instalar Tailwind: {error_msg}")
            
            success_msg = stdout.decode('utf-8', errors='ignore').strip()
            print(f"✅ Tailwind CSS instalado com sucesso")
            if success_msg:
                print(f"📦 Output: {success_msg[:200]}...")  # Primeiros 200 chars
                
        except Exception as e:
            print(f"❌ Exceção durante instalação: {str(e)}")
            raise
    
    async def _create_config_files(self):
        """Cria arquivos de configuração do Tailwind"""
        print("⚙️ Criando arquivos de configuração...")
        
        # tailwind.config.js
        config_content = """/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{html,tg}",
    "./components/**/*.{html,tg}",
    "./templates/**/*.html"
  ],
  theme: {
    extend: {
      colors: {
        'tagonpy': {
          50: '#f0f9ff',
          500: '#3b82f6',
          900: '#1e3a8a'
        }
      }
    },
  },
  plugins: [],
}"""
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        # input.css
        input_css_content = """@tailwind base;
@tailwind components;
@tailwind utilities;

/* TagonPy Custom Styles */
@layer components {
  .tagonpy-container {
    @apply max-w-7xl mx-auto px-4 sm:px-6 lg:px-8;
  }
  
  .tagonpy-button {
    @apply px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors;
  }
  
  .tagonpy-card {
    @apply bg-white dark:bg-gray-800 rounded-lg shadow-md p-6;
  }
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  :root {
    color-scheme: dark;
  }
}"""
        
        with open(self.input_css, 'w', encoding='utf-8') as f:
            f.write(input_css_content)
        
        print("✅ Arquivos de configuração criados")
    
    async def _initial_build(self):
        """Executa build inicial do CSS (versão corrigida para Windows)"""
        print("🔨 Executando build inicial...")
        
        try:
            if self.is_windows:
                # Windows: usar shell=True e npx via shell
                cmd = f"npx tailwindcss -i {self.input_css} -o {self.output_css}"
                print(f"🔧 Executando: {cmd}")
                
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    cwd=self.project_root,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=True
                )
            else:
                # Unix/Linux/macOS
                process = await asyncio.create_subprocess_exec(
                    "npx", "tailwindcss", 
                    "-i", str(self.input_css),
                    "-o", str(self.output_css),
                    cwd=self.project_root,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore').strip()
                print(f"❌ Erro no build: {error_msg}")
                print(f"❌ stdout: {stdout.decode('utf-8', errors='ignore')}")
                raise Exception(f"Erro no build inicial: {error_msg}")
            
            # Verifica se arquivo foi criado
            if self.output_css.exists():
                size = self.output_css.stat().st_size
                print(f"✅ CSS compilado com sucesso: {self.output_css} ({size} bytes)")
            else:
                raise Exception("Arquivo CSS não foi gerado")
                
        except Exception as e:
            print(f"❌ Exceção durante build inicial: {str(e)}")
            raise
    
    async def start_watch_mode(self):
        """
        Inicia o modo watch do Tailwind CSS (versão corrigida para Windows)
        """
        if not self.is_initialized:
            await self.initialize()
        
        print("👀 Iniciando Tailwind CSS watch mode...")
        
        # Para processo anterior se existir
        if self.build_process:
            await self.stop_watch_mode()
        
        try:
            if self.is_windows:
                # Windows: usar shell=True
                cmd = f"npx tailwindcss -i {self.input_css} -o {self.output_css} --watch"
                print(f"🔧 Executando watch: {cmd}")
                
                self.build_process = await asyncio.create_subprocess_shell(
                    cmd,
                    cwd=self.project_root,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=True
                )
            else:
                # Unix/Linux/macOS
                self.build_process = await asyncio.create_subprocess_exec(
                    "npx", "tailwindcss",
                    "-i", str(self.input_css),
                    "-o", str(self.output_css),
                    "--watch",
                    cwd=self.project_root,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            print("✅ Tailwind CSS watch mode ativo")
            
            # Monitora output do processo em background
            asyncio.create_task(self._monitor_build_process())
            
        except Exception as e:
            print(f"❌ Erro ao iniciar watch mode: {str(e)}")
            raise
    
    async def stop_watch_mode(self):
        """Para o modo watch"""
        if self.build_process:
            print("⏹️ Parando Tailwind CSS watch mode...")
            try:
                self.build_process.terminate()
                await asyncio.wait_for(self.build_process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                print("⚠️ Forçando parada do processo...")
                self.build_process.kill()
                await self.build_process.wait()
            
            self.build_process = None
            print("✅ Tailwind CSS watch mode parado")
    
    async def _monitor_build_process(self):
        """Monitora o processo de build para logs"""
        if not self.build_process:
            return
            
        print("👀 Monitorando processo de build...")
        
        try:
            while self.build_process.returncode is None:
                try:
                    # Lê stdout e stderr
                    line = await asyncio.wait_for(
                        self.build_process.stdout.readline(), 
                        timeout=1.0
                    )
                    
                    if line:
                        output = line.decode('utf-8', errors='ignore').strip()
                        if output and not output.startswith('Done in'):
                            print(f"🎨 Tailwind: {output}")
                            
                except asyncio.TimeoutError:
                    # Timeout é normal, continua monitorando
                    continue
                except Exception as e:
                    print(f"⚠️ Erro no monitoramento: {e}")
                    break
                    
        except Exception as e:
            print(f"❌ Erro fatal no monitoramento: {e}")
        
        print("👀 Monitoramento finalizado")
    
    async def build_production(self):
        """Build de produção com minificação (versão corrigida para Windows)"""
        print("🚀 Executando build de produção...")
        
        try:
            if self.is_windows:
                cmd = f"npx tailwindcss -i {self.input_css} -o {self.output_css} --minify"
                print(f"🔧 Executando: {cmd}")
                
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    cwd=self.project_root,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=True
                )
            else:
                process = await asyncio.create_subprocess_exec(
                    "npx", "tailwindcss",
                    "-i", str(self.input_css),
                    "-o", str(self.output_css),
                    "--minify",
                    cwd=self.project_root,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Calcula tamanho do arquivo
                size = self.output_css.stat().st_size
                size_kb = size / 1024
                print(f"✅ Build de produção concluído: {size_kb:.1f}KB")
            else:
                error_msg = stderr.decode('utf-8', errors='ignore').strip()
                print(f"❌ Erro no build de produção: {error_msg}")
                raise Exception(f"Erro no build de produção: {error_msg}")
                
        except Exception as e:
            print(f"❌ Exceção durante build de produção: {str(e)}")
            raise
    
    def get_css_content(self) -> str:
        """Retorna conteúdo do CSS compilado"""
        try:
            if self.output_css.exists():
                with open(self.output_css, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(f"📖 CSS carregado: {len(content)} caracteres")
                    return content
            else:
                print("⚠️ Arquivo CSS compilado não encontrado")
                return ""
        except Exception as e:
            print(f"❌ Erro ao ler CSS: {str(e)}")
            return ""
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do Tailwind"""
        return {
            "initialized": self.is_initialized,
            "watching": self.build_process is not None,
            "config_exists": self.config_file.exists(),
            "input_css_exists": self.input_css.exists(),
            "output_css_exists": self.output_css.exists(),
            "output_css_size": self.output_css.stat().st_size if self.output_css.exists() else 0,
            "system": platform.system(),
            "project_root": str(self.project_root.absolute())
        }