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
        self.node_modules_bin = self.project_root / "node_modules" / ".bin"
        
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
        
        # Verifica se npx está disponível
        npx_check = await self._check_npx()
        if not npx_check["available"]:
            print(f"⚠️ NPX não encontrado: {npx_check['error']}")
        else:
            print(f"✅ NPX encontrado: {npx_check['version']}")
        
        # Cria estrutura de diretórios
        await self._create_directory_structure()
        
        # Cria package.json se não existir
        await self._create_package_json()
        
        # Instala Tailwind CSS
        await self._install_tailwind()
        
        # Cria arquivos de configuração
        await self._create_config_files()
        
        # Build inicial (CORRIGIDO COM MÚLTIPLAS ESTRATÉGIAS)
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
    
    async def _check_npx(self) -> Dict[str, Any]:
        """NOVO: Verifica se NPX está disponível"""
        try:
            print("🔍 Verificando NPX...")
            
            if self.is_windows:
                cmd = "npx --version"
                result = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=True
                )
            else:
                result = await asyncio.create_subprocess_exec(
                    "npx", "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                version = stdout.decode().strip()
                return {
                    "available": True,
                    "version": version,
                    "error": None
                }
            else:
                error = stderr.decode().strip()
                return {
                    "available": False,
                    "version": None,
                    "error": error
                }
                
        except Exception as e:
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
        """Cria package.json se não existir - CORRIGIDO COM NPXS"""
        if self.package_json.exists():
            print("📦 package.json já existe - atualizando scripts...")
            # Carrega package.json existente e atualiza scripts
            try:
                with open(self.package_json, 'r', encoding='utf-8') as f:
                    package_config = json.load(f)
            except:
                package_config = {}
        else:
            print("📦 Criando package.json...")
            package_config = {
                "name": "tagonpy-project",
                "version": "1.0.0",
                "description": "TagonPy project with Tailwind CSS"
            }
        
        # CORREÇÃO: Scripts usando npx para maior compatibilidade
        package_config["scripts"] = {
            "build-css": "npx tailwindcss -i ./assets/css/input.css -o ./assets/css/output.css",
            "watch-css": "npx tailwindcss -i ./assets/css/input.css -o ./assets/css/output.css --watch",
            "build-css-prod": "npx tailwindcss -i ./assets/css/input.css -o ./assets/css/output.css --minify"
        }
        
        # Garante que devDependencies existe
        if "devDependencies" not in package_config:
            package_config["devDependencies"] = {}
        
        with open(self.package_json, 'w', encoding='utf-8') as f:
            json.dump(package_config, f, indent=2)
        
        print("✅ package.json criado/atualizado com scripts npx")
    
    async def _install_tailwind(self):
        """Instala Tailwind CSS via npm (versão corrigida para Windows)"""
        print("⬇️ Instalando Tailwind CSS...")
        
        try:
            if self.is_windows:
                # Windows: usar shell=True
                cmd = "npm install -D tailwindcss@latest"
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
                    "npm", "install", "-D", "tailwindcss@latest",
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
        """
        Executa build inicial do CSS - VERSÃO FINAL COM MÚLTIPLAS ESTRATÉGIAS
        """
        print("🔨 Executando build inicial com múltiplas estratégias...")
        
        strategies = [
            ("NPX Direto", self._build_with_npx_direct),
            ("NPM Script", self._build_with_npm_script),
            ("Node_modules Local", self._build_with_local_executable),
        ]
        
        for strategy_name, strategy_func in strategies:
            print(f"🔧 Tentando estratégia: {strategy_name}")
            try:
                success = await strategy_func()
                if success:
                    print(f"✅ Sucesso com estratégia: {strategy_name}")
                    return
                else:
                    print(f"⚠️ Falhou com estratégia: {strategy_name}")
            except Exception as e:
                print(f"❌ Erro com estratégia {strategy_name}: {str(e)}")
        
        # Se todas as estratégias falharam, cria fallback
        print("🔧 Todas as estratégias falharam, criando CSS de fallback...")
        await self._create_fallback_css()
    
    async def _build_with_npx_direct(self) -> bool:
        """Estratégia 1: NPX direto"""
        try:
            if self.is_windows:
                cmd = f"npx tailwindcss -i \"{self.input_css.absolute()}\" -o \"{self.output_css.absolute()}\""
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
                    cwd=self.project_root,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and self.output_css.exists():
                size = self.output_css.stat().st_size
                print(f"✅ NPX Direct - CSS compilado: {size} bytes")
                return True
            else:
                print(f"❌ NPX Direct falhou: {stderr.decode('utf-8', errors='ignore')}")
                return False
                
        except Exception as e:
            print(f"❌ Exceção NPX Direct: {str(e)}")
            return False
    
    async def _build_with_npm_script(self) -> bool:
        """Estratégia 2: NPM Script"""
        try:
            if self.is_windows:
                cmd = "npm run build-css"
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    cwd=self.project_root,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=True
                )
            else:
                process = await asyncio.create_subprocess_exec(
                    "npm", "run", "build-css",
                    cwd=self.project_root,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and self.output_css.exists():
                size = self.output_css.stat().st_size
                print(f"✅ NPM Script - CSS compilado: {size} bytes")
                return True
            else:
                print(f"❌ NPM Script falhou: {stderr.decode('utf-8', errors='ignore')}")
                return False
                
        except Exception as e:
            print(f"❌ Exceção NPM Script: {str(e)}")
            return False
    
    async def _build_with_local_executable(self) -> bool:
        """Estratégia 3: Executável local do node_modules"""
        try:
            # Procura executáveis no node_modules/.bin
            possible_executables = []
            
            if self.is_windows:
                possible_executables = [
                    self.node_modules_bin / "tailwindcss.cmd",
                    self.node_modules_bin / "tailwindcss.bat",
                    self.node_modules_bin / "tailwindcss.exe",
                    self.node_modules_bin / "tailwindcss"
                ]
            else:
                possible_executables = [
                    self.node_modules_bin / "tailwindcss"
                ]
            
            tailwind_exec = None
            for executable in possible_executables:
                if executable.exists():
                    tailwind_exec = executable
                    break
            
            if not tailwind_exec:
                print("❌ Nenhum executável Tailwind encontrado em node_modules")
                return False
            
            print(f"✅ Encontrado executável: {tailwind_exec}")
            
            if self.is_windows:
                cmd = f"\"{tailwind_exec.absolute()}\" -i \"{self.input_css.absolute()}\" -o \"{self.output_css.absolute()}\""
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    cwd=self.project_root,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=True
                )
            else:
                process = await asyncio.create_subprocess_exec(
                    str(tailwind_exec),
                    "-i", str(self.input_css),
                    "-o", str(self.output_css),
                    cwd=self.project_root,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and self.output_css.exists():
                size = self.output_css.stat().st_size
                print(f"✅ Executável Local - CSS compilado: {size} bytes")
                return True
            else:
                print(f"❌ Executável Local falhou: {stderr.decode('utf-8', errors='ignore')}")
                return False
                
        except Exception as e:
            print(f"❌ Exceção Executável Local: {str(e)}")
            return False
    
    async def _create_fallback_css(self):
        """Cria CSS de fallback quando build falha"""
        fallback_css = """/* TagonPy Fallback CSS com classes Tailwind básicas */

/* Reset */
*, *::before, *::after {
  box-sizing: border-box;
  border-width: 0;
  border-style: solid;
}

html {
  line-height: 1.5;
  -webkit-text-size-adjust: 100%;
  tab-size: 4;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

body {
  margin: 0;
  line-height: inherit;
}

/* Cores de fundo */
.bg-gray-900 { background-color: rgb(17 24 39); }
.bg-gray-800 { background-color: rgb(31 41 55); }
.bg-blue-500 { background-color: rgb(59 130 246); }
.bg-green-400 { background-color: rgb(74 222 128); }
.bg-yellow-400 { background-color: rgb(250 204 21); }
.bg-purple-400 { background-color: rgb(196 181 253); }
.bg-cyan-400 { background-color: rgb(34 211 238); }
.bg-cyan-500 { background-color: rgb(6 182 212); }
.bg-green-500 { background-color: rgb(34 197 94); }
.bg-yellow-500 { background-color: rgb(234 179 8); }

/* Cores de texto */
.text-white { color: rgb(255 255 255); }
.text-gray-300 { color: rgb(209 213 219); }
.text-gray-400 { color: rgb(156 163 175); }
.text-blue-400 { color: rgb(96 165 250); }
.text-green-400 { color: rgb(74 222 128); }
.text-yellow-400 { color: rgb(250 204 21); }
.text-purple-400 { color: rgb(196 181 253); }
.text-cyan-400 { color: rgb(34 211 238); }
.text-transparent { color: transparent; }

/* Layout */
.container { 
  width: 100%;
  margin-left: auto;
  margin-right: auto;
  padding-left: 1rem;
  padding-right: 1rem;
  max-width: 1280px;
}

.min-h-screen { min-height: 100vh; }
.mx-auto { margin-left: auto; margin-right: auto; }
.px-4 { padding-left: 1rem; padding-right: 1rem; }
.py-8 { padding-top: 2rem; padding-bottom: 2rem; }
.p-6 { padding: 1.5rem; }
.mb-4 { margin-bottom: 1rem; }
.mb-6 { margin-bottom: 1.5rem; }
.mb-12 { margin-bottom: 3rem; }
.mr-2 { margin-right: 0.5rem; }
.mr-4 { margin-right: 1rem; }

/* Grid */
.grid { display: grid; }
.grid-cols-1 { grid-template-columns: repeat(1, minmax(0, 1fr)); }
.gap-6 { gap: 1.5rem; }
.gap-8 { gap: 2rem; }

@media (min-width: 768px) {
  .md\\:grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (min-width: 1024px) {
  .lg\\:grid-cols-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}

/* Flexbox */
.flex { display: flex; }
.items-center { align-items: center; }
.items-start { align-items: flex-start; }
.justify-center { justify-content: center; }
.space-x-4 > :not([hidden]) ~ :not([hidden]) { margin-left: 1rem; }

/* Texto */
.text-center { text-align: center; }
.text-lg { font-size: 1.125rem; line-height: 1.75rem; }
.text-xl { font-size: 1.25rem; line-height: 1.75rem; }
.text-2xl { font-size: 1.5rem; line-height: 2rem; }
.text-3xl { font-size: 1.875rem; line-height: 2.25rem; }
.text-4xl { font-size: 2.25rem; line-height: 2.5rem; }
.text-5xl { font-size: 3rem; line-height: 1; }
.text-6xl { font-size: 3.75rem; line-height: 1; }

.font-bold { font-weight: 700; }
.font-semibold { font-weight: 600; }

/* Bordas */
.rounded-lg { border-radius: 0.5rem; }
.rounded-full { border-radius: 9999px; }

/* Tamanhos */
.w-3 { width: 0.75rem; }
.h-3 { height: 0.75rem; }
.max-w-2xl { max-width: 42rem; }

/* Transições */
.transition-colors { 
  transition-property: color, background-color, border-color;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 150ms;
}

/* Hover states */
.hover\\:bg-gray-750:hover { background-color: #374151; }

/* Gradientes */
.bg-gradient-to-r { 
  background: linear-gradient(to right, rgb(96 165 250), rgb(34 211 238));
}

.bg-clip-text { 
  -webkit-background-clip: text;
  background-clip: text;
}

/* Responsivo básico */
@media (max-width: 767px) {
  .container { padding-left: 0.5rem; padding-right: 0.5rem; }
  .text-5xl { font-size: 2.5rem; }
  .text-6xl { font-size: 3rem; }
}
"""
        
        try:
            with open(self.output_css, 'w', encoding='utf-8') as f:
                f.write(fallback_css)
            
            size = self.output_css.stat().st_size
            print(f"✅ CSS de fallback criado: {self.output_css} ({size} bytes)")
            
        except Exception as e:
            print(f"❌ Erro ao criar CSS de fallback: {str(e)}")
    
    async def start_watch_mode(self):
        """
        Inicia o modo watch do Tailwind CSS usando a melhor estratégia disponível
        """
        if not self.is_initialized:
            await self.initialize()
        
        print("👀 Iniciando Tailwind CSS watch mode...")
        
        # Para processo anterior se existir
        if self.build_process:
            await self.stop_watch_mode()
        
        # Tenta diferentes estratégias para watch mode
        strategies = [
            ("NPX Watch", self._start_watch_with_npx),
            ("NPM Script Watch", self._start_watch_with_npm_script)
        ]
        
        for strategy_name, strategy_func in strategies:
            print(f"🔧 Tentando watch com estratégia: {strategy_name}")
            try:
                success = await strategy_func()
                if success:
                    print(f"✅ Watch ativo com estratégia: {strategy_name}")
                    # Monitora output do processo em background
                    asyncio.create_task(self._monitor_build_process())
                    return
                else:
                    print(f"⚠️ Falhou watch com estratégia: {strategy_name}")
            except Exception as e:
                print(f"❌ Erro watch com estratégia {strategy_name}: {str(e)}")
        
        print("❌ Não foi possível iniciar watch mode")
    
    async def _start_watch_with_npx(self) -> bool:
        """Watch usando NPX direto"""
        try:
            if self.is_windows:
                cmd = f"npx tailwindcss -i \"{self.input_css.absolute()}\" -o \"{self.output_css.absolute()}\" --watch"
                self.build_process = await asyncio.create_subprocess_shell(
                    cmd,
                    cwd=self.project_root,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=True
                )
            else:
                self.build_process = await asyncio.create_subprocess_exec(
                    "npx", "tailwindcss",
                    "-i", str(self.input_css),
                    "-o", str(self.output_css),
                    "--watch",
                    cwd=self.project_root,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            # Aguarda um pouco para ver se o processo inicia corretamente
            await asyncio.sleep(1)
            
            if self.build_process.returncode is None:  # Processo ainda rodando
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ Exceção NPX Watch: {str(e)}")
            return False
    
    async def _start_watch_with_npm_script(self) -> bool:
        """Watch usando NPM Script"""
        try:
            if self.is_windows:
                cmd = "npm run watch-css"
                self.build_process = await asyncio.create_subprocess_shell(
                    cmd,
                    cwd=self.project_root,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=True
                )
            else:
                self.build_process = await asyncio.create_subprocess_exec(
                    "npm", "run", "watch-css",
                    cwd=self.project_root,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            # Aguarda um pouco para ver se o processo inicia corretamente
            await asyncio.sleep(1)
            
            if self.build_process.returncode is None:  # Processo ainda rodando
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ Exceção NPM Script Watch: {str(e)}")
            return False
    
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
       """Build de produção com minificação usando múltiplas estratégias"""
       print("🚀 Executando build de produção...")
       
       strategies = [
           ("NPX Production", self._build_production_with_npx),
           ("NPM Script Production", self._build_production_with_npm_script),
       ]
       
       for strategy_name, strategy_func in strategies:
           print(f"🔧 Tentando build de produção: {strategy_name}")
           try:
               success = await strategy_func()
               if success:
                   print(f"✅ Sucesso build de produção: {strategy_name}")
                   return
               else:
                   print(f"⚠️ Falhou build de produção: {strategy_name}")
           except Exception as e:
               print(f"❌ Erro build de produção {strategy_name}: {str(e)}")
       
       print("❌ Não foi possível executar build de produção")
       raise Exception("Falha em todas as estratégias de build de produção")
   
    async def _build_production_with_npx(self) -> bool:
       """Build de produção usando NPX"""
       try:
           if self.is_windows:
               cmd = f"npx tailwindcss -i \"{self.input_css.absolute()}\" -o \"{self.output_css.absolute()}\" --minify"
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
           
           if process.returncode == 0 and self.output_css.exists():
               size = self.output_css.stat().st_size
               size_kb = size / 1024
               print(f"✅ NPX Production - CSS minificado: {size_kb:.1f}KB")
               return True
           else:
               print(f"❌ NPX Production falhou: {stderr.decode('utf-8', errors='ignore')}")
               return False
               
       except Exception as e:
           print(f"❌ Exceção NPX Production: {str(e)}")
           return False
   
    async def _build_production_with_npm_script(self) -> bool:
       """Build de produção usando NPM Script"""
       try:
           if self.is_windows:
               cmd = "npm run build-css-prod"
               process = await asyncio.create_subprocess_shell(
                   cmd,
                   cwd=self.project_root,
                   stdout=asyncio.subprocess.PIPE,
                   stderr=asyncio.subprocess.PIPE,
                   shell=True
               )
           else:
               process = await asyncio.create_subprocess_exec(
                   "npm", "run", "build-css-prod",
                   cwd=self.project_root,
                   stdout=asyncio.subprocess.PIPE,
                   stderr=asyncio.subprocess.PIPE
               )
           
           stdout, stderr = await process.communicate()
           
           if process.returncode == 0 and self.output_css.exists():
               size = self.output_css.stat().st_size
               size_kb = size / 1024
               print(f"✅ NPM Script Production - CSS minificado: {size_kb:.1f}KB")
               return True
           else:
               print(f"❌ NPM Script Production falhou: {stderr.decode('utf-8', errors='ignore')}")
               return False
               
       except Exception as e:
           print(f"❌ Exceção NPM Script Production: {str(e)}")
           return False
   
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
       """Retorna status detalhado do Tailwind"""
       return {
           "initialized": self.is_initialized,
           "watching": self.build_process is not None,
           "config_exists": self.config_file.exists(),
           "input_css_exists": self.input_css.exists(),
           "output_css_exists": self.output_css.exists(),
           "output_css_size": self.output_css.stat().st_size if self.output_css.exists() else 0,
           "system": platform.system(),
           "project_root": str(self.project_root.absolute()),
           "node_modules_exists": self.node_modules_bin.exists(),
           "possible_executables": self._get_available_executables()
       }
   
    def _get_available_executables(self) -> Dict[str, bool]:
       """Verifica quais executáveis estão disponíveis"""
       executables = {}
       
       if self.is_windows:
           possible_paths = [
               self.node_modules_bin / "tailwindcss.cmd",
               self.node_modules_bin / "tailwindcss.bat",
               self.node_modules_bin / "tailwindcss.exe",
               self.node_modules_bin / "tailwindcss"
           ]
       else:
           possible_paths = [
               self.node_modules_bin / "tailwindcss"
           ]
       
       for path in possible_paths:
           executables[str(path.name)] = path.exists()
       
       return executables