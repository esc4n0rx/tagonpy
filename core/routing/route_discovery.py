import os
import asyncio
from typing import List, Dict
from pathlib import Path
import re

from .models import RouteConfig

class RouteDiscovery:
    """
    Sistema de descoberta automática de rotas baseado em estrutura de arquivos
    Inspirado no sistema file-based routing do Next.js
    """
    
    def __init__(self, pages_dir: str = "pages"):
        self.pages_dir = pages_dir
        self.route_patterns = {
            # Padrões para diferentes tipos de rota
            'dynamic': r'\[([^\]]+)\]',  # [id], [slug]
            'catch_all': r'\[\.\.\.([^\]]+)\]',  # [...params]
            'optional': r'\[\[([^\]]+)\]\]'  # [[optional]]
        }
    
    async def discover_routes(self) -> List[RouteConfig]:
        """
        Descobre todas as rotas no diretório pages/
        Retorna lista de configurações de rota
        """
        routes = []
        
        if not os.path.exists(self.pages_dir):
            print(f"⚠️ Diretório {self.pages_dir} não encontrado. Criando...")
            os.makedirs(self.pages_dir, exist_ok=True)
            await self._create_default_pages()
        
        # Escaneia recursivamente o diretório
        for root, dirs, files in os.walk(self.pages_dir):
            for file in files:
                if file.endswith('.tg'):
                    file_path = os.path.join(root, file)
                    route_config = await self._analyze_file_route(file_path)
                    if route_config:
                        routes.append(route_config)
        
        # Ordena rotas por especificidade (estáticas primeiro, dinâmicas depois)
        routes.sort(key=self._route_specificity_score)
        
        return routes
    
    async def _analyze_file_route(self, file_path: str) -> RouteConfig:
        """
        Analisa um arquivo .tg e determina sua configuração de rota
        """
        # Calcula o caminho relativo
        rel_path = os.path.relpath(file_path, self.pages_dir)
        
        # Remove extensão .tg
        route_path = os.path.splitext(rel_path)[0]
        
        # Converte separadores de sistema para barras web
        route_path = route_path.replace(os.sep, '/')
        
        # Trata arquivos index como rota raiz
        if route_path.endswith('/index'):
            route_path = route_path[:-6] or '/'
        elif route_path == 'index':
            route_path = '/'
        
        # Adiciona barra inicial se necessário
        if not route_path.startswith('/'):
            route_path = '/' + route_path
        
        # Analisa o arquivo para extrair configurações
        config = await self._parse_route_config(file_path)
        
        return RouteConfig(
            path=route_path,
            component_path=file_path,
            middlewares=config.get('middlewares', []),
            guards=config.get('guards', []),
            params=config.get('params', {}),
            layout=config.get('layout')
        )
    
    async def _parse_route_config(self, file_path: str) -> Dict:
        """
        Parseia um arquivo .tg para extrair configurações de rota
        Busca por comentários especiais no início do arquivo
        """
        config = {
            'middlewares': [],
            'guards': [],
            'params': {},
            'layout': None
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Busca por configurações em comentários especiais
            config_patterns = {
                'middlewares': r'#\s*@middlewares?\s*:\s*(.+)',
                'guards': r'#\s*@guards?\s*:\s*(.+)',
                'layout': r'#\s*@layout\s*:\s*(.+)'
            }
            
            for config_type, pattern in config_patterns.items():
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    if config_type in ['middlewares', 'guards']:
                        # Split por vírgula e limpa espaços
                        config[config_type] = [
                            item.strip() 
                            for item in matches[0].split(',')
                            if item.strip()
                        ]
                    else:
                        config[config_type] = matches[0].strip()
            
        except Exception as e:
            print(f"⚠️ Erro ao analisar config de {file_path}: {str(e)}")
        
        return config
    
    def _route_specificity_score(self, route_config: RouteConfig) -> int:
        """
        Calcula pontuação de especificidade para ordenação de rotas
        Rotas mais específicas têm pontuação menor (vêm primeiro)
        """
        path = route_config.path
        score = 0
        
        # Rotas dinâmicas têm pontuação maior
        if '[' in path and ']' in path:
            score += 100
        
        # Catch-all routes têm pontuação ainda maior
        if '[...' in path:
            score += 200
        
        # Rotas mais profundas têm prioridade
        score -= path.count('/') * 10
        
        # Rotas com mais caracteres literais têm prioridade
        literal_chars = len(re.sub(r'\[([^\]]+)\]', '', path))
        score -= literal_chars
        
        return score
    
    async def _create_default_pages(self):
        """
        Cria páginas padrão se o diretório estiver vazio
        """
        default_pages = {
            'index.tg': '''# @middlewares: logging
# @guards: none

Imports: from datetime import datetime

Funcoes:
def get_welcome_message():
    return "Bem-vindo ao TagonPy com Roteamento Avançado!"

def get_current_time():
    return datetime.now().strftime("%d/%m/%Y às %H:%M:%S")

Html:
<div class="welcome-page">
    <h1>{{ get_welcome_message() }}</h1>
    <p>Esta é a página inicial (/) do seu projeto TagonPy.</p>
    <p>Horário atual: {{ get_current_time() }}</p>
    <nav>
        <a href="/about">Sobre</a> |
        <a href="/user/123">Usuário 123</a> |
        <a href="/blog/meu-primeiro-post">Blog Post</a>
    </nav>
</div>

Css:
.welcome-page {
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem;
    text-align: center;
    background: #0a0a0a;
    color: white;
    min-height: 100vh;
}

.welcome-page h1 {
    color: #3b82f6;
    margin-bottom: 2rem;
}

.welcome-page nav a {
    color: #10b981;
    text-decoration: none;
    margin: 0 1rem;
}

.welcome-page nav a:hover {
    text-decoration: underline;
}
'''
        }
        
        for filename, content in default_pages.items():
            file_path = os.path.join(self.pages_dir, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"📄 Página padrão criada: {filename}")