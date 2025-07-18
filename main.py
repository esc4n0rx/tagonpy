#!/usr/bin/env python3
"""
TagonPy - Framework Web Moderno & Reativo
Entrada principal do servidor de desenvolvimento
"""

import sys
import os
import argparse
from pathlib import Path
from core.server import TagonServer

def create_directory_structure():
    """Cria estrutura de diretórios se não existir"""
    directories = [
        "components",
        "public/static",
        "templates"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="TagonPy Dev Server")
    parser.add_argument("--host", default="localhost", help="Host do servidor")
    parser.add_argument("--port", type=int, default=3000, help="Porta do servidor")
    parser.add_argument("--components", default="components", help="Diretório dos componentes")
    
    args = parser.parse_args()
    
    # Cria estrutura de diretórios
    create_directory_structure()
    
    # Verifica se existe App.tg
    app_component = Path(args.components) / "App.tg"
    if not app_component.exists():
        print(f"❌ Arquivo App.tg não encontrado em {args.components}/")
        print("📝 Criando arquivo App.tg de exemplo...")
        
        # Cria App.tg básico se não existir
        with open(app_component, 'w', encoding='utf-8') as f:
            f.write("""Imports: from datetime import datetime

Funcoes: def saudacao(): return "Olá mundo do TagonPy!"

Html:
<div>
    <h1>{{ saudacao() }}</h1>
    <p>Bem-vindo ao TagonPy! 🚀</p>
    <p>Edite este arquivo em components/App.tg para começar.</p>
</div>

Css:
h1 {
    color: #4caf50;
    font-family: sans-serif;
    text-align: center;
}

p {
    text-align: center;
    color: #666;
    font-size: 1.1em;
}
""")
        print("✅ Arquivo App.tg criado com sucesso!")
    
    # Inicia servidor
    server = TagonServer(
        host=args.host,
        port=args.port,
        components_dir=args.components
    )
    
    server.start()

if __name__ == "__main__":
    main()
