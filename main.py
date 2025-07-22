#!/usr/bin/env python3
"""
TagonPy - Framework Web Moderno & Reativo
Entrada principal do servidor de desenvolvimento com roteamento avançado
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
        "pages",  # NOVO: diretório para roteamento file-based
        "public/static",
        "templates"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

def main():
    """Função principal (SÍNCRONA)"""
    parser = argparse.ArgumentParser(description="TagonPy Advanced Dev Server")
    parser.add_argument("--host", default="localhost", help="Host do servidor")
    parser.add_argument("--port", type=int, default=3000, help="Porta do servidor")
    parser.add_argument("--components", default="components", help="Diretório dos componentes")
    parser.add_argument("--pages", default="pages", help="Diretório das páginas (roteamento)")
    
    args = parser.parse_args()
    
    # Cria estrutura de diretórios
    create_directory_structure()
    
    # Verifica se existe estrutura de páginas
    pages_dir = Path(args.pages)
    if not pages_dir.exists() or not any(pages_dir.glob("*.tg")):
        print(f"📄 Nenhuma página encontrada em {args.pages}/")
        print("🔄 O sistema de roteamento criará páginas padrão automaticamente...")
    
    # Inicia servidor com roteamento avançado
    server = TagonServer(
        host=args.host,
        port=args.port,
        components_dir=args.components,
        pages_dir=args.pages
    )
    
    # MUDANÇA: Chama start síncrono
    server.start()

if __name__ == "__main__":
    # MUDANÇA: Executa função principal síncrona
    main()