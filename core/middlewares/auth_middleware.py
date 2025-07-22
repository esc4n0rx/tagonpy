import jwt
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException
from datetime import datetime, timedelta

from .base_middleware import BaseMiddleware

class AuthMiddleware(BaseMiddleware):
    """
    Middleware de autenticação JWT
    Verifica tokens e injeta informações do usuário no contexto
    """
    
    def __init__(self, secret_key: str = "tagonpy-secret-key", algorithm: str = "HS256"):
        super().__init__("auth", priority=10)  # Alta prioridade
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.excluded_paths = ["/", "/login", "/register", "/public"]
    
    async def before_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Verifica autenticação antes da requisição
        """
        path = request.url.path
        
        # Pula autenticação para rotas excluídas
        if any(path.startswith(excluded) for excluded in self.excluded_paths):
            return {"auth": {"authenticated": False, "user": None}}
        
        # Extrai token do header Authorization
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return {"auth": {"authenticated": False, "user": None, "error": "Token não fornecido"}}
        
        token = auth_header.split(" ")[1]
        
        try:
            # Decodifica e valida o token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Verifica expiração
            if datetime.utcnow() > datetime.fromtimestamp(payload.get("exp", 0)):
                return {"auth": {"authenticated": False, "user": None, "error": "Token expirado"}}
            
            # Injeta dados do usuário no contexto
            user_data = {
                "id": payload.get("user_id"),
                "email": payload.get("email"),
                "name": payload.get("name"),
                "roles": payload.get("roles", [])
            }
            
            return {
                "auth": {
                    "authenticated": True,
                    "user": user_data,
                    "token": token
                }
            }
            
        except jwt.InvalidTokenError as e:
            return {"auth": {"authenticated": False, "user": None, "error": f"Token inválido: {str(e)}"}}
        except Exception as e:
            # CORREÇÃO: Captura erros de JWT não instalado
            print(f"⚠️ Erro no AuthMiddleware (JWT pode não estar instalado): {str(e)}")
            return {"auth": {"authenticated": False, "user": None, "error": "Auth middleware error"}}
    
    async def after_request(self, request: Request, response_data: Dict) -> Optional[Dict[str, Any]]:
        """
        Processa resposta após autenticação
        """
        # Pode adicionar headers de segurança, logs, etc.
        return {
            "security_headers": {
                "X-Frame-Options": "DENY",
                "X-Content-Type-Options": "nosniff"
            }
        }
    
    def generate_token(self, user_data: Dict, expires_in_hours: int = 24) -> str:
        """
        Gera um token JWT para um usuário
        
        Args:
            user_data: Dados do usuário
            expires_in_hours: Tempo de expiração em horas
            
        Returns:
            Token JWT como string
        """
        try:
            payload = {
                "user_id": user_data.get("id"),
                "email": user_data.get("email"),
                "name": user_data.get("name"),
                "roles": user_data.get("roles", []),
                "exp": datetime.utcnow() + timedelta(hours=expires_in_hours),
                "iat": datetime.utcnow()
            }
            
            return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        except Exception as e:
            print(f"⚠️ Erro ao gerar token JWT: {str(e)}")
            return ""
    
    def add_excluded_path(self, path: str):
        """Adiciona caminho à lista de exclusões"""
        if path not in self.excluded_paths:
            self.excluded_paths.append(path)
            print(f"🚫 Caminho '{path}' excluído da autenticação")