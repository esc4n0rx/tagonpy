import re
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, ValidationError

class ParamValidator:
    """
    Validador de parâmetros dinâmicos de rota
    """
    
    def __init__(self):
        self.type_patterns = {
            'int': r'^\d+$',
            'float': r'^\d+\.\d+$',
            'string': r'^[a-zA-Z0-9_-]+$',
            'slug': r'^[a-z0-9]+(?:-[a-z0-9]+)*$',
            'uuid': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        }
    
    def validate_param(self, value: str, param_type: str = 'string') -> tuple[bool, Any]:
        """
        Valida um parâmetro baseado no tipo especificado
        
        Returns:
            Tuple (is_valid, converted_value)
        """
        if param_type not in self.type_patterns:
            return True, value  # Tipo desconhecido, aceita qualquer valor
        
        pattern = self.type_patterns[param_type]
        if not re.match(pattern, value):
            return False, None
        
        # Converte para o tipo apropriado
        try:
            if param_type == 'int':
                return True, int(value)
            elif param_type == 'float':
                return True, float(value)
            else:
                return True, value
        except ValueError:
            return False, None

class DynamicParams:
    """
    Gerenciador de parâmetros dinâmicos de rota
    """
    
    def __init__(self):
        self.validator = ParamValidator()
        self.route_param_configs: Dict[str, Dict] = {}
    
    def register_route_params(self, route_path: str, param_configs: Dict[str, str]):
        """
        Registra configuração de parâmetros para uma rota
        
        Args:
            route_path: Caminho da rota (ex: /user/[id])
            param_configs: Dict com nome_param: tipo (ex: {'id': 'int'})
        """
        self.route_param_configs[route_path] = param_configs
        print(f"📋 Parâmetros registrados para {route_path}: {param_configs}")
    
    def extract_route_params(self, route_template: str, actual_path: str) -> Dict[str, Any]:
        """
        Extrai parâmetros dinâmicos de uma URL real
        
        Args:
            route_template: Template da rota (ex: /user/[id])
            actual_path: URL real (ex: /user/123)
            
        Returns:
            Dict com parâmetros extraídos e validados
        """
        params = {}
        
        # Converte template para regex
        regex_pattern = re.sub(r'\[([^\]]+)\]', r'([^/]+)', route_template)
        regex_pattern = f'^{regex_pattern}$'
        
        # Extrai nomes dos parâmetros
        param_names = re.findall(r'\[([^\]]+)\]', route_template)
        
        # Faz match na URL real
        match = re.match(regex_pattern, actual_path)
        if not match:
            return params
        
        # Combina nomes com valores
        param_values = match.groups()
        for name, value in zip(param_names, param_values):
            # Valida se há configuração específica para este parâmetro
            param_type = 'string'  # padrão
            if route_template in self.route_param_configs:
                param_type = self.route_param_configs[route_template].get(name, 'string')
            
            # Valida e converte o parâmetro
            is_valid, converted_value = self.validator.validate_param(value, param_type)
            if is_valid:
                params[name] = converted_value
            else:
                print(f"⚠️ Parâmetro inválido: {name}={value} (esperado: {param_type})")
                params[name] = value  # Mantém valor original se validação falhar
        
        return params
    
    def get_param_info(self) -> Dict:
        """
        Retorna informações sobre configurações de parâmetros
        """
        return {
            "configured_routes": len(self.route_param_configs),
            "configurations": self.route_param_configs,
            "supported_types": list(self.validator.type_patterns.keys())
        }