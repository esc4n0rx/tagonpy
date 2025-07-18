import re
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class TagonComponent:
    """Representa um componente .tg parseado"""
    imports: str
    functions: str
    html: str
    css: str
    raw_content: str

class TagonParser:
    """Parser para arquivos .tg com sintaxe reativa personalizada"""
    
    def __init__(self):
        # Padrões regex para extrair seções do arquivo .tg
        self.patterns = {
            'imports': r'Imports:\s*(.*?)(?=\n\s*[A-Z][a-z]*:|$)',
            'functions': r'Funcoes:\s*(.*?)(?=\n\s*[A-Z][a-z]*:|$)',
            'html': r'Html:\s*(.*?)(?=\n\s*[A-Z][a-z]*:|$)',
            'css': r'Css:\s*(.*?)(?=\n\s*[A-Z][a-z]*:|$)'
        }
    
    def parse_file(self, file_path: str) -> TagonComponent:
        """
        Lê e parseia um arquivo .tg
        
        Args:
            file_path: Caminho para o arquivo .tg
            
        Returns:
            TagonComponent: Componente parseado
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            return self.parse_content(content)
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Arquivo .tg não encontrado: {file_path}")
        except Exception as e:
            raise Exception(f"Erro ao parsear arquivo .tg: {str(e)}")
    
    def parse_content(self, content: str) -> TagonComponent:
        """
        Parseia o conteúdo de um arquivo .tg
        
        Args:
            content: Conteúdo do arquivo .tg
            
        Returns:
            TagonComponent: Componente parseado
        """
        # Extrai cada seção usando regex
        sections = {}
        
        for section_name, pattern in self.patterns.items():
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            sections[section_name] = match.group(1).strip() if match else ""
        
        return TagonComponent(
            imports=sections.get('imports', ''),
            functions=sections.get('functions', ''),
            html=sections.get('html', ''),
            css=sections.get('css', ''),
            raw_content=content
        )
    
    def extract_template_variables(self, html: str) -> list:
        """
        Extrai variáveis de template do HTML (formato {{ variavel }})
        
        Args:
            html: Conteúdo HTML
            
        Returns:
            list: Lista de variáveis encontradas
        """
        pattern = r'\{\{\s*([^}]+)\s*\}\}'
        matches = re.findall(pattern, html)
        return [match.strip() for match in matches]