import time
import json
from typing import Dict, Any, Optional
from fastapi import Request
from datetime import datetime

from .base_middleware import BaseMiddleware

class LoggingMiddleware(BaseMiddleware):
    """
    Middleware de logging avançado
    Registra informações detalhadas sobre requisições e respostas
    """
    
    def __init__(self, 
                 log_level: str = "INFO",
                 log_requests: bool = True,
                 log_responses: bool = True,
                 log_performance: bool = True):
        super().__init__("logging", priority=1)  # Primeira execução
        self.log_level = log_level
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_performance = log_performance
        self.request_start_times = {}
    
    async def before_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Registra informações da requisição
        """
        request_id = id(request)
        start_time = time.time()
        self.request_start_times[request_id] = start_time
        
        if self.log_requests:
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "headers": dict(request.headers),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent")
            }
            
            print(f"📥 REQUEST [{request.method}] {request.url.path} - ID: {request_id}")
            if self.log_level == "DEBUG":
                print(f"📋 Request Details: {json.dumps(log_data, indent=2)}")
        
        return {
            "logging": {
                "request_id": request_id,
                "start_time": start_time,
                "timestamp": datetime.now().isoformat()
            }
        }
    
    async def after_request(self, request: Request, response_data: Dict) -> Optional[Dict[str, Any]]:
        """
        Registra informações da resposta e performance
        """
        request_id = id(request)
        end_time = time.time()
        
        # Calcula tempo de processamento
        start_time = self.request_start_times.pop(request_id, end_time)
        processing_time = (end_time - start_time) * 1000  # em millisegundos
        
        if self.log_responses:
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "processing_time_ms": round(processing_time, 2),
                "response_size": len(response_data.get("html", "")),
                "status": "success" if "html" in response_data else "error"
            }
            
            # Determina emoji baseado na performance
            if processing_time < 100:
                perf_emoji = "⚡"
            elif processing_time < 500:
                perf_emoji = "✅"
            elif processing_time < 1000:
                perf_emoji = "⚠️"
            else:
                perf_emoji = "🐌"
            
            print(f"📤 RESPONSE [{request.method}] {request.url.path} - {round(processing_time, 2)}ms {perf_emoji}")
            
            if self.log_level == "DEBUG":
                print(f"📊 Response Details: {json.dumps(log_data, indent=2)}")
        
        # Registra métricas de performance
        if self.log_performance:
            self._log_performance_metrics(request, processing_time)
        
        return {
            "performance": {
                "processing_time_ms": round(processing_time, 2),
                "end_time": end_time
            }
        }
    
    def _log_performance_metrics(self, request: Request, processing_time: float):
        """
        Registra métricas de performance
        """
        # Identifica requisições lentas
        if processing_time > 1000:  # > 1 segundo
            print(f"🐌 SLOW REQUEST: {request.url.path} took {round(processing_time, 2)}ms")
        
        # Métricas por endpoint (simplificado)
        endpoint = request.url.path
        if not hasattr(self, '_endpoint_metrics'):
            self._endpoint_metrics = {}
        
        if endpoint not in self._endpoint_metrics:
            self._endpoint_metrics[endpoint] = {
                "count": 0,
                "total_time": 0,
                "avg_time": 0,
                "min_time": float('inf'),
                "max_time": 0
            }
        
        metrics = self._endpoint_metrics[endpoint]
        metrics["count"] += 1
        metrics["total_time"] += processing_time
        metrics["avg_time"] = metrics["total_time"] / metrics["count"]
        metrics["min_time"] = min(metrics["min_time"], processing_time)
        metrics["max_time"] = max(metrics["max_time"], processing_time)
    
    def get_performance_report(self) -> Dict:
        """
        Retorna relatório de performance
        """
        if not hasattr(self, '_endpoint_metrics'):
            return {"message": "Nenhuma métrica coletada ainda"}
        
        return {
            "total_endpoints": len(self._endpoint_metrics),
            "metrics": {
                endpoint: {
                    "requests": data["count"],
                    "avg_response_time_ms": round(data["avg_time"], 2),
                    "min_response_time_ms": round(data["min_time"], 2),
                    "max_response_time_ms": round(data["max_time"], 2)
                }
                for endpoint, data in self._endpoint_metrics.items()
            }
        }