import os
import json
import subprocess
import asyncio
import platform
from pathlib import Path
from typing import Optional, Dict, Any
import shutil

from .cdn_fallback import TailwindCDNManager

class TailwindManager:
    """
    Gerenciador do Tailwind CSS para TagonPy
    Handles installation, configuration, building com CDN fallback
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
        self.local_compilation_failed = False
        
        # NOVO: CDN Fallback Manager
        self.cdn_manager = TailwindCDNManager()
        
        print(f"🔧 Sistema detectado: {platform.system()}")
        print(f"📁 Diretório do projeto: {self.project_root.absolute()}")
        
    async def initialize(self):
        """
        Inicializa o Tailwind CSS no projeto com fallback CDN
        """
        print("🎨 Inicializando Tailwind CSS com fallback CDN...")
        
        try:
            # Tenta inicialização local primeiro
            await self._initialize_local_compilation()
            print("✅ Tailwind CSS local inicializado com sucesso!")
            
        except Exception as e:
            print(f"⚠️ Compilação local falhou: {str(e)}")
            self.local_compilation_failed = True
            
            # Fallback para CDN
            print("🌐 Ativando fallback CDN...")
            await self.cdn_manager.check_cdn_availability()
            
            if self.cdn_manager.is_available:
                print("✅ Tailwind CSS via CDN configurado com sucesso!")
            else:
                print("❌ Nem compilação local nem CDN funcionaram")
                raise Exception("Tailwind CSS completamente indisponível")
        
        self.is_initialized = True
        
    async def _initialize_local_compilation(self):
        """
        Tenta inicializar compilação local (código original)
        """
        # Verifica se Node.js está instalado
        node_check = await self._check_node()
        if not node_check["available"]:
            raise Exception(f"Node.js não encontrado. Detalhes: {node_check['error']}")
        
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
        
        # Build inicial com múltiplas estratégias
        success = await self._initial_build()
        if not success:
            raise Exception("Todas as estratégias de build falharam")
    
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
    
    async def _initial_build(self) -> bool:
        """
        Executa build inicial do CSS - RETORNA BOOL para indicar sucesso
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
                    return True
                else:
                    print(f"⚠️ Falhou com estratégia: {strategy_name}")
            except Exception as e:
                print(f"❌ Erro com estratégia {strategy_name}: {str(e)}")
        
        # Se todas as estratégias falharam
        print("❌ Todas as estratégias de build local falharam")
        return False
    
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
    
    async def start_watch_mode(self):
        """
        Inicia o modo watch do Tailwind CSS
        """
        if self.local_compilation_failed:
            print("⚠️ Watch mode não disponível - usando CDN")
            return
            
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
       if self.local_compilation_failed:
           print("⚠️ Build de produção não disponível - usando CDN")
           return
           
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
        """Retorna conteúdo do CSS compilado ou fallback"""
        if self.local_compilation_failed or not self.output_css.exists():
            print("⚠️ Usando CDN - CSS local não disponível")
            return ""  # CDN será usado no template
        
        try:
            with open(self.output_css, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"📖 CSS local carregado: {len(content)} caracteres")
                return content
        except Exception as e:
            print(f"❌ Erro ao ler CSS local: {str(e)}")
            return ""
    
    def should_use_cdn(self) -> bool:
        """Indica se deve usar CDN ao invés de CSS local"""
        return self.local_compilation_failed or not self.output_css.exists()
    
    def get_cdn_html(self) -> str:
        """Retorna HTML para CDN"""
        return self.cdn_manager.get_cdn_html_injection()
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status detalhado incluindo CDN"""
        base_status = {
            "initialized": self.is_initialized,
            "local_compilation_failed": self.local_compilation_failed,
            "should_use_cdn": self.should_use_cdn(),
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
        
        base_status["cdn"] = self.cdn_manager.get_status()
        
        return base_status

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